
from rest_framework import serializers

from .models import CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_price = serializers.DecimalField(
        source="product.price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    product_image = serializers.ImageField(
        source="product.image",
        read_only=True,
    )
    product_location = serializers.CharField(
        source="product.location",
        read_only=True,
    )
    seller_username = serializers.CharField(
        source="product.seller.username",
        read_only=True,
    )
    subtotal = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product_id",
            "product_name",
            "product_price",
            "product_image",
            "product_location",
            "seller_username",
            "quantity",
            "subtotal",
            "added_at",
        ]
        read_only_fields = fields
