# Generated by Django 2.2.6 on 2022-02-05 15:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0016_auto_20220204_1647'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='text',
            field=models.TextField(blank=True, help_text='Текст нового комментария', verbose_name='Текст комментария'),
        ),
    ]
