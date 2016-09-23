from __future__ import unicode_literals

from django.db import models
from registrasion.models import commerce
from pinax.stripe.models import Charge


class StripePayment(commerce.PaymentBase):

    charge = models.ForeignKey(Charge)

class StripeCreditNoteRefund(commerce.CreditNoteRefund):

    charge = models.ForeignKey(Charge)
