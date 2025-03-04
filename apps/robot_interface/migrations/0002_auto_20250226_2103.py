# Generated by Django 3.2 on 2025-02-26 19:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fizic_inventory', '0001_initial'),
        ('robot_interface', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='box',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='fizic_inventory.container'),
        ),
        migrations.AlterField(
            model_name='task',
            name='source_section',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='source_tasks', to='fizic_inventory.zone'),
        ),
        migrations.AlterField(
            model_name='task',
            name='target_section',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='target_tasks', to='fizic_inventory.zone'),
        ),
    ]
