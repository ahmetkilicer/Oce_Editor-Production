# Generated by Django 4.1.7 on 2023-07-01 14:37

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ErrorLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('level', models.CharField(max_length=20)),
                ('message', models.TextField()),
            ],
            options={
                'verbose_name_plural': 'Error Logs',
            },
        ),
    ]
