#!/bin/bash
# test_docker.sh

# Stop any running containers
docker-compose -f docker/docker-compose.yml down -v

# Build and start test environment
docker-compose -f docker/docker-compose.test.yml up --build -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Run tests
docker-compose -f docker/docker-compose.test.yml run test pytest tests/docker -v

# Cleanup
docker-compose -f docker/docker-compose.test.yml down -v
