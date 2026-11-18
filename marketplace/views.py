
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import Payment
from payments.services.mpesa import (
    MpesaAPIError,
    MpesaConfigurationError,
    initiate_stk_push,
)

from .models import Order
from .serializers import CheckoutSerializer


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
