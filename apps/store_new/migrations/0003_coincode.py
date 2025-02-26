# Generated by Django 3.2 on 2025-02-26 22:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store_new', '0002_boxqueue_deliveryqueue'),
    ]

    operations = [
        migrations.CreateModel(
            name='CoinCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(help_text='Cod generat de 3 caractere', max_length=3, unique=True)),
                ('value', models.PositiveIntegerField(help_text='Numărul de coins acordați la redeem')),
                ('usage_limit', models.PositiveIntegerField(default=1, help_text='Numărul de utilizări permise pentru acest cod')),
                ('used_count', models.PositiveIntegerField(default=0, help_text='Numărul de utilizări deja efectuate')),
                ('status', models.CharField(choices=[('active', 'Active'), ('used', 'Used')], default='active', max_length=10)),
            ],
        ),
    ]
