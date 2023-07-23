from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model



class Company(models.Model):
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='company', blank=True, null=True)
    salesforce_username = models.CharField(max_length=255, null=True, blank=True)
    salesforce_password = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name

class CustomUser(AbstractUser):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    dark_mode = models.BooleanField(default=False)


# Create your models here.
class Folder(models.Model):
    name = models.CharField(max_length=50)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    last_updated_date = models.DateTimeField(auto_now=True)
    @property
    def num_of_pre(self):
        num_of_pre = Presentation.objects.filter(folder_id = self.id).count()
        return num_of_pre
    def __str__(self):
        return self.name
    @property
    def total_size(self):
        total_size = 0.0
        for presentation in self.presentations.all():
            total_size += presentation.total_size
        return total_size
    def save(self, *args, **kwargs):
        if not self.id:
            if 'request' in kwargs:
                request = kwargs.pop('request')
                User = get_user_model()
                user = User.objects.get(username=request.user.username)
                self.company = user.company
        super().save(*args, **kwargs)
    

class Presentation(models.Model):
    Taptop = 'TT'
    TapBottom = 'TB'
    SwipeUp = 'SU'
    SwipeDown = 'SD'

    PLAYER_GESTURE = [
    (Taptop , "Taptop" ),
    (TapBottom , "TapBottom" ),
    (SwipeUp , "SwipeUp" ),
    (SwipeDown , "SwipeDown" )
    ]

    name = models.CharField(max_length=255)
    created_date = models.DateTimeField(auto_now_add=True)
    is_push_oce = models.BooleanField(default=False)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_pinch = models.BooleanField(default=False)
    is_double_tap = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_send_email = models.BooleanField(default=False)
    player_gesture = models.CharField(max_length=30, choices=PLAYER_GESTURE, default='TapBottom')
    folder = models.ForeignKey(Folder, on_delete=models.SET_NULL, blank=True, null=True, related_name='presentations')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    last_updated_date = models.DateTimeField(auto_now=True)
    def save(self, *args, **kwargs):
        if not self.id:
            if 'request' in kwargs:
                request = kwargs.pop('request')
                User = get_user_model()
                user = User.objects.get(username=request.user.username)
                self.company = user.company
        super().save(*args, **kwargs)
    @property
    def firstAsset(self):
        asset = Asset.objects.filter(presentation_id = self.id).order_by('sort_number').first()
        firstAsset =  asset.img.url
        return firstAsset
    @firstAsset.setter
    def firstAsset(self, value):
        if value is None:
            self.value = 0
        self._firstAsset = value
    @property
    def num_of_asset(self):
        num_of_asset = Asset.objects.filter(presentation_id = self.id).count()
        return num_of_asset
    @num_of_asset.setter
    def num_of_asset(self, value):
        if value is None:
            self.value = 0
        self._num_of_asset = value

    def __str__(self):
        return self.name
    @property
    def total_size(self):
        total_size = 0.0
        for asset in self.assets.all():
            total_size += asset.total_size
        return total_size


class Asset(models.Model):
    name = models.CharField(max_length=100)
    is_asset = models.BooleanField(default=False)
    img = models.ImageField(upload_to='media', null=True)
    activation_date = models.DateField(blank=True, null=True)
    deactivation_date = models.DateField(blank=True, null=True)
    is_mandatory = models.BooleanField(default=False)
    presentation = models.ForeignKey(Presentation, on_delete=models.CASCADE, blank=True, null=True, related_name='assets')
    sort_number = models.BigIntegerField(default=10000)
    thumbnail = models.ImageField(upload_to='thumbnails', blank=True, null=True)
    size = models.FloatField(default=0)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    def save(self, *args, **kwargs):
        if not self.id:
            if 'request' in kwargs:
                request = kwargs.pop('request')
                User = get_user_model()
                user = User.objects.get(username=request.user.username)
                self.company = user.company
        super().save(*args, **kwargs)

    def img_url(self):
        if self.img and hasattr(self.img, 'url'):
            return self.img.url
    def __str__(self):
        return self.name
    @property
    def total_size(self):
        total_size = self.size
        for ac in self.coordinates.all():
            total_size += ac.size
        return total_size
    

class Product(models.Model):
    name = models.CharField(max_length=255)
    salesforce_id = models.CharField(max_length=255, default='0')
    is_active = models.BooleanField(default=False)
    assets = models.ManyToManyField('Asset', related_name='products', blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

class Message(models.Model):
    name = models.CharField(max_length=255)
    product = models.ForeignKey(Product, models.CASCADE)
    salesforce_id = models.CharField(max_length=255, default='0')
    assets = models.ManyToManyField('Asset', related_name='messages', blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.product.name}"



class AssetCoordinate(models.Model):
    ASSET_TYPE_CHOICES = (
        ('link', 'Link'),
        ('popup', 'Popup'),
        ('video', 'Video'),
    )

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='coordinates')
    coordinate_type = models.CharField(max_length=15, choices=ASSET_TYPE_CHOICES)
    start_top = models.IntegerField(default=0)
    start_left = models.IntegerField(default=0)
    end_top = models.IntegerField(default=0)
    end_left = models.IntegerField(default=0)
    linked_asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='linked_from_assets',null=True, blank=True)
    linked_url = models.URLField(null=True, blank=True)
    image = models.ImageField(upload_to='popups', null=True, blank=True) # Add the popup images here
    video = models.FileField(upload_to='videos', null=True, blank=True)  # Add the video field here
    is_embedded = models.BooleanField(default=False)
    isEveryLink = models.BooleanField(default=False)
    size = models.FloatField(default=0.0)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    def save(self, *args, **kwargs):
        if not self.id:
            if 'request' in kwargs:
                request = kwargs.pop('request')
                User = get_user_model()
                user = User.objects.get(username=request.user.username)
                self.company = user.company
        super().save(*args, **kwargs)


    def __str__(self):
        if self.linked_asset:
            return f"{self.asset.name} - {self.coordinate_type} - {self.linked_asset.name}"
        else:
            return f"{self.asset.name} - {self.coordinate_type}"


class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.message
    def save(self, *args, **kwargs):
        if self.pk is None:
            # Only execute this code if it's a new notification being saved
            max_notification_count = 50
            user_notifications = Notification.objects.filter(user=self.user).order_by('-created_at')

            if user_notifications.count() >= max_notification_count:
                # Delete the oldest notification(s) if the limit is reached
                excess_count = user_notifications.count() - max_notification_count + 1
                excess_notifications = user_notifications[:excess_count]
                excess_notifications.delete()

        super().save(*args, **kwargs)