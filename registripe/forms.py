from functools import partial

from django import forms
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.forms import widgets

from django_countries import countries
from django_countries.fields import LazyTypedChoiceField
from django_countries.widgets import CountrySelectWidget


class NoRenderWidget(forms.widgets.HiddenInput):

    def render(self, name, value, attrs=None):
        return "<!-- no widget: " + name + " -->"


def secure_striped(widget):
    ''' Calls stripe() with secure=True. '''
    return striped(widget, True)


def striped(WidgetClass, secure=False):
    ''' Takes a given widget and overrides the render method to be suitable
    for stripe.js.

    Arguments:
        widget: The widget class

        secure: if True, only the `data-stripe` attribute will be set. Name
            will be set to None.

    '''

    class StripedWidget(WidgetClass):

        def render(self, name, value, attrs=None):

            if not attrs:
                attrs = {}

            attrs["data-stripe"] = name

            if secure:
                name = ""

            return super(StripedWidget, self).render(
                name, value, attrs=attrs
            )

    return StripedWidget


class CreditCardForm(forms.Form):

    def _media(self):
        js = (
            'https://js.stripe.com/v2/',
            reverse("registripe_pubkey"),
        )

        return forms.Media(js=js)

    media = property(_media)

    number = forms.CharField(
        required=False,
        max_length=255,
        widget=secure_striped(widgets.TextInput)(),
    )
    exp_month = forms.CharField(
        required=False,
        max_length=2,
        widget=secure_striped(widgets.TextInput)(),
    )
    exp_year = forms.CharField(
        required=False,
        max_length=4,
        widget=secure_striped(widgets.TextInput)(),
    )
    cvc = forms.CharField(
        required=False,
        max_length=4,
        widget=secure_striped(widgets.TextInput)(),
    )

    stripe_token = forms.CharField(
        max_length=255,
        #required=True,
        widget=NoRenderWidget(),
    )

    name = forms.CharField(
        required=True,
        max_length=255,
        widget=striped(widgets.TextInput),
    )
    address_line1 = forms.CharField(
        required=True,
        max_length=255,
        widget=striped(widgets.TextInput),
    )
    address_line2 = forms.CharField(
        required=False,
        max_length=255,
        widget=striped(widgets.TextInput),
    )
    address_city = forms.CharField(
        required=True,
        max_length=255,
        widget=striped(widgets.TextInput),
    )
    address_state = forms.CharField(
        required=True, max_length=255,
        widget=striped(widgets.TextInput),
    )
    address_zip = forms.CharField(
        required=True,
        max_length=255,
        widget=striped(widgets.TextInput),
    )
    address_country = LazyTypedChoiceField(
        choices=countries,
        widget=striped(CountrySelectWidget),
    )


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
