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


def publish_to_mqtt(request, packet_id):
    """API endpoint to manually publish a packet to MQTT"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        from .mqtt_publisher import publish_eucaws_to_mqtt
        
        # Get the packet
        packet = SatelliteData.objects.get(id=packet_id)
        
        # Check if it's decoded
        if not packet.is_eucaws_decoded:
            return JsonResponse({
                'success': False,
                'error': 'Packet is not decoded - cannot publish'
            })
        
        # Check if we have IMEI
        if not packet.imei:
            return JsonResponse({
                'success': False,
                'error': 'No IMEI found - cannot determine topic'
            })
        
        # Build EUCAWS data from packet
        eucaws_data = {
            'timestamp': packet.eucaws_timestamp or packet.timestamp,
            'latitude': packet.latitude,
            'longitude': packet.longitude,
            'wind_speed_ms': packet.wind_speed_ms,
            'wind_speed_knots': packet.wind_speed_knots,
            'wind_direction': packet.wind_direction,
            'air_temperature': packet.air_temperature,
            'sea_temperature': packet.sea_temperature,
            'barometric_pressure': packet.barometric_pressure,
            'relative_humidity': packet.relative_humidity,
            'is_decoded': packet.is_eucaws_decoded,
        }
        
        # Publish to MQTT
        result = publish_eucaws_to_mqtt(packet.imei, eucaws_data)
        
        if isinstance(result, dict) and result.get('success'):
            # Update the packet with the topic
            packet.mqtt_topic = result.get('topic')
            packet.save(update_fields=['mqtt_topic'])
            
            return JsonResponse({
                'success': True,
                'topic': result.get('topic'),
                'message': f'Published to {result.get("topic")}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'MQTT publish failed'
            })
            
    except SatelliteData.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Packet not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
