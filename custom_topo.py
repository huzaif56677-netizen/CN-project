#!/usr/bin/env python3
"""
Custom Diamond Topology for Packet Loss Detection and Recovery
"""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

class DiamondTopo(Topo):
    def build(self):
        # Add hosts
        h1 = self.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
        h2 = self.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')

        # Add switches
        s1 = self.addSwitch('s1', cls=OVSKernelSwitch, protocols='OpenFlow13')
        s2 = self.addSwitch('s2', cls=OVSKernelSwitch, protocols='OpenFlow13')
        s3 = self.addSwitch('s3', cls=OVSKernelSwitch, protocols='OpenFlow13')
        s4 = self.addSwitch('s4', cls=OVSKernelSwitch, protocols='OpenFlow13')

        # Connect hosts to switches
        self.addLink(h1, s1)
        self.addLink(s4, h2)

        # Primary Path (s1 <-> s2 <-> s4) with 20% packet loss
        self.addLink(s1, s2, port1=2, port2=1, loss=20)
        self.addLink(s2, s4, port1=2, port2=2)

        # Backup Path (s1 <-> s3 <-> s4) with 0% loss
        self.addLink(s1, s3, port1=3, port2=1, loss=0)
        self.addLink(s3, s4, port1=2, port2=3)

topos = {'diamond': (lambda: DiamondTopo())}

if __name__ == '__main__':
    setLogLevel('info')
    topo = DiamondTopo()
    # autoSetMacs and autoStaticArp prevent ARP drops on lossy links
    net = Mininet(
        topo=topo, 
        link=TCLink, 
        controller=RemoteController,
        autoSetMacs=True,
        autoStaticArp=True
    )
    net.start()
    info("*** Mininet network running. Type exit to stop.\n")
    CLI(net)
    net.stop()
