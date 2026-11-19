
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .cart_serializers import CartItemSerializer
from .models import Cart, CartItem, Product


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get_cart(self, user):
        cart, _ = Cart.objects.get_or_create(user=user)
        return cart

    def get(self, request):
        cart = self.get_cart(request.user)

        items = cart.items.select_related(
            "product",
            "product__seller",
            "product__category",
        ).all()

        total = sum(
            (item.subtotal for item in items),
            Decimal("0.00"),
        )

        serializer = CartItemSerializer(items, many=True)

        return Response(
            {
                "items": serializer.data,
                "item_count": sum(item.quantity for item in items),
                "total": str(total),
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def post(self, request):
        product_id = request.data.get("product_id")
        quantity = request.data.get("quantity", 1)

        try:
            product_id = int(product_id)
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Product ID and quantity must be valid integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if product_id < 1 or quantity < 1:
            return Response(
                {"detail": "Product ID and quantity must be positive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product = get_object_or_404(
            Product.objects.select_for_update().select_related("seller"),
            pk=product_id,
            is_available=True,
            stock__gt=0,
        )

        if product.seller_id == request.user.id:
            return Response(
                {"detail": "You cannot add your own product to your cart."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart = Cart.objects.select_for_update().get_or_create(
            user=request.user
        )[0]

        existing_items = list(
            cart.items.select_related("product").select_for_update()
        )

        if existing_items:
            existing_sellers = {
                item.product.seller_id for item in existing_items
            }

            if product.seller_id not in existing_sellers:
                return Response(
                    {
                        "detail": (
                            "Your cart can contain products from one seller "
                            "at a time. Complete or clear your current cart "
                            "before adding products from another seller."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        cart_item, created = CartItem.objects.select_for_update().get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity},
        )

        if not created:
            cart_item.quantity += quantity

        if cart_item.quantity > product.stock:
            return Response(
                {
                    "detail": (
                        f"Only {product.stock} units of this product are "
                        "currently available."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart_item.save(update_fields=["quantity"])

        serializer = CartItemSerializer(
            cart_item,
            context={"request": request},
        )

        return Response(
            {
                "message": "Product added to cart.",
                "item": serializer.data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CartItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id):
        quantity = request.data.get("quantity")

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Quantity must be a valid integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quantity < 1:
            return Response(
                {"detail": "Quantity must be at least one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart = get_object_or_404(Cart, user=request.user)

        item = get_object_or_404(
            CartItem.objects.select_related("product"),
            pk=item_id,
            cart=cart,
        )

        if not item.product.is_available:
            return Response(
                {"detail": "This product is no longer available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quantity > item.product.stock:
            return Response(
                {
                    "detail": (
                        f"Only {item.product.stock} units are currently available."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        item.quantity = quantity
        item.save(update_fields=["quantity"])

        return Response(
            {
                "message": "Cart quantity updated.",
                "item": CartItemSerializer(item).data,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, item_id):
        cart = get_object_or_404(Cart, user=request.user)

        item = get_object_or_404(
            CartItem,
            pk=item_id,
            cart=cart,
        )

        item.delete()

        return Response(
            {"message": "Item removed from cart."},
            status=status.HTTP_200_OK,
        )


class CartClearView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        cart.items.all().delete()

        return Response(
            {"message": "Your cart has been cleared."},
            status=status.HTTP_200_OK,
        )
