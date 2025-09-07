import os
import json
import time
import random
import logging
from datetime import datetime
from dotenv import load_dotenv
from confluent_kafka import Producer
from faker import Faker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IoTDataProducer:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Kafka configuration
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.topic = os.getenv('KAFKA_TOPIC_RAW', 'iot-raw-data')
        
        # Device simulation settings
        self.num_devices = int(os.getenv('NUM_DEVICES', 5))
        self.sensor_types = os.getenv('SENSOR_TYPES', 'temperature,humidity,heart_rate').split(',')
        self.update_interval = float(os.getenv('UPDATE_INTERVAL_MS', 1000)) / 1000.0
        
        # Initialize Kafka producer
        self.producer = Producer({
            'bootstrap.servers': self.bootstrap_servers,
            'client.id': 'iot-producer',
            'acks': '1'  # Wait for leader to acknowledge
        })
        
        # Initialize Faker for realistic device names
        self.fake = Faker()
        self.devices = [
            {
                'device_id': f'device_{i:03d}',
                'device_name': f'{self.fake.word().capitalize()}-{self.fake.word().capitalize()}-{random.randint(100, 999)}',
                'location': {
                    'latitude': random.uniform(-90, 90),
                    'longitude': random.uniform(-180, 180)
                },
                'sensors': {sensor: self._get_initial_value(sensor) for sensor in self.sensor_types}
            }
            for i in range(self.num_devices)
        ]
        
        logger.info(f'Initialized IoT producer with {self.num_devices} devices')
    
    def _get_initial_value(self, sensor_type):
        """Get initial sensor value based on sensor type."""
        if sensor_type == 'temperature':
            return random.uniform(20.0, 30.0)  # Celsius
        elif sensor_type == 'humidity':
            return random.uniform(30.0, 80.0)  # Percentage
        elif sensor_type == 'heart_rate':
            return random.randint(60, 100)     # BPM
        else:
            return random.random() * 100
    
    def _generate_sensor_data(self, device):
        """Generate new sensor readings with some randomness."""
        data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'device_id': device['device_id'],
            'device_name': device['device_name'],
            'location': device['location'],
            'sensor_readings': {}
        }
        
        # Update each sensor value with some randomness
        for sensor, current_value in device['sensors'].items():
            if sensor == 'temperature':
                # Temperature changes slowly (±0.5°C)
                new_value = current_value + random.uniform(-0.5, 0.5)
                # Keep within reasonable bounds
                new_value = max(15.0, min(40.0, new_value))
            elif sensor == 'humidity':
                # Humidity changes slowly (±2%)
                new_value = current_value + random.uniform(-2.0, 2.0)
                new_value = max(20.0, min(95.0, new_value))
            elif sensor == 'heart_rate':
                # Heart rate changes more dramatically
                new_value = current_value + random.randint(-5, 5)
                new_value = max(40, min(180, new_value))
            else:
                # Generic sensor with small changes
                new_value = current_value * random.uniform(0.95, 1.05)
            
            device['sensors'][sensor] = new_value
            data['sensor_readings'][sensor] = round(new_value, 2)
        
        return data
    
    def delivery_report(self, err, msg):
        """Callback for message delivery reports."""
        if err is not None:
            logger.error(f'Message delivery failed: {err}')
        else:
            logger.debug(f'Message delivered to {msg.topic()} [{msg.partition()}]')
    
    def run(self):
        """Main loop to generate and publish sensor data."""
        logger.info('Starting IoT data producer...')
        
        try:
            while True:
                for device in self.devices:
                    # Generate sensor data
                    data = self._generate_sensor_data(device)
                    
                    # Publish to Kafka
                    self.producer.produce(
                        topic=self.topic,
                        key=device['device_id'].encode('utf-8'),
                        value=json.dumps(data).encode('utf-8'),
                        callback=self.delivery_report
                    )
                    
                    # Log the first few messages to show it's working
                    if len(self.devices) <= 5:  # Only log if we have few devices
                        logger.info(f'Sent data from {device["device_name"]}: {data["sensor_readings"]}')
                    
                    # Flush messages immediately for better batching
                    self.producer.poll(0)
                    
                    # Small delay between messages from the same device
                    time.sleep(0.1)
                
                # Wait for the next batch
                time.sleep(max(0, self.update_interval - 0.1 * len(self.devices)))
                
        except KeyboardInterrupt:
            logger.info('Shutting down producer...')
        finally:
            # Flush any remaining messages
            self.producer.flush()
            logger.info('Producer shut down complete')

if __name__ == '__main__':
    producer = IoTDataProducer()
    producer.run()
