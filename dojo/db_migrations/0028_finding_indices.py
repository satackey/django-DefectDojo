# Generated by Django 2.2.4 on 2020-01-19 16:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dojo', '0027_jira_issue_type_settings'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='finding',
            index=models.Index(fields=['false_p'], name='dojo_findin_false_p_aac0c7_idx'),
        ),
        migrations.AddIndex(
            model_name='finding',
            index=models.Index(fields=['verified'], name='dojo_findin_verifie_beb0fc_idx'),
        ),
        migrations.AddIndex(
            model_name='finding',
            index=models.Index(fields=['mitigated'], name='dojo_findin_mitigat_946a13_idx'),
        ),
        migrations.AddIndex(
            model_name='finding',
            index=models.Index(fields=['active'], name='dojo_findin_active_d51077_idx'),
        ),
        migrations.AddIndex(
            model_name='finding',
            index=models.Index(fields=['date'], name='dojo_findin_date_8e9143_idx'),
        ),
        migrations.AlterField(
            model_name='finding',
            name='title',
            field=models.CharField(max_length=511),
        ),
        migrations.AddIndex(
            model_name='finding',
            index=models.Index(fields=['title'], name='dojo_findin_title_78f900_idx'),
        ),

    ]
