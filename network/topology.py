#!/usr/bin/env python3
"""
Custom Diamond Topology for Mininet:
- h1 connects to s1
- s4 connects to h2
- Primary path: s1 <-> s2 <-> s4 (lossy link on s1-s2)
- Alternate path: s1 <-> s3 <-> s4 (loss-free link)
"""

import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import PRIMARY_PACKET_LOSS, ALTERNATE_PACKET_LOSS

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

        # Add switches (OpenFlow 1.3)
        s1 = self.addSwitch('s1', cls=OVSKernelSwitch, protocols='OpenFlow13')
        s2 = self.addSwitch('s2', cls=OVSKernelSwitch, protocols='OpenFlow13')
        s3 = self.addSwitch('s3', cls=OVSKernelSwitch, protocols='OpenFlow13')
        s4 = self.addSwitch('s4', cls=OVSKernelSwitch, protocols='OpenFlow13')

        # Connect hosts to perimeter switches
        # s1: port 1 connects to h1
        self.addLink(h1, s1, port2=1)
        # s4: port 1 connects to h2
        self.addLink(h2, s4, port2=1)

        # Primary Path: s1 <-> s2 <-> s4 (lossy link configured via TCLink)
        # s1: port 2 connects to s2 port 1
        self.addLink(s1, s2, port1=2, port2=1, loss=PRIMARY_PACKET_LOSS)
        # s2: port 2 connects to s4 port 2
        self.addLink(s2, s4, port1=2, port2=2)

        # Alternate Path: s1 <-> s3 <-> s4 (clean link, 0% loss)
        # s1: port 3 connects to s3 port 1
        self.addLink(s1, s3, port1=3, port2=1, loss=ALTERNATE_PACKET_LOSS)
        # s3: port 2 connects to s4 port 3
        self.addLink(s3, s4, port1=2, port2=3)


topos = {'diamond': (lambda: DiamondTopo())}


import re
import subprocess


def cleanup_stale_network_state():
    """Removes leftover veth interfaces and OVS bridges from previous runs without killing Ryu."""
    try:
        # Delete stale OVS bridges
        for br in ['s1', 's2', 's3', 's4']:
            subprocess.run(['ovs-vsctl', '--if-exists', 'del-br', br], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Delete stale veth link pairs
        out = subprocess.check_output(['ip', 'link', 'show'], stderr=subprocess.DEVNULL).decode('utf-8')
        for intf in set(re.findall(r'([a-zA-Z0-9_]+-eth\d+)', out)):
            subprocess.run(['ip', 'link', 'delete', intf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def run_mininet():
    setLogLevel('info')
    cleanup_stale_network_state()
    topo = DiamondTopo()
    info(f"*** Starting Diamond Topology (Primary loss={PRIMARY_PACKET_LOSS}%, Alternate loss={ALTERNATE_PACKET_LOSS}%)\n")
    net = Mininet(
        topo=topo,
        link=TCLink,
        controller=RemoteController,
        autoSetMacs=True,
        autoStaticArp=True
    )
    net.start()

    h1 = net.get('h1')
    h2 = net.get('h2')

    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    h1.cmd(f'cd {project_dir}')
    h2.cmd(f'cd {project_dir}')

    # Create FIFO for non-root trigger from Web Dashboard
    fifo_path = '/tmp/mininet_h1.fifo'
    if os.path.exists(fifo_path):
        try:
            os.remove(fifo_path)
        except Exception:
            pass
    try:
        os.mkfifo(fifo_path)
        os.chmod(fifo_path, 0o666)
        # Background daemon inside h1 reading lines from FIFO and executing them
        h1.cmd('nohup bash -c \'while true; do read -r line < /tmp/mininet_h1.fifo; if [ -n "$line" ]; then eval "$line" >> /tmp/client_h1.log 2>&1; fi; done\' > /tmp/h1_fifo.log 2>&1 &')
        info("*** FIFO command trigger active on /tmp/mininet_h1.fifo (Dashboard Start Transmission enabled)\n")
    except Exception as e:
        info(f"*** Warning setting up FIFO: {e}\n")

    # Record host PIDs for status tracking
    try:
        with open('/tmp/mininet_h1.pid', 'w') as f:
            f.write(str(h1.pid))
        with open('/tmp/mininet_h2.pid', 'w') as f:
            f.write(str(h2.pid))
    except Exception:
        pass

    info("*** Auto-starting UDP Server on h2 (10.0.0.2:5000)...\n")
    h2.cmd('nohup python3 -u udp/server.py > /tmp/udp_server_h2.log 2>&1 &')
    info("*** Mininet network running. Ready for transmission!\n")
    info("*** Two ways to run the transmission:\n")
    info("***   1. Click 'Start Transmission' on the React Dashboard (http://localhost:5173)\n")
    info("***   2. Or in this Mininet CLI: mininet> h1 python3 udp/client.py\n\n")

    CLI(net)

    info("*** Stopping Mininet network...\n")
    for cleanup_file in ['/tmp/mininet_h1.pid', '/tmp/mininet_h2.pid', '/tmp/mininet_h1.fifo']:
        if os.path.exists(cleanup_file):
            try:
                os.remove(cleanup_file)
            except Exception:
                pass
    net.stop()


if __name__ == '__main__':
    run_mininet()
