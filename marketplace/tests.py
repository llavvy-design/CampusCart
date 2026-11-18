from rest_framework.test import APIClient
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from payments.models import Payment
from payments.services.mpesa import MpesaAPIError
from .models import Order


User = get_user_model()


class OrderCheckoutTests(TestCase):

    def setUp(self):
        self.buyer = User.objects.create_user(
            username="checkout_buyer",
            password="test-password-123"
        )

        self.other_buyer = User.objects.create_user(
            username="other_buyer",
            password="test-password-456"
        )

        self.order = Order.objects.create(
            buyer=self.buyer,
            total_amount=Decimal("500.00")
        )

        self.checkout_url = reverse(
            "marketplace:order_checkout",
            kwargs={"order_id": self.order.pk}
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.buyer)

    def mock_successful_stk_push(self, payment):
        """Simulate Safaricom accepting an STK Push request."""

        payment.merchant_request_id = "MERCHANT_TEST_123"
        payment.checkout_request_id = "ws_CO_CHECKOUT_TEST_123"
        payment.result_description = "STK Push accepted"

        payment.save(update_fields=[
            "merchant_request_id",
            "checkout_request_id",
            "result_description",
            "updated_at",
        ])

        return {
            "ResponseCode": "0",
            "ResponseDescription": "Success",
            "MerchantRequestID": "MERCHANT_TEST_123",
            "CheckoutRequestID": "ws_CO_CHECKOUT_TEST_123",
            "CustomerMessage": "Success. Request accepted.",
        }

    def test_authenticated_buyer_can_initiate_checkout(self):
        with patch(
            "marketplace.views.initiate_stk_push",
            side_effect=self.mock_successful_stk_push
        ):
            response = self.client.post(
                self.checkout_url,
                {"phone_number": "0712345678"},
                content_type="application/json"
            )

        self.assertEqual(response.status_code, 202)

        payment = Payment.objects.get(order=self.order)

        self.assertEqual(payment.amount, Decimal("500.00"))
        self.assertEqual(payment.phone_number, "254712345678")
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(
            payment.checkout_request_id,
            "ws_CO_CHECKOUT_TEST_123"
        )

        self.assertEqual(
            response.json()["status"],
            Payment.Status.PENDING
        )

    def test_client_cannot_override_order_amount(self):
        with patch(
            "marketplace.views.initiate_stk_push",
            side_effect=self.mock_successful_stk_push
        ):
            response = self.client.post(
                self.checkout_url,
                {
                    "phone_number": "0712345678",
                    "amount": "1.00",
                },
                content_type="application/json"
            )

        self.assertEqual(response.status_code, 202)

        payment = Payment.objects.get(order=self.order)

        self.assertEqual(payment.amount, Decimal("500.00"))

    def test_unauthenticated_user_cannot_checkout(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
        self.checkout_url,
        {"phone_number": "0712345678"},
        content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(Payment.objects.count(), 0)

    def test_buyer_cannot_checkout_another_users_order(self):
        self.order.buyer = self.other_buyer
        self.order.save()

        response = self.client.post(
            self.checkout_url,
            {"phone_number": "0712345678"},
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Payment.objects.count(), 0)

    def test_invalid_phone_number_is_rejected(self):
        response = self.client.post(
            self.checkout_url,
            {"phone_number": "12345"},
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Payment.objects.count(), 0)

    def test_existing_pending_payment_prevents_duplicate_checkout(self):
        Payment.objects.create(
            order=self.order,
            phone_number="254712345678",
            amount=Decimal("500.00"),
            status=Payment.Status.PENDING,
        )

        response = self.client.post(
            self.checkout_url,
            {"phone_number": "0712345678"},
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(Payment.objects.count(), 1)

    def test_daraja_failure_marks_payment_as_failed(self):
        with patch(
            "marketplace.views.initiate_stk_push",
            side_effect=MpesaAPIError("Daraja connection failed")
        ):
            response = self.client.post(
                self.checkout_url,
                {"phone_number": "0712345678"},
                content_type="application/json"
            )

        self.assertEqual(response.status_code, 502)

        payment = Payment.objects.get(order=self.order)

        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertIn(
            "Daraja connection failed",
            payment.result_description
        )

    def test_cancelled_order_cannot_be_paid(self):
        self.order.status = Order.Status.CANCELLED
        self.order.save()

        response = self.client.post(
            self.checkout_url,
            {"phone_number": "0712345678"},
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Payment.objects.count(), 0)