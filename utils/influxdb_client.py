import os
import logging
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InfluxDBWriter:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # InfluxDB configuration
        self.url = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
        self.token = os.getenv('INFLUXDB_TOKEN')
        self.org = os.getenv('INFLUXDB_ORG', 'my-org')
        self.bucket = os.getenv('INFLUXDB_BUCKET', 'iot_data')
        
        # Initialize InfluxDB client
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        
        logger.info(f'Initialized InfluxDB writer for {self.url} (org: {self.org}, bucket: {self.bucket})')
    
    def write_measurement(self, measurement, tags, fields, timestamp=None):
        """
        Write a single measurement to InfluxDB.
        
        Args:
            measurement (str): The measurement name
            tags (dict): Dictionary of tag key-value pairs
            fields (dict): Dictionary of field key-value pairs
            timestamp (datetime, optional): Timestamp for the measurement. Defaults to current time.
        """
        try:
            point = Point(measurement)
            
            # Add tags
            for key, value in tags.items():
                if value is not None:  # Skip None values
                    point = point.tag(key, str(value))
            
            # Add fields
            for key, value in fields.items():
                if value is not None:  # Skip None values
                    point = point.field(key, value)
            
            # Set timestamp if provided
            if timestamp:
                point = point.time(timestamp)
            
            # Write the point
            self.write_api.write(bucket=self.bucket, record=point)
            logger.debug(f'Wrote point to InfluxDB: {measurement} {tags} {fields}')
            
        except Exception as e:
            logger.error(f'Error writing to InfluxDB: {str(e)}', exc_info=True)
            raise
    
    def close(self):
        """Close the InfluxDB client connections."""
        try:
            self.write_api.close()
            self.client.close()
            logger.info('Closed InfluxDB connections')
        except Exception as e:
            logger.error(f'Error closing InfluxDB client: {str(e)}')
            raise

# Example usage
if __name__ == "__main__":
    # Initialize the writer
    writer = InfluxDBWriter()
    
    try:
        # Example: Write a temperature reading
        writer.write_measurement(
            measurement='sensor_data',
            tags={
                'device_id': 'device_001',
                'sensor_type': 'temperature',
                'location': 'room_101'
            },
            fields={
                'value': 23.5,
                'unit': 'celsius',
                'status': 'normal'
            },
            timestamp=datetime.utcnow()
        )
        
        logger.info('Successfully wrote example data to InfluxDB')
        
    finally:
        # Always close the writer when done
        writer.close()
