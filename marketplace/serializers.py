from decimal import Decimal

from django.db import transaction

from rest_framework import serializers

from payments.services.mpesa import normalize_mpesa_phone

from .models import (
    Cart,
    Order,
    OrderItem,
    Product,
)


class CheckoutSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
        max_length=20,
        required=True
    )

    def validate_phone_number(self, value):
        try:
            return normalize_mpesa_phone(value)
        except ValueError as error:
            raise serializers.ValidationError(str(error))


class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "total_amount",
            "fulfilment_location",
            "buyer_note",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "order_number",
            "status",
            "total_amount",
            "created_at",
        ]

    @transaction.atomic
    def create(self, validated_data):
        buyer = self.context["request"].user

        # Lock the buyer's cart while processing the order.
        try:
            cart = Cart.objects.select_for_update().get(user=buyer)
        except Cart.DoesNotExist:
            raise serializers.ValidationError({
                "cart": "You do not have a shopping cart."
            })

        # Lock cart items and retrieve their products.
        cart_items = list(
            cart.items.select_for_update()
            .select_related("product")
            .order_by("product_id")
        )

        if not cart_items:
            raise serializers.ValidationError({
                "cart": "Your shopping cart is empty."
            })

        # Lock product records to protect stock updates.
        product_ids = [item.product_id for item in cart_items]

        locked_products = {
            product.pk: product
            for product in Product.objects.select_for_update()
            .filter(pk__in=product_ids)
            .order_by("pk")
        }

        if len(locked_products) != len(product_ids):
            raise serializers.ValidationError({
                "cart": "One or more products are no longer available."
            })

        # All products in one order must belong to one seller.
        sellers = {
            locked_products[item.product_id].seller_id
            for item in cart_items
        }

        if len(sellers) != 1:
            raise serializers.ValidationError({
                "cart": (
                    "Please place separate orders for products "
                    "from different sellers."
                )
            })

        seller_id = next(iter(sellers))

        if buyer.pk == seller_id:
            raise serializers.ValidationError({
                "cart": "You cannot purchase your own products."
            })

        total_amount = Decimal("0.00")
        order_items = []

        # Validate stock and calculate the order total.
        for cart_item in cart_items:
            product = locked_products[cart_item.product_id]

            if not product.is_available:
                raise serializers.ValidationError({
                    "cart": f"{product.name} is currently unavailable."
                })

            if cart_item.quantity < 1:
                raise serializers.ValidationError({
                    "cart": f"Invalid quantity for {product.name}."
                })

            if product.stock < cart_item.quantity:
                raise serializers.ValidationError({
                    "cart": (
                        f"Insufficient stock for {product.name}. "
                        f"Available quantity: {product.stock}."
                    )
                })

            line_total = product.price * cart_item.quantity
            total_amount += line_total

            order_items.append({
                "product": product,
                "product_name": product.name,
                "unit_price": product.price,
                "quantity": cart_item.quantity,
            })

        # Save explicit seller ownership on the order.
        order = Order.objects.create(
            buyer=buyer,
            seller_id=seller_id,
            total_amount=total_amount,
            **validated_data,
        )

        # Create order items and reserve product stock.
        for item_data in order_items:
            product = item_data["product"]
            quantity = item_data["quantity"]

            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=item_data["product_name"],
                unit_price=item_data["unit_price"],
                quantity=quantity,
            )

            product.stock -= quantity
            product.save(update_fields=["stock", "updated_at"])

        # Clear the cart only after successful order creation.
        cart.items.all().delete()

        return order


# ==================================================
# SELLER ORDER SERIALIZERS
# ==================================================

class SellerOrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_name",
            "unit_price",
            "quantity",
            "line_total",
        ]
        read_only_fields = fields


class SellerOrderListSerializer(serializers.ModelSerializer):
    buyer_username = serializers.CharField(
        source="buyer.username",
        read_only=True
    )

    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "buyer_username",
            "status",
            "total_amount",
            "item_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_item_count(self, obj):
        return obj.items.count()


class SellerOrderDetailSerializer(serializers.ModelSerializer):
    buyer_username = serializers.CharField(
        source="buyer.username",
        read_only=True
    )

    items = SellerOrderItemSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "buyer_username",
            "status",
            "total_amount",
            "fulfilment_location",
            "buyer_note",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SellerOrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=Order.Status.choices
    )

    def validate_status(self, new_status):
        order = self.instance

        allowed_transitions = {
            Order.Status.CONFIRMED: [
                Order.Status.PROCESSING,
            ],
            Order.Status.PROCESSING: [
                Order.Status.COMPLETED,
            ],
        }

        allowed = allowed_transitions.get(order.status, [])

        if new_status not in allowed:
            raise serializers.ValidationError(
                f"Cannot change order status from "
                f"'{order.status}' to '{new_status}'."
            )

        return new_status


class SellerOrderCancellationSerializer(serializers.Serializer):
    """
    Validate whether a seller is allowed to cancel an order.

    Payment records must already have been locked by the view
    inside the active database transaction.
    """

    def validate(self, attrs):
        order = self.instance
        payments = self.context.get("payments", [])

        if order.status != Order.Status.PENDING:
            raise serializers.ValidationError({
                "order": (
                    "Only pending orders can be cancelled through "
                    "this endpoint."
                )
            })

        pending_payments = [
            payment
            for payment in payments
            if payment.status == "pending"
        ]

        if pending_payments:
            raise serializers.ValidationError({
                "payment": (
                    "This order has a payment being processed. "
                    "Wait for the payment result before cancelling."
                )
            })

        successful_payments = [
            payment
            for payment in payments
            if payment.status == "successful"
        ]

        if successful_payments:
            raise serializers.ValidationError({
                "payment": (
                    "This order has already been paid. "
                    "A separate refund process is required."
                )
            })

        return attrs
