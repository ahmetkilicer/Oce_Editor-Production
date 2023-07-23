from django.contrib import admin
from .models import Folder, Asset, Presentation, Product, Message, AssetCoordinate, Company, CustomUser, Notification


from django.contrib.auth import get_user_model

CustomUser = get_user_model()

class CustomUserAdmin(admin.ModelAdmin):
    # Your custom admin configuration
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.set_password(form.cleaned_data['password'])
        super().save_model(request, obj, form, change)

admin.site.register(CustomUser, CustomUserAdmin)
# Register your models here.
admin.site.register(Company)
admin.site.register(Folder)
admin.site.register(Asset)
admin.site.register(Presentation)
admin.site.register(Product)
admin.site.register(Message)
admin.site.register(AssetCoordinate)
admin.site.register(Notification)
