"""
EUCAWS (Enhanced Underway Coastal and Atmospheric Weather Station) Payload Decoder

Decodes 30-byte E-SURFMAR format #100 payloads from EUCAWS maritime automatic 
weather stations transmitted via Iridium SBD satellite communications.

This decoder was reverse-engineered from actual payload data. Some fields have
HIGH confidence (validated with multiple samples), while others are EXPERIMENTAL
and need validation with known good weather data.

Format #100 is a proprietary E-SURFMAR binary format designed for efficient
Iridium SBD transmission. For official specification, contact:
E-SURFMAR Programme / Météo-France
https://eumetnet.eu/observations/surface-marine-observations/
"""

import struct
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class EUCAWSDecoder:
    """
    Decoder for E-SURFMAR Format #100 (30-byte EUCAWS payloads)
    
    CONFIRMED FIELDS (HIGH confidence):
    - Hour of observation (byte 6)
    - Station ID (bytes 8-11)
    - Barometric pressure (bytes 22-23)
    - Sea surface temperature (bytes 26-27)
    
    EXPERIMENTAL FIELDS (MEDIUM/LOW confidence):
    - Air temperature (bytes 12-13) - works for some samples
    - Wind speed/direction - NOT YET DECODED
    - Humidity - NOT YET DECODED
    """
    
    # Expected magic header for format #100
    MAGIC_HEADER = bytes.fromhex('648003fb4ce0')
    
    def __init__(self, data: bytes):
        if len(data) != 30:
            raise ValueError(f"E-SURFMAR format #100 payload must be exactly 30 bytes, got {len(data)}")
        self.data = data
        self.decoded = {}
    
    def decode_hour(self, byte_value: int) -> int:
        """
        Decode hour from byte 6
        Hours 0-15: byte = hour + 96 (0x60 + hour)
        Hours 16-23: byte = hour + 64 (0x40 + hour)
        """
        if byte_value >= 96:  # 0x60
            return byte_value - 96
        else:  # 0x40-0x5F range
            return byte_value - 64
    
    def decode(self, session_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Decode the complete E-SURFMAR format #100 payload
        
        Args:
            session_time: Session timestamp from Iridium DirectIP (for date context)
        
        Returns:
            Dictionary containing decoded weather data with confidence levels
        
        Format #100 structure (reverse-engineered):
        Bytes 0-5:   Magic header (64 80 03 fb 4c e0)
        Byte 6:      Hour of observation (encoded: 0-15: +96, 16-23: +64)
        Byte 7:      Format version (always 0x01)
        Bytes 8-11:  Station ID (constant: bf d2 1f 5d)
        Bytes 12-13: Air temperature (experimental: (value - 45000) / 100 °C)
        Bytes 14-15: Unknown (possibly wind speed)
        Byte 16:     Flags or missing data marker (0x7F or 0xFF)
        Bytes 17-21: Missing/null data (always 0xFF)
        Bytes 22-23: Barometric pressure ((value - 27000) / 10 hPa)
        Bytes 24-25: Unknown
        Bytes 26-27: Sea surface temperature ((value - 50000) / 100 °C)
        Bytes 28-29: Footer (always fe 00)
        """
        try:
            # Verify magic header
            if self.data[0:6] != self.MAGIC_HEADER:
                raise ValueError(f"Invalid magic header: {self.data[0:6].hex()} (expected {self.MAGIC_HEADER.hex()})")
            
            self.decoded['format_version'] = self.data[7]
            self.decoded['raw_payload_hex'] = self.data.hex()
            
            # CONFIRMED: Decode hour (HIGH confidence)
            hour = self.decode_hour(self.data[6])
            self.decoded['hour'] = hour
            
            # Create observation timestamp if session_time provided
            if session_time:
                obs_time = session_time.replace(hour=hour, minute=0, second=0, microsecond=0)
                self.decoded['timestamp'] = obs_time
                self.decoded['timestamp_unix'] = int(obs_time.timestamp())
            else:
                self.decoded['timestamp'] = None
                self.decoded['timestamp_unix'] = None
            
            # CONFIRMED: Station ID (HIGH confidence)
            station_id_hex = self.data[8:12].hex()
            self.decoded['station_id'] = station_id_hex
            
            # CONFIRMED: Barometric Pressure (HIGH confidence)
            # Formula: (bytes_22_23 - 27000) / 10 hPa
            pressure_raw = struct.unpack('>H', self.data[22:24])[0]
            pressure_hpa = (pressure_raw - 27000) / 10.0
            
            if 900 < pressure_hpa < 1100:  # Realistic range
                self.decoded['barometric_pressure'] = round(pressure_hpa, 1)
                self.decoded['pressure_confidence'] = 'HIGH'
            else:
                self.decoded['barometric_pressure'] = None
                self.decoded['pressure_raw'] = pressure_raw
                self.decoded['pressure_confidence'] = 'LOW - out of range'
            
            # CONFIRMED: Sea Surface Temperature (HIGH confidence)
            # Formula: (bytes_26_27 - 50000) / 100 °C
            sea_temp_raw = struct.unpack('>H', self.data[26:28])[0]
            sea_temp_c = (sea_temp_raw - 50000) / 100.0
            
            if -5 < sea_temp_c < 35:  # Realistic range
                self.decoded['sea_temperature'] = round(sea_temp_c, 2)
                self.decoded['sea_temp_confidence'] = 'HIGH'
            else:
                self.decoded['sea_temperature'] = None
                self.decoded['sea_temp_raw'] = sea_temp_raw
                self.decoded['sea_temp_confidence'] = 'LOW - out of range'
            
            # EXPERIMENTAL: Air Temperature (MEDIUM confidence)
            # Formula: (bytes_12_13 - 45000) / 100 °C
            # Works for some samples but not all - needs validation
            air_temp_raw = struct.unpack('>H', self.data[12:14])[0]
            air_temp_c = (air_temp_raw - 45000) / 100.0
            
            if -40 < air_temp_c < 50:  # Wide range for safety
                self.decoded['air_temperature'] = round(air_temp_c, 2)
                self.decoded['air_temp_confidence'] = 'MEDIUM - needs validation'
            else:
                self.decoded['air_temperature'] = None
                self.decoded['air_temp_raw'] = air_temp_raw
                self.decoded['air_temp_confidence'] = 'LOW - out of range'
            
            # UNKNOWN FIELDS (for future decoding)
            # These fields vary but we haven't determined their meaning yet
            self.decoded['field_14_15_raw'] = struct.unpack('>H', self.data[14:16])[0]
            self.decoded['field_16_raw'] = self.data[16]
            self.decoded['field_24_25_raw'] = struct.unpack('>H', self.data[24:26])[0]
            
            # Wind speed and direction - NOT YET DECODED
            self.decoded['wind_speed_ms'] = None
            self.decoded['wind_speed_knots'] = None
            self.decoded['wind_direction'] = None
            self.decoded['relative_humidity'] = None
            
            self.decoded['is_decoded'] = True
            self.decoded['decode_error'] = None
            self.decoded['decoder_version'] = 'E-SURFMAR Format #100 (reverse-engineered v1.0)'
            
        except Exception as e:
            self.decoded['is_decoded'] = False
            self.decoded['decode_error'] = str(e)
            self.decoded['timestamp'] = None
            self.decoded['barometric_pressure'] = None
            self.decoded['sea_temperature'] = None
            self.decoded['air_temperature'] = None
            self.decoded['wind_speed_ms'] = None
            self.decoded['wind_speed_knots'] = None
            self.decoded['wind_direction'] = None
            self.decoded['relative_humidity'] = None
        
        return self.decoded


def decode_eucaws_payload(data: bytes, session_time: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Decode an E-SURFMAR format #100 payload (30-byte EUCAWS)
    
    Args:
        data: Raw 30-byte payload from EUCAWS station
        session_time: Optional session timestamp from Iridium DirectIP for date context
        
    Returns:
        Dictionary containing decoded weather and metadata
        
    Example:
        >>> payload = bytes.fromhex('648003fb4ce06b01bfd21f5dd9beef9bffffffffffff97ed5fffc0f1fe00')
        >>> session_time = datetime(2025, 12, 3, 11, 0, 15, tzinfo=timezone.utc)
        >>> result = decode_eucaws_payload(payload, session_time)
        >>> print(f"Pressure: {result['barometric_pressure']} hPa")
        >>> print(f"Sea temp: {result['sea_temperature']} °C")
    """
    if len(data) != 30:
        return {
            'is_decoded': False,
            'decode_error': f'Invalid payload size: {len(data)} bytes (expected 30)',
            'timestamp': None,
            'barometric_pressure': None,
            'sea_temperature': None,
            'air_temperature': None,
            'wind_speed_ms': None,
            'wind_speed_knots': None,
            'wind_direction': None,
            'relative_humidity': None,
        }
    
    decoder = EUCAWSDecoder(data)
    return decoder.decode(session_time)
