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
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        message = {
            "router_id": MY_IP,
            "message": f"Hello from {MY_IP}"
        }

        data = json.dumps(message).encode()

        for neighbor in NEIGHBORS:
            if neighbor:
                sock.sendto(data, (neighbor, PORT))
                print(f"[{MY_IP}] Sent message to {neighbor}")

        time.sleep(5)

def listen_for_updates():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((MY_IP, PORT))

    print(f"[{MY_IP}] Listening for updates...")

    while True:
        data, addr = sock.recvfrom(1024)
        print(f"Received from {addr}: {data}")

if __name__ == "__main__":
    threading.Thread(target=broadcast_updates, daemon=True).start()
    listen_for_updates()