#!/usr/bin/env python3
"""
Ryu OpenFlow 1.3 Controller with REST API for Dynamic Path Rerouting.
Controls switches s1, s2, s3, s4 in the diamond topology.
"""

import json
import time
from webob import Response
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.app.wsgi import ControllerBase, WSGIApplication, route

REST_INSTANCE = 'sdn_reroute_api_app'


class SDNRestController(ControllerBase):
    """REST API endpoints for SDN controller dynamic rerouting and monitoring."""

    def __init__(self, req, link, data, **config):
        super(SDNRestController, self).__init__(req, link, data, **config)
        self.ryu_app = data[REST_INSTANCE]

    @route('sdn', '/status', methods=['GET'])
    def get_status(self, req, **kwargs):
        """Returns connected switches and currently active forwarding path."""
        data = {
            "active_path": self.ryu_app.active_path,
            "connected_switches": list(self.ryu_app.datapaths.keys()),
            "last_reroute_time": self.ryu_app.last_reroute_time,
            "reroute_count": self.ryu_app.reroute_count
        }
        return Response(content_type='application/json', body=json.dumps(data))

    @route('sdn', '/reroute', methods=['POST'])
    def trigger_reroute(self, req, **kwargs):
        """Triggers dynamic rerouting from Primary Path (s2) to Alternate Path (s3)."""
        t_received = time.time()
        self.ryu_app.logger.info("[SDN Controller] Dynamic Reroute requested! Switching to Alternate Path (s3)...")
        success = self.ryu_app.install_alternate_path_flows()
        t_applied = time.time()

        res = {
            "status": "SUCCESS" if success else "FAILED",
            "active_path": "alternate_s3",
            "applied_timestamp": t_applied,
            "switch_time_ms": (t_applied - t_received) * 1000
        }
        return Response(json=res)

    @route('sdn', '/reset', methods=['POST'])
    def trigger_reset(self, req, **kwargs):
        """Resets forwarding to Primary Path (s2)."""
        self.ryu_app.logger.info("[SDN Controller] Reset requested! Reverting to Primary Path (s2)...")
        self.ryu_app.remove_alternate_path_flows()
        res = {
            "status": "SUCCESS",
            "active_path": "primary_s2"
        }
        return Response(json=res)


class DynamicRerouteSDN(app_manager.RyuApp):
    """Main Ryu SDN Application managing Diamond Topology OpenFlow 1.3 rules."""
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(DynamicRerouteSDN, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(SDNRestController, {REST_INSTANCE: self})
        self.datapaths = {}
        self.active_path = "primary_s2"
        self.last_reroute_time = None
        self.reroute_count = 0

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handles switch connection and installs baseline primary flows."""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        self.datapaths[datapath.id] = datapath

        self.logger.info(f"[SDN Controller] Switch connected: DPID={datapath.id}")

        # Table-Miss Flow Entry (priority 0): send unhandled packets to controller
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, priority=0, match=match, actions=actions)

        # Baseline Forwarding Rules (Priority 1):
        # s1: port 1 (h1) <-> port 2 (s2)
        if datapath.id == 1:
            self.add_flow(datapath, priority=1, match=parser.OFPMatch(in_port=1), actions=[parser.OFPActionOutput(2)])
            self.add_flow(datapath, priority=1, match=parser.OFPMatch(in_port=2), actions=[parser.OFPActionOutput(1)])
        # s2: port 1 (s1) <-> port 2 (s4)
        elif datapath.id == 2:
            self.add_flow(datapath, priority=1, match=parser.OFPMatch(in_port=1), actions=[parser.OFPActionOutput(2)])
            self.add_flow(datapath, priority=1, match=parser.OFPMatch(in_port=2), actions=[parser.OFPActionOutput(1)])
        # s3: port 1 (s1) <-> port 2 (s4) [Ready in standby]
        elif datapath.id == 3:
            self.add_flow(datapath, priority=1, match=parser.OFPMatch(in_port=1), actions=[parser.OFPActionOutput(2)])
            self.add_flow(datapath, priority=1, match=parser.OFPMatch(in_port=2), actions=[parser.OFPActionOutput(1)])
        # s4: port 1 (h2) <-> port 2 (s2)
        elif datapath.id == 4:
            self.add_flow(datapath, priority=1, match=parser.OFPMatch(in_port=1), actions=[parser.OFPActionOutput(2)])
            self.add_flow(datapath, priority=1, match=parser.OFPMatch(in_port=2), actions=[parser.OFPActionOutput(1)])

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """Helper to add an OpenFlow entry."""
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

    def delete_flow_by_priority(self, datapath, priority):
        """Helper to delete flows with a specific priority."""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        mod = parser.OFPFlowMod(
            datapath=datapath,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
            priority=priority,
            match=parser.OFPMatch()
        )
        datapath.send_msg(mod)

    def install_alternate_path_flows(self):
        """
        Installs higher-priority flows (priority 10) on s1 and s4
        to instantly divert traffic to alternate path through s3 (port 3).
        """
        if 1 not in self.datapaths or 4 not in self.datapaths:
            self.logger.warning("[SDN Controller] Cannot reroute: switches s1 or s4 not yet connected.")
            return False

        dp1 = self.datapaths[1]
        dp4 = self.datapaths[4]
        p1 = dp1.ofproto_parser
        p4 = dp4.ofproto_parser

        # Switch 1: Forward h1 traffic (port 1) to s3 (port 3) and vice-versa
        self.add_flow(dp1, priority=10, match=p1.OFPMatch(in_port=1), actions=[p1.OFPActionOutput(3)])
        self.add_flow(dp1, priority=10, match=p1.OFPMatch(in_port=3), actions=[p1.OFPActionOutput(1)])

        # Switch 4: Forward h2 traffic (port 1) to s3 (port 3) and vice-versa
        self.add_flow(dp4, priority=10, match=p4.OFPMatch(in_port=1), actions=[p4.OFPActionOutput(3)])
        self.add_flow(dp4, priority=10, match=p4.OFPMatch(in_port=3), actions=[p4.OFPActionOutput(1)])

        self.active_path = "alternate_s3"
        self.last_reroute_time = time.time()
        self.reroute_count += 1
        self.logger.info("[SDN Controller] Active flows overridden to Alternate Path (s3) at priority 10!")
        return True

    def remove_alternate_path_flows(self):
        """Removes priority 10 flows from s1 and s4, falling back to priority 1 (s2)."""
        if 1 in self.datapaths:
            self.delete_flow_by_priority(self.datapaths[1], priority=10)
        if 4 in self.datapaths:
            self.delete_flow_by_priority(self.datapaths[4], priority=10)

        self.active_path = "primary_s2"
        self.logger.info("[SDN Controller] Reverted to Primary Path (s2)!")
        return True
