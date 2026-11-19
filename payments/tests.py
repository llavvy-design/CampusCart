import json
from decimal import Decimal
from unittest.mock import Mock, patch
from rest_framework.test import APIClient

from .services.mpesa import (
    MpesaAPIError,
    MpesaConfigurationError,
    query_stk_push,
)

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

    def test_successful_payment_creates_buyer_notification(self):
        from notifications.models import Notification

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
            },
        }

        response = self.send_callback(callback)

        self.assertEqual(response.status_code, 200)

        notification = Notification.objects.get(
            recipient=self.user,
            notification_type="payment_successful",
        )

        self.assertEqual(
            notification.message,
            "Your payment was received and your order has been confirmed.",
        )
        self.assertIsNone(notification.actor)

    def test_duplicate_successful_callback_does_not_create_duplicate_notification(self):
        from notifications.models import Notification

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
            },
        }

        self.send_callback(callback)
        self.send_callback(callback)

        self.assertEqual(
            Notification.objects.filter(
                recipient=self.user,
                notification_type="payment_successful",
            ).count(),
            1,
        )
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
class MpesaQueryTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="query_test_buyer",
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
            checkout_request_id="ws_CO_QUERY_TEST_123",
            stk_timestamp="20261118160732"
        )

    @patch("payments.services.mpesa.requests.post")
    @patch("payments.services.mpesa.get_access_token")
    @patch("payments.services.mpesa.generate_stk_password")
    def test_query_stk_push_success(
        self,
        mock_password,
        mock_token,
        mock_post
    ):
        mock_password.return_value = (
            "20261118170000",
            "mock-generated-password"
        )

        mock_token.return_value = "mock-access-token"

        mock_response = Mock()
        mock_response.json.return_value = {
            "ResponseCode": "0",
            "ResponseDescription": "The service request has been accepted successfully",
            "MerchantRequestID": "test-merchant-id",
            "CheckoutRequestID": "ws_CO_QUERY_TEST_123",
            "ResultCode": "0",
            "ResultDesc": "The service request is processed successfully"
        }
        mock_response.raise_for_status.return_value = None

        mock_post.return_value = mock_response

        result = query_stk_push(self.payment)

        self.assertEqual(result["ResponseCode"], "0")

        mock_post.assert_called_once()

        request_kwargs = mock_post.call_args.kwargs

        self.assertEqual(
            request_kwargs["json"]["CheckoutRequestID"],
            "ws_CO_QUERY_TEST_123"
        )

        self.assertEqual(
            request_kwargs["headers"]["Authorization"],
            "Bearer mock-access-token"
        )

        self.assertEqual(
            request_kwargs["json"]["Timestamp"],
            "20261118170000"
        )

    def test_query_without_checkout_id_raises_error(self):
        self.payment.checkout_request_id = ""

        with self.assertRaises(ValueError):
            query_stk_push(self.payment)

    def test_query_without_shortcode_raises_configuration_error(self):
        with patch.dict("os.environ", {"MPESA_SHORTCODE": ""}):
            with self.assertRaises(MpesaConfigurationError):
                query_stk_push(self.payment)


class PaymentStatusViewTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.buyer = User.objects.create_user(
            username="status_test_buyer",
            password="test-password-123"
        )

        self.other_buyer = User.objects.create_user(
            username="other_status_buyer",
            password="test-password-123"
        )

        self.order = Order.objects.create(
            buyer=self.buyer,
            total_amount=Decimal("500.00")
        )

        self.payment = Payment.objects.create(
            order=self.order,
            phone_number="254712345678",
            amount=Decimal("500.00"),
            checkout_request_id="ws_CO_STATUS_TEST_123"
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.buyer)

        self.url = f"/payments/{self.payment.pk}/status/"

    @patch("payments.views.query_stk_push")
    def test_buyer_can_check_pending_payment(self, mock_query):
        mock_query.return_value = {
            "ResponseCode": "0",
            "ResponseDescription": "Query accepted",
            "CheckoutRequestID": "ws_CO_STATUS_TEST_123"
        }

        response = self.client.get(self.url)

        self.payment.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Payment.Status.PENDING)
        self.assertIn("query_response", response.data)

        # An accepted query must not mark payment as successful.
        self.assertEqual(self.payment.status, Payment.Status.PENDING)

        mock_query.assert_called_once()

    def test_unauthenticated_user_cannot_check_payment(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)

    @patch("payments.views.query_stk_push")
    def test_buyer_cannot_check_another_buyers_payment(self, mock_query):
        other_order = Order.objects.create(
            buyer=self.other_buyer,
            total_amount=Decimal("300.00")
        )

        other_payment = Payment.objects.create(
            order=other_order,
            phone_number="254711111111",
            amount=Decimal("300.00"),
            checkout_request_id="ws_CO_OTHER_BUYER_123"
        )

        response = self.client.get(
            f"/payments/{other_payment.pk}/status/"
        )

        self.assertEqual(response.status_code, 404)
        mock_query.assert_not_called()

    @patch("payments.views.query_stk_push")
    def test_finalized_payment_does_not_query_daraja(self, mock_query):
        self.payment.status = Payment.Status.SUCCESSFUL
        self.payment.mpesa_receipt_number = "TESTRECEIPT123"
        self.payment.save()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Payment.Status.SUCCESSFUL)
        self.assertEqual(
            response.data["receipt_number"],
            "TESTRECEIPT123"
        )

        mock_query.assert_not_called()

    @patch("payments.views.query_stk_push")
    def test_daraja_error_returns_gateway_error(self, mock_query):
        mock_query.side_effect = MpesaAPIError(
            "Safaricom API unavailable"
        )

        response = self.client.get(self.url)

        self.payment.refresh_from_db()

        self.assertEqual(response.status_code, 502)
        self.assertEqual(self.payment.status, Payment.Status.PENDING)

    @patch("payments.views.query_stk_push")
    def test_missing_payment_returns_404(self, mock_query):
        response = self.client.get("/payments/99999/status/")

        self.assertEqual(response.status_code, 404)
        mock_query.assert_not_called()
