# Real-Time IoT ETL Pipeline

A real-time ETL pipeline for processing IoT sensor data with anomaly detection and real-time visualization.

## Architecture

```
[IoT Devices] → [Kafka] → [Spark Streaming] → [InfluxDB] → [Grafana]
                  ↓
           [Anomaly Detection]
```

## Features

- Real-time data ingestion from simulated IoT devices
- Stream processing with Apache Spark
- Anomaly detection for sensor readings
- Time-series data storage with InfluxDB
- Real-time visualization with Grafana

## Prerequisites

- Python 3.8+
- Java 8 or 11
- Apache Kafka
- Apache Spark 3.4.1
- InfluxDB 2.x
- Grafana 9.x+

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables (copy `.env.example` to `.env` and configure)
4. Start Kafka and create required topics
5. Start InfluxDB and Grafana
6. Run the data producer and Spark streaming job

## Project Structure

```
iot-etl-pipeline/
├── config/               # Configuration files
├── docs/                 # Documentation
├── scripts/              # Utility scripts
└── src/                  # Source code
    ├── producer/         # Kafka producer for IoT data
    ├── spark/            # Spark streaming and processing
    │   ├── streaming/    # Spark streaming jobs
    │   ├── processing/   # Data processing logic
    │   └── storage/      # Storage integration
    └── utils/            # Utility functions
```

## Running the Pipeline

1. Start the IoT data producer:
   ```bash
   python -m src.producer.iot_producer
   ```

2. Run the Spark streaming job:
   ```bash
   spark-submit src/spark/streaming/streaming_job.py
   ```

## License

MIT
