from django.db import models
from django.utils import timezone


class SatelliteData(models.Model):
    """Model to store received satellite data packets"""
    
    # Reception metadata
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    source_ip = models.GenericIPAddressField()
    source_port = models.IntegerField()
    payload = models.TextField()
    payload_size = models.IntegerField()
    
    # Parsed Iridium SBD fields
    imei = models.CharField(max_length=15, null=True, blank=True, db_index=True)
    message_sequence = models.IntegerField(null=True, blank=True)
    session_status = models.IntegerField(null=True, blank=True)
    momsn = models.IntegerField(null=True, blank=True, help_text="Mobile Originated Message Sequence Number")
    mtmsn = models.IntegerField(null=True, blank=True, help_text="Mobile Terminated Message Sequence Number")
    session_time = models.DateTimeField(null=True, blank=True)
    
    # GPS data (if available)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    cep_radius = models.IntegerField(null=True, blank=True, help_text="GPS accuracy in meters")
    
    # Decoded payload
    decoded_payload = models.TextField(null=True, blank=True)
    payload_hex = models.TextField(null=True, blank=True)
    
    # Parsing status
    is_parsed = models.BooleanField(default=False)
    parse_error = models.TextField(null=True, blank=True)
    
    # EUCAWS weather station fields
    eucaws_timestamp = models.DateTimeField(null=True, blank=True, help_text="Timestamp from EUCAWS payload")
    wind_speed_ms = models.FloatField(null=True, blank=True, help_text="Wind speed in m/s")
    wind_speed_knots = models.FloatField(null=True, blank=True, help_text="Wind speed in knots")
    wind_direction = models.FloatField(null=True, blank=True, help_text="Wind direction in degrees")
    air_temperature = models.FloatField(null=True, blank=True, help_text="Air temperature in °C")
    sea_temperature = models.FloatField(null=True, blank=True, help_text="Sea temperature in °C")
    barometric_pressure = models.FloatField(null=True, blank=True, help_text="Pressure in hPa")
    relative_humidity = models.FloatField(null=True, blank=True, help_text="Humidity in %")
    is_eucaws_decoded = models.BooleanField(default=False)
    eucaws_decode_error = models.TextField(null=True, blank=True)
    mqtt_topic = models.CharField(max_length=255, null=True, blank=True, help_text="MQTT topic where data was published")
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Satellite Data Packet'
        verbose_name_plural = 'Satellite Data Packets'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['source_ip']),
            models.Index(fields=['imei']),
        ]
    
    def __str__(self):
        if self.imei:
            return f"{self.timestamp} - IMEI: {self.imei}"
        return f"{self.timestamp} - {self.source_ip}:{self.source_port}"
