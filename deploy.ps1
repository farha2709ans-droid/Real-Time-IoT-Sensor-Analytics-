# IoT ETL Pipeline Deployment Script
# This script sets up the complete IoT ETL pipeline

# Stop on error
$ErrorActionPreference = "Stop"

# Load environment variables
$envFile = ".\.env"
if (-not (Test-Path $envFile)) {
    Write-Host "Creating .env file from .env.example..."
    Copy-Item ".\.env.example" -Destination $envFile
    Write-Host "Please edit the .env file with your configuration and run the script again."
    exit 1
}

# Load environment variables
Get-Content $envFile | ForEach-Object {
    $name, $value = $_.Split('=', 2)
    if ($name -and $value) {
        [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
    }
}

# Function to check if a command exists
function Test-CommandExists {
    param($command)
    $exists = $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
    return $exists
}

# Check for Docker and Docker Compose
if (-not (Test-CommandExists "docker")) {
    Write-Error "Docker is not installed. Please install Docker Desktop and try again."
    exit 1
}

if (-not (Test-CommandExists "docker-compose")) {
    Write-Error "Docker Compose is not installed. Please install Docker Desktop and try again."
    exit 1
}

# Function to wait for a service to be healthy
function Wait-ForService {
    param(
        [string]$serviceName,
        [string]$healthCheck,
        [int]$maxRetries = 30,
        [int]$delay = 5
    )
    
    $retryCount = 0
    $isHealthy = $false
    
    Write-Host "Waiting for $serviceName to be ready..."
    
    while (-not $isHealthy -and $retryCount -lt $maxRetries) {
        try {
            $result = Invoke-Expression $healthCheck -ErrorAction SilentlyContinue
            if ($LASTEXITCODE -eq 0) {
                $isHealthy = $true
                Write-Host "$serviceName is ready!"
                break
            }
        } catch {
            # Ignore errors and retry
        }
        
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            Write-Host "Waiting for $serviceName to be ready... (Attempt $retryCount/$maxRetries)"
            Start-Sleep -Seconds $delay
        }
    }
    
    if (-not $isHealthy) {
        Write-Error "Timed out waiting for $serviceName to be ready"
        exit 1
    }
}

# Start Docker containers
Write-Host "Starting Docker containers..."
docker-compose up -d

# Wait for services to be ready
Wait-ForService -serviceName "Kafka" -healthCheck "docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list"
Wait-ForService -serviceName "InfluxDB" -healthCheck "curl -s http://localhost:8086/health"
Wait-ForService -serviceName "Grafana" -healthCheck "curl -s http://localhost:3000/api/health"

# Create Kafka topics
Write-Host "Creating Kafka topics..."
$kafkaTopics = @(
    @{ Name = $env:KAFKA_TOPIC_RAW; Partitions = 1; Replication = 1 },
    @{ Name = $env:KAFKA_TOPIC_PROCESSED; Partitions = 1; Replication = 1 }
)

foreach ($topic in $kafkaTopics) {
    Write-Host "Creating topic: $($topic.Name)"
    docker-compose exec -T kafka kafka-topics \
        --create \
        --bootstrap-server localhost:9092 \
        --topic $($topic.Name) \
        --partitions $topic.Partitions \
        --replication-factor $topic.Replication \
        --if-not-exists
}

# Setup InfluxDB
Write-Host "Setting up InfluxDB..."
$influxSetup = @{
    username = $env:INFLUXDB_USERNAME
    password = $env:INFLUXDB_PASSWORD
    org = $env:INFLUXDB_ORG
    bucket = $env:INFLUXDB_BUCKET
    token = $env:INFLUXDB_TOKEN
}

try {
    # Check if the bucket exists
    $bucketExists = docker-compose exec -T influxdb \
        influx bucket list \
        --org $($influxSetup.org) \
        --token $($influxSetup.token) \
        --name $($influxSetup.bucket) \
        --json | ConvertFrom-Json
    
    if (-not $bucketExists) {
        Write-Host "Creating InfluxDB bucket: $($influxSetup.bucket)"
        docker-compose exec -T influxdb \
            influx bucket create \
            --name $influxSetup.bucket \
            --org $influxSetup.org \
            --retention 30d \
            --token $influxSetup.token \
            --json
    } else {
        Write-Host "InfluxDB bucket already exists: $($influxSetup.bucket)"
    }
} catch {
    Write-Error "Failed to set up InfluxDB: $_"
    exit 1
}

# Setup Grafana
Write-Host "Setting up Grafana..."
$grafanaUrl = "http://localhost:3000"
$grafanaAuth = "admin:$($env:GF_SECURITY_ADMIN_PASSWORD)"

# Wait for Grafana to be ready
$maxRetries = 30
$retryCount = 0
$grafanaReady = $false

while (-not $grafanaReady -and $retryCount -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "$grafanaUrl/api/health" -Method Get -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $grafanaReady = $true
            break
        }
    } catch {
        # Ignore errors and retry
    }
    
    $retryCount++
    if ($retryCount -lt $maxRetries) {
        Write-Host "Waiting for Grafana to be ready... (Attempt $retryCount/$maxRetries)"
        Start-Sleep -Seconds 5
    }
}

if (-not $grafanaReady) {
    Write-Error "Timed out waiting for Grafana to be ready"
    exit 1
}

# Add InfluxDB as a data source
$influxDataSource = @{
    name = "InfluxDB"
    type = "influxdb"
    url = "http://influxdb:8086"
    access = "proxy"
    isDefault = $true
    jsonData = @{
        httpMode = "POST"
        organization = $influxSetup.org
        defaultBucket = $influxSetup.bucket
        version = "Flux"
    }
    secureJsonData = @{
        token = $influxSetup.token
    }
}

try {
    # Check if data source already exists
    $dataSources = Invoke-RestMethod -Uri "$grafanaUrl/api/datasources" -Method Get -Headers @{
        Authorization = "Basic $([Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($grafanaAuth)))"
    }
    
    $existingDs = $dataSources | Where-Object { $_.name -eq $influxDataSource.name }
    
    if ($existingDs) {
        Write-Host "Updating existing data source: $($influxDataSource.name)"
        $response = Invoke-RestMethod -Uri "$grafanaUrl/api/datasources/$($existingDs.id)" -Method Put -Body ($influxDataSource | ConvertTo-Json) -ContentType "application/json" -Headers @{
            Authorization = "Basic $([Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($grafanaAuth)))"
        }
    } else {
        Write-Host "Creating data source: $($influxDataSource.name)"
        $response = Invoke-RestMethod -Uri "$grafanaUrl/api/datasources" -Method Post -Body ($influxDataSource | ConvertTo-Json) -ContentType "application/json" -Headers @{
            Authorization = "Basic $([Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($grafanaAuth)))"
        }
    }
    
    # Import dashboard
    $dashboardJson = Get-Content -Path ".\grafana\dashboards\iot-dashboard.json" -Raw
    $dashboard = @{
        dashboard = ($dashboardJson | ConvertFrom-Json -AsHashtable)
        overwrite = $true
        folderId = 0
    }
    
    $response = Invoke-RestMethod -Uri "$grafanaUrl/api/dashboards/db" -Method Post -Body ($dashboard | ConvertTo-Json -Depth 10) -ContentType "application/json" -Headers @{
        Authorization = "Basic $([Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($grafanaAuth)))"
    }
    
    Write-Host "Grafana dashboard imported successfully!"
    Write-Host "Dashboard URL: $grafanaUrl$($response.url)"
    
} catch {
    Write-Error "Failed to set up Grafana: $_"
    Write-Host "Response: $($_.Exception.Response.GetResponseStream())"
    exit 1
}

# Create a .env file for Python applications
$envContent = @"
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_RAW=$($env:KAFKA_TOPIC_RAW)
KAFKA_TOPIC_PROCESSED=$($env:KAFKA_TOPIC_PROCESSED)
KAFKA_GROUP_ID=$($env:KAFKA_GROUP_ID)

# InfluxDB Configuration
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=$($influxSetup.token)
INFLUXDB_ORG=$($influxSetup.org)
INFLUXDB_BUCKET=$($influxSetup.bucket)

# Application Settings
LOG_LEVEL=INFO
BATCH_INTERVAL_SECONDS=60
ANOMALY_THRESHOLD=3.0

# Device Simulation Settings
NUM_DEVICES=5
SENSOR_TYPES=temperature,humidity,heart_rate
UPDATE_INTERVAL_MS=1000
"@

$envContent | Out-File -FilePath ".env" -Force

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " IoT ETL Pipeline Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "- Grafana:       http://localhost:3000 (admin/$($env:GF_SECURITY_ADMIN_PASSWORD))"
Write-Host "- InfluxDB:      http://localhost:8086"
Write-Host "- Kafka UI:      http://localhost:8080"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Start the IoT data producer:"
Write-Host "   python -m src.producer.iot_producer"
Write-Host ""
Write-Host "2. Run the Spark streaming job:"
Write-Host "   spark-submit src/spark/streaming/streaming_job.py"
Write-Host ""
Write-Host "3. Access the Grafana dashboard to view real-time data"
Write-Host ""
Write-Host "To stop all services, run:"
Write-Host "   docker-compose down"
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
