#!/bin/bash

# Create docker_logs directory if it doesn't exist
mkdir -p docker_logs

cd docker

# Get logs for each service
docker compose logs api > ../docker_logs/api.log
docker compose logs consumer > ../docker_logs/consumer.log
docker compose logs db > ../docker_logs/db.log
docker compose logs rabbitmq > ../docker_logs/rabbitmq.log
docker compose logs bot > ../docker_logs/bot.log

cd ..

echo "Logs have been collected in docker_logs directory"
