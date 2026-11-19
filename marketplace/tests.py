from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient

from notifications.models import Notification
from payments.models import Payment
from payments.services.mpesa import MpesaAPIError

from .models import (
    Cart,
    CartItem,
    Category,
    Order,
    OrderItem,
    Product,
)


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


class OrderCreationTests(TestCase):

    def setUp(self):
        self.buyer = User.objects.create_user(
            username="order_buyer",
            password="test-password-123"
        )

        self.seller = User.objects.create_user(
            username="order_seller",
            password="test-password-456"
        )

        self.other_seller = User.objects.create_user(
            username="other_seller",
            password="test-password-789"
        )

        self.category = Category.objects.create(
            name="Books"
        )

        self.product_one = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Python Programming",
            description="A programming textbook.",
            price=Decimal("800.00"),
            stock=10,
            is_available=True,
        )

        self.product_two = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Database Systems",
            description="A database textbook.",
            price=Decimal("500.00"),
            stock=5,
            is_available=True,
        )

        self.cart = Cart.objects.create(
            user=self.buyer
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.buyer)

        self.order_url = reverse("marketplace:order_create")

    def add_to_cart(self, product, quantity=1):
        return CartItem.objects.create(
            cart=self.cart,
            product=product,
            quantity=quantity,
        )

    def test_buyer_can_create_order_from_cart(self):
        self.add_to_cart(self.product_one, quantity=2)
        self.add_to_cart(self.product_two, quantity=1)

        response = self.client.post(
            self.order_url,
            {
                "fulfilment_location": "Main Campus",
                "buyer_note": "Please contact me before delivery.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        order = Order.objects.get(buyer=self.buyer)

        self.assertEqual(order.seller, self.seller)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.total_amount, Decimal("2100.00"))
        self.assertEqual(order.fulfilment_location, "Main Campus")
        self.assertEqual(
            order.buyer_note,
            "Please contact me before delivery."
        )

        self.assertEqual(order.items.count(), 2)

        # Refresh the original product instances to read saved stock.
        self.product_one.refresh_from_db()
        self.product_two.refresh_from_db()

        self.assertEqual(self.product_one.stock, 8)
        self.assertEqual(self.product_two.stock, 4)

        self.assertEqual(self.cart.items.count(), 0)

    def test_order_items_preserve_product_names_and_prices(self):
        self.add_to_cart(self.product_one, quantity=2)

        response = self.client.post(
            self.order_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        order = Order.objects.get(buyer=self.buyer)
        order_item = OrderItem.objects.get(order=order)

        self.assertEqual(
            order_item.product_name,
            "Python Programming"
        )
        self.assertEqual(
            order_item.unit_price,
            Decimal("800.00")
        )
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(
            order_item.line_total,
            Decimal("1600.00")
        )

    def test_buyer_cannot_override_order_total(self):
        self.add_to_cart(self.product_one, quantity=1)

        response = self.client.post(
            self.order_url,
            {
                "total_amount": "1.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        order = Order.objects.get(buyer=self.buyer)

        self.assertEqual(
            order.total_amount,
            Decimal("800.00")
        )

    def test_empty_cart_cannot_create_order(self):
        response = self.client.post(
            self.order_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_products_from_multiple_sellers_are_rejected(self):
        other_product = Product.objects.create(
            seller=self.other_seller,
            category=self.category,
            name="Scientific Calculator",
            description="A scientific calculator.",
            price=Decimal("1200.00"),
            stock=5,
            is_available=True,
        )

        self.add_to_cart(self.product_one)
        self.add_to_cart(other_product)

        response = self.client.post(
            self.order_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.cart.items.count(), 2)

        self.product_one.refresh_from_db()
        other_product.refresh_from_db()

        self.assertEqual(self.product_one.stock, 10)
        self.assertEqual(other_product.stock, 5)

    def test_buyer_cannot_purchase_own_product(self):
        own_product = Product.objects.create(
            seller=self.buyer,
            category=self.category,
            name="My Own Book",
            description="A book listed by the buyer.",
            price=Decimal("300.00"),
            stock=3,
            is_available=True,
        )

        self.add_to_cart(own_product)

        response = self.client.post(
            self.order_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.cart.items.count(), 1)

        own_product.refresh_from_db()
        self.assertEqual(own_product.stock, 3)

    def test_insufficient_stock_rejects_order(self):
        self.add_to_cart(self.product_one, quantity=11)

        response = self.client.post(
            self.order_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.cart.items.count(), 1)

        self.product_one.refresh_from_db()
        self.assertEqual(self.product_one.stock, 10)

    def test_unavailable_product_rejects_order(self):
        self.product_one.is_available = False
        self.product_one.save(update_fields=["is_available"])

        self.add_to_cart(self.product_one)

        response = self.client.post(
            self.order_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.cart.items.count(), 1)

        self.product_one.refresh_from_db()
        self.assertEqual(self.product_one.stock, 10)

    def test_failed_order_does_not_partially_reduce_stock(self):
        self.add_to_cart(self.product_one, quantity=2)
        self.add_to_cart(self.product_two, quantity=10)

        response = self.client.post(
            self.order_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)
        self.assertEqual(self.cart.items.count(), 2)

        self.product_one.refresh_from_db()
        self.product_two.refresh_from_db()

        self.assertEqual(self.product_one.stock, 10)
        self.assertEqual(self.product_two.stock, 5)

    def test_unauthenticated_user_cannot_create_order(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.order_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(Order.objects.count(), 0)


class SellerOrderManagementTests(TestCase):

    def setUp(self):
        self.buyer = User.objects.create_user(
            username="seller_api_buyer",
            password="test-password-123"
        )

        self.seller = User.objects.create_user(
            username="seller_api_seller",
            password="test-password-456"
        )

        self.other_seller = User.objects.create_user(
            username="seller_api_other",
            password="test-password-789"
        )

        self.category = Category.objects.create(
            name="Seller API Books"
        )

        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Django for Beginners",
            description="A Django programming book.",
            price=Decimal("1200.00"),
            stock=8,
            is_available=True,
        )

        self.order = Order.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            status=Order.Status.CONFIRMED,
            total_amount=Decimal("2400.00"),
            fulfilment_location="Main Campus",
            buyer_note="Please call when you arrive.",
        )

        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name="Django for Beginners",
            unit_price=Decimal("1200.00"),
            quantity=2,
        )

        # An unrelated order belonging to another seller.
        self.other_order = Order.objects.create(
            buyer=self.buyer,
            seller=self.other_seller,
            status=Order.Status.CONFIRMED,
            total_amount=Decimal("500.00"),
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.seller)

        self.list_url = reverse(
            "marketplace:seller_order_list"
        )

        self.detail_url = reverse(
            "marketplace:seller_order_detail",
            kwargs={"order_id": self.order.pk}
        )

        self.status_url = reverse(
            "marketplace:seller_order_status_update",
            kwargs={"order_id": self.order.pk}
        )

    def test_seller_can_list_only_their_orders(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["orders"]), 1)

        listed_order = response.data["orders"][0]

        self.assertEqual(listed_order["id"], self.order.pk)
        self.assertEqual(
            listed_order["buyer_username"],
            self.buyer.username
        )
        self.assertEqual(listed_order["item_count"], 1)

    def test_seller_can_view_order_details(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.order.pk)
        self.assertEqual(
            response.data["buyer_username"],
            self.buyer.username
        )
        self.assertEqual(
            response.data["fulfilment_location"],
            "Main Campus"
        )
        self.assertEqual(
            response.data["buyer_note"],
            "Please call when you arrive."
        )
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(
            response.data["items"][0]["product_name"],
            "Django for Beginners"
        )
        self.assertEqual(
            response.data["items"][0]["line_total"],
            "2400.00"
        )

    def test_seller_cannot_view_another_sellers_order(self):
        url = reverse(
            "marketplace:seller_order_detail",
            kwargs={"order_id": self.other_order.pk}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_seller_cannot_update_another_sellers_order(self):
        url = reverse(
            "marketplace:seller_order_status_update",
            kwargs={"order_id": self.other_order.pk}
        )

        response = self.client.patch(
            url,
            {"status": Order.Status.PROCESSING},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.other_order.refresh_from_db()
        self.assertEqual(
            self.other_order.status,
            Order.Status.CONFIRMED
        )

    def test_buyer_cannot_access_seller_order_list(self):
        self.client.force_authenticate(user=self.buyer)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_unauthenticated_user_cannot_access_seller_orders(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 401)

    def test_seller_can_move_confirmed_order_to_processing(self):
        response = self.client.patch(
            self.status_url,
            {"status": Order.Status.PROCESSING},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.order.refresh_from_db()
        self.assertEqual(
            self.order.status,
            Order.Status.PROCESSING
        )

    def test_seller_can_move_processing_order_to_completed(self):
        self.order.status = Order.Status.PROCESSING
        self.order.save(update_fields=["status"])

        response = self.client.patch(
            self.status_url,
            {"status": Order.Status.COMPLETED},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.order.refresh_from_db()
        self.assertEqual(
            self.order.status,
            Order.Status.COMPLETED
        )

    def test_seller_status_update_creates_buyer_notification(self):
        response = self.client.patch(
            self.status_url,
            {"status": Order.Status.PROCESSING},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        notification = Notification.objects.get(
            recipient=self.buyer,
            actor=self.seller,
            notification_type="order_status_updated",
        )

        self.assertEqual(
            notification.message,
            "Your order is now being processed by the seller."
        )

    def test_seller_cannot_process_pending_unpaid_order(self):
        self.order.status = Order.Status.PENDING
        self.order.save(update_fields=["status"])

        response = self.client.patch(
            self.status_url,
            {"status": Order.Status.PROCESSING},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.order.refresh_from_db()
        self.assertEqual(
            self.order.status,
            Order.Status.PENDING
        )

        self.assertEqual(
            Notification.objects.filter(
                recipient=self.buyer,
                notification_type="order_status_updated",
            ).count(),
            0,
        )

    def test_seller_cannot_skip_processing_and_complete_order(self):
        response = self.client.patch(
            self.status_url,
            {"status": Order.Status.COMPLETED},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.order.refresh_from_db()
        self.assertEqual(
            self.order.status,
            Order.Status.CONFIRMED
        )

    def test_seller_cannot_change_completed_order_again(self):
        self.order.status = Order.Status.COMPLETED
        self.order.save(update_fields=["status"])

        response = self.client.patch(
            self.status_url,
            {"status": Order.Status.PROCESSING},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.order.refresh_from_db()
        self.assertEqual(
            self.order.status,
            Order.Status.COMPLETED
        )

    def test_invalid_status_value_is_rejected(self):
        response = self.client.patch(
            self.status_url,
            {"status": "shipped"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.order.refresh_from_db()
        self.assertEqual(
            self.order.status,
            Order.Status.CONFIRMED
        )
