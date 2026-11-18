
import json
import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Payment
from .services.mpesa import normalize_mpesa_phone


logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def mpesa_callback(request):
    """
    Receive and process an M-Pesa STK Push callback.

    The checkout request ID links the callback to the original
    CampusCart payment attempt.
    """

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"ResultCode": 1, "ResultDesc": "Invalid JSON payload"},
            status=400
        )

    callback = payload.get("Body", {}).get("stkCallback", {})

    checkout_id = callback.get("CheckoutRequestID")
    result_code = callback.get("ResultCode")
    result_description = callback.get("ResultDesc", "")

    if not checkout_id or result_code is None:
        return JsonResponse(
            {"ResultCode": 1, "ResultDesc": "Missing callback information"},
            status=400
        )

    with transaction.atomic():
        try:
            payment = (
                Payment.objects
                .select_for_update()
                .select_related("order")
                .get(checkout_request_id=checkout_id)
            )
        except Payment.DoesNotExist:
            logger.warning(
                "Received callback for unknown CheckoutRequestID: %s",
                checkout_id
            )

            # Acknowledge the callback, but do not change any payment.
            return JsonResponse(
                {"ResultCode": 0, "ResultDesc": "Callback received"}
            )

        # Store the callback for auditing and troubleshooting.
        payment.callback_data = payload
        payment.result_code = str(result_code)
        payment.result_description = str(result_description)

        # Ignore duplicate callbacks for an already-finalized payment.
        if payment.status != Payment.Status.PENDING:
            payment.save(update_fields=[
                "callback_data",
                "result_code",
                "result_description",
                "updated_at",
            ])

            return JsonResponse(
                {"ResultCode": 0, "ResultDesc": "Callback already processed"}
            )

        if str(result_code) != "0":
            payment.status = Payment.Status.FAILED

            payment.save(update_fields=[
                "status",
                "callback_data",
                "result_code",
                "result_description",
                "updated_at",
            ])

            return JsonResponse(
                {"ResultCode": 0, "ResultDesc": "Payment failure recorded"}
            )

        # Successful callbacks contain payment metadata.
        items = callback.get("CallbackMetadata", {}).get("Item", [])

        metadata = {
            item.get("Name"): item.get("Value")
            for item in items
            if item.get("Name")
        }

        receipt = metadata.get("MpesaReceiptNumber")
        callback_amount = metadata.get("Amount")
        callback_phone = metadata.get("PhoneNumber")

        if not receipt or callback_amount is None or not callback_phone:
            payment.result_description = (
                "Successful callback received without required payment metadata."
            )
            payment.save(update_fields=[
                "callback_data",
                "result_code",
                "result_description",
                "updated_at",
            ])

            logger.error(
                "Incomplete successful callback for payment %s",
                payment.pk
            )

            return JsonResponse(
                {"ResultCode": 0, "ResultDesc": "Callback received"}
            )

        try:
            received_amount = Decimal(str(callback_amount))
            received_phone = normalize_mpesa_phone(callback_phone)
        except (InvalidOperation, ValueError):
            payment.result_description = (
                "Callback payment details could not be validated."
            )
            payment.save(update_fields=[
                "callback_data",
                "result_code",
                "result_description",
                "updated_at",
            ])

            return JsonResponse(
                {"ResultCode": 0, "ResultDesc": "Callback received"}
            )

        # Never mark the payment successful if the amount or phone differs.
        if (
            received_amount != payment.amount
            or received_phone != payment.phone_number
        ):
            payment.result_description = (
                "Callback details do not match the original payment. "
                "Manual verification required."
            )
            payment.save(update_fields=[
                "callback_data",
                "result_code",
                "result_description",
                "updated_at",
            ])

            logger.error(
                "Payment callback mismatch for payment %s",
                payment.pk
            )

            return JsonResponse(
                {"ResultCode": 0, "ResultDesc": "Callback received"}
            )

        payment.status = Payment.Status.SUCCESSFUL
        payment.mpesa_receipt_number = str(receipt)

        payment.save(update_fields=[
            "status",
            "mpesa_receipt_number",
            "callback_data",
            "result_code",
            "result_description",
            "updated_at",
        ])

        # Confirm the order only when it is still pending.
        if payment.order.status == payment.order.Status.PENDING:
            payment.order.status = payment.order.Status.CONFIRMED
            payment.order.save(update_fields=["status", "updated_at"])

    return JsonResponse(
        {"ResultCode": 0, "ResultDesc": "Payment processed successfully"}
    )
