
from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path(
        "mpesa/callback/",
        views.mpesa_callback,
        name="mpesa_callback"
    ),
    path(
        "<int:payment_id>/status/",
        views.PaymentStatusView.as_view(),
        name="payment_status"
    ),
]
