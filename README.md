# SDN QoS Priority Controller

## Overview

This project implements a simple SDN controller using Ryu that prioritizes different types of network traffic. The controller gives higher priority to UDP traffic compared to TCP using OpenFlow rules and OVS queues.

---

## Objective

- Identify traffic types (UDP, TCP, etc.)
- Assign higher priority to UDP
- Assign lower priority to TCP
- Install flow rules dynamically using SDN
- Enforce traffic shaping using OVS QoS queues

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

### Switch Port Map

| Switch | Port | Connected to |
|--------|------|--------------|
| s1 | s1-eth1 | h1 |
| s1 | s1-eth2 | s2 |
| s2 | s2-eth1 | s1 |
| s2 | s2-eth2 | h2 |
| s2 | s2-eth3 | s3 |
| s3 | s3-eth1 | s2 |
| s3 | s3-eth2 | h3 |

---

## How It Works

1. When a packet arrives at a switch with no existing rule, it is sent to the controller.
2. The controller inspects the protocol:
   - **UDP** → high priority (100) → queue 100 (high bandwidth)
   - **TCP** → low priority (10) → queue 10 (limited bandwidth)
3. A flow rule with `OFPActionSetQueue` is installed in the switch.
4. Future matching packets are handled directly by the switch using the assigned queue.

> **Note:** OpenFlow priority alone only controls which rule matches first — it does not limit bandwidth. OVS queues are required to actually enforce traffic shaping.

---

## Flow Rules

| Traffic | Protocol | Priority | Queue |
|---------|----------|----------|-------|
| UDP     | 17       | 100      | 100   |
| TCP     | 6        | 10       | 10    |
| Others  | Any      | 1        | —     |
| ARP     | —        | Flood    | —     |

---

## Steps to Run

### Terminal 1 — Start the Controller

```bash
cd ~/CN
source ryu-env/bin/activate
ryu-manager qos.py
```

### Terminal 2 — Start Mininet

```bash
sudo mn --controller=remote --custom topology.py --topo=customtopo --switch=ovsk,protocols=OpenFlow13
```

### Terminal 3 — Set Up OVS QoS Queues

Run this once after Mininet starts:

```bash
for PORT in s1-eth1 s1-eth2 s2-eth1 s2-eth2 s2-eth3 s3-eth1 s3-eth2; do
  sudo ovs-vsctl set port $PORT qos=@newqos -- \
    --id=@newqos create qos type=linux-htb \
    queues:100=@q100 queues:10=@q10 -- \
    --id=@q100 create queue other-config:min-rate=10000000 -- \
    --id=@q10 create queue other-config:max-rate=1000000
done
```

| Queue | Rate | Used by |
|-------|------|---------|
| 100 | min 10 Mbps | UDP |
| 10 | max 1 Mbps | TCP |

### Terminal 2 — Test Connectivity

```bash
pingall
```

---

## QoS Latency Experiment

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

> Ryu QoS controller is running — UDP gets priority 100 (queue 100), TCP gets priority 10 (queue 10).

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
| 1 — UDP alone | 0.037 | 0.084 | 1.019 | 0.116 |
| 2 — QoS ON, competing | 0.028 | 0.127 | 3.021 | 0.328 |
| 3 — QoS OFF, competing | 0.030 | 0.088 | 1.255 | 0.146 |

### What to Look For

- **`avg`** — Typical latency; your headline number
- **`max`** — Worst case during congestion; shows QoS impact most clearly
- **`mdev`** — Stability; how much latency varied (lower is better)

### Analysis

The results from the initial run (without OVS queues) showed Situation 2 performing worse than Situation 3, which is the opposite of expected. This is because:

- **OpenFlow priority alone does not shape bandwidth** — it only controls rule matching order, not actual traffic rates.
- **ICMP (ping) gets priority 1** — the measurement traffic itself was the lowest priority on the network.
- **Mininet runs on one machine** — controller round-trips during flow rule installation added latency spikes in Situation 2.

The fix is to configure OVS queues (see Terminal 3 setup above) and use `OFPActionSetQueue` in the controller so traffic is actually rate-limited at the switch level.

> **Expected result after fix:** `avg` and `max` should stay low in Situation 2 but spike noticeably in Situation 3 — proving the priority rules and queues are working.

---

## Common Errors and Fixes

| Error | Fix |
|-------|-----|
| `listener bind failed: Address already in use` | Run `h2 pkill iperf` then retry |
| `bash: kill: %1: no such job` | Process already stopped — ignore and continue |
| QoS ON performs worse than QoS OFF | OVS queues not configured — run the Terminal 3 queue setup script |