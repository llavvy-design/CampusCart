from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
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
    CheckoutSerializer,
    OrderCreateSerializer,
    SellerOrderCancellationSerializer,
    SellerOrderDetailSerializer,
    SellerOrderListSerializer,
    SellerOrderStatusUpdateSerializer,
)


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
