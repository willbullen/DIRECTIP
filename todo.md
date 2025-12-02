
## EUCAWS Integration
- [x] Update database models to store decoded EUCAWS weather data
- [x] Integrate EUCAWS decoder into socket server
- [x] Update dashboard to display weather station data with proper formatting
- [ ] Add IMEI extraction from filenames for email-received .sbd files
- [ ] Test with actual EUCAWS data from port 7777
- [x] Implement MQTT publisher for EUCAWS weather data (based on MIDDLEMIN config)
- [x] Add MQTT broker configuration to environment variables
- [ ] Test MQTT publishing with sample EUCAWS data

## Troubleshooting - EUCAWS Decoder Not Working
- [x] Check actual payload size being received (110 bytes - full DirectIP message)
- [x] Verify EUCAWS decoder is being called correctly (was only checking len==30)
- [x] Debug the 30-byte payload structure (embedded in DirectIP IEI 2)
- [x] Fix decoder to handle actual Iridium DirectIP message format
- [ ] Test with real satellite data
- [ ] Verify weather fields are being saved to database
