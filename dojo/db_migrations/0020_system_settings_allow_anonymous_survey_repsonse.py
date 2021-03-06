# Generated by Django 2.2.1 on 2019-08-21 19:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dojo', '0019_notetype_additions'),
    ]

    operations = [
        migrations.AddField(
            model_name='system_settings',
            name='allow_anonymous_survey_repsonse',
            field=models.BooleanField(default=False, help_text='Enable anyone with a link to the survey to answer a survey', verbose_name='Allow Anonymous Survey Responses'),
        ),
    ]
