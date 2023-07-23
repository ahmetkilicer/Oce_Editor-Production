from rest_framework.serializers import ModelSerializer
from .models import Presentation

class PresentationSerializer(ModelSerializer):
    class Meta:
        model = Presentation
        fields = '__all__'