import copy

from django import forms
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.forms import widgets
from django.utils import timezone

from django_countries import countries
from django_countries.fields import LazyTypedChoiceField
from django_countries.widgets import CountrySelectWidget


class NoRenderWidget(forms.widgets.HiddenInput):

    def render(self, name, value, attrs=None):
        return "<!-- no widget: " + name + " -->"


def secure_striped(field):
    ''' Calls stripe() with secure=True. '''
    return striped(field, True)


def striped(field, secure=False):

    oldwidget = field.widget
    field.widget = StripeWidgetProxy(oldwidget, secure)
    return field


class StripeWidgetProxy(widgets.Widget):

    def __init__(self, underlying, secure=False):
        self.underlying = underlying
        self.secure = secure

    def __deepcopy__(self, memo):
        copy_underlying = copy.deepcopy(self.underlying, memo)
        return type(self)(copy_underlying)

    def __getattribute__(self, attr):
        spr = super(StripeWidgetProxy, self).__getattribute__
        if attr in ("underlying", "render", "secure", "__deepcopy__"):
            return spr(attr)
        else:
            return getattr(self.underlying, attr)

    def render(self, name, value, attrs=None):

        print "RENDER: " + name
        if not attrs:
            attrs = {}

        attrs["data-stripe"] = name

        if self.secure:
            name = ""

        return self.underlying.render(name, value, attrs=attrs)


class CreditCardForm(forms.Form):

    def _media(self):
        js = (
            'https://js.stripe.com/v2/',
            reverse("registripe_pubkey"),
        )

        return forms.Media(js=js)

    media = property(_media)

    number = secure_striped(forms.CharField(
        required=False,
        label="Credit card Number",
        help_text="Your credit card number, with or without spaces.",
        max_length=255,
    ))
    exp_month = secure_striped(forms.IntegerField(
        required=False,
        label="Card expiry month",
        min_value=1,
        max_value=12,
    ))
    exp_year = secure_striped(forms.IntegerField(
        required=False,
        label="Card expiry year",
        help_text="The expiry year for your card in 4-digit form",
        min_value=lambda: timezone.now().year,
    ))
    cvc = secure_striped(forms.CharField(
        required=False,
        min_length=3,
        max_length=4,
    ))

    stripe_token = forms.CharField(
        max_length=255,
        #required=True,
        widget=NoRenderWidget(),
    )

    name = striped(forms.CharField(
        required=True,
        label="Cardholder name",
        help_text="The cardholder's name, as it appears on the credit card",
        max_length=255,
    ))
    address_line1 = striped(forms.CharField(
        required=True,
        label="Cardholder account address, line 1",
        max_length=255,
    ))
    address_line2 = striped(forms.CharField(
        required=False,
        label="Cardholder account address, line 2",
        max_length=255,
    ))
    address_city = striped(forms.CharField(
        required=True,
        label="Cardholder account city",
        max_length=255,
    ))
    address_state = striped(forms.CharField(
        required=True,
        max_length=255,
        label="Cardholder account state or province",
    ))
    address_zip = striped(forms.CharField(
        required=True,
        max_length=255,
        label="Cardholder account postal code",
    ))
    address_country = striped(LazyTypedChoiceField(
        label="Cardholder account country",
        choices=countries,
        widget=CountrySelectWidget,
    ))


'''{
From stripe.js details:

Card details:

The first argument to createToken is a JavaScript object containing credit card data entered by the user. It should contain the following required members:

number: card number as a string without any separators (e.g., "4242424242424242")
exp_month: two digit number representing the card's expiration month (e.g., 12)
exp_year: two or four digit number representing the card's expiration year (e.g., 2017)
(The expiration date can also be passed as a single string.)

cvc: optional, but we highly recommend you provide it to help prevent fraud. This is the card's security code, as a string (e.g., "123").
The following fields are entirely optional and cannot result in a token creation failure:

name: cardholder name
address_line1: billing address line 1
address_line2: billing address line 2
address_city: billing address city
address_state: billing address state
address_zip: billing postal code as a string (e.g., "94301")
address_country: billing address country
}
'''
