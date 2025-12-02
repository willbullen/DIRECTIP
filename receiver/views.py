from django.shortcuts import render
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import SatelliteData


def dashboard(request):
    """Main dashboard view"""
    # Get statistics
    total_packets = SatelliteData.objects.count()
    
    context = {
        'total_packets': total_packets,
        'listening_port': 7777,
        'server_ip': '138.68.158.9',
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
