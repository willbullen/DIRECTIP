from django.shortcuts import render
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from .models import SatelliteData
import paho.mqtt.client as mqtt


def dashboard(request):
    """Main dashboard view with EUCAWS weather data"""
    # Get latest packets
    recent_packets = SatelliteData.objects.all().order_by('-timestamp')[:50]
    
    # Get statistics
    total_packets = SatelliteData.objects.count()
    eucaws_decoded = SatelliteData.objects.filter(is_eucaws_decoded=True).count()
    unique_imeis = SatelliteData.objects.filter(imei__isnull=False).values('imei').distinct().count()
    
    # Last hour count
    one_hour_ago = timezone.now() - timedelta(hours=1)
    last_hour_count = SatelliteData.objects.filter(timestamp__gte=one_hour_ago).count()
    
    # Check MQTT broker connection
    mqtt_connected = False
    try:
        client = mqtt.Client(client_id="mqtt_status_check")
        client.username_pw_set("admin", "B@ff1ed!2025")
        client.connect("138.68.158.9", 1883, 5)
        mqtt_connected = True
        client.disconnect()
    except Exception:
        mqtt_connected = False
    
    stats = {
        'total_packets': total_packets,
        'eucaws_decoded': eucaws_decoded,
        'unique_imeis': unique_imeis,
        'last_hour_count': last_hour_count,
        'mqtt_connected': mqtt_connected,
    }
    
    context = {
        'recent_packets': recent_packets,
        'stats': stats,
        'page': 1,
    }
    
    return render(request, 'receiver/dashboard.html', context)


def get_packets(request):
    """API endpoint to get satellite data packets"""
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 20)
    
    packets = SatelliteData.objects.all()
    paginator = Paginator(packets, per_page)
    page_obj = paginator.get_page(page)
    
    data = {
        'packets': [
            {
                'id': p.id,
                'timestamp': p.timestamp.isoformat(),
                'source_ip': p.source_ip,
                'source_port': p.source_port,
                'payload': p.payload[:100] + '...' if len(p.payload) > 100 else p.payload,
                'payload_size': p.payload_size,
            }
            for p in page_obj
        ],
        'total': paginator.count,
        'page': page_obj.number,
        'total_pages': paginator.num_pages,
    }
    
    return JsonResponse(data)


def get_stats(request):
    """API endpoint to get real-time statistics"""
    total_packets = SatelliteData.objects.count()
    
    data = {
        'total_packets': total_packets,
        'listening_port': 7777,
        'server_ip': '138.68.158.9',
        'status': 'active',
    }
    
    return JsonResponse(data)
