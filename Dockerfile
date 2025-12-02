FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=directip_project.settings

# Set work directory
WORKDIR /app

# No additional system dependencies needed for SQLite

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Create data directory for SQLite
RUN mkdir -p /app/data

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Expose ports
EXPOSE 3011 7777

# Run migrations and start server
CMD python manage.py migrate && \
    gunicorn directip_project.wsgi:application --bind 0.0.0.0:3011 --workers 3 --timeout 120
