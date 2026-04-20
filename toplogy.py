from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
import os

class CustomTopo(Topo):
    def build(self):
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        self.addLink(h1, s1)
        self.addLink(h2, s2)
        self.addLink(h3, s3)
        self.addLink(s1, s2)
        self.addLink(s2, s3)

def setup_qos():
    # Apply QoS queues to all switch ports
    ports = ['s1-eth1', 's1-eth2', 's2-eth1', 's2-eth2', 's2-eth3', 's3-eth1', 's3-eth2']
    for port in ports:
        os.system(f"""
            ovs-vsctl set port {port} qos=@newqos -- \
            --id=@newqos create qos type=linux-htb \
            queues:100=@q100 queues:10=@q10 -- \
            --id=@q100 create queue other-config:min-rate=10000000 -- \
            --id=@q10 create queue other-config:max-rate=1000000
        """)

topos = {'customtopo': (lambda: CustomTopo())}

# Only runs if you execute topology.py directly, not via --custom flag
if __name__ == '__main__':
    topo = CustomTopo()
    net = Mininet(topo=topo, controller=RemoteController)
    net.start()
    setup_qos()
    from mininet.cli import CLI
    CLI(net)
    net.stop()