# Generated by Django 3.2 on 2025-02-20 06:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='box',
            name='code',
            field=models.CharField(blank=True, max_length=10, unique=True),
        ),
    ]
