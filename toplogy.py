from mininet.topo import Topo
from mininet.link import TCLink

class CustomTopo(Topo):
    def build(self):
        # Add hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')

        # Add switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')

        # Create links with Bandwidth Limits (1 Mbps)
        # We use TCLink to enable traffic control features
        self.addLink(h1, s1, cls=TCLink, bw=10) # Host links can stay fast
        self.addLink(h2, s2, cls=TCLink, bw=10)
        self.addLink(h3, s3, cls=TCLink, bw=10)

        # Bottleneck links between switches
        self.addLink(s1, s2, cls=TCLink, bw=1)
        self.addLink(s2, s3, cls=TCLink, bw=1)

topos = {'customtopo': (lambda: CustomTopo())}
