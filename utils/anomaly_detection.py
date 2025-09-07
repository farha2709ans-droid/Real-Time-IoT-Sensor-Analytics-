import numpy as np
from typing import Dict, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AnomalyDetector:
    """
    A class for detecting anomalies in time series data using statistical methods.
    """
    
    def __init__(self, window_size: int = 10, threshold: float = 3.0):
        """
        Initialize the anomaly detector.
        
        Args:
            window_size: Number of previous values to consider for statistics
            threshold: Number of standard deviations from the mean to consider an anomaly
        """
        self.window_size = window_size
        self.threshold = threshold
        self.windows: Dict[str, list] = {}
        
        logger.info(f'Initialized AnomalyDetector with window_size={window_size}, threshold={threshold}')
    
    def _update_window(self, device_id: str, sensor_type: str, value: float) -> None:
        """
        Update the rolling window for a specific device and sensor type.
        
        Args:
            device_id: Unique identifier for the device
            sensor_type: Type of sensor (e.g., 'temperature', 'humidity')
            value: The sensor reading value
        """
        key = f"{device_id}:{sensor_type}"
        
        if key not in self.windows:
            self.windows[key] = []
        
        self.windows[key].append(value)
        
        # Maintain the window size
        if len(self.windows[key]) > self.window_size:
            self.windows[key].pop(0)
    
    def detect_anomaly(
        self, 
        device_id: str, 
        sensor_type: str, 
        value: float,
        timestamp: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        Detect if a sensor reading is anomalous.
        
        Args:
            device_id: Unique identifier for the device
            sensor_type: Type of sensor (e.g., 'temperature', 'humidity')
            value: The sensor reading value
            timestamp: Optional timestamp of the reading
            
        Returns:
            Tuple of (is_anomaly, anomaly_info)
        """
        key = f"{device_id}:{sensor_type}"
        
        # If we don't have enough data yet, just update the window
        if key not in self.windows or len(self.windows[key]) < 5:  # Minimum 5 points for stats
            self._update_window(device_id, sensor_type, value)
            return False, {"reason": "Insufficient data", "window_size": len(self.windows.get(key, []))}
        
        # Calculate statistics
        window = self.windows[key]
        mean = np.mean(window)
        std = np.std(window)
        
        # Handle case where std is 0 (all values are the same)
        if std == 0:
            std = 1e-10
        
        # Calculate z-score
        z_score = abs((value - mean) / std)
        is_anomaly = z_score > self.threshold
        
        # Update the window with the current value
        self._update_window(device_id, sensor_type, value)
        
        # Prepare anomaly info
        anomaly_info = {
            "is_anomaly": is_anomaly,
            "z_score": float(z_score),
            "mean": float(mean),
            "std": float(std),
            "current_value": float(value),
            "window_size": len(window),
            "threshold": self.threshold,
            "timestamp": timestamp
        }
        
        if is_anomaly:
            logger.warning(
                f"Anomaly detected for {device_id} {sensor_type}: "
                f"value={value:.2f}, mean={mean:.2f}, std={std:.2f}, z-score={z_score:.2f}"
            )
        
        return is_anomaly, anomaly_info

# Example usage
if __name__ == "__main__":
    # Initialize the anomaly detector
    detector = AnomalyDetector(window_size=10, threshold=3.0)
    
    # Simulate some normal data
    normal_data = [25.0, 25.1, 24.9, 25.2, 25.0, 25.1, 24.8, 25.0, 25.2, 25.1]
    
    print("Testing with normal data:")
    for i, value in enumerate(normal_data):
        is_anomaly, info = detector.detect_anomaly("device_001", "temperature", value)
        print(f"Value: {value:.2f}, Anomaly: {is_anomaly}, Z-score: {info.get('z_score', 0):.2f}")
    
    # Test with an anomalous value
    print("\nTesting with anomalous data:")
    is_anomaly, info = detector.detect_anomaly("device_001", "temperature", 30.0)
    print(f"Value: 30.0, Anomaly: {is_anomaly}, Z-score: {info.get('z_score', 0):.2f}")
