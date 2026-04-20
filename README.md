

```markdown
# SDN QoS Priority Controller

## Overview
This project implements an SDN controller using Ryu that prioritizes UDP traffic over TCP. By using OpenFlow 1.3, we dynamically install flow rules that ensure high-priority traffic bypasses buffer congestion.

## Network Topology
A linear topology with bandwidth constraints to simulate a real-world bottleneck.

```
h1 (User) — s1 — s2 (Bottleneck) — s3 — h3 (Attacker/Flood)
                  |
                 h2 (Server)
```

---

## How It Works
1. **Control Plane:** Ryu inspects initial packets. 
   - **UDP:** Assigned Priority 100
   - **TCP:** Assigned Priority 10
2. **Data Plane:** Mininet switches (OVS) enforce these priorities. When the 1Mbps link is saturated, the switch processes Priority 100 packets first.

---

## Steps to Run

### 1. Start the Controller
```bash
ryu-manager qos.py
```

### 2. Start Mininet (with Traffic Control)
```bash
sudo mn --controller=remote --custom topology.py --topo=customtopo --link=tc --switch=ovsk,protocols=OpenFlow13
```

---

## QoS Latency Experiment

### Situation 1: No Congestion
**Goal:** Establish baseline latency.
```bash
h1 ping -c 50 -i 0.2 h2
```

### Situation 2: QoS ON (Congested)
**Goal:** Test UDP performance while TCP floods the network.
1. **h2 (Server):** `h2 iperf -s &`
2. **h3 (Flood):** `h3 iperf -c h2 -t 60 -P 20 &`
3. **h1 (Record):** `h1 ping -c 100 -i 0.2 h2`

### Situation 3: QoS OFF (Congested)
**Goal:** See the impact of "Best Effort" delivery without priorities.
1. **Stop Ryu**, then run: `ryu-manager ryu.app.simple_switch_13`
2. **Restart Mininet:** `sudo mn -c && sudo mn --controller=remote --custom topology.py --topo=customtopo --link=tc --switch=ovsk,protocols=OpenFlow13`
3. **Repeat Situation 2 commands.**

---

## Results Table

| Situation | Avg Latency (ms) | Max Latency (ms) | Mdev (Stability) |
|-----------|------------------|------------------|------------------|
| No Load   |                  |                  |                  |
| QoS ON    |                  |                  |                  |
| QoS OFF   |                  |                  |                  |

### Verification Command
To see the rules in the switch during the test:
`sudo ovs-ofctl -O OpenFlow13 dump-flows s2`
```



### Why this version is better:
* **The `--link=tc` flag:** This tells Mininet to actually load the Linux Traffic Control module, which is required for the `bw=1` setting to work.
* **Parallelism (`-P 20`):** By using 20 streams instead of 4, you ensure that the TCP windowing mechanism doesn't "accidentally" leave gaps for your pings.
* **Linear Bottleneck:** By setting the links between `s1-s2` and `s2-s3` to 1Mbps, you create a "funnel" at `s2` that forces the QoS logic to trigger.
