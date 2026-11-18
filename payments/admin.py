from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "order",
        "phone_number",
        "amount",
        "status",
        "mpesa_receipt_number",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "phone_number",
        "mpesa_receipt_number",
        "checkout_request_id",
        "order__order_number",
    )

    readonly_fields = (
        "merchant_request_id",
        "checkout_request_id",
        "mpesa_receipt_number",
        "result_code",
        "result_description",
        "callback_data",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)