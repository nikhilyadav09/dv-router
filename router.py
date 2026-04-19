import socket
import json
import threading
import time
import os

# ENABLE FORWARDING
os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")

MY_IP = os.getenv("MY_IP", "127.0.0.1")
NEIGHBORS = os.getenv("NEIGHBORS", "").split(",")
PORT = 5000

MY_SUBNET = os.getenv("MY_SUBNET", "10.0.1.0/24")

# [distance, next_hop, last_updated, is_direct]
routing_table = {
    MY_SUBNET: [0, "0.0.0.0", time.time(), True]
}

# ✅ Add direct neighbors
def add_direct_routes():
    for neighbor in NEIGHBORS:
        if neighbor:
            subnet = neighbor.rsplit(".", 1)[0] + ".0/24"
            routing_table[subnet] = [1, neighbor, time.time(), True]

def is_direct_neighbor(ip):
    return ip in NEIGHBORS


# ✅ Bellman-Ford update
def update_logic(neighbor_ip, routes_from_neighbor):
    updated = False

    for route in routes_from_neighbor:
        subnet = route["subnet"]
        neighbor_distance = route["distance"]

        if subnet == MY_SUBNET:
            continue

        if is_direct_neighbor(neighbor_ip):
            new_distance = 1
        else:
            new_distance = neighbor_distance + 1

        if subnet not in routing_table:
            routing_table[subnet] = [new_distance, neighbor_ip, time.time(), False]
            updated = True
        else:
            current_distance, current_hop, _, is_direct = routing_table[subnet]

            if new_distance < current_distance:
                routing_table[subnet] = [new_distance, neighbor_ip, time.time(), False]
                updated = True

            elif current_hop == neighbor_ip:
                routing_table[subnet] = [new_distance, neighbor_ip, time.time(), is_direct]
                updated = True

    if updated:
        print(f"[{MY_IP}] Routing table updated:")

        for subnet, (dist, hop, _, _) in routing_table.items():
            print(f"  {subnet} -> dist {dist} via {hop}")

            if subnet == MY_SUBNET:
                continue

            if hop != "0.0.0.0":
                if hop.startswith("10.0.3."):
                    cmd = f"ip route replace {subnet} via {hop} dev eth1"
                else:
                    cmd = f"ip route replace {subnet} via {hop} dev eth0"

                print(f"[{MY_IP}] Running: {cmd}")
                os.system(cmd)


# ✅ Split Horizon
def broadcast_updates():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        for neighbor in NEIGHBORS:
            if not neighbor:
                continue

            routes = []

            for subnet, (distance, next_hop, _, _) in routing_table.items():

                if next_hop == neighbor:
                    continue

                routes.append({
                    "subnet": subnet,
                    "distance": distance
                })

            message = {
                "router_id": MY_IP,
                "version": 1.0,
                "routes": routes
            }

            data = json.dumps(message).encode()
            sock.sendto(data, (neighbor, PORT))

            print(f"[{MY_IP}] Sent filtered routes to {neighbor}")

        time.sleep(5)


# ✅ Receive updates
def listen_for_updates():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))

    print(f"[{MY_IP}] Listening for updates...")

    while True:
        data, addr = sock.recvfrom(4096)

        message = json.loads(data.decode())
        neighbor_ip = message["router_id"]
        routes = message["routes"]

        print(f"[{MY_IP}] Received routes from {neighbor_ip}")

        update_logic(neighbor_ip, routes)


# ✅ Remove stale routes (FIXED)
def remove_stale_routes():
    while True:
        now = time.time()
        to_delete = []

        for subnet, (dist, hop, last_update, is_direct) in routing_table.items():
            if subnet == MY_SUBNET:
                continue

            # remove both direct + learned if timeout
            if now - last_update > 15:
                print(f"[{MY_IP}] Removing stale route: {subnet}")
                to_delete.append(subnet)

        for subnet in to_delete:
            del routing_table[subnet]
            os.system(f"ip route del {subnet}")

        time.sleep(5)


# ✅ MAIN
if __name__ == "__main__":
    add_direct_routes()
    threading.Thread(target=broadcast_updates, daemon=True).start()
    threading.Thread(target=remove_stale_routes, daemon=True).start()
    listen_for_updates()