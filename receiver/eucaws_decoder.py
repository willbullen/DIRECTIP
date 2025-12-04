"""
E-SURFMAR Format #100 Decoder - Official Implementation

Based on "E-SURFMAR recommended ship-to-shore dataformats" v1.9, 2 September 2019
by Météo-France, Centre de Météorologie Marine.

Format #100 is designed for Shipborne Automated Weather Stations (S-AWS).
Minimum message length: 235 bits (30 bytes) for autonomous S-AWS without visual observations.

Reference: DOI: 10.5281/zenodo.1324186

DEPLOYMENT INSTRUCTIONS:
1. Copy this file to: /opt/DIRECTIP/utils/eucaws_decoder.py
2. Restart the socket server: docker-compose restart socket_server
3. Test with existing messages in the database
"""

import struct
from datetime import datetime, timezone
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BitReader:
    """Helper class to read bits sequentially from a byte array (MSB first)"""
    
    def __init__(self, data: bytes):
        self.data = data
        self.bit_position = 0
    
    def read_bits(self, num_bits: int) -> int:
        """Read specified number of bits and return as unsigned integer"""
        if num_bits == 0:
            return 0
            
        result = 0
        for _ in range(num_bits):
            byte_index = self.bit_position // 8
            bit_index = 7 - (self.bit_position % 8)  # MSB first within each byte
            
            if byte_index >= len(self.data):
                raise ValueError(f"Attempt to read beyond data length at bit {self.bit_position}")
            
            bit = (self.data[byte_index] >> bit_index) & 1
            result = (result << 1) | bit
            self.bit_position += 1
        
        return result
    
    def read_signed_bits(self, num_bits: int) -> int:
        """Read signed integer using two's complement representation"""
        value = self.read_bits(num_bits)
        # Check if sign bit is set (MSB)
        if value & (1 << (num_bits - 1)):
            # Convert from two's complement to negative number
            value = value - (1 << num_bits)
        return value
    
    def get_position(self) -> int:
        """Get current bit position for debugging"""
        return self.bit_position


def decode_eucaws_payload(payload_hex: str, session_time: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Decode E-SURFMAR Format #100 payload according to official specification
    
    Args:
        payload_hex: Hexadecimal string of the payload (minimum 30 bytes / 60 hex chars)
        session_time: Optional session timestamp from Iridium DirectIP (for fallback date)
    
    Returns:
        Dictionary containing decoded weather parameters and metadata
        
    Formula for all fields: Physical_value = (raw_value × slope) + offset
    Missing data indicator: All bits set to 1 for the field
    """
    result = {
        'is_decoded': False,
        'decode_error': None,
        'decoder_version': 'E-SURFMAR Format #100 Official v1.9',
        'format_version': None,
        
        # Timestamp
        'timestamp': None,
        
        # Position
        'latitude': None,
        'longitude': None,
        
        # Pressure (in hPa)
        'barometric_pressure': None,      # Pressure at barometer height
        'msl_pressure': None,              # Mean sea level pressure
        'pressure_tendency_3h': None,      # 3-hour pressure change
        'pressure_tendency_char': None,    # Characteristic of tendency (0-8)
        
        # Wind (true wind)
        'wind_direction_true': None,       # Degrees clockwise from north
        'wind_speed_ms': None,             # m/s
        'wind_speed_knots': None,          # knots (converted)
        
        # Wind (relative to ship)
        'wind_direction_relative': None,   # Degrees from bow
        'wind_speed_relative': None,       # m/s
        
        # Wind gusts
        'wind_gust_speed': None,           # m/s
        'wind_gust_direction': None,       # Degrees
        
        # Temperature (in Celsius)
        'air_temperature': None,
        'sea_temperature': None,
        
        # Humidity
        'relative_humidity': None,         # %
        
        # Technical parameters
        'battery_voltage': None,           # V
        'processor_temperature': None,     # Celsius
        'gps_height': None,                # m above sea level
        
        # Ship navigation
        'ship_course': None,               # Degrees
        'ship_speed': None,                # m/s
        'ship_heading': None,              # Degrees
        'draft': None,                     # m
        
        # Metadata
        'callsign_encrypted': None,
        'has_visual_obs': False,
        'has_wave_obs': False,
        'has_ice_obs': False,
        'has_other_obs': False,
    }
    
    try:
        # Convert hex string to bytes
        payload_bytes = bytes.fromhex(payload_hex)
        
        if len(payload_bytes) < 30:
            result['decode_error'] = f"Payload too short: {len(payload_bytes)} bytes (expected minimum 30)"
            return result
        
        reader = BitReader(payload_bytes)
        
        # ===== GREEN BLOCK (Mandatory - 235 bits) =====
        
        # 1. Format identifier (8 bits) - BUFR ID 001198
        format_id = reader.read_bits(8)
        result['format_version'] = format_id
        
        if format_id != 100:
            result['decode_error'] = f"Invalid format ID: {format_id} (expected 100 for S-AWS)"
            return result
        
        # 2. Callsign encryption indicator (1 bit) - BUFR ID 001199
        # 0 = encrypted, 1 = not encrypted
        callsign_encrypted_bit = reader.read_bits(1)
        result['callsign_encrypted'] = (callsign_encrypted_bit == 0)
        
        # 3. Ship's Course Over Ground - past 10 min (7 bits) - BUFR ID 001012 (COG10)
        # Slope=5, Offset=0, Max=360°, Missing=all 1s (127)
        cog_raw = reader.read_bits(7)
        if cog_raw != 0x7F:
            result['ship_course'] = cog_raw * 5.0
        
        # 4. Ship's Speed Over Ground - past 10 min (6 bits) - BUFR ID 001013 (SOG10)
        # Slope=0.5, Offset=0, Max=30 m/s, Missing=all 1s (63)
        sog_raw = reader.read_bits(6)
        if sog_raw != 0x3F:
            result['ship_speed'] = sog_raw * 0.5
        
        # 5. Ship's True Heading - past 10 min (7 bits) - BUFR ID 011104 (HDT10)
        # Slope=5, Offset=0, Max=360°, Missing=all 1s (127)
        hdt_raw = reader.read_bits(7)
        if hdt_raw != 0x7F:
            result['ship_heading'] = hdt_raw * 5.0
        
        # 6. Departure of summer loadline from sea level (5 bits) - BUFR ID 010039 (S_hh)
        # Slope=1, Offset=-10, Max=20m, Missing=all 1s (signed -16)
        draft_raw = reader.read_signed_bits(5)
        if draft_raw != -16:
            result['draft'] = draft_raw * 1.0 - 10.0
        
        # 7. Timestamp (Year, Month, Day, Hour, Minute)
        # Year (7 bits): Slope=1, Offset=2000, Max=2126
        year_raw = reader.read_bits(7)
        year = year_raw + 2000
        
        # Month (4 bits): 1-12
        month = reader.read_bits(4)
        
        # Day (6 bits): 1-31
        day = reader.read_bits(6)
        
        # Hour (5 bits): 0-23, UTC
        hour = reader.read_bits(5)
        
        # Minute (6 bits): 0-59
        minute = reader.read_bits(6)
        
        try:
            if 1 <= month <= 12 and 1 <= day <= 31 and 0 <= hour <= 23 and 0 <= minute <= 59:
                result['timestamp'] = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
            else:
                raise ValueError(f"Invalid date/time values: {year}-{month}-{day} {hour}:{minute}")
        except ValueError as e:
            logger.warning(f"Invalid timestamp in payload: {e}")
            result['timestamp'] = session_time if session_time else datetime.now(timezone.utc)
        
        # 8. Position
        # Latitude (15 bits): Slope=0.01, Offset=-90, Max=90°, Missing=all 1s
        lat_raw = reader.read_signed_bits(15)
        if lat_raw != -16384:  # Not all 1s
            result['latitude'] = lat_raw * 0.01 - 90.0
        
        # Longitude (16 bits): Slope=0.01, Offset=-180, Max=180°, Missing=all 1s
        lon_raw = reader.read_signed_bits(16)
        if lon_raw != -32768:  # Not all 1s
            result['longitude'] = lon_raw * 0.01 - 180.0
        
        # 9. Pressure at barometer height (11 bits) - BUFR ID 010004
        # Slope=10, Offset=85000 Pa, Max=105460 Pa, Missing=all 1s (2047)
        press_raw = reader.read_bits(11)
        if press_raw != 0x7FF:
            pressure_pa = press_raw * 10 + 85000
            result['barometric_pressure'] = pressure_pa / 100.0  # Convert Pa to hPa
        
        # 10. Mean Sea Level Pressure (11 bits) - BUFR ID 010051
        # Slope=10, Offset=85000 Pa, Max=105460 Pa, Missing=all 1s (2047)
        mslp_raw = reader.read_bits(11)
        if mslp_raw != 0x7FF:
            mslp_pa = mslp_raw * 10 + 85000
            result['msl_pressure'] = mslp_pa / 100.0  # Convert Pa to hPa
        
        # 11. 3-hour pressure change (10 bits) - BUFR ID 010061 (ppp)
        # Slope=10, Offset=-5000 Pa, Max=5000 Pa, Missing=all 1s (signed -512)
        ppp_raw = reader.read_signed_bits(10)
        if ppp_raw != -512:
            ppp_pa = ppp_raw * 10 - 5000
            result['pressure_tendency_3h'] = ppp_pa / 100.0  # Convert Pa to hPa
        
        # 12. Characteristic of pressure tendency (4 bits) - BUFR ID 010063 (a)
        # Code 0-8, Missing=all 1s (15)
        a_raw = reader.read_bits(4)
        if a_raw != 0xF:
            result['pressure_tendency_char'] = a_raw
        
        # 13. True wind direction (7 bits) - BUFR ID 011001 (dd)
        # Slope=5, Offset=0, Max=360°, Missing=all 1s (127)
        dd_raw = reader.read_bits(7)
        if dd_raw != 0x7F:
            result['wind_direction_true'] = dd_raw * 5.0
        
        # 14. True wind speed (10 bits) - BUFR ID 011002 (ff)
        # Slope=0.1, Offset=0, Max=102 m/s, Missing=all 1s (1023)
        ff_raw = reader.read_bits(10)
        if ff_raw != 0x3FF:
            wind_speed_ms = ff_raw * 0.1
            result['wind_speed_ms'] = wind_speed_ms
            result['wind_speed_knots'] = wind_speed_ms * 1.94384  # Convert m/s to knots
        
        # 15. Relative wind direction (7 bits) - BUFR ID 011007 (RWD)
        # Slope=5, Offset=0, Max=360°, Missing=all 1s (127)
        rwd_raw = reader.read_bits(7)
        if rwd_raw != 0x7F:
            result['wind_direction_relative'] = rwd_raw * 5.0
        
        # 16. Relative wind speed (8 bits) - BUFR ID 011008 (RWS)
        # Slope=0.5, Offset=0, Max=127 m/s, Missing=all 1s (255)
        rws_raw = reader.read_bits(8)
        if rws_raw != 0xFF:
            result['wind_speed_relative'] = rws_raw * 0.5
        
        # 17. Maximum wind gust speed (8 bits) - BUFR ID 011041 (ff_max)
        # Slope=0.5, Offset=0, Max=127 m/s, Missing=all 1s (255)
        ffmax_raw = reader.read_bits(8)
        if ffmax_raw != 0xFF:
            result['wind_gust_speed'] = ffmax_raw * 0.5
        
        # 18. Maximum wind gust direction (7 bits) - BUFR ID 011043 (dd(ff_max))
        # Slope=5, Offset=0, Max=360°, Missing=all 1s (127)
        ddmax_raw = reader.read_bits(7)
        if ddmax_raw != 0x7F:
            result['wind_gust_direction'] = ddmax_raw * 5.0
        
        # 19. Air temperature (10 bits) - BUFR ID 012101 (Ta)
        # Slope=0.1, Offset=223.2 K, Max=325.4 K, Missing=all 1s (1023)
        ta_raw = reader.read_bits(10)
        if ta_raw != 0x3FF:
            temp_k = ta_raw * 0.1 + 223.2
            result['air_temperature'] = temp_k - 273.15  # Convert Kelvin to Celsius
        
        # 20. Relative humidity (10 bits) - BUFR ID 013009 (U)
        # Slope=0.1, Offset=0, Max=100 %, Missing=all 1s (1023)
        u_raw = reader.read_bits(10)
        if u_raw != 0x3FF:
            result['relative_humidity'] = u_raw * 0.1
        
        # 21. Sea surface temperature (12 bits) - BUFR ID 022043 (SST)
        # Slope=0.01, Offset=268.15 K, Max=309.05 K, Missing=all 1s (4095)
        sst_raw = reader.read_bits(12)
        if sst_raw != 0xFFF:
            temp_k = sst_raw * 0.01 + 268.15
            result['sea_temperature'] = temp_k - 273.15  # Convert Kelvin to Celsius
        
        # 22. Battery voltage (7 bits) - BUFR ID 025026 (Vbat)
        # Slope=0.2, Offset=5.0 V, Max=30.2 V, Missing=all 1s (127)
        vbat_raw = reader.read_bits(7)
        if vbat_raw != 0x7F:
            result['battery_voltage'] = vbat_raw * 0.2 + 5.0
        
        # 23. Processor temperature (8 bits) - BUFR ID 010201 (T_proc)
        # Slope=0.5, Offset=233.15 K, Max=360.15 K, Missing=all 1s (255)
        tproc_raw = reader.read_bits(8)
        if tproc_raw != 0xFF:
            temp_k = tproc_raw * 0.5 + 233.15
            result['processor_temperature'] = temp_k - 273.15  # Convert Kelvin to Celsius
        
        # 24. GPS height above sea level (8 bits) - BUFR ID 010200
        # Slope=1, Offset=-50 m, Max=204 m, Missing=all 1s (signed -128)
        gps_h_raw = reader.read_signed_bits(8)
        if gps_h_raw != -128:
            result['gps_height'] = gps_h_raw * 1.0 - 50.0
        
        # 25. Optional blocks presence indicators (4 bits at end of green block)
        result['has_visual_obs'] = bool(reader.read_bits(1))
        result['has_wave_obs'] = bool(reader.read_bits(1))
        result['has_ice_obs'] = bool(reader.read_bits(1))
        result['has_other_obs'] = bool(reader.read_bits(1))
        
        # Total bits read: 235 bits = 29.375 bytes (30 bytes with padding)
        logger.info(f"[EUCAWS] Decoded Format #100 successfully. Bit position: {reader.get_position()}")
        
        # Optional blocks (Yellow, Blue-violet, Pink-violet, Orange) are not decoded yet
        # They would follow after the green block if presence indicators are set
        
        result['is_decoded'] = True
        
    except Exception as e:
        result['decode_error'] = str(e)
        logger.error(f"[EUCAWS] Decode error: {e}", exc_info=True)
    
    return result


# Backward compatibility function for existing code
def decode_eucaws_payload_legacy(data: bytes, session_time: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Legacy function signature that accepts bytes instead of hex string
    Converts to hex and calls the main decoder
    """
    return decode_eucaws_payload(data.hex(), session_time)


if __name__ == "__main__":
    # Test with a sample payload
    import sys
    
    # Example payload from actual EUCAWS transmission
    test_payload = "648003fb4ce06b01bfd21f5dd9beef9bffffffffffff97ed5fffc0f1fe00"
    
    print("=" * 80)
    print("E-SURFMAR Format #100 Decoder - Test")
    print("=" * 80)
    print(f"Payload: {test_payload}")
    print(f"Length: {len(test_payload) // 2} bytes")
    print()
    
    result = decode_eucaws_payload(test_payload)
    
    print("Decoding result:")
    print(f"  Decoded: {result['is_decoded']}")
    if result['decode_error']:
        print(f"  Error: {result['decode_error']}")
    print()
    
    if result['is_decoded']:
        print("Weather Parameters:")
        print(f"  Timestamp: {result['timestamp']}")
        print(f"  Position: {result['latitude']}, {result['longitude']}")
        print(f"  Air Temperature: {result['air_temperature']} °C")
        print(f"  Sea Temperature: {result['sea_temperature']} °C")
        print(f"  Barometric Pressure: {result['barometric_pressure']} hPa")
        print(f"  MSL Pressure: {result['msl_pressure']} hPa")
        print(f"  Wind Speed: {result['wind_speed_ms']} m/s ({result['wind_speed_knots']} knots)")
        print(f"  Wind Direction: {result['wind_direction_true']}°")
        print(f"  Relative Humidity: {result['relative_humidity']} %")
        print(f"  Battery Voltage: {result['battery_voltage']} V")
