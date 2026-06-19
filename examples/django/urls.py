"""URL configuration for the Django example."""

from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("payments/", views.create_payment, name="sibs-create-payment"),
    path("payments/<str:payment_id>/", views.payment_status, name="sibs-payment-status"),
    path("webhooks/sibs/", views.sibs_webhook, name="sibs-webhook"),
]
