from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.services.notification_service import create_notification
from payments.models import Payment
from payments.services.mpesa import (
    MpesaAPIError,
    MpesaConfigurationError,
    initiate_stk_push,
)

from .models import Order, Product
from .serializers import (
    BuyerOrderDetailSerializer,
    BuyerOrderListSerializer,
    CheckoutSerializer,
    OrderCreateSerializer,
    ProductSerializer,
    PublicProductSerializer,
    SellerOrderCancellationSerializer,
    SellerOrderDetailSerializer,
    SellerOrderListSerializer,
    SellerOrderStatusUpdateSerializer,
)


# ==================================================
# PRODUCT MANAGEMENT
# ==================================================

class ProductListCreateView(APIView):
    """
    Public product browsing and authenticated product creation.

    Public users can browse available products.
    Authenticated users can create products.
    """

    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        products = (
            Product.objects
            .filter(
                is_available=True,
                stock__gt=0,
            )
            .select_related("seller", "category")
        )

        # Search by product name or description.
        search = request.query_params.get("search", "").strip()

        if search:
            products = products.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
            )

        # Filter by category ID.
        category = request.query_params.get("category")

        if category:
            try:
                category_id = int(category)
                if category_id < 1:
                    raise ValueError
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Category must be a valid positive ID."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            products = products.filter(
                category_id=category_id,
                category__is_active=True,
            )

        # Filter by product condition.
        condition = request.query_params.get("condition")

        if condition:
            valid_conditions = Product.Condition.values

            if condition not in valid_conditions:
                return Response(
                    {
                        "detail": (
                            "Invalid condition. Choose one of: "
                            + ", ".join(valid_conditions)
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            products = products.filter(condition=condition)

        # Filter by location.
        location = request.query_params.get("location", "").strip()

        if location:
            products = products.filter(
                location__icontains=location,
            )

        # Filter by minimum price.
        min_price = request.query_params.get("min_price")

        if min_price:
            try:
                min_price_value = Decimal(min_price)

                if not min_price_value.is_finite() or min_price_value < 0:
                    raise InvalidOperation

            except (InvalidOperation, TypeError, ValueError):
                return Response(
                    {"detail": "Minimum price must be a valid non-negative number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            products = products.filter(
                price__gte=min_price_value,
            )

        # Filter by maximum price.
        max_price = request.query_params.get("max_price")

        if max_price:
            try:
                max_price_value = Decimal(max_price)

                if not max_price_value.is_finite() or max_price_value < 0:
                    raise InvalidOperation

            except (InvalidOperation, TypeError, ValueError):
                return Response(
                    {"detail": "Maximum price must be a valid non-negative number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            products = products.filter(
                price__lte=max_price_value,
            )

        if (
            min_price
            and max_price
            and min_price_value > max_price_value
        ):
            return Response(
                {"detail": "Minimum price cannot exceed maximum price."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Support a small, explicit set of sorting options.
        ordering = request.query_params.get("ordering", "-created_at")

        allowed_ordering = {
            "created_at",
            "-created_at",
            "price",
            "-price",
            "name",
            "-name",
        }

        if ordering not in allowed_ordering:
            return Response(
                {
                    "detail": (
                        "Invalid ordering. Allowed values: "
                        + ", ".join(sorted(allowed_ordering))
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        products = products.order_by(ordering, "pk")

        serializer = PublicProductSerializer(
            products,
            many=True,
            context={"request": request},
        )

        return Response(
            {
                "count": products.count(),
                "products": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        serializer = ProductSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        # Ownership comes from the authenticated user,
        # never from submitted request data.
        product = serializer.save(seller=request.user)

        response_serializer = ProductSerializer(
            product,
            context={"request": request},
        )

        return Response(
            {
                "message": "Product created successfully.",
                "product": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class MyProductListView(APIView):
    """
    Return all products belonging to the authenticated seller,
    including unavailable listings.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        products = (
            Product.objects
            .filter(seller=request.user)
            .select_related("seller", "category")
            .order_by("-created_at", "-pk")
        )

        serializer = ProductSerializer(
            products,
            many=True,
            context={"request": request},
        )

        return Response(
            {
                "count": products.count(),
                "products": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ProductDetailView(APIView):
    """
    Public product details and seller-owned product management.

    GET: Publicly view available products.
    PATCH: Only the product owner can update the listing.
    DELETE: Only the product owner can deactivate the listing.
    """

    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, product_id):
        product = get_object_or_404(
            Product.objects
            .filter(
                is_available=True,
                stock__gt=0,
            )
            .select_related("seller", "category"),
            pk=product_id,
        )

        serializer = PublicProductSerializer(
            product,
            context={"request": request},
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request, product_id):
        with transaction.atomic():
            product = get_object_or_404(
                Product.objects
                .select_for_update()
                .filter(seller=request.user),
                pk=product_id,
            )

            serializer = ProductSerializer(
                instance=product,
                data=request.data,
                partial=True,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)

            product = serializer.save()

            # Do not publish a listing with no available stock.
            if product.is_available and product.stock < 1:
                return Response(
                    {
                        "detail": (
                            "A product must have at least one unit "
                            "of stock to be available."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            response_serializer = ProductSerializer(
                product,
                context={"request": request},
            )

        return Response(
            {
                "message": "Product updated successfully.",
                "product": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, product_id):
        with transaction.atomic():
            product = get_object_or_404(
                Product.objects
                .select_for_update()
                .filter(seller=request.user),
                pk=product_id,
            )

            # Deactivate instead of physically deleting.
            # Existing order items may still reference this product.
            product.is_available = False
            product.save(
                update_fields=["is_available", "updated_at"]
            )

        return Response(
            {
                "message": (
                    "Product listing deactivated successfully."
                ),
                "product_id": product.pk,
                "is_available": False,
            },
            status=status.HTTP_200_OK,
        )


# ==================================================
# ORDER CREATION AND CHECKOUT
# ==================================================

class OrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OrderCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        order = serializer.save()

        response_serializer = OrderCreateSerializer(order)

        return Response(
            {
                "message": "Your order has been placed successfully.",
                "order": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class OrderCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data["phone_number"]

        # Lock and validate the order before creating a payment.
        with transaction.atomic():
            order = get_object_or_404(
                Order.objects.select_for_update(),
                pk=order_id,
                buyer=request.user,
            )

            if order.status != Order.Status.PENDING:
                return Response(
                    {"detail": "This order is not available for payment."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if order.total_amount < 1 or (
                order.total_amount != order.total_amount.to_integral_value()
            ):
                return Response(
                    {
                        "detail": (
                            "The order total must be at least KSh 1 "
                            "and a whole number to use M-Pesa."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            existing_payment = Payment.objects.filter(
                order=order,
                status=Payment.Status.PENDING,
            ).first()

            if existing_payment:
                return Response(
                    {
                        "detail": (
                            "A payment attempt is already pending for this order."
                        ),
                        "payment_id": existing_payment.pk,
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            payment = Payment.objects.create(
                order=order,
                phone_number=phone_number,
                amount=order.total_amount,
                status=Payment.Status.PENDING,
            )

        # Make the external Daraja request outside the database transaction.
        try:
            daraja_response = initiate_stk_push(payment)

        except (MpesaAPIError, MpesaConfigurationError, ValueError) as error:
            payment.status = Payment.Status.FAILED
            payment.result_description = str(error)
            payment.save(
                update_fields=[
                    "status",
                    "result_description",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "detail": "Unable to initiate M-Pesa payment.",
                    "reason": str(error),
                    "payment_id": payment.pk,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "message": "STK Push request accepted. Check your phone.",
                "payment_id": payment.pk,
                "order_number": str(order.order_number),
                "amount": str(payment.amount),
                "status": payment.status,
                "checkout_request_id": payment.checkout_request_id,
                "customer_message": daraja_response.get(
                    "CustomerMessage",
                    "Enter your M-Pesa PIN to complete payment.",
                ),
            },
            status=status.HTTP_202_ACCEPTED,
        )


# ==================================================
# BUYER ORDER MANAGEMENT
# ==================================================

class BuyerOrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = (
            Order.objects
            .filter(buyer=request.user)
            .select_related("seller")
            .prefetch_related("items", "payments")
            .order_by("-created_at", "-pk")
        )

        serializer = BuyerOrderListSerializer(
            orders,
            many=True,
        )

        return Response(
            {
                "count": orders.count(),
                "orders": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class BuyerOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects
            .filter(buyer=request.user)
            .select_related("seller")
            .prefetch_related("items", "payments"),
            pk=order_id,
        )

        serializer = BuyerOrderDetailSerializer(order)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class BuyerOrderCancellationView(APIView):
    """
    Allow a buyer to cancel an eligible unpaid order.

    The order, its payments and its products are locked before
    stock is restored. The locking order is consistent with the
    M-Pesa callback and seller cancellation workflows.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        with transaction.atomic():
            # Only the buyer who owns this order can cancel it.
            order = get_object_or_404(
                Order.objects.select_for_update(),
                pk=order_id,
                buyer=request.user,
            )

            # Lock all payment attempts for this order.
            payments = list(
                Payment.objects
                .select_for_update()
                .filter(order=order)
                .order_by("pk")
            )

            if order.status != Order.Status.PENDING:
                return Response(
                    {
                        "detail": (
                            "You can only cancel orders that are still pending."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if any(
                payment.status == Payment.Status.PENDING
                for payment in payments
            ):
                return Response(
                    {
                        "detail": (
                            "A payment is still being processed. "
                            "Please wait for its result before cancelling."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            if any(
                payment.status == Payment.Status.SUCCESSFUL
                for payment in payments
            ):
                return Response(
                    {
                        "detail": (
                            "This order has a successful payment. "
                            "A refund process is required before cancellation."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            # Retrieve order items before restoring stock.
            order_items = list(
                order.items.all().order_by("product_id")
            )

            product_ids = [
                item.product_id
                for item in order_items
            ]

            # Lock products in a consistent order.
            locked_products = {
                product.pk: product
                for product in Product.objects
                .select_for_update()
                .filter(pk__in=product_ids)
                .order_by("pk")
            }

            if len(locked_products) != len(set(product_ids)):
                return Response(
                    {
                        "detail": (
                            "One or more products could not be found. "
                            "Stock restoration was not completed."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            # Restore the reserved stock.
            for item in order_items:
                product = locked_products[item.product_id]
                product.stock += item.quantity
                product.save(
                    update_fields=["stock", "updated_at"]
                )

            # Mark the order cancelled in the same transaction.
            order.status = Order.Status.CANCELLED
            order.save(update_fields=["status", "updated_at"])

            # Notify the seller, if this order has an assigned seller.
            if order.seller is not None:
                create_notification(
                    recipient=order.seller,
                    actor=request.user,
                    notification_type="order_status_updated",
                    message=(
                        "The buyer cancelled their order. "
                        "The reserved product stock has been released."
                    ),
                )

            response_serializer = BuyerOrderDetailSerializer(order)

        return Response(
            {
                "message": (
                    "Order cancelled successfully. "
                    "Product stock has been restored."
                ),
                "order": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# ==================================================
# SELLER ORDER MANAGEMENT
# ==================================================

class SellerOrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = (
            Order.objects
            .filter(seller=request.user)
            .select_related("buyer")
            .prefetch_related("items")
            .order_by("-created_at")
        )

        serializer = SellerOrderListSerializer(
            orders,
            many=True,
        )

        return Response(
            {
                "count": orders.count(),
                "orders": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class SellerOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects
            .filter(seller=request.user)
            .select_related("buyer")
            .prefetch_related("items"),
            pk=order_id,
        )

        serializer = SellerOrderDetailSerializer(order)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class SellerOrderStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, order_id):
        with transaction.atomic():
            # Only the seller assigned to this order can update it.
            order = get_object_or_404(
                Order.objects.select_for_update(),
                pk=order_id,
                seller=request.user,
            )

            serializer = SellerOrderStatusUpdateSerializer(
                instance=order,
                data=request.data,
            )
            serializer.is_valid(raise_exception=True)

            new_status = serializer.validated_data["status"]

            order.status = new_status
            order.save(update_fields=["status", "updated_at"])

            status_messages = {
                Order.Status.PROCESSING: (
                    "Your order is now being processed by the seller."
                ),
                Order.Status.COMPLETED: (
                    "Your order has been marked as completed."
                ),
            }

            create_notification(
                recipient=order.buyer,
                actor=request.user,
                notification_type="order_status_updated",
                message=status_messages[new_status],
            )

            response_serializer = SellerOrderDetailSerializer(order)

        return Response(
            {
                "message": "Order status updated successfully.",
                "order": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class SellerOrderCancellationView(APIView):
    """
    Allow a seller to cancel an eligible unpaid order.

    The order and its payments are locked before stock is restored.
    This follows the same order-then-payment locking sequence as
    the M-Pesa callback.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        with transaction.atomic():
            # Only the seller assigned to this order can cancel it.
            order = get_object_or_404(
                Order.objects.select_for_update(),
                pk=order_id,
                seller=request.user,
            )

            # Lock all payment attempts for this order.
            payments = list(
                Payment.objects
                .select_for_update()
                .filter(order=order)
                .order_by("pk")
            )

            serializer = SellerOrderCancellationSerializer(
                instance=order,
                data=request.data,
                context={"payments": payments},
            )
            serializer.is_valid(raise_exception=True)

            # Retrieve order items before restoring stock.
            order_items = list(
                order.items.all().order_by("product_id")
            )

            product_ids = [
                item.product_id
                for item in order_items
            ]

            # Lock products in a consistent order.
            locked_products = {
                product.pk: product
                for product in Product.objects
                .select_for_update()
                .filter(pk__in=product_ids)
                .order_by("pk")
            }

            if len(locked_products) != len(set(product_ids)):
                return Response(
                    {
                        "detail": (
                            "One or more products could not be found. "
                            "Stock restoration was not completed."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            # Restore the reserved stock.
            for item in order_items:
                product = locked_products[item.product_id]
                product.stock += item.quantity
                product.save(
                    update_fields=["stock", "updated_at"]
                )

            # Mark the order cancelled in the same transaction.
            order.status = Order.Status.CANCELLED
            order.save(update_fields=["status", "updated_at"])

            # Notify the buyer.
            create_notification(
                recipient=order.buyer,
                actor=request.user,
                notification_type="order_status_updated",
                message=(
                    "The seller cancelled your order. "
                    "The reserved product stock has been released."
                ),
            )

            response_serializer = SellerOrderDetailSerializer(order)

        return Response(
            {
                "message": (
                    "Order cancelled successfully. "
                    "Product stock has been restored."
                ),
                "order": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )
