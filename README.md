## 📌 Distance Vector Router (Docker)

This project implements a **Distance Vector Routing Protocol** using Python and Docker.

### 🚀 Features

* Bellman-Ford based routing
* UDP routing updates (JSON)
* Split Horizon (loop prevention)
* Automatic kernel route updates
* Timeout-based failure recovery

---

### 🧱 Network Topology

Three routers connected in a triangle:

* Router A → (10.0.1.2, 10.0.3.2)
* Router B → (10.0.1.3, 10.0.2.2)
* Router C → (10.0.2.3, 10.0.3.3)

---

### ⚙️ Setup

```bash
chmod +x run_all.sh
./run_all.sh
```

---

### 🧪 Test Commands

```bash
# Routing tables
docker exec router_a ip route
docker exec router_b ip route
docker exec router_c ip route

# Connectivity
docker exec router_a ping -c 4 10.0.3.3

# Failure test
docker stop router_c
sleep 35
docker exec router_b ip route
```

---

### 📂 Tech Stack

* Python (socket, threading)
* Docker
* Linux networking (ip route)

---

### 📌 Notes

* No external Python dependencies required
* Uses UDP port 5000 for routing updates

---
