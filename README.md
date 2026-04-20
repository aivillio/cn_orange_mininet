That command is a great "sanity check" to prove that the network is actually under stress. I've integrated it into the **Situation 2** and **Situation 3** flows in the README so you can verify the port congestion in real-time.

---

## 📝 Updated `README.md`

```markdown
# SDN QoS Priority Controller

## Overview
This project implements an SDN controller using Ryu that prioritizes UDP traffic over TCP. By using OpenFlow 1.3, we dynamically install flow rules that ensure high-priority traffic bypasses buffer congestion.

## Network Topology
A linear topology with tight bandwidth constraints (0.5 Mbps) and a limited buffer (queue size 10) to force observable congestion.

```
h1 (Testing) — s1 — s2 (Bottleneck) — s3 — h3 (Flood Source)
                  |
                 h2 (Target Server)
```

---

## How It Works
1. **Control Plane:** Ryu inspects initial packets via `PacketIn`. 
   - **UDP:** Priority 100
   - **TCP:** Priority 10
2. **Data Plane:** Mininet switches (OVS) enforce these priorities. Because the buffer is limited to 10 packets, Priority 100 packets are moved to the front of the queue, while lower priority packets wait or are dropped.

---

## Steps to Run

### 1. Start the Controller
```bash
ryu-manager qos.py
```

### 2. Start Mininet
```bash
sudo mn --controller=remote --custom topology.py --topo=customtopo --link=tc --switch=ovsk,protocols=OpenFlow13
```

---

## QoS Latency Experiment

### Situation 1: No Congestion (Baseline)
```bash
h1 ping -c 50 -i 0.2 h2
```

### Situation 2: QoS ON (Congested)
1. **h2 (Server):** `h2 iperf -s &`
2. **h3 (Flood):** `h3 iperf -c h2 -t 60 -P 20 &`
3. **Verify Congestion (External Terminal):**
   Run this to see if the switch ports are dropping or queuing packets:
   ```bash
   sudo ovs-ofctl -O OpenFlow13 dump-ports-desc s2
   ```
4. **h1 (Record):** `h1 ping -c 100 -i 0.2 h2`

### Situation 3: QoS OFF (Congested)
1. **Switch Controller:** Stop `qos.py` and run `ryu-manager ryu.app.simple_switch_13`.
2. **Restart Mininet:** `sudo mn -c && sudo mn --controller=remote --custom topology.py --topo=customtopo --link=tc --switch=ovsk,protocols=OpenFlow13`
3. **Repeat Situation 2 steps:** Run the `iperf` flood and record the `h1` ping results. Compare the `avg` and `max` latency.

---

## Results Table

| Situation | Avg Latency (ms) | Max Latency (ms) | Mdev (Stability) |
|-----------|------------------|------------------|------------------|
| No Load   |                  |                  |                  |
| QoS ON    |                  |                  |                  |
| QoS OFF   |                  |                  |                  |

### Verification of Flow Rules
To verify that the priorities (100 vs 10) are active in the switch hardware:
```bash
sudo ovs-ofctl -O OpenFlow13 dump-flows s2
```
```

---

### 💡 Why we added that command
When you run `dump-ports-desc`, you are looking at the hardware-level statistics of the virtual switch. 
* If the `tx_packets` and `rx_packets` are moving but you see no latency change, your pipe is still too big.
* With the **0.5 Mbps** limit we set in the topology, that command should show the switch working at its limit, making your QoS logic the "hero" that saves the UDP packets from the queue!# SDN QoS Priority Controller

## Overview

This project implements a simple SDN controller using Ryu that prioritizes different types of network traffic. The controller gives higher priority to UDP traffic compared to TCP using OpenFlow rules.

---

## Objective

- Identify traffic types (UDP, TCP, etc.)
- Assign higher priority to UDP
- Assign lower priority to TCP
- Install flow rules dynamically using SDN

---

## Tools Used

| Tool | Version |
|------|---------|
| Python | 3.10 |
| Ryu Controller | — |
| Mininet | — |
| Open vSwitch | — |
| OpenFlow | 1.3 |

---

## Network Topology

A custom topology is created using the Mininet Python API, consisting of:

- **3 Hosts:** h1, h2, h3
- **3 Switches:** s1, s2, s3

```
h1 — s1 — s2 — s3 — h3
          |
         h2
```

---

## How It Works

1. When a packet arrives at a switch with no existing rule, it is sent to the controller.
2. The controller inspects the protocol:
   - **UDP** → high priority (100)
   - **TCP** → low priority (10)
3. A flow rule is installed in the switch based on the protocol.
4. Future matching packets are handled directly by the switch.

---

## Flow Rules

| Traffic | Protocol | Priority |
|---------|----------|----------|
| UDP     | 17       | 100      |
| TCP     | 6        | 10       |
| Others  | Any      | 1        |
| ARP     | —        | Flood    |

---

## Steps to Run

### 1. Activate Virtual Environment

```bash
cd ~/CN
source ryu-env/bin/activate
```

### 2. Start the Controller

```bash
python -m ryu.cmd.manager qos.py
```

### 3. Run Mininet *(new terminal)*

```bash
sudo mn --custom topology.py --topo customtopo --controller=remote
```

### 4. Test Connectivity

```bash
pingall
```

---

## QoS Latency Experiment

### Terminal Setup

**Terminal 1 — Start Mininet**

```bash
sudo mn --controller=remote --custom topology.py --topo=customtopo --switch=ovsk,protocols=OpenFlow13
```

| Flag | Meaning |
|------|---------|
| `--controller=remote` | Connect to your external Ryu controller |
| `--custom topology.py` | Load your custom topology file |
| `--topo=customtopo` | Use the topology name defined in `topos = {'customtopo': ...}` |
| `--switch=ovsk` | Use Open vSwitch kernel mode |
| `protocols=OpenFlow13` | Force OpenFlow 1.3 to match your controller |

**Terminal 2 — Start QoS Controller**

```bash
ryu-manager qos.py
```

---

## Experiment Situations

### Situation 1 — UDP Alone (No Contention)

```bash
# Warmup — lets flow rules install, not recorded
h1 ping -c 10 -i 0.2 h2

# Start UDP server on h2
h2 iperf -s -u &

# Record
h1 ping -c 100 -i 0.2 h2
```

| Flag | Meaning |
|------|---------|
| `-c 10` / `-c 100` | Send exactly 10 or 100 packets then stop |
| `-i 0.2` | Wait 0.2s between each ping (faster than default 1s) |
| `-s` | Server mode — h2 listens for incoming traffic |
| `-u` | Expect UDP traffic |
| `&` | Run in background so you can keep typing |

**Cleanup:**

```bash
h2 pkill iperf
```

---

### Situation 2 — UDP + TCP Competing, QoS ON

> Ryu QoS controller is running — UDP gets priority 100, TCP gets priority 10.

```bash
# Start TCP server on h2
h2 iperf -s &

# Flood h2 with TCP from h3 (background)
h3 iperf -c h2 -t 60 -i 1 -P 4 &

# Warmup
h1 ping -c 10 -i 0.2 h2

# Record
h1 ping -c 100 -i 0.2 h2
```

| Flag | Meaning |
|------|---------|
| `-s` | TCP server mode on h2 |
| `-c h2` | Client mode — h3 connects and floods h2 with TCP |
| `-t 60` | Keep flooding for 60 seconds |
| `-i 1` | Print stats every second to confirm active sending |
| `-P 4` | Run 4 parallel TCP streams for heavier congestion |
| `&` | Background so ping can run simultaneously |

**Cleanup:**

```bash
h2 pkill iperf
h3 pkill iperf
```

---

### Situation 3 — UDP + TCP Competing, QoS OFF

**Step 1 — Exit and clean up Mininet**

```bash
exit
sudo mn -c
```

| Command | Meaning |
|---------|---------|
| `exit` | Leave the Mininet CLI |
| `sudo mn -c` | Wipe all Mininet state — interfaces, switches, links |

**Step 2 — Stop Ryu QoS controller**

Press `Ctrl+C` in Terminal 2, then start the plain switch:

```bash
ryu-manager ryu.app.simple_switch_13
```

> `ryu.app.simple_switch_13` is a built-in plain learning switch — no QoS, no priorities.

**Step 3 — Restart Mininet**

```bash
sudo mn --controller=remote --custom topology.py --topo=customtopo --switch=ovsk,protocols=OpenFlow13
```

**Step 4 — Run identical commands to Situation 2**

```bash
h2 iperf -s &
h3 iperf -c h2 -t 60 -i 1 -P 4 &
h1 ping -c 10 -i 0.2 h2
h1 ping -c 100 -i 0.2 h2
```

---

## Results

| Situation | min (ms) | avg (ms) | max (ms) | mdev (ms) |
|-----------|----------|----------|----------|-----------|
| 1 — UDP alone | | | | |
| 2 — QoS ON, competing | | | | |
| 3 — QoS OFF, competing | | | | |

### What to Look For

- **`avg`** — Typical latency; your headline number
- **`max`** — Worst case during congestion; shows QoS impact most clearly
- **`mdev`** — Stability; how much latency varied (lower is better)

> **Expected result:** `avg` and `max` should stay low in Situation 2 but spike noticeably in Situation 3 — proving the priority rules are working.

---

## Common Errors and Fixes

| Error | Fix |
|-------|-----|
| `listener bind failed: Address already in use` | Run `h2 pkill iperf` then retry |
| `bash: kill: %1: no such job` | Process already stopped — ignore and continue |
