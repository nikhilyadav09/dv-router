# Distance Vector Router

Custom Distance Vector Routing implementation using Python and Docker.

## Features
- UDP-based routing updates
- Bellman-Ford algorithm
- Split Horizon (to prevent loops)
- Docker-based network simulation

## Run
Build:
docker build -t my-router .

Create networks:
docker network create --subnet=10.0.1.0/24 net_ab
docker network create --subnet=10.0.2.0/24 net_bc
docker network create --subnet=10.0.3.0/24 net_ac
