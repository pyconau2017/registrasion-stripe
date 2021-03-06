# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-09-23 06:36
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pinax_stripe', '0003_make_cvc_check_blankable'),
        ('registrasion', '0005_auto_20160905_0945'),
        ('registripe', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StripeCreditNoteRefund',
            fields=[
                ('creditnoterefund_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='registrasion.CreditNoteRefund')),
                ('charge', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pinax_stripe.Charge')),
            ],
            bases=('registrasion.creditnoterefund',),
        ),
    ]
