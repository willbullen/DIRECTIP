"""
MQTT Publisher for EUCAWS Weather Data

Publishes decoded EUCAWS weather observations to MQTT broker
following the MIDDLEMIN topic structure: valentia/eucaws/{station_id}/observation
"""
import json
import logging
import paho.mqtt.client as mqtt
from django.conf import settings
from datetime import datetime

logger = logging.getLogger(__name__)


class EUCAWSMQTTPublisher:
    """
    Publishes EUCAWS weather data to MQTT broker
    
    Topic structure: valentia/eucaws/{station_id}/observation
    """
    
    def __init__(self):
        self.broker_host = getattr(settings, 'MQTT_BROKER_HOST', '138.68.158.9')
        self.broker_port = getattr(settings, 'MQTT_BROKER_PORT', 1883)
        self.username = getattr(settings, 'MQTT_USERNAME', 'admin')
        self.password = getattr(settings, 'MQTT_PASSWORD', 'B@ff1ed!2025')
        self.qos = 1
        self.client = None
        self.connected = False
        
    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client = mqtt.Client(client_id=f"directip_publisher_{datetime.now().timestamp()}")
            self.client.username_pw_set(self.username, self.password)
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish
            
            logger.info(f"[MQTT] Connecting to {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
        except Exception as e:
            logger.error(f"[MQTT] Connection error: {e}")
            self.connected = False
            
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to broker"""
        if rc == 0:
            self.connected = True
            logger.info("[MQTT] Connected successfully")
        else:
            self.connected = False
            logger.error(f"[MQTT] Connection failed with code {rc}")
            
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from broker"""
        self.connected = False
        if rc != 0:
            logger.warning(f"[MQTT] Unexpected disconnection (code {rc})")
        else:
            logger.info("[MQTT] Disconnected")
            
    def _on_publish(self, client, userdata, mid):
        """Callback when message is published"""
        logger.debug(f"[MQTT] Message {mid} published")
        
    def publish_observation(self, imei, eucaws_data):
        """
        Publish EUCAWS observation data to MQTT
        
        Args:
            imei: Station IMEI (used as station_id)
            eucaws_data: Dictionary containing decoded EUCAWS weather data
        """
        if not self.connected:
            logger.warning("[MQTT] Not connected, attempting to connect...")
            self.connect()
            
        if not self.connected:
            logger.error("[MQTT] Cannot publish - not connected to broker")
            return False
            
        try:
            # Use IMEI directly in topic: valentia/eucaws/{IMEI}/telemetry
            topic = f"valentia/eucaws/{imei}/telemetry" if imei else "valentia/eucaws/unknown/telemetry"
            
            # Build MQTT payload matching MIDDLEMIN format
            payload = {
                "observation_time": eucaws_data.get('timestamp').isoformat() if eucaws_data.get('timestamp') else datetime.utcnow().isoformat() + 'Z',
            }
            
            # Add location if available
            if eucaws_data.get('latitude') is not None:
                payload['latitude'] = float(eucaws_data['latitude'])
            if eucaws_data.get('longitude') is not None:
                payload['longitude'] = float(eucaws_data['longitude'])
                
            # Add wind data
            if eucaws_data.get('wind_speed_ms') is not None:
                payload['wind_speed'] = float(eucaws_data['wind_speed_ms'])
            if eucaws_data.get('wind_direction') is not None:
                payload['wind_direction'] = int(eucaws_data['wind_direction'])
                
            # Add temperature data
            if eucaws_data.get('air_temperature') is not None:
                payload['air_temperature'] = float(eucaws_data['air_temperature'])
            if eucaws_data.get('sea_temperature') is not None:
                # Note: MIDDLEMIN doesn't have sea_temperature, could add as custom field
                pass
                
            # Add humidity
            if eucaws_data.get('relative_humidity') is not None:
                payload['relative_humidity'] = float(eucaws_data['relative_humidity'])
                
            # Add pressure
            if eucaws_data.get('barometric_pressure') is not None:
                payload['atmospheric_pressure'] = float(eucaws_data['barometric_pressure'])
                
            # Add quality flag
            payload['data_quality_flag'] = 0 if eucaws_data.get('is_decoded') else 1
            
            # Publish to MQTT
            payload_json = json.dumps(payload)
            result = self.client.publish(topic, payload_json, qos=self.qos)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"[MQTT] Published to {topic}: {len(payload)} fields")
                return {'success': True, 'topic': topic}
            else:
                logger.error(f"[MQTT] Publish failed with code {result.rc}")
                return {'success': False, 'topic': topic}
                
        except Exception as e:
            logger.error(f"[MQTT] Error publishing observation: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("[MQTT] Disconnected")


# Global publisher instance
_publisher_instance = None


def get_mqtt_publisher():
    """Get or create the global MQTT publisher instance"""
    global _publisher_instance
    
    if _publisher_instance is None:
        _publisher_instance = EUCAWSMQTTPublisher()
        _publisher_instance.connect()
        
    return _publisher_instance


def publish_eucaws_to_mqtt(imei, eucaws_data):
    """
    Convenience function to publish EUCAWS data to MQTT
    
    Args:
        imei: Station IMEI
        eucaws_data: Decoded EUCAWS weather data dictionary
    """
    publisher = get_mqtt_publisher()
    return publisher.publish_observation(imei, eucaws_data)
