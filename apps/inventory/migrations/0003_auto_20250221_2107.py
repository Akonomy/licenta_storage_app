# Generated by Django 3.2 on 2025-02-21 19:07

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_alter_box_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='box',
            name='added_date',
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AddField(
            model_name='box',
            name='sold_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
