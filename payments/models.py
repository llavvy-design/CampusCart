from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Payment(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESSFUL = "successful", "Successful"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    order = models.ForeignKey(
        "marketplace.Order",
        on_delete=models.PROTECT,
        related_name="payments"
    )

    phone_number = models.CharField(max_length=15)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("1.00"))]
    )

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING
    )

    merchant_request_id = models.CharField(
        max_length=100,
        blank=True
    )

    stk_timestamp = models.CharField(
    max_length=14,
    blank=True
    )

    checkout_request_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True
    )

    mpesa_receipt_number = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True
    )

    result_code = models.CharField(
        max_length=20,
        blank=True
    )

    result_description = models.TextField(blank=True)

    callback_data = models.JSONField(
        default=dict,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return (
            f"Payment for order {self.order.order_number} "
            f"({self.get_status_display()})"
        )