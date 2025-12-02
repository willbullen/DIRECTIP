"""
EUCAWS (Enhanced Underway Coastal and Atmospheric Weather Station) Payload Decoder

Decodes 30-byte binary payloads from EUCAWS maritime automatic weather stations
transmitted via Iridium SBD satellite communications.
"""

import struct
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class EUCAWSDecoder:
    """Decoder for EUCAWS 30-byte binary payloads"""
    
    # Null/No Data indicators
    NULL_UINT16 = 0xFFFF
    NULL_INT16 = 0x7FFF
    NULL_INT16_NEG = -1
    
    def __init__(self, data: bytes):
        if len(data) != 30:
            raise ValueError(f"EUCAWS payload must be exactly 30 bytes, got {len(data)}")
        self.data = data
        self.decoded = {}
        
    def decode(self) -> Dict[str, Any]:
        """
        Decode the complete EUCAWS payload
        
        Standard EUCAWS 30-byte format (big-endian):
        Bytes 0-3:   Timestamp (Unix time, uint32)
        Bytes 4-7:   Latitude (int32, degrees * 1000000)
        Bytes 8-11:  Longitude (int32, degrees * 1000000)
        Bytes 12-13: Wind Speed (uint16, m/s * 100 or knots * 100)
        Bytes 14-15: Wind Direction (uint16, degrees * 10)
        Bytes 16-17: Air Temperature (int16, °C * 10)
        Bytes 18-19: Sea Temperature (int16, °C * 10)
        Bytes 20-21: Barometric Pressure (uint16, hPa * 10)
        Bytes 22-23: Relative Humidity (uint16, % * 10)
        Bytes 24-25: Additional Sensor 1
        Bytes 26-27: Additional Sensor 2  
        Bytes 28-29: Additional Sensor 3 / Checksum
        """
        try:
            # Timestamp (bytes 0-3)
            timestamp_raw = struct.unpack('>I', self.data[0:4])[0]
            try:
                self.decoded['timestamp'] = datetime.fromtimestamp(timestamp_raw, tz=timezone.utc)
                self.decoded['timestamp_unix'] = timestamp_raw
            except (ValueError, OSError):
                self.decoded['timestamp'] = None
                self.decoded['timestamp_unix'] = timestamp_raw
            
            # GPS Coordinates (bytes 4-11)
            lat_raw = struct.unpack('>i', self.data[4:8])[0]
            lon_raw = struct.unpack('>i', self.data[8:12])[0]
            
            # Validate GPS coordinates (must be within valid ranges)
            latitude = lat_raw / 1000000.0
            longitude = lon_raw / 1000000.0
            
            if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                self.decoded['latitude'] = latitude
                self.decoded['longitude'] = longitude
            else:
                self.decoded['latitude'] = None
                self.decoded['longitude'] = None
            
            # Wind Speed (bytes 12-13)
            wind_speed_raw = struct.unpack('>H', self.data[12:14])[0]
            if wind_speed_raw == self.NULL_UINT16:
                self.decoded['wind_speed_ms'] = None
                self.decoded['wind_speed_knots'] = None
            else:
                # Assume m/s * 100
                wind_ms = wind_speed_raw / 100.0
                if wind_ms > 100:  # Unrealistic, might be knots
                    self.decoded['wind_speed_ms'] = None
                    self.decoded['wind_speed_knots'] = wind_speed_raw / 100.0
                else:
                    self.decoded['wind_speed_ms'] = wind_ms
                    self.decoded['wind_speed_knots'] = wind_ms * 1.94384  # Convert to knots
            
            # Wind Direction (bytes 14-15)
            wind_dir_raw = struct.unpack('>H', self.data[14:16])[0]
            if wind_dir_raw == self.NULL_UINT16:
                self.decoded['wind_direction'] = None
            else:
                wind_dir = wind_dir_raw / 10.0
                if 0 <= wind_dir <= 360:
                    self.decoded['wind_direction'] = wind_dir
                else:
                    self.decoded['wind_direction'] = None
            
            # Air Temperature (bytes 16-17)
            air_temp_raw = struct.unpack('>h', self.data[16:18])[0]
            if air_temp_raw == self.NULL_INT16 or air_temp_raw == self.NULL_INT16_NEG:
                self.decoded['air_temperature'] = None
            else:
                air_temp = air_temp_raw / 10.0
                if -50 <= air_temp <= 60:  # Realistic range
                    self.decoded['air_temperature'] = air_temp
                else:
                    self.decoded['air_temperature'] = None
            
            # Sea Temperature (bytes 18-19)
            sea_temp_raw = struct.unpack('>h', self.data[18:20])[0]
            if sea_temp_raw == self.NULL_INT16 or sea_temp_raw == self.NULL_INT16_NEG:
                self.decoded['sea_temperature'] = None
            else:
                sea_temp = sea_temp_raw / 10.0
                if -5 <= sea_temp <= 40:  # Realistic range
                    self.decoded['sea_temperature'] = sea_temp
                else:
                    self.decoded['sea_temperature'] = None
            
            # Barometric Pressure (bytes 20-21)
            pressure_raw = struct.unpack('>H', self.data[20:22])[0]
            if pressure_raw == self.NULL_UINT16:
                self.decoded['barometric_pressure'] = None
            else:
                # Try direct hPa * 10
                pressure = pressure_raw / 10.0
                if 800 <= pressure <= 1100:  # Realistic range
                    self.decoded['barometric_pressure'] = pressure
                else:
                    self.decoded['barometric_pressure'] = None
            
            # Relative Humidity (bytes 22-23)
            humidity_raw = struct.unpack('>H', self.data[22:24])[0]
            if humidity_raw == self.NULL_UINT16:
                self.decoded['relative_humidity'] = None
            else:
                humidity = humidity_raw / 10.0
                if 0 <= humidity <= 100:  # Valid percentage
                    self.decoded['relative_humidity'] = humidity
                else:
                    self.decoded['relative_humidity'] = None
            
            # Additional sensors (bytes 24-29)
            sensor1_raw = struct.unpack('>H', self.data[24:26])[0]
            sensor2_raw = struct.unpack('>H', self.data[26:28])[0]
            sensor3_raw = struct.unpack('>H', self.data[28:30])[0]
            
            self.decoded['sensor1_raw'] = sensor1_raw if sensor1_raw != self.NULL_UINT16 else None
            self.decoded['sensor2_raw'] = sensor2_raw if sensor2_raw != self.NULL_UINT16 else None
            self.decoded['sensor3_raw'] = sensor3_raw if sensor3_raw != self.NULL_UINT16 else None
            
            self.decoded['is_decoded'] = True
            self.decoded['decode_error'] = None
            
        except Exception as e:
            self.decoded['is_decoded'] = False
            self.decoded['decode_error'] = str(e)
        
        return self.decoded


def decode_eucaws_payload(data: bytes) -> Dict[str, Any]:
    """
    Decode a EUCAWS 30-byte payload
    
    Args:
        data: Raw 30-byte payload from EUCAWS station
        
    Returns:
        Dictionary containing decoded weather and ship data
    """
    if len(data) != 30:
        return {
            'is_decoded': False,
            'decode_error': f'Invalid payload size: {len(data)} bytes (expected 30)'
        }
    
    decoder = EUCAWSDecoder(data)
    return decoder.decode()
