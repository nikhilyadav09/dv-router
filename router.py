import socket
import json
import threading
import time
import os

MY_IP = os.getenv("MY_IP", "127.0.0.1")
NEIGHBORS = os.getenv("NEIGHBORS", "").split(",")
PORT = 5000

routing_table = {}

def broadcast_updates():
    while True:
        print(f"[{MY_IP}] Broadcasting routing table...")
        time.sleep(5)

def listen_for_updates():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((MY_IP, PORT))
    print(f"[{MY_IP}] Listening on {PORT}")

    while True:
        data, addr = sock.recvfrom(4096)
        message = json.loads(data.decode())

        neighbor_ip = message.get("router_id")
        routes = message.get("routes", [])

        print(f"[{MY_IP}] Received update from {neighbor_ip}")
        update_logic(neighbor_ip, routes)

def update_logic(neighbor_ip, routes):
    print(f"[{MY_IP}] Processing routes from {neighbor_ip}")
    pass

if __name__ == "__main__":
    threading.Thread(target=broadcast_updates, daemon=True).start()
    listen_for_updates()
