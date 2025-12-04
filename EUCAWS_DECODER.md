# EUCAWS Format #100 Decoder

## Overview

This decoder handles **E-SURFMAR Format #100** payloads from EUCAWS (Enhanced Underway Coastal and Atmospheric Weather Station) maritime automatic weather stations transmitted via Iridium SBD satellite communications.

The decoder is based on the **official E-SURFMAR specification** v1.9 (2 September 2019) by Météo-France, Centre de Météorologie Marine.

**Reference**: DOI: 10.5281/zenodo.1324186

## Format Details

**E-SURFMAR Format #100** is a proprietary binary format designed for Shipborne Automated Weather Stations (S-AWS). The minimum message length is **235 bits (30 bytes)** for autonomous S-AWS without visual observations.

### Format Structure

The format uses **bit-level encoding** (not byte-aligned) with the following structure:

1. **Green Block** (Mandatory - 235 bits / 30 bytes): Core weather observations
2. **Yellow Block** (Optional): Visual observations (manned stations)
3. **Blue-violet Block** (Optional): Wave observations
4. **Pink-violet Block** (Optional): Ice observations
5. **Orange Block** (Optional): Other sensor data

Each optional block starts with a 1-bit presence indicator. EUCAWS autonomous stations typically send only the Green Block.

### Decoding Formula

All fields follow the formula:

```
Physical value = (raw_value × slope) + offset
```

Missing data is indicated by all bits set to 1 for that field.

### Decoded Fields (Green Block)

| BUFR ID | Field | Bits | Slope | Offset | Units | Notes |
|---------|-------|------|-------|--------|-------|-------|
| 001198 | Format ID | 8 | 1 | 0 | - | Always 100 for S-AWS |
| 001199 | Callsign encryption | 1 | - | - | - | 0=encrypted, 1=not encrypted |
| 001012 | Ship's Course (COG10) | 7 | 5 | 0 | degrees | Past 10 minutes |
| 001013 | Ship's Speed (SOG10) | 6 | 0.5 | 0 | m/s | Past 10 minutes |
| 011104 | Ship's Heading (HDT10) | 7 | 5 | 0 | degrees | Past 10 minutes |
| 010039 | Draft | 5 | 1 | -10 | m | Summer loadline from sea level |
| 004001 | Year | 7 | 1 | 2000 | - | 2000-2126 |
| 004002 | Month | 4 | 1 | 0 | - | 1-12 |
| 004003 | Day | 6 | 1 | 0 | - | 1-31 |
| 004004 | Hour | 5 | 1 | 0 | - | 0-23 UTC |
| 004005 | Minute | 6 | 1 | 0 | - | 0-59 |
| 005002 | Latitude | 15 | 0.01 | -90 | degrees | Coarse accuracy |
| 006002 | Longitude | 16 | 0.01 | -180 | degrees | Coarse accuracy |
| 010004 | Pressure (barometer) | 11 | 10 | 85000 | Pa | Pressure at barometer height |
| 010051 | MSLP | 11 | 10 | 85000 | Pa | Mean sea level pressure |
| 010061 | 3h pressure change | 10 | 10 | -5000 | Pa | Past 3 hours |
| 010063 | Pressure tendency | 4 | 1 | 0 | code | Characteristic 0-8 |
| 011001 | Wind direction (dd) | 7 | 5 | 0 | degrees | True wind, clockwise from north |
| 011002 | Wind speed (ff) | 10 | 0.1 | 0 | m/s | True wind speed |
| 011007 | Relative wind dir (RWD) | 7 | 5 | 0 | degrees | From bow |
| 011008 | Relative wind speed (RWS) | 8 | 0.5 | 0 | m/s | Relative to ship |
| 011041 | Max gust speed | 8 | 0.5 | 0 | m/s | Past 10 minutes |
| 011043 | Max gust direction | 7 | 5 | 0 | degrees | Past 10 minutes |
| 012101 | Air temperature (Ta) | 10 | 0.1 | 223.2 | K | Convert to °C: -273.15 |
| 013009 | Relative humidity (U) | 10 | 0.1 | 0 | % | 0-100% |
| 022043 | Sea temperature (SST) | 12 | 0.01 | 268.15 | K | Convert to °C: -273.15 |
| 025026 | Battery voltage | 7 | 0.2 | 5.0 | V | AWS supply voltage |
| 010201 | Processor temp | 8 | 0.5 | 233.15 | K | AWS processor temperature |
| 010200 | GPS height | 8 | 1 | -50 | m | Above sea level |
| - | Visual obs indicator | 1 | - | - | - | Presence of yellow block |
| - | Wave obs indicator | 1 | - | - | - | Presence of blue-violet block |
| - | Ice obs indicator | 1 | - | - | - | Presence of pink-violet block |
| - | Other obs indicator | 1 | - | - | - | Presence of orange block |

**Total**: 235 bits = 29.375 bytes (padded to 30 bytes)

## Usage

### In Django Application

The decoder is automatically called when a 30-byte payload is received on port 7777:

```python
from receiver.eucaws_decoder import decode_eucaws_payload
from datetime import datetime, timezone

# Decode a payload (hex string)
payload_hex = "648003fb4ce06b01bfd21f5dd9beef9bffffffffffff97ed5fffc0f1fe00"
session_time = datetime(2025, 12, 3, 11, 0, 15, tzinfo=timezone.utc)

result = decode_eucaws_payload(payload_hex, session_time)

print(f"Decoded: {result['is_decoded']}")
print(f"Timestamp: {result['timestamp']}")
print(f"Position: {result['latitude']}, {result['longitude']}")
print(f"Air temp: {result['air_temperature']} °C")
print(f"Sea temp: {result['sea_temperature']} °C")
print(f"Pressure: {result['barometric_pressure']} hPa")
print(f"Wind: {result['wind_speed_ms']} m/s @ {result['wind_direction_true']}°")
print(f"Humidity: {result['relative_humidity']} %")
```

### Reprocess Existing Data

To reprocess all existing database records with the new decoder:

```bash
# Dry run (show what would be processed)
docker exec directip-app python manage.py reprocess_eucaws --dry-run

# Process all unprocessed records
docker exec directip-app python manage.py reprocess_eucaws

# Process only 100 records
docker exec directip-app python manage.py reprocess_eucaws --limit 100

# Force reprocess all records (even already decoded)
docker exec directip-app python manage.py reprocess_eucaws --force
```

## Deployment

### 1. Update the Code

```bash
cd /opt/DIRECTIP
sudo git pull origin main
```

### 2. Rebuild and Restart

```bash
sudo docker compose down
sudo docker compose up -d --build
```

### 3. Reprocess Existing Data

```bash
sudo docker compose exec app python manage.py reprocess_eucaws
```

### 4. Verify

Check the logs:
```bash
sudo docker compose logs -f app
```

Check the dashboard:
```
http://YOUR_SERVER_IP:3011
```

## Sample Decoded Data

Example from actual EUCAWS transmission (2025-12-03 11:00 UTC):

```
Payload: 648003fb4ce06b01bfd21f5dd9beef9bffffffffffff97ed5fffc0f1fe00

Decoded results:
  Timestamp: 2025-12-03 11:00:00+00:00
  Position: 53.30°N, 6.13°W (Valentia, Ireland)
  Air Temperature: 10.75 °C
  Barometric Pressure: 999.7 hPa
  MSL Pressure: 1002.7 hPa
  Relative Humidity: 72.5 %
  Battery Voltage: 24.2 V
  Wind Speed: None (missing data)
  Sea Temperature: None (missing data)
```

Note: Some fields may show `None` when marked as missing data (all bits set to 1) in the transmission.

## Technical Notes

1. **Bit-level encoding**: The format uses bit-level fields, not byte-aligned. A BitReader class handles sequential bit extraction.

2. **Missing data**: Fields with all bits set to 1 indicate missing/unavailable data. The decoder returns `None` for these fields.

3. **Temperature units**: Temperatures are encoded in Kelvin and automatically converted to Celsius by the decoder.

4. **Pressure units**: Pressures are encoded in Pascals (Pa) and automatically converted to hectopascals (hPa) by the decoder.

5. **Wind measurements**: According to WMO rules, wind measurements are sampled over the 10 minutes preceding the observation time.

6. **Optional blocks**: EUCAWS autonomous stations typically send only the mandatory Green Block (235 bits). Visual, wave, ice, and other sensor blocks are optional and indicated by presence bits at the end of the Green Block.

## References

- [E-SURFMAR recommended ship-to-shore dataformats v1.9](https://doi.org/10.5281/zenodo.1324186)
- [E-SURFMAR Programme](https://eumetnet.eu/observations/surface-marine-observations/)
- [EUCAWS Documentation](http://www.sterela-meteo.fr/docs/eucaws.pdf)
- [Sterela Neptune Datasheet](http://www.sterela-meteo.fr/docs/neptune_datasheet.pdf)

## Version History

- **v2.0** (2025-12-04): Official E-SURFMAR Format #100 implementation
  - Based on official specification v1.9 (DOI: 10.5281/zenodo.1324186)
  - Complete bit-level decoder with all mandatory fields
  - Accurate formulas for all weather parameters
  - Proper handling of missing data indicators
  - Full support for: timestamp, position, pressure, wind, temperature, humidity, technical parameters

- **v1.0** (2025-12-03): Initial reverse-engineered decoder
  - HIGH confidence: Hour, Station ID, Pressure, Sea Temperature
  - MEDIUM confidence: Air Temperature
  - Unknown: Wind Speed, Wind Direction, Humidity
