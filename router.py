import socket
import json
import threading
import time
import os
import subprocess

os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")

MY_IP = os.getenv("MY_IP", "127.0.0.1")
NEIGHBORS = [n for n in os.getenv("NEIGHBORS", "").split(",") if n]
PORT = 5000

# Derive all directly connected subnets from MY_IP + NEIGHBORS
def get_local_subnets():
    result = subprocess.run(["ip", "addr"], capture_output=True, text=True)
    subnets = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("inet ") and "127." not in line:
            cidr = line.split()[1]  # e.g. "10.0.1.2/24"
            parts = cidr.split("/")
            ip_parts = parts[0].split(".")
            prefix = int(parts[1])
            # Build network address (assumes /24)
            subnet = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/{prefix}"
            subnets.append(subnet)
    return subnets

# { subnet: [distance, next_hop, last_updated] }
routing_table = {}
table_lock = threading.Lock()

def initialize_routing_table():
    local_subnets = get_local_subnets()
    with table_lock:
        for subnet in local_subnets:
            routing_table[subnet] = [0, "0.0.0.0", time.time()]
    print(f"[{MY_IP}] Initialized with local subnets: {local_subnets}")

def is_direct_neighbor(ip):
    return ip in NEIGHBORS

def update_logic(neighbor_ip, routes_from_neighbor):
    updated = False
    with table_lock:
        for route in routes_from_neighbor:
            subnet = route["subnet"]
            advertised_distance = route["distance"]
            new_distance = advertised_distance + 1

            # Skip routes to our own subnets
            if subnet in routing_table and routing_table[subnet][1] == "0.0.0.0":
                continue

            if subnet not in routing_table:
                routing_table[subnet] = [new_distance, neighbor_ip, time.time()]
                updated = True
                print(f"[{MY_IP}] New route: {subnet} via {neighbor_ip} dist {new_distance}")
            else:
                current_distance, current_hop, _ = routing_table[subnet]

                # Accept if shorter, or refresh if same neighbor is updating us
                if new_distance < current_distance or (new_distance == current_distance and current_hop != neighbor_ip):
                    routing_table[subnet] = [new_distance, neighbor_ip, time.time()]
                    updated = True
                    print(f"[{MY_IP}] Better/equal route: {subnet} via {neighbor_ip} dist {new_distance}")
                elif current_hop == neighbor_ip:
                    # Refresh timestamp (and possibly updated distance from same neighbor)
                    routing_table[subnet] = [new_distance, neighbor_ip, time.time()]
                    if new_distance != current_distance:
                        updated = True
                        print(f"[{MY_IP}] Updated route: {subnet} via {neighbor_ip} dist {new_distance}")

    if updated:
        with table_lock:
            snapshot = dict(routing_table)
        apply_kernel_routes(snapshot)

def apply_kernel_routes(snapshot=None):
    if snapshot is None:
        with table_lock:
            snapshot = dict(routing_table)
    local = set(get_local_subnets())
    for subnet, (dist, hop, _) in snapshot.items():
        if hop == "0.0.0.0" or subnet in local:
            continue
        cmd = f"ip route replace {subnet} via {hop}"
        print(f"[{MY_IP}] Running: {cmd}")
        os.system(cmd)

def broadcast_updates():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    while True:
        with table_lock:
            table_snapshot = dict(routing_table)

        for neighbor in NEIGHBORS:
            routes = []
            for subnet, (distance, next_hop, _) in table_snapshot.items():
                # Split Horizon: don't advertise routes learned from this neighbor back to them
                if next_hop == neighbor:
                    continue
                routes.append({"subnet": subnet, "distance": distance})

            message = {
                "router_id": MY_IP,
                "version": 1.0,
                "routes": routes
            }
            data = json.dumps(message).encode()
            try:
                sock.sendto(data, (neighbor, PORT))
                print(f"[{MY_IP}] Sent {len(routes)} routes to {neighbor}")
            except Exception as e:
                print(f"[{MY_IP}] Send error to {neighbor}: {e}")

        time.sleep(5)

def listen_for_updates():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", PORT))
    print(f"[{MY_IP}] Listening on port {PORT}...")

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            message = json.loads(data.decode())
            neighbor_ip = addr[0]  # use actual source IP, not router_id (which may be on a different subnet)
            routes = message["routes"]
            print(f"[{MY_IP}] Received {len(routes)} routes from {neighbor_ip}")
            update_logic(neighbor_ip, routes)
        except Exception as e:
            print(f"[{MY_IP}] Receive error: {e}")

def remove_stale_routes():
    TIMEOUT = 15  # 3x the broadcast interval

    while True:
        time.sleep(5)
        now = time.time()
        to_delete = []
        to_fix = []

        local_subnets = set(get_local_subnets())
        with table_lock:
            for subnet in local_subnets:
                if subnet not in routing_table:
                    routing_table[subnet] = [0, "0.0.0.0", now]
                    print(f"[{MY_IP}] Discovered new local subnet: {subnet}")
                elif routing_table[subnet][1] != "0.0.0.0":
                    old_hop = routing_table[subnet][1]
                    routing_table[subnet] = [0, "0.0.0.0", now]
                    to_fix.append((subnet, old_hop))

            for subnet, (dist, hop, last_update) in list(routing_table.items()):
                if hop == "0.0.0.0":
                    # If a directly-connected subnet is no longer present, remove it
                    if subnet not in local_subnets:
                        print(f"[{MY_IP}] Local subnet detached: {subnet}")
                        to_delete.append(subnet)
                    continue
                if now - last_update > TIMEOUT:
                    print(f"[{MY_IP}] Stale route expired: {subnet} via {hop}")
                    to_delete.append(subnet)

            for subnet in to_delete:
                del routing_table[subnet]

        for subnet, old_hop in to_fix:
            os.system(f"ip route del {subnet} via {old_hop} 2>/dev/null")
        for subnet in to_delete:
            os.system(f"ip route del {subnet} 2>/dev/null")

if __name__ == "__main__":
    initialize_routing_table()
    threading.Thread(target=broadcast_updates, daemon=True).start()
    threading.Thread(target=remove_stale_routes, daemon=True).start()
    listen_for_updates()