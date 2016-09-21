import forms
import models

from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render

from registrasion.controllers.invoice import InvoiceController
from registrasion.models import commerce

from pinax.stripe import actions
from stripe.error import StripeError

from symposion.conference.models import Conference

CURRENCY = settings.INVOICE_CURRENCY
CONFERENCE_ID = settings.CONFERENCE_ID


def pubkey_script(request):
    ''' Returns a JS snippet that sets the Stripe public key for Stripe.js. '''

    script_template = "Stripe.setPublishableKey('%s');"
    script = script_template % settings.PINAX_STRIPE_PUBLIC_KEY

    return HttpResponse(script, content_type="text/javascript")


def card(request, invoice_id):
    ''' View that shows and processes a Stripe CreditCardForm to pay the given
    invoice. Redirects back to the invoice once the invoice is fully paid.

    Arguments:
        invoice_id (castable to str): The invoice id for the invoice to pay.

    '''

    form = forms.CreditCardForm(request.POST or None)

    inv = InvoiceController.for_id_or_404(str(invoice_id))

    if not inv.can_view(user=request.user):
        raise Http404()

    to_invoice = redirect("invoice", inv.invoice.id)

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

    token = form.cleaned_data["stripe_token"]

    customer = actions.customers.get_customer_for_user(request.user)

    if not customer:
        customer = actions.customers.create(request.user)

    card = actions.sources.create_card(customer, token)

    description="Payment for %s invoice #%s" % (
        conference.title, inv.invoice.id
    )

    try:
        charge = actions.charges.create(
            amount_to_pay,
            customer,
            currency=CURRENCY,
            description=description,
            capture=False,
        )

        receipt = charge.stripe_charge.receipt_number
        if not receipt:
            receipt = charge.stripe_charge.id
        reference = "Paid with Stripe receipt number: " + receipt

        # Create the payment object
        models.StripePayment.objects.create(
            invoice=inv.invoice,
            reference=reference,
            amount=charge.amount,
            charge=charge,
        )
    except StripeError as e:
        raise e
    finally:
        # Do not actually charge the account until we've reconciled locally.
        actions.charges.capture(charge)

    inv.update_status()

    messages.success(request, "This invoice was successfully paid.")
