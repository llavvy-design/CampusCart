import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('marketplace', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(max_length=15)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('1.00'))])),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('successful', 'Successful'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='pending', max_length=15)),
                ('merchant_request_id', models.CharField(blank=True, max_length=100)),
                ('checkout_request_id', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('mpesa_receipt_number', models.CharField(blank=True, max_length=30, null=True, unique=True)),
                ('result_code', models.CharField(blank=True, max_length=20)),
                ('result_description', models.TextField(blank=True)),
                ('callback_data', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payments', to='marketplace.order')),
            ],
            options={
                'verbose_name': 'Payment',
                'verbose_name_plural': 'Payments',
                'ordering': ['-created_at'],
            },
        ),
    ]
