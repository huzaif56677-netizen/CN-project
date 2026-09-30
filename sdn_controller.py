#!/usr/bin/env python3
"""
Ryu Controller with REST API for Dynamic Path Rerouting
"""

import json
from webob import Response
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.app.wsgi import ControllerBase, WSGIApplication, route

REST_INSTANCE = 'rest_reroute_api_app'

class RerouteController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(RerouteController, self).__init__(req, link, data, **config)
        self.ryu_app = data[REST_INSTANCE]

    @route('reroute', '/reroute', methods=['POST'])
    def trigger_reroute(self, req, **kwargs):
        """REST endpoint called by UDP client when loss threshold is breached."""
        self.ryu_app.logger.info("[SDN REST] Triggering Dynamic Rerouting to Backup Path!")
        self.ryu_app.install_reroute_flows()
        return Response(content_type='application/json', body=json.dumps({"status": "SUCCESS", "path": "backup_s3"}))


class DynamicRerouteSDN(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(DynamicRerouteSDN, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(RerouteController, {REST_INSTANCE: self})
        self.datapaths = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.datapaths[datapath.id] = datapath

        self.logger.info(f"[SDN Controller] Switch connected: DPID={datapath.id}")

        # Install Table-Miss Flow entry (send unknown packets to controller port)
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, priority=0, match=match, actions=actions)

        # Baseline Primary Forwarding Rules (Priority 1)
        if datapath.id == 1: # s1: h1 (port 1) <-> s2 (port 2)
            self.add_flow(datapath, priority=1, match=parser.OFPMatch(in_port=1), actions=[parser.OFPActionOutput(2)])
            self.add_flow(datapath, priority=1, match=parser.OFPMatch(in_port=2), actions=[parser.OFPActionOutput(1)])
        elif datapath.id == 2: # s2: s1 (port 1) <-> s4 (port 2)
            self.add_flow(datapath, priority=1, match=parser.OFPMatch(in_port=1), actions=[parser.OFPActionOutput(2)])
            self.add_flow(datapath, priority=1, match=parser.OFPMatch(in_port=2), actions=[parser.OFPActionOutput(1)])
        elif datapath.id == 3: # s3: s1 (port 1) <-> s4 (port 2)
            self.add_flow(datapath, priority=1, match=parser.OFPMatch(in_port=1), actions=[parser.OFPActionOutput(2)])
            self.add_flow(datapath, priority=1, match=parser.OFPMatch(in_port=2), actions=[parser.OFPActionOutput(1)])
        elif datapath.id == 4: # s4: h2 (port 1) <-> s2 (port 2)
            self.add_flow(datapath, priority=1, match=parser.OFPMatch(in_port=1), actions=[parser.OFPActionOutput(2)])
            self.add_flow(datapath, priority=1, match=parser.OFPMatch(in_port=2), actions=[parser.OFPActionOutput(1)])

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath, 
            priority=priority, 
            match=match, 
            instructions=inst
        )
        datapath.send_msg(mod)

    def install_reroute_flows(self):
        """Installs higher-priority flows on s1 and s4 to force traffic via s3."""
        if 1 in self.datapaths and 4 in self.datapaths:
            dp1 = self.datapaths[1]
            dp4 = self.datapaths[4]
            p1 = dp1.ofproto_parser
            p4 = dp4.ofproto_parser

            # Update Switch 1: Forward h1 traffic to Port 3 (s3) with Priority 10
            self.add_flow(dp1, priority=10, match=p1.OFPMatch(in_port=1), actions=[p1.OFPActionOutput(3)])
            self.add_flow(dp1, priority=10, match=p1.OFPMatch(in_port=3), actions=[p1.OFPActionOutput(1)])

            # Update Switch 4: Forward h2 traffic to Port 3 (s3) with Priority 10
            self.add_flow(dp4, priority=10, match=p4.OFPMatch(in_port=1), actions=[p4.OFPActionOutput(3)])
            self.add_flow(dp4, priority=10, match=p4.OFPMatch(in_port=3), actions=[p4.OFPActionOutput(1)])

            self.logger.info("[SDN Controller] Active flows successfully overridden to Backup Path (s3)!")
