from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """
        Called once when Django starts.
        Start the background scheduler here.
        """
        import os
        
        # Only start in the main process
        # Prevents double-start when Django uses --reload (which forks a child)
        if os.environ.get('RUN_MAIN') != 'true':
            return
        
        # Don't start during migrations or management commands other than runserver
        import sys
        if 'runserver' not in sys.argv and 'gunicorn' not in sys.argv[0]:
            return
        
        from .scheduler import start_scheduler
        start_scheduler()
