from django.db import models

# Create your models here.
from django.db import models

class ErrorLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=20)
    message = models.TextField()

    class Meta:
        verbose_name_plural = "Error Logs"

    def __str__(self):
        return self.message[:50]  # Return a truncated version of the log message
