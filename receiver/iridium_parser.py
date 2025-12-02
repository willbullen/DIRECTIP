"""
Iridium SBD (Short Burst Data) DirectIP Protocol Parser

This module parses Iridium SBD DirectIP messages according to the protocol specification.
The DirectIP protocol uses Information Elements (IEs) with a header structure.
"""

import struct
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple


class IridiumSBDParser:
    """Parser for Iridium SBD DirectIP protocol messages"""
    
    # Information Element IDs
    IE_HEADER = 0x01
    IE_PAYLOAD = 0x02
    IE_LOCATION = 0x03
    IE_CONFIRMATION = 0x05
    
    def __init__(self, data: bytes):
        self.data = data
        self.position = 0
        self.parsed_data = {}
        
    def parse(self) -> Dict[str, Any]:
        """Parse the complete Iridium SBD message"""
        try:
            # Protocol revision (1 byte)
            if len(self.data) < 3:
                raise ValueError("Message too short")
            
            protocol_revision = self.data[0]
            self.position = 1
            
            # Overall message length (2 bytes, big-endian)
            overall_length = struct.unpack('>H', self.data[1:3])[0]
            self.position = 3
            
            self.parsed_data['protocol_revision'] = protocol_revision
            self.parsed_data['message_length'] = overall_length
            
            # Parse Information Elements
            while self.position < len(self.data):
                if self.position + 3 > len(self.data):
                    break
                    
                ie_id = self.data[self.position]
                ie_length = struct.unpack('>H', self.data[self.position+1:self.position+3])[0]
                self.position += 3
                
                if self.position + ie_length > len(self.data):
                    break
                
                ie_data = self.data[self.position:self.position+ie_length]
                self.position += ie_length
                
                # Parse based on IE type
                if ie_id == self.IE_HEADER:
                    self._parse_header(ie_data)
                elif ie_id == self.IE_PAYLOAD:
                    self._parse_payload(ie_data)
                elif ie_id == self.IE_LOCATION:
                    self._parse_location(ie_data)
                elif ie_id == self.IE_CONFIRMATION:
                    self._parse_confirmation(ie_data)
            
            self.parsed_data['is_parsed'] = True
            return self.parsed_data
            
        except Exception as e:
            self.parsed_data['is_parsed'] = False
            self.parsed_data['parse_error'] = str(e)
            return self.parsed_data
    
    def _parse_header(self, data: bytes):
        """Parse the Header Information Element"""
        if len(data) < 28:
            return
        
        # CDR reference (4 bytes)
        cdr_reference = struct.unpack('>I', data[0:4])[0]
        
        # IMEI (15 bytes ASCII)
        imei = data[4:19].decode('ascii', errors='ignore').strip()
        
        # Session status (1 byte)
        session_status = data[19]
        
        # MOMSN (2 bytes)
        momsn = struct.unpack('>H', data[20:22])[0]
        
        # MTMSN (2 bytes)
        mtmsn = struct.unpack('>H', data[22:24])[0]
        
        # Session time (4 bytes, Unix timestamp)
        session_time_unix = struct.unpack('>I', data[24:28])[0]
        session_time = datetime.fromtimestamp(session_time_unix, tz=timezone.utc)
        
        self.parsed_data.update({
            'cdr_reference': cdr_reference,
            'imei': imei,
            'session_status': session_status,
            'momsn': momsn,
            'mtmsn': mtmsn,
            'session_time': session_time,
        })
    
    def _parse_payload(self, data: bytes):
        """Parse the Payload Information Element"""
        self.parsed_data['payload_hex'] = data.hex()
        
        # Try to decode as ASCII text
        try:
            decoded = data.decode('ascii', errors='ignore')
            if decoded.isprintable():
                self.parsed_data['decoded_payload'] = decoded
            else:
                self.parsed_data['decoded_payload'] = f"Binary data ({len(data)} bytes)"
        except:
            self.parsed_data['decoded_payload'] = f"Binary data ({len(data)} bytes)"
    
    def _parse_location(self, data: bytes):
        """Parse the Location Information Element"""
        if len(data) < 11:
            return
        
        # Reserved (1 byte)
        # Latitude (4 bytes, signed, degrees * 1000000)
        lat_raw = struct.unpack('>i', data[1:5])[0]
        latitude = lat_raw / 1000000.0
        
        # Longitude (4 bytes, signed, degrees * 1000000)
        lon_raw = struct.unpack('>i', data[5:9])[0]
        longitude = lon_raw / 1000000.0
        
        # CEP radius (2 bytes, unsigned, in meters)
        cep_radius = struct.unpack('>H', data[9:11])[0]
        
        self.parsed_data.update({
            'latitude': latitude,
            'longitude': longitude,
            'cep_radius': cep_radius,
        })
    
    def _parse_confirmation(self, data: bytes):
        """Parse the Confirmation Information Element"""
        if len(data) < 1:
            return
        
        confirmation_status = data[0]
        self.parsed_data['confirmation_status'] = confirmation_status


def parse_iridium_message(data: bytes) -> Dict[str, Any]:
    """
    Parse an Iridium SBD DirectIP message
    
    Args:
        data: Raw bytes from the socket connection
        
    Returns:
        Dictionary containing parsed fields
    """
    parser = IridiumSBDParser(data)
    return parser.parse()


def extract_imei_simple(data: bytes) -> Optional[str]:
    """
    Simple IMEI extraction for cases where full parsing fails
    Looks for 15-digit numeric sequences
    """
    try:
        # Try to find IMEI pattern in the data
        text = data.decode('ascii', errors='ignore')
        import re
        imei_match = re.search(r'\d{15}', text)
        if imei_match:
            return imei_match.group(0)
    except:
        pass
    return None
