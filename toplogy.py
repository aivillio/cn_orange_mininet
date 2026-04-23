from mininet.topo import Topo
from mininet.link import TCLink

class CustomTopo(Topo):
    def build(self):
        # --- Add Hosts ---
        # h1 will be our "Testing Host" (Pings)
        # h2 will be our "Server" (iperf -s)
        # h3 will be our "Congestion Source" (iperf -c)
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')

        # --- Add Switches ---
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        
        # --- Create Links ---
        
       
        # These are kept fast (10 Mbps) so the bottleneck is between switches, not at the host.
        self.addLink(h1, s1, cls=TCLink, bw=10)
        self.addLink(h2, s2, cls=TCLink, bw=10)
        self.addLink(h3, s3, cls=TCLink, bw=10)

        # 2. Switch-to-Switch Bottleneck Links
       
        self.addLink(s1, s2, cls=TCLink, bw=0.5, delay='5ms', max_queue_size=10)
        self.addLink(s2, s3, cls=TCLink, bw=0.5, delay='5ms', max_queue_size=10)

# This dictionary allows  a call  to the topo using '--topo customtopo'
topos = {'customtopo': (lambda: CustomTopo())}
