# EUCAWS Decoder Integration - Changes Summary

## Date: 2025-12-03

### Changes Made

1. **Updated `receiver/eucaws_decoder.py`**
   - Replaced generic EUCAWS decoder with E-SURFMAR Format #100 decoder
   - Reverse-engineered from actual payload data
   - Decodes: Hour, Station ID, Barometric Pressure, Sea Temperature, Air Temperature (experimental)
   - Added confidence levels for each decoded field
   - Improved error handling and validation

2. **Updated `receiver/socket_server.py`**
   - Modified to pass `session_time` to decoder for date context
   - Enables accurate timestamp reconstruction from hour-only payload

3. **Added `receiver/management/commands/reprocess_eucaws.py`**
   - Django management command to reprocess existing database records
   - Supports dry-run, limit, and force options
   - Provides detailed progress and summary output

4. **Added `EUCAWS_DECODER.md`**
   - Comprehensive documentation of the decoder
   - Format specification (reverse-engineered)
   - Usage examples and deployment instructions
   - Known issues and future improvements

### Deployment Instructions

```bash
cd /opt/DIRECTIP
sudo git pull origin main
sudo docker compose down
sudo docker compose up -d --build
sudo docker compose exec app python manage.py reprocess_eucaws
```

### Testing

Test the decoder with existing data:
```bash
sudo docker compose exec app python manage.py reprocess_eucaws --dry-run --limit 10
```

### Decoder Performance

Based on sample data (19 payloads):
- **Hour decoding**: 100% success
- **Barometric Pressure**: ~80% success (realistic values)
- **Sea Surface Temperature**: ~80% success (realistic values)
- **Air Temperature**: ~40% success (needs validation)
- **Wind/Humidity**: Not yet decoded

### Next Steps

1. Validate air temperature decoding with known good weather data
2. Decode wind speed and direction fields
3. Decode humidity field
4. Contact Météo-France for official Format #100 specification
