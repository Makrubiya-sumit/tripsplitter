from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('expenses', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='currency',
            field=models.CharField(
                choices=[
                    ('INR', 'Indian Rupee (₹)'), ('USD', 'US Dollar ($)'),
                    ('EUR', 'Euro (€)'), ('GBP', 'British Pound (£)'),
                    ('AED', 'UAE Dirham (د.إ)'), ('AUD', 'Australian Dollar (A$)'),
                    ('CAD', 'Canadian Dollar (C$)'), ('SGD', 'Singapore Dollar (S$)'),
                    ('JPY', 'Japanese Yen (¥)'), ('THB', 'Thai Baht (฿)'),
                ],
                default='INR', max_length=3,
            ),
        ),
    ]
