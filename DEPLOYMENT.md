# DIRECTIP - EUCAWS Deployment Guide

## Overview

DIRECTIP is a Django-based satellite data receiver system for EUCAWS (Enhanced Underway Coastal and Atmospheric Weather System) data transmitted via Iridium SBD (Short Burst Data).

**Features:**
- ✅ TCP socket server on port 7777 for Iridium DirectIP connections
- ✅ EUCAWS 30-byte payload decoder (weather station data)
- ✅ MQTT publisher for real-time data forwarding
- ✅ Modern dark-themed web dashboard
- ✅ SQLite database for data persistence
- ✅ Docker containerized deployment

---

## Quick Deployment

### On Your DigitalOcean Droplet (138.68.158.9)

```bash
# Navigate to deployment directory
cd /opt
sudo rm -rf DIRECTIP  # Remove old version if exists

# Clone the repository
sudo git clone https://github.com/willbullen/DIRECTIP.git
cd DIRECTIP

# Configure firewall
sudo ufw allow 3011/tcp  # Web dashboard
sudo ufw allow 7777/tcp  # Socket server
sudo ufw status

# Deploy with Docker
sudo docker compose up -d --build

# Monitor logs
sudo docker compose logs -f app
```

**Access Points:**
- **Web Dashboard**: http://138.68.158.9:3011
- **Socket Server**: Port 7777 (for Iridium DirectIP)

---

## System Architecture

```
Iridium Satellite → DirectIP (Port 7777) → Django Socket Server
                                                ↓
                                        EUCAWS Decoder
                                                ↓
                                    ┌──────────┴──────────┐
                                    ↓                     ↓
                            SQLite Database        MQTT Publisher
                                    ↓                     ↓
                            Web Dashboard      MIDDLEMIN System
```

---

## EUCAWS Data Format

The system receives 30-byte binary payloads containing:

| Bytes | Field | Description |
|-------|-------|-------------|
| 0-3 | Timestamp | Unix timestamp (UTC) |
| 4-7 | Latitude | Signed integer (×10^-7) |
| 8-11 | Longitude | Signed integer (×10^-7) |
| 12-13 | Wind Speed | Unsigned integer (knots ×100) |
| 14-15 | Wind Direction | Unsigned integer (degrees) |
| 16-17 | Air Temperature | Signed integer (°C ×100) |
| 18-19 | Sea Temperature | Signed integer (°C ×100) |
| 20-21 | Barometric Pressure | Unsigned integer (hPa ×10) |
| 22-23 | Relative Humidity | Unsigned integer (% ×10) |
| 24-29 | Reserved | Additional sensor data |

**Note**: `0xFFFF` (65535) indicates "no data" for that sensor.

---

## MQTT Configuration

The system automatically publishes decoded EUCAWS data to your MQTT broker following the MIDDLEMIN topic structure.

### MQTT Settings (Environment Variables)

```bash
MQTT_BROKER_HOST=mqtt.metvalentia.com
MQTT_BROKER_PORT=1883
MQTT_USERNAME=valentia
MQTT_PASSWORD=valentia_mqtt_2024
```

### MQTT Topic Structure

```
valentia/eucaws/{imei}/observation
```

Example: `valentia/eucaws/eucaws_300234068471160/observation`

### MQTT Payload Format

```json
{
  "observation_time": "2024-12-02T16:00:00Z",
  "latitude": 51.9389,
  "longitude": -10.2444,
  "wind_speed": 12.5,
  "wind_direction": 280,
  "air_temperature": 15.5,
  "relative_humidity": 65.0,
  "atmospheric_pressure": 1013.25,
  "data_quality_flag": 0
}
```

---

## Testing

### 1. Test Socket Server

Send test data to port 7777:

```bash
# Simple text test
echo "TEST DATA" | nc 138.68.158.9 7777

# Binary EUCAWS test (30 bytes)
python3 << 'EOF'
import socket
import struct
import time

# Create 30-byte EUCAWS payload
timestamp = int(time.time())
lat = int(51.9389 * 1e7)  # Valentia Observatory
lon = int(-10.2444 * 1e7)
wind_speed = 1250  # 12.50 knots
wind_dir = 280
air_temp = 1550  # 15.50°C
sea_temp = 1200  # 12.00°C
pressure = 10132  # 1013.2 hPa
humidity = 650  # 65.0%

payload = struct.pack('>IiiHHhhHH', 
    timestamp, lat, lon, wind_speed, wind_dir,
    air_temp, sea_temp, pressure, humidity)
payload += b'\xff\xff\xff\xff\xff\xff'  # Reserved bytes

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('138.68.158.9', 7777))
sock.sendall(payload)
sock.close()
print("Test EUCAWS packet sent!")
EOF
```

### 2. Verify in Dashboard

Open http://138.68.158.9:3011 and check:
- Total packets counter increased
- New row appears in the table
- EUCAWS decoded badge shows "✓ Decoded"
- Weather data fields populated

### 3. Verify MQTT Publishing

Subscribe to MQTT broker:

```bash
mosquitto_sub -h mqtt.metvalentia.com -p 1883 \
  -u valentia -P valentia_mqtt_2024 \
  -t "valentia/eucaws/+/observation" \
  -v
```

---

## Management Commands

```bash
# View logs
sudo docker compose logs -f app

# Restart services
sudo docker compose restart

# Stop services
sudo docker compose down

# Update to latest code
cd /opt/DIRECTIP
sudo git pull origin main
sudo docker compose up -d --build

# Access Django shell
sudo docker compose exec app python manage.py shell

# View database
sudo docker compose exec app python manage.py dbshell
```

---

## Database Schema

### SatelliteData Model

```python
class SatelliteData(models.Model):
    # Reception metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    source_ip = models.CharField(max_length=45)
    source_port = models.IntegerField()
    payload = models.TextField()
    payload_size = models.IntegerField()
    
    # Iridium SBD fields
    imei = models.CharField(max_length=15, null=True)
    momsn = models.IntegerField(null=True)
    mtmsn = models.IntegerField(null=True)
    session_time = models.DateTimeField(null=True)
    is_parsed = models.BooleanField(default=False)
    
    # GPS data
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    cep_radius = models.IntegerField(null=True)
    
    # EUCAWS weather data
    wind_speed_knots = models.FloatField(null=True)
    wind_direction = models.FloatField(null=True)
    air_temperature = models.FloatField(null=True)
    sea_temperature = models.FloatField(null=True)
    barometric_pressure = models.FloatField(null=True)
    relative_humidity = models.FloatField(null=True)
    is_eucaws_decoded = models.BooleanField(default=False)
```

---

## Troubleshooting

### Socket Server Not Receiving Data

1. Check firewall:
   ```bash
   sudo ufw status
   sudo ufw allow 7777/tcp
   ```

2. Verify container is running:
   ```bash
   sudo docker compose ps
   ```

3. Check socket server logs:
   ```bash
   sudo docker compose logs app | grep Socket
   ```

### MQTT Not Publishing

1. Check MQTT configuration in settings:
   ```bash
   sudo docker compose exec app python manage.py shell
   >>> from django.conf import settings
   >>> print(settings.MQTT_BROKER_HOST)
   >>> print(settings.MQTT_USERNAME)
   ```

2. Test MQTT connectivity:
   ```bash
   mosquitto_pub -h mqtt.metvalentia.com -p 1883 \
     -u valentia -P valentia_mqtt_2024 \
     -t "test/topic" -m "test message"
   ```

3. Check MQTT logs:
   ```bash
   sudo docker compose logs app | grep MQTT
   ```

### Dashboard Not Loading

1. Check web server logs:
   ```bash
   sudo docker compose logs app | grep gunicorn
   ```

2. Verify port 3011 is accessible:
   ```bash
   curl http://localhost:3011
   ```

3. Check firewall:
   ```bash
   sudo ufw allow 3011/tcp
   ```

---

## Environment Variables

Create `.env` file in project root to customize:

```bash
# Database
USE_SQLITE=1

# MQTT Configuration
MQTT_BROKER_HOST=mqtt.metvalentia.com
MQTT_BROKER_PORT=1883
MQTT_USERNAME=valentia
MQTT_PASSWORD=valentia_mqtt_2024

# Django
DEBUG=False
SECRET_KEY=your-secret-key-here
```

---

## Next Steps

1. **Monitor Initial Data**: Watch the dashboard for incoming EUCAWS transmissions
2. **Verify MQTT Flow**: Confirm data is reaching your MIDDLEMIN system
3. **Set Up Alerts**: Configure monitoring for socket server downtime
4. **Add SSL/TLS**: Set up Nginx reverse proxy with Let's Encrypt for HTTPS
5. **Backup Database**: Schedule regular backups of SQLite database

---

## Support

For issues or questions:
- GitHub: https://github.com/willbullen/DIRECTIP
- MIDDLEMIN Integration: https://github.com/willbullen/MIDDLEMIN

---

**DIRECTIP © 2024 | EUCAWS Satellite Data Receiver**
