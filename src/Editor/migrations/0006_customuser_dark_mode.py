# Generated by Django 4.1.7 on 2023-06-16 07:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Editor', '0005_company_logo'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='dark_mode',
            field=models.BooleanField(default=False),
        ),
    ]
