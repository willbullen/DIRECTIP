#!/bin/bash
set -e

echo "=== DIRECTIP Django Deployment Script ==="
echo "This script will deploy the DIRECTIP satellite data receiver system"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo "Please run as root (use sudo)"
   exit 1
fi

# Navigate to deployment directory
cd /opt

# Clean up old installation
if [ -d "DIRECTIP" ]; then
    echo "Removing old DIRECTIP installation..."
    docker compose -f DIRECTIP/docker-compose.yml down 2>/dev/null || true
    rm -rf DIRECTIP
fi

# Clone repository
echo "Cloning DIRECTIP repository..."
git clone https://github.com/willbullen/DIRECTIP.git
cd DIRECTIP

# Configure firewall
echo "Configuring firewall..."
ufw allow 3011/tcp  # Web dashboard
ufw allow 7777/tcp  # Socket server

# Build and start
echo "Building and starting Docker containers..."
docker compose up -d --build

# Wait for startup
echo "Waiting for services to start..."
sleep 20

# Check status
echo ""
echo "=== Deployment Status ==="
docker compose ps
echo ""
echo "=== Recent Logs ==="
docker compose logs --tail=50 app

echo ""
echo "=== Deployment Complete ==="
echo "Dashboard: http://$(hostname -I | awk '{print $1}'):3011"
echo "Socket Server: Port 7777"
echo ""
echo "Test with: echo 'TEST DATA' | nc $(hostname -I | awk '{print $1}') 7777"
echo ""
echo "Management commands:"
echo "  View logs: cd /opt/DIRECTIP && docker compose logs -f app"
echo "  Restart: cd /opt/DIRECTIP && docker compose restart"
echo "  Stop: cd /opt/DIRECTIP && docker compose down"
