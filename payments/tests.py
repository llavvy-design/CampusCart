import json
from decimal import Decimal
from unittest.mock import Mock, patch
from .services.mpesa import MpesaConfigurationError, query_stk_push

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