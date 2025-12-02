from django.apps import AppConfig


class ReceiverConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'receiver'
    
    def ready(self):
        """Start the socket server when Django starts"""
        import os
        # Only start in the main process (not in reloader)
        if os.environ.get('RUN_MAIN') != 'true' and os.environ.get('DJANGO_SETTINGS_MODULE'):
            from .socket_server import start_socket_server
            start_socket_server()
