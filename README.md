# SDN QoS Priority Controller

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
h1 (Testing) — s1 — s2 (Bottleneck) — s3 — h3 (Flood Source)
                         |
                        h2 (Target Server)
```

> **Note:** A linear topology with tight bandwidth constraints (0.5 Mbps) and a limited buffer (queue size 10) is used to force observable congestion.

---

## How It Works

1. When a packet arrives at a switch with no existing rule, it is sent to the controller.
2. The controller inspects the protocol:
   - **UDP** → high priority (100)
   - **TCP** → low priority (10)
3. A flow rule is installed in the switch based on the protocol.
4. Future matching packets are handled directly by the switch.

Because the buffer is limited to 10 packets, Priority 100 packets are moved to the front of the queue, while lower priority packets wait or are dropped.

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
ryu-manager qos.py
```

### 3. Run Mininet *(new terminal)*

```bash
sudo mn --controller=remote --custom topology.py --topo=customtopo --link=tc --switch=ovsk,protocols=OpenFlow13
```

| Flag | Meaning |
|------|---------|
| `--controller=remote` | Connect to your external Ryu controller |
| `--custom topology.py` | Load your custom topology file |
| `--topo=customtopo` | Use the topology name defined in `topos = {'customtopo': ...}` |
| `--link=tc` | Enable traffic control (bandwidth limits) |
| `--switch=ovsk` | Use Open vSwitch kernel mode |
| `protocols=OpenFlow13` | Force OpenFlow 1.3 to match your controller |

### 4. Test Connectivity

```bash
pingall
```

---

## QoS Latency Experiment

### Situation 1 — No Congestion (Baseline)

```bash
h1 ping -c 50 -i 0.2 h2
```

---

### Situation 2 — QoS ON (Congested)

> Ryu QoS controller is running — UDP gets priority 100, TCP gets priority 10.

**Step 1 — Start TCP server on h2:**
```bash
h2 iperf -s &
```

**Step 2 — Flood h2 with TCP from h3:**
```bash
h3 iperf -c h2 -t 60 -P 20 &
```

**Step 3 — Verify Congestion (External Terminal):**

Run this to see if the switch ports are dropping or queuing packets:
```bash
sudo ovs-ofctl -O OpenFlow13 dump-ports-desc s2
```

> - If `tx_packets` and `rx_packets` are moving but you see no latency change, your pipe is still too big.
> - With the **0.5 Mbps** limit set in the topology, this command should show the switch working at its limit, making the QoS logic the "hero" that saves UDP packets from the queue.

**Step 4 — Record ping from h1:**
```bash
h1 ping -c 100 -i 0.2 h2
```

**Cleanup:**
```bash
h2 pkill iperf
h3 pkill iperf
```

---

### Situation 3 — QoS OFF (Congested)

**Step 1 — Exit and clean up Mininet:**
```bash
exit
sudo mn -c
```

| Command | Meaning |
|---------|---------|
| `exit` | Leave the Mininet CLI |
| `sudo mn -c` | Wipe all Mininet state — interfaces, switches, links |

**Step 2 — Stop Ryu QoS controller:**

Press `Ctrl+C` in the controller terminal, then start the plain switch:

```bash
ryu-manager ryu.app.simple_switch_13
```

> `ryu.app.simple_switch_13` is a built-in plain learning switch — no QoS, no priorities.

**Step 3 — Restart Mininet:**
```bash
sudo mn --controller=remote --custom topology.py --topo=customtopo --link=tc --switch=ovsk,protocols=OpenFlow13
```

**Step 4 — Repeat Situation 2 steps:**
```bash
h2 iperf -s &
h3 iperf -c h2 -t 60 -P 20 &
h1 ping -c 100 -i 0.2 h2
```

Compare the `avg` and `max` latency against Situation 2.

---

## Results

| Situation | min (ms) | avg (ms) | max (ms) | mdev (ms) |
|-----------|----------|----------|----------|-----------|
| 1 — No Load | | | | |
| 2 — QoS ON, competing | | | | |
| 3 — QoS OFF, competing | | | | |

### What to Look For

- **`avg`** — Typical latency; your headline number
- **`max`** — Worst case during congestion; shows QoS impact most clearly
- **`mdev`** — Stability; how much latency varied (lower is better)

> **Expected result:** `avg` and `max` should stay low in Situation 2 but spike noticeably in Situation 3 — proving the priority rules are working.

---

## Verification Commands

### Check Active Flow Rules

To verify that the priorities (100 vs 10) are active in the switch hardware:
```bash
sudo ovs-ofctl -O OpenFlow13 dump-flows s2
```

### Check Port Congestion (Real-Time)
```bash
sudo ovs-ofctl -O OpenFlow13 dump-ports-desc s2
```

---

## Common Errors and Fixes

| Error | Fix |
|-------|-----|
| `listener bind failed: Address already in use` | Run `h2 pkill iperf` then retry |
| `bash: kill: %1: no such job` | Process already stopped — ignore and continue |
