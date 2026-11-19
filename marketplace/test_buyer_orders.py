
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


class BuyerOrderManagementTests(TestCase):

    def setUp(self):
        self.buyer = User.objects.create_user(
            username="buyer_test",
            password="buyer-password-123",
        )

        self.other_buyer = User.objects.create_user(
            username="other_buyer_test",
            password="other-password-123",
        )

        self.seller = User.objects.create_user(
            username="seller_test",
            password="seller-password-123",
        )

        self.category = Category.objects.create(
            name="Buyer Order Test Books",
        )

        # Stock has already been reduced by the order reservation.
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Django Development Guide",
            description="A book for buyer order management tests.",
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
            product_name="Django Development Guide",
            unit_price=Decimal("500.00"),
            quantity=2,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.buyer)

        self.list_url = reverse(
            "marketplace:buyer_order_list",
        )

        self.detail_url = reverse(
            "marketplace:buyer_order_detail",
            kwargs={"order_id": self.order.pk},
        )

        self.cancel_url = reverse(
            "marketplace:buyer_order_cancel",
            kwargs={"order_id": self.order.pk},
        )

    def cancel_order(self):
        return self.client.post(
            self.cancel_url,
            {},
            format="json",
        )

    # ==============================================
    # BUYER ORDER LIST TESTS
    # ==============================================

    def test_buyer_can_view_own_orders(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        self.assertEqual(
            response.data["orders"][0]["id"],
            self.order.pk,
        )

        self.assertEqual(
            response.data["orders"][0]["seller_username"],
            self.seller.username,
        )

    def test_buyer_only_sees_their_own_orders(self):
        other_order = Order.objects.create(
            buyer=self.other_buyer,
            seller=self.seller,
            status=Order.Status.PENDING,
            total_amount=Decimal("500.00"),
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

        returned_ids = [
            order["id"]
            for order in response.data["orders"]
        ]

        self.assertIn(self.order.pk, returned_ids)
        self.assertNotIn(other_order.pk, returned_ids)

    def test_unauthenticated_user_cannot_view_order_list(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 401)

    # ==============================================
    # BUYER ORDER DETAIL TESTS
    # ==============================================

    def test_buyer_can_view_order_details(self):
        Payment.objects.create(
            order=self.order,
            phone_number="254712345678",
            amount=Decimal("1000.00"),
            status=Payment.Status.FAILED,
        )

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.data["seller_username"],
            self.seller.username,
        )

        self.assertEqual(
            response.data["status"],
            Order.Status.PENDING,
        )

        self.assertEqual(
            response.data["fulfilment_location"],
            "Main Campus",
        )

        self.assertEqual(len(response.data["items"]), 1)

        self.assertEqual(
            response.data["items"][0]["product_name"],
            "Django Development Guide",
        )

        self.assertEqual(
            response.data["items"][0]["quantity"],
            2,
        )

    def test_order_details_include_payment_summary(self):
        payment = Payment.objects.create(
            order=self.order,
            phone_number="254712345678",
            amount=Decimal("1000.00"),
            status=Payment.Status.FAILED,
        )

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["payments"]), 1)

        payment_summary = response.data["payments"][0]

        self.assertEqual(payment_summary["id"], payment.pk)
        self.assertEqual(
            payment_summary["amount"],
            "1000.00",
        )
        self.assertEqual(
            payment_summary["status"],
            Payment.Status.FAILED,
        )

        self.assertNotIn("phone_number", payment_summary)
        self.assertNotIn("callback_data", payment_summary)

    def test_other_buyer_cannot_view_order_details(self):
        self.client.force_authenticate(user=self.other_buyer)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_user_cannot_view_order_details(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 401)

    # ==============================================
    # BUYER ORDER CANCELLATION TESTS
    # ==============================================

    def test_buyer_can_cancel_pending_unpaid_order(self):
        response = self.cancel_order()

        self.assertEqual(response.status_code, 200)

        self.order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.CANCELLED,
        )

        self.assertEqual(self.product.stock, 10)

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

    def test_cancellation_creates_seller_notification(self):
        response = self.cancel_order()

        self.assertEqual(response.status_code, 200)

        notification = Notification.objects.get(
            recipient=self.seller,
            actor=self.buyer,
            notification_type="order_status_updated",
        )

        self.assertEqual(
            notification.message,
            (
                "The buyer cancelled their order. "
                "The reserved product stock has been released."
            ),
        )

    def test_other_buyer_cannot_cancel_order(self):
        self.client.force_authenticate(user=self.other_buyer)

        response = self.cancel_order()

        self.assertEqual(response.status_code, 404)

        self.order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.PENDING,
        )

        self.assertEqual(self.product.stock, 8)

    def test_seller_cannot_use_buyer_cancellation_endpoint(self):
        self.client.force_authenticate(user=self.seller)

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

    def test_pending_payment_prevents_buyer_cancellation(self):
        Payment.objects.create(
            order=self.order,
            phone_number="254712345678",
            amount=Decimal("1000.00"),
            status=Payment.Status.PENDING,
        )

        response = self.cancel_order()

        self.assertEqual(response.status_code, 409)

        self.order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.PENDING,
        )

        self.assertEqual(self.product.stock, 8)

    def test_successful_payment_prevents_buyer_cancellation(self):
        Payment.objects.create(
            order=self.order,
            phone_number="254712345678",
            amount=Decimal("1000.00"),
            status=Payment.Status.SUCCESSFUL,
            mpesa_receipt_number="BUYERTEST123",
        )

        response = self.cancel_order()

        self.assertEqual(response.status_code, 409)

        self.order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(
            self.order.status,
            Order.Status.PENDING,
        )

        self.assertEqual(self.product.stock, 8)

    def test_failed_payment_does_not_prevent_buyer_cancellation(self):
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

    def test_confirmed_order_cannot_be_cancelled_by_buyer(self):
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

    def test_completed_order_cannot_be_cancelled_by_buyer(self):
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
