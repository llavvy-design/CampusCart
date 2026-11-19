
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient

from notifications.models import Notification
from payments.models import Payment

from .models import (
    Category,
    Order,
    OrderItem,
    Product,
)


User = get_user_model()


class SellerOrderCancellationTests(TestCase):

    def setUp(self):
        self.buyer = User.objects.create_user(
            username="cancellation_buyer",
            password="test-password-123",
        )

        self.seller = User.objects.create_user(
            username="cancellation_seller",
            password="test-password-456",
        )

        self.other_seller = User.objects.create_user(
            username="cancellation_other_seller",
            password="test-password-789",
        )

        self.category = Category.objects.create(
            name="Cancellation Test Books",
        )

        # Stock is already reduced by the order reservation.
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Python Testing Guide",
            description="A book for testing cancellation.",
            price=Decimal("500.00"),
            stock=8,
            is_available=True,
        )

        self.order = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            status=Order.Status.PENDING,
            total_amount=Decimal("1000.00"),
            fulfilment_location="Main Campus",
            buyer_note="Please call before delivery.",
        )

        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name="Python Testing Guide",
            unit_price=Decimal("500.00"),
            quantity=2,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.seller)

        self.cancel_url = reverse(
            "marketplace:seller_order_cancel",
            kwargs={"order_id": self.order.pk},
        )

    def cancel_order(self):
        return self.client.post(
            self.cancel_url,
            {},
            format="json",
        )

    def test_seller_can_cancel_pending_unpaid_order(self):
        response = self.cancel_order()

        self.assertEqual(response.status_code, 200)

        self.order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.CANCELLED,
        )

        self.assertEqual(self.product.stock, 10)

        self.assertIn(
            "stock has been restored",
            response.data["message"],
        )

    def test_cancellation_restores_product_stock(self):
        self.assertEqual(self.product.stock, 8)

        response = self.cancel_order()

        self.assertEqual(response.status_code, 200)

        self.product.refresh_from_db()

        self.assertEqual(self.product.stock, 10)

    def test_repeated_cancellation_does_not_restore_stock_twice(self):
        first_response = self.cancel_order()

        self.assertEqual(first_response.status_code, 200)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)

        second_response = self.cancel_order()

        self.assertEqual(second_response.status_code, 400)

        self.product.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(self.product.stock, 10)
        self.assertEqual(
            self.order.status,
            Order.Status.CANCELLED,
        )

    def test_cancellation_creates_buyer_notification(self):
        response = self.cancel_order()

        self.assertEqual(response.status_code, 200)

        notification = Notification.objects.get(
            recipient=self.buyer,
            actor=self.seller,
            notification_type="order_status_updated",
        )

        self.assertEqual(
            notification.message,
            (
                "The seller cancelled your order. "
                "The reserved product stock has been released."
            ),
        )

    def test_other_seller_cannot_cancel_order(self):
        self.client.force_authenticate(user=self.other_seller)

        response = self.cancel_order()

        self.assertEqual(response.status_code, 404)

        self.order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.PENDING,
        )
        self.assertEqual(self.product.stock, 8)

    def test_buyer_cannot_use_seller_cancellation_endpoint(self):
        self.client.force_authenticate(user=self.buyer)

        response = self.cancel_order()

        self.assertEqual(response.status_code, 404)

        self.order.refresh_from_db()
        self.assertEqual(
            self.order.status,
            Order.Status.PENDING,
        )

    def test_unauthenticated_user_cannot_cancel_order(self):
        self.client.force_authenticate(user=None)

        response = self.cancel_order()

        self.assertEqual(response.status_code, 401)

    def test_pending_payment_prevents_cancellation(self):
        Payment.objects.create(
            order=self.order,
            phone_number="254712345678",
            amount=Decimal("1000.00"),
            status=Payment.Status.PENDING,
        )

        response = self.cancel_order()

        self.assertEqual(response.status_code, 400)
        self.assertIn("payment", response.data)

        self.order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.PENDING,
        )
        self.assertEqual(self.product.stock, 8)

    def test_successful_payment_prevents_cancellation(self):
        Payment.objects.create(
            order=self.order,
            phone_number="254712345678",
            amount=Decimal("1000.00"),
            status=Payment.Status.SUCCESSFUL,
            mpesa_receipt_number="TESTRECEIPT123",
        )

        response = self.cancel_order()

        self.assertEqual(response.status_code, 400)
        self.assertIn("payment", response.data)

        self.order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.PENDING,
        )
        self.assertEqual(self.product.stock, 8)

    def test_failed_payment_does_not_prevent_cancellation(self):
        Payment.objects.create(
            order=self.order,
            phone_number="254712345678",
            amount=Decimal("1000.00"),
            status=Payment.Status.FAILED,
        )

        response = self.cancel_order()

        self.assertEqual(response.status_code, 200)

        self.order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.CANCELLED,
        )
        self.assertEqual(self.product.stock, 10)

    def test_confirmed_order_cannot_be_cancelled(self):
        self.order.status = Order.Status.CONFIRMED
        self.order.save(update_fields=["status"])

        response = self.cancel_order()

        self.assertEqual(response.status_code, 400)

        self.order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.CONFIRMED,
        )
        self.assertEqual(self.product.stock, 8)

    def test_completed_order_cannot_be_cancelled(self):
        self.order.status = Order.Status.COMPLETED
        self.order.save(update_fields=["status"])

        response = self.cancel_order()

        self.assertEqual(response.status_code, 400)

        self.order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.COMPLETED,
        )
        self.assertEqual(self.product.stock, 8)
