# IoT ETL Pipeline - Deployment Guide

This guide will help you deploy the IoT ETL pipeline on your local machine using Docker.

## Prerequisites

1. **Docker Desktop**
   - Download and install from: https://www.docker.com/products/docker-desktop/
   - Make sure Docker is running before proceeding

2. **Python 3.8+**
   - Download and install from: https://www.python.org/downloads/
   - Make sure Python is added to your system PATH

3. **Java 8 or 11** (for Spark)
   - Download and install from: https://adoptium.net/
   - Set JAVA_HOME environment variable

4. **Apache Spark** (for local development)
   - Download from: https://spark.apache.org/downloads.html
   - Extract and add to your system PATH

## Deployment Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd iot-etl-pipeline
```

### 2. Set Up Environment Variables

Copy the example environment file and update it with your configuration:

```bash
copy .env.example .env
```

Edit the `.env` file with your preferred settings.

### 3. Run the Deployment Script

Open a PowerShell terminal and run:

```powershell
.\deploy.ps1
```

This script will:
- Start all required Docker containers (Kafka, InfluxDB, Grafana)
- Create Kafka topics
- Set up InfluxDB buckets
- Configure Grafana data sources and dashboards

### 4. Start the IoT Data Producer

In a new terminal, start the IoT data producer:

```bash
python -m src.producer.iot_producer
```

### 5. Run the Spark Streaming Job

In another terminal, start the Spark streaming job:

```bash
spark-submit src/spark/streaming/streaming_job.py
```

## Accessing Services

- **Grafana Dashboard**: http://localhost:3000
  - Username: `admin`
  - Password: `admin` (or as set in your .env file)

- **InfluxDB UI**: http://localhost:8086
  - Username: `admin`
  - Password: `admin123` (or as set in your .env file)

- **Kafka UI**: http://localhost:8080

## Stopping the Services

To stop all services, run:

```bash
docker-compose down
```

## Troubleshooting

### Common Issues

1. **Port Conflicts**
   - Make sure ports 3000 (Grafana), 8086 (InfluxDB), 9092 (Kafka), and 8080 (Kafka UI) are available

2. **Docker Not Running**
   - Ensure Docker Desktop is running
   - Try restarting Docker Desktop if you encounter network issues

3. **Permission Issues**
   - On Windows, run PowerShell as Administrator
   - Make sure your user has permission to run Docker commands

4. **Spark Job Fails**
   - Make sure JAVA_HOME is set correctly
   - Check that Spark is properly installed and in your PATH

## Next Steps

- Customize the Grafana dashboard for your specific needs
- Add more sensor types to the IoT producer
- Implement additional data processing in the Spark job
- Set up alerts in Grafana for critical conditions

## Support

For any issues or questions, please open an issue in the repository.
