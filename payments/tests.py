import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from marketplace.models import Order
from .models import Payment


@override_settings(ALLOWED_HOSTS=["localhost", "testserver"])
class MpesaCallbackTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="campuscart_buyer",
            password="test-password-123"
        )

        self.order = Order.objects.create(
            buyer=self.user,
            total_amount=Decimal("500.00")
        )

        self.payment = Payment.objects.create(
            order=self.order,
            phone_number="254712345678",
            amount=Decimal("500.00"),
            checkout_request_id="ws_CO_TEST_123"
        )

        self.callback_url = "/payments/mpesa/callback/"

    def send_callback(self, callback):
        payload = {
            "Body": {
                "stkCallback": callback
            }
        }

        return self.client.post(
            self.callback_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_HOST="localhost"
        )

    def test_successful_payment_confirms_order(self):
        callback = {
            "CheckoutRequestID": "ws_CO_TEST_123",
            "ResultCode": 0,
            "ResultDesc": "The service request is processed successfully",
            "CallbackMetadata": {
                "Item": [
                    {"Name": "Amount", "Value": 500},
                    {"Name": "MpesaReceiptNumber", "Value": "ABC123XYZ"},
                    {"Name": "PhoneNumber", "Value": 254712345678},
                ]
            }
        }

        response = self.send_callback(callback)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.payment.status, Payment.Status.SUCCESSFUL)
        self.assertEqual(self.payment.mpesa_receipt_number, "ABC123XYZ")
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)

    def test_failed_payment_does_not_confirm_order(self):
        callback = {
            "CheckoutRequestID": "ws_CO_TEST_123",
            "ResultCode": 1032,
            "ResultDesc": "Request cancelled by customer"
        }

        response = self.send_callback(callback)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.payment.status, Payment.Status.FAILED)
        self.assertEqual(self.order.status, Order.Status.PENDING)

    def test_amount_mismatch_does_not_confirm_order(self):
        callback = {
            "CheckoutRequestID": "ws_CO_TEST_123",
            "ResultCode": 0,
            "ResultDesc": "Success",
            "CallbackMetadata": {
                "Item": [
                    {"Name": "Amount", "Value": 400},
                    {"Name": "MpesaReceiptNumber", "Value": "ABC123XYZ"},
                    {"Name": "PhoneNumber", "Value": 254712345678},
                ]
            }
        }

        response = self.send_callback(callback)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.payment.status, Payment.Status.PENDING)
        self.assertEqual(self.order.status, Order.Status.PENDING)
        self.assertIn("do not match", self.payment.result_description)

    def test_unknown_checkout_id_is_acknowledged(self):
        callback = {
            "CheckoutRequestID": "UNKNOWN_TEST_ID",
            "ResultCode": 1,
            "ResultDesc": "Test transaction"
        }

        response = self.send_callback(callback)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["ResultCode"],
            0
        )
