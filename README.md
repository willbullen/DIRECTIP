# DIRECTIP - Satellite Data Reception System

A Django-based satellite data receiver system that listens for incoming data on port 7777 and provides a real-time web dashboard for monitoring.

## Features

- **TCP Socket Server**: Listens on port 7777 for incoming satellite data
- **PostgreSQL Database**: Stores all received data packets with timestamps
- **Real-time Dashboard**: Modern dark-themed UI with shadcn-style components
- **Auto-refresh**: Dashboard updates every 5 seconds
- **Docker Deployment**: Fully containerized for easy deployment

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Ports 3010 (web) and 7777 (socket) available

### Deployment

1. **Clone the repository**:
   ```bash
   cd /opt
   sudo git clone https://github.com/willbullen/DIRECTIP.git
   cd DIRECTIP
   ```

2. **Configure firewall**:
   ```bash
   sudo ufw allow 3010/tcp  # Web dashboard
   sudo ufw allow 7777/tcp  # Socket server
   ```

3. **Start the application**:
   ```bash
   sudo docker compose up -d --build
   ```

4. **Check status**:
   ```bash
   sudo docker compose ps
   sudo docker compose logs -f app
   ```

5. **Access the dashboard**:
   - Open your browser to: `http://YOUR_SERVER_IP:3010`

## Testing

Send test data to the socket server:

```bash
echo "TEST SATELLITE DATA" | nc YOUR_SERVER_IP 7777
```

The data should appear in the dashboard within 5 seconds.

## Management Commands

```bash
# View logs
sudo docker compose logs -f app

# Restart services
sudo docker compose restart

# Stop services
sudo docker compose down

# Update and rebuild
sudo docker compose down
sudo git pull origin main
sudo docker compose up -d --build

# Access Django shell
sudo docker compose exec app python manage.py shell

# Create superuser for admin panel
sudo docker compose exec app python manage.py createsuperuser
```

## Architecture

- **Framework**: Django 5.2
- **Database**: PostgreSQL 16
- **Web Server**: Gunicorn
- **Frontend**: Tailwind CSS with shadcn-style components
- **Socket Server**: Python threading with Django ORM

## Configuration

Environment variables (set in docker-compose.yml):

- `DB_NAME`: Database name (default: directip)
- `DB_USER`: Database user (default: directip)
- `DB_PASSWORD`: Database password (default: directip_password)
- `DB_HOST`: Database host (default: db)
- `DB_PORT`: Database port (default: 5432)

## Future Enhancements

- MQTT broker integration for data forwarding
- Data export functionality (CSV/JSON)
- Advanced filtering and search
- Data visualization charts
- Authentication and user management

## License

MIT
