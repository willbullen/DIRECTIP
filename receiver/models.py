from django.db import models
from django.utils import timezone


class SatelliteData(models.Model):
    """Model to store received satellite data packets"""
    
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    source_ip = models.GenericIPAddressField()
    source_port = models.IntegerField()
    payload = models.TextField()
    payload_size = models.IntegerField()
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Satellite Data Packet'
        verbose_name_plural = 'Satellite Data Packets'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['source_ip']),
        ]
    
    def __str__(self):
        return f"{self.timestamp} - {self.source_ip}:{self.source_port}"
