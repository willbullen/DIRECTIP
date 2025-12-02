import socket
import threading
import logging
from django.utils import timezone
from .models import SatelliteData
from .iridium_parser import parse_iridium_message, extract_imei_simple
from .eucaws_decoder import decode_eucaws_payload

logger = logging.getLogger(__name__)


class SatelliteSocketServer:
    """TCP Socket server to receive satellite data on port 7777"""
    
    def __init__(self, host='0.0.0.0', port=7777):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        
    def start(self):
        """Start the TCP socket server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            logger.info(f"[Socket] TCP server listening on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    # Handle each client in a separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except Exception as e:
                    if self.running:
                        logger.error(f"[Socket] Error accepting connection: {e}")
                        
        except Exception as e:
            logger.error(f"[Socket] Server error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
    
    def handle_client(self, client_socket, address):
        """Handle incoming client connection and data"""
        try:
            # Receive data from client
            data = client_socket.recv(4096)
            
            if data:
                # Parse Iridium SBD message
                parsed = parse_iridium_message(data)
                
                # Extract IMEI if parsing failed
                if not parsed.get('imei'):
                    parsed['imei'] = extract_imei_simple(data)
                
                payload = data.decode('utf-8', errors='replace')
                
                # Try to decode EUCAWS payload (30 bytes)
                eucaws_data = {}
                if len(data) == 30:
                    try:
                        eucaws_data = decode_eucaws_payload(data)
                        logger.info(f"[Socket] EUCAWS decoded: {eucaws_data.get('is_decoded')}")
                    except Exception as e:
                        logger.error(f"[Socket] EUCAWS decode error: {e}")
                
                # Save to database with parsed fields
                SatelliteData.objects.create(
                    source_ip=address[0],
                    source_port=address[1],
                    payload=payload,
                    payload_size=len(data),
                    timestamp=timezone.now(),
                    # Parsed Iridium fields
                    imei=parsed.get('imei'),
                    message_sequence=parsed.get('cdr_reference'),
                    session_status=parsed.get('session_status'),
                    momsn=parsed.get('momsn'),
                    mtmsn=parsed.get('mtmsn'),
                    session_time=parsed.get('session_time'),
                    latitude=parsed.get('latitude') or eucaws_data.get('latitude'),
                    longitude=parsed.get('longitude') or eucaws_data.get('longitude'),
                    cep_radius=parsed.get('cep_radius'),
                    decoded_payload=parsed.get('decoded_payload'),
                    payload_hex=parsed.get('payload_hex'),
                    is_parsed=parsed.get('is_parsed', False),
                    parse_error=parsed.get('parse_error'),
                    # EUCAWS weather fields
                    eucaws_timestamp=eucaws_data.get('timestamp'),
                    wind_speed_ms=eucaws_data.get('wind_speed_ms'),
                    wind_speed_knots=eucaws_data.get('wind_speed_knots'),
                    wind_direction=eucaws_data.get('wind_direction'),
                    air_temperature=eucaws_data.get('air_temperature'),
                    sea_temperature=eucaws_data.get('sea_temperature'),
                    barometric_pressure=eucaws_data.get('barometric_pressure'),
                    relative_humidity=eucaws_data.get('relative_humidity'),
                    is_eucaws_decoded=eucaws_data.get('is_decoded', False),
                    eucaws_decode_error=eucaws_data.get('decode_error'),
                )
                
                logger.info(f"[Socket] Received {len(data)} bytes from {address[0]}:{address[1]}")
                
        except Exception as e:
            logger.error(f"[Socket] Error handling client {address}: {e}")
        finally:
            client_socket.close()
    
    def stop(self):
        """Stop the socket server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("[Socket] Server stopped")


# Global server instance
_server_instance = None


def start_socket_server():
    """Start the socket server in a background thread"""
    global _server_instance
    
    if _server_instance is None:
        _server_instance = SatelliteSocketServer()
        server_thread = threading.Thread(target=_server_instance.start)
        server_thread.daemon = True
        server_thread.start()
        logger.info("[Socket] Background server thread started")


def stop_socket_server():
    """Stop the socket server"""
    global _server_instance
    
    if _server_instance:
        _server_instance.stop()
        _server_instance = None
