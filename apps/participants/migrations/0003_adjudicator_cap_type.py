from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('participants', '0002_adj_type_and_break_size'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adjudicator',
            name='adj_type',
            field=models.CharField(
                choices=[
                    ('C', 'Core Adjudication Panel (CAP)'),
                    ('I', 'Independent Adjudicator (IA)'),
                    ('S', 'School Judge'),
                    ('N', 'New / Trainee Judge'),
                ],
                default='I',
                max_length=1,
            ),
        ),
    ]
