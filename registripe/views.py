import forms
import models

from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import redirect, render

from registrasion.controllers.credit_note import CreditNoteController
from registrasion.controllers.invoice import InvoiceController
from registrasion.models import commerce

from pinax.stripe import actions
from pinax.stripe.actions import refunds as pinax_stripe_actions_refunds

from stripe.error import StripeError

from symposion.conference.models import Conference

CURRENCY = settings.INVOICE_CURRENCY
CONFERENCE_ID = settings.CONFERENCE_ID


def _staff_only(user):
    ''' Returns true if the user is staff. '''
    return user.is_staff


def pubkey_script(request):
    ''' Returns a JS snippet that sets the Stripe public key for Stripe.js. '''

    script_template = "Stripe.setPublishableKey('%s');"
    script = script_template % settings.PINAX_STRIPE_PUBLIC_KEY

    return HttpResponse(script, content_type="text/javascript")


def card(request, invoice_id, access_code=None):
    ''' View that shows and processes a Stripe CreditCardForm to pay the given
    invoice. Redirects back to the invoice once the invoice is fully paid.

    Arguments:
        invoice_id (castable to str): The invoice id for the invoice to pay.
        access_code (str): The optional access code for the invoice (for
            unauthenticated payment)

    '''

    form = forms.CreditCardForm(request.POST or None)

    inv = InvoiceController.for_id_or_404(str(invoice_id))

    if not inv.can_view(user=request.user, access_code=access_code):
        raise Http404()

    args = [inv.invoice.id]
    if access_code:
        args.append(access_code)
    to_invoice = redirect("invoice", *args)

    if inv.invoice.balance_due() <= 0:
        return to_invoice

    if request.POST and form.is_valid():
        try:
            inv.validate_allowed_to_pay()  # Verify that we're allowed to do this.
            process_card(request, form, inv)
            return to_invoice
        except StripeError as e:
            form.add_error(None, ValidationError(e))
        except ValidationError as ve:
            form.add_error(None, ve)

    data = {
        "invoice": inv.invoice,
        "form": form,
    }

    return render(
        request, "registrasion/stripe/credit_card_payment.html", data
    )


@transaction.atomic
def process_card(request, form, inv):
    ''' Processes the given credit card form

    Arguments:
        request: the current request context
        form: a CreditCardForm
        inv: an InvoiceController
    '''

    conference = Conference.objects.get(id=CONFERENCE_ID)
    amount_to_pay = inv.invoice.balance_due()
    user = inv.invoice.user
    token = form.cleaned_data["stripe_token"]

    customer = actions.customers.get_customer_for_user(user)

    if not customer:
        customer = actions.customers.create(user)

    card = actions.sources.create_card(customer, token)

    description="Payment for %s invoice #%s" % (
        conference.title, inv.invoice.id
    )

    charge = actions.charges.create(
        amount_to_pay,
        customer,
        source=card,
        currency=CURRENCY,
        description=description,
        capture=True,
    )

    receipt = charge.stripe_charge.id
    reference = "Paid with Stripe reference: " + receipt

    # Create the payment object
    models.StripePayment.objects.create(
        invoice=inv.invoice,
        reference=reference,
        amount=charge.amount,
        charge=charge,
    )

    inv.update_status()

    messages.success(request, "This invoice was successfully paid.")


@user_passes_test(_staff_only)
def refund(request, credit_note_id):
    ''' Allows staff to select a Stripe charge for the owner of the credit
    note, and refund the credit note into stripe. '''

    cn = CreditNoteController.for_id_or_404(str(credit_note_id))

    to_credit_note = redirect("credit_note", cn.credit_note.id)

    if not cn.credit_note.is_unclaimed:
        return to_credit_note

    form = forms.StripeRefundForm(
        request.POST or None,
        user=cn.credit_note.invoice.user,
        min_value=cn.credit_note.value,
    )

    if request.POST and form.is_valid():
        try:
            process_refund(cn, form)
            return to_credit_note
        except StripeError as se:
            form.add_error(None, ValidationError(se))

    data = {
        "credit_note": cn.credit_note,
        "form": form,
    }

    return render(
        request, "registrasion/stripe/refund.html", data
    )


def process_refund(cn, form):
    payment = form.cleaned_data["payment"]
    charge = payment.charge

    to_refund = cn.credit_note.value
    stripe_charge_id = charge.stripe_charge.id

    # Test that the given charge is allowed to be refunded.
    max_refund = actions.charges.calculate_refund_amount(charge)

    if max_refund < to_refund:
        raise ValidationError(
            "You must select a payment holding greater value than "
            "the credit note."
        )

    refund = actions.refunds.create(charge, to_refund)

    models.StripeCreditNoteRefund.objects.create(
        parent=cn.credit_note,
        charge=charge,
        reference="Refunded %s to Stripe charge %s" % (
            to_refund, stripe_charge_id
        )
    )
