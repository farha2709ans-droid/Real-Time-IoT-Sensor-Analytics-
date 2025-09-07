#!/bin/bash

# Exit on error
set -e

# Load environment variables
source ../.env

# Create Kafka topics
echo "Creating Kafka topics..."
docker-compose exec -T kafka \
  kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic $KAFKA_TOPIC_RAW \
  --partitions 1 \
  --replication-factor 1 \
  --if-not-exists

docker-compose exec -T kafka \
  kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic $KAFKA_TOPIC_PROCESSED \
  --partitions 1 \
  --replication-factor 1 \
  --if-not-exists

echo "Kafka topics created successfully!"

# Setup InfluxDB
# Note: This requires the influx CLI to be installed locally
# You can install it with: brew install influxdb-cli (on macOS)
echo "Setting up InfluxDB..."

# Wait for InfluxDB to be ready
until curl -s http://localhost:8086/health; do
  echo "Waiting for InfluxDB to be ready..."
  sleep 5
done

# Create the bucket (if it doesn't exist)
influx bucket create \
  --name $INFLUXDB_BUCKET \
  --org $INFLUXDB_ORG \
  --token $INFLUXDB_TOKEN \
  --retention 30d \
  --json

echo "InfluxDB setup complete!"

echo "Infrastructure setup completed successfully!"
echo "Kafka UI: http://localhost:8080"
echo "Grafana: http://localhost:3000 (admin/admin)"
echo "InfluxDB: http://localhost:8086"
