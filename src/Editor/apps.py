from django.apps import AppConfig

class EditorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Editor'

    def ready(self):
        import Editor.signals
