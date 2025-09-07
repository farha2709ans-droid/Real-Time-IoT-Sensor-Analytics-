import os
import json
import logging
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp, window, avg, stddev, lit, when
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, MapType, TimestampType
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IoTStreamingJob:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Configuration
        self.kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.kafka_topic_raw = os.getenv('KAFKA_TOPIC_RAW', 'iot-raw-data')
        self.kafka_group_id = os.getenv('KAFKA_GROUP_ID', 'iot-spark-consumer')
        self.anomaly_threshold = float(os.getenv('ANOMALY_THRESHOLD', 3.0))
        
        # Initialize Spark session
        self.spark = self._init_spark_session()
        
        # Define schema for incoming JSON data
        self.schema = self._define_schema()
        
        logger.info('Initialized Spark Streaming job')
    
    def _init_spark_session(self):
        """Initialize and return a Spark session with appropriate configurations."""
        return SparkSession.builder \
            .appName("IoT-Streaming-ETL") \
            .config("spark.sql.streaming.checkpointLocation", 
                   "/tmp/checkpoints/iot_streaming") \
            .config("spark.sql.shuffle.partitions", "2") \
            .getOrCreate()
    
    def _define_schema(self):
        """Define the schema for the incoming JSON data."""
        return StructType([
            StructField("timestamp", StringType(), False),
            StructField("device_id", StringType(), False),
            StructField("device_name", StringType(), True),
            StructField("location", MapType(StringType(), DoubleType()), True),
            StructField("sensor_readings", MapType(StringType(), DoubleType()), False)
        ])
    
    def _process_micro_batch(self, df, epoch_id):
        """Process each micro-batch of data."""
        if df.rdd.isEmpty():
            logger.info("No data in this micro-batch")
            return
        
        # Show schema for debugging
        logger.info(f"Processing micro-batch {epoch_id} with schema:")
        df.printSchema()
        
        # Show sample data
        logger.info(f"Sample data in batch {epoch_id}:")
        df.show(5, truncate=False)
        
        # Here you would add your processing logic
        # For now, just log the count of records
        logger.info(f"Processed {df.count()} records in batch {epoch_id}")
    
    def start(self):
        """Start the Spark Streaming job."""
        logger.info("Starting Spark Streaming job...")
        
        try:
            # Read from Kafka
            kafka_df = self.spark.readStream \
                .format("kafka") \
                .option("kafka.bootstrap.servers", self.kafka_bootstrap_servers) \
                .option("subscribe", self.kafka_topic_raw) \
                .option("startingOffsets", "latest") \
                .option("failOnDataLoss", "false") \
                .load()
            
            # Parse the value (which is in JSON) and cast to our schema
            parsed_df = kafka_df.select(
                from_json(
                    col("value").cast("string"), 
                    self.schema
                ).alias("parsed_value")
            ).select("parsed_value.*")
            
            # Convert timestamp string to timestamp type
            processed_df = parsed_df.withColumn(
                "timestamp", 
                to_timestamp(col("timestamp"))
            )
            
            # Process the streaming data
            query = processed_df.writeStream \
                .foreachBatch(self._process_micro_batch) \
                .outputMode("append") \
                .start()
            
            # Wait for the streaming query to terminate
            query.awaitTermination()
            
        except Exception as e:
            logger.error(f"Error in streaming job: {str(e)}", exc_info=True)
            raise
        finally:
            # Stop the Spark session when done
            self.spark.stop()
            logger.info("Spark session stopped")

if __name__ == "__main__":
    job = IoTStreamingJob()
    job.start()
