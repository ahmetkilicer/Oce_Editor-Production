from django.core.exceptions import MiddlewareNotUsed
from error_logs.models import ErrorLog

class ErrorLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        # Log the error using ErrorLog model
        ErrorLog.objects.create(level='ERROR', message=str(exception))

        # Raise MiddlewareNotUsed to prevent other middlewares from processing the exception
        raise MiddlewareNotUsed()
