from io import BytesIO
import os
from PIL import Image
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Asset, AssetCoordinate
from django.db import models



@receiver(post_save, sender=Asset)
def create_thumbnail(sender, instance, created, **kwargs):
    if created and instance.img:
        # Open the uploaded image using PIL
        img = Image.open(instance.img)

        # Create a thumbnail and save it to a temporary file
        thumb_io = BytesIO()
        img.thumbnail(( 328,232 ))
        img.save(thumb_io, format='JPEG')
        thumb_io.seek(0)

        # Save the thumbnail to a thumbnail file
        thumbnail_name = os.path.basename(instance.img.name).rsplit('.', 1)[0] + '_thumbnail.jpg'
        thumbnail_path = os.path.join('thumbnails', thumbnail_name)
        thumb_file = ContentFile(thumb_io.read())
        default_storage.save(thumbnail_path, thumb_file)

        # Calculate the size of the image and thumbnail in megabytes
        size_in_bytes = default_storage.size(instance.img.name) + default_storage.size(thumbnail_path)
        size_in_mb = size_in_bytes / (1024 * 1024)

        # Update the Asset object with the thumbnail path and size
        instance.thumbnail.name = thumbnail_path
        instance.size = round(size_in_mb, 2)  # Round to 2 decimal places
        instance.save()
