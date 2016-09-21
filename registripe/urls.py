from django.conf.urls import url

from registripe import views

from pinax.stripe.views import (
    Webhook,
)


urlpatterns = [
    url(r"^card/([0-9]*)/$", views.card, name="registripe_card"),
    url(r"^pubkey/$", views.pubkey_script, name="registripe_pubkey"),
    url(r"^webhook/$", Webhook.as_view(), name="pinax_stripe_webhook"),
]
