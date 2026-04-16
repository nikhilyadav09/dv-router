import socket
import json
import threading
import time
import os

MY_IP = os.getenv("MY_IP", "127.0.0.1")
NEIGHBORS = os.getenv("NEIGHBORS", "").split(",")
PORT = 5000

MY_SUBNET = os.getenv("MY_SUBNET", "10.0.1.0/24")

routing_table = {
    MY_SUBNET: [0, "0.0.0.0"]
}

def update_logic(neighbor_ip, routes_from_neighbor):
    updated = False

    for route in routes_from_neighbor:
        subnet = route["subnet"]
        neighbor_distance = route["distance"]

        new_distance = neighbor_distance + 1

        if subnet not in routing_table:
            routing_table[subnet] = [new_distance, neighbor_ip]
            updated = True

        else:
            current_distance = routing_table[subnet][0]

            if new_distance < current_distance:
                routing_table[subnet] = [new_distance, neighbor_ip]
                updated = True

    if updated:
        print(f"[{MY_IP}] Routing table updated:")
        print(f"[{MY_IP}] Current routing table:")
        for subnet, (dist, hop) in routing_table.items():
            print(f"  {subnet} -> dist {dist} via {hop}")

def broadcast_updates():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        routes = []
        for subnet, (distance, _) in routing_table.items():
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

        for neighbor in NEIGHBORS:
            if neighbor:
                sock.sendto(data, (neighbor, PORT))
                print(f"[{MY_IP}] Sent routing table to {neighbor}")

        time.sleep(5)

def listen_for_updates():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((MY_IP, PORT))

    print(f"[{MY_IP}] Listening for updates...")

    while True:
        data, addr = sock.recvfrom(4096)

        message = json.loads(data.decode())
        neighbor_ip = message["router_id"]
        routes = message["routes"]

        print(f"[{MY_IP}] Received routes from {neighbor_ip}")

        update_logic(neighbor_ip, routes)

if __name__ == "__main__":
    threading.Thread(target=broadcast_updates, daemon=True).start()
    listen_for_updates()