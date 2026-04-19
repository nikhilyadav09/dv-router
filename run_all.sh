#!/bin/bash

echo "🛑 Stopping old containers..."
docker stop router_a router_b router_c 2>/dev/null

echo "🧹 Removing old containers..."
docker rm router_a router_b router_c 2>/dev/null

echo "🔨 Rebuilding Docker image..."
docker build -t my-router .

echo "🚀 Starting Router A..."
docker run -dit --name router_a --privileged \
--network net_ab --ip 10.0.1.2 \
-e MY_IP=10.0.1.2 \
-e MY_SUBNET=10.0.1.0/24 \
-e NEIGHBORS=10.0.1.3,10.0.3.3 \
my-router

echo "🔗 Connecting Router A to net_ac..."
docker network connect net_ac router_a --ip 10.0.3.2


echo "🚀 Starting Router B..."
docker run -dit --name router_b --privileged \
--network net_ab --ip 10.0.1.3 \
-e MY_IP=10.0.1.3 \
-e MY_SUBNET=10.0.2.0/24 \
-e NEIGHBORS=10.0.1.2,10.0.2.3 \
my-router

echo "🔗 Connecting Router B to net_bc..."
docker network connect net_bc router_b --ip 10.0.2.2


echo "🚀 Starting Router C..."
docker run -dit --name router_c --privileged \
--network net_bc --ip 10.0.2.3 \
-e MY_IP=10.0.2.3 \
-e MY_SUBNET=10.0.3.0/24 \
-e NEIGHBORS=10.0.2.2,10.0.3.2 \
my-router

echo "🔗 Connecting Router C to net_ac..."
docker network connect net_ac router_c --ip 10.0.3.3

echo "✅ All routers built and started successfully!"
