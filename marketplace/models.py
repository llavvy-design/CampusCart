import uuid

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


# ==================================================
# 1. PRODUCT CATEGORY
# ==================================================

class Category(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


# ==================================================
# 2. PRODUCT
# ==================================================

class Product(models.Model):

    class Condition(models.TextChoices):
        NEW = "new", "New"
        LIKE_NEW = "like_new", "Like New"
        GOOD = "good", "Good"
        FAIR = "fair", "Fair"

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="products"
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products"
    )

    name = models.CharField(
        max_length=200
    )

    description = models.TextField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01"))
        ]
    )

    condition = models.CharField(
        max_length=20,
        choices=Condition.choices,
        default=Condition.GOOD
    )

    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True
    )

    stock = models.PositiveIntegerField(
        default=1
    )

    location = models.CharField(
        max_length=150,
        blank=True
    )

    is_available = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


# ==================================================
# 3. SHOPPING CART
# ==================================================

class Cart(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.user.username}'s Cart"


# ==================================================
# 4. CART ITEM
# ==================================================

class CartItem(models.Model):

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items"
    )

    quantity = models.PositiveIntegerField(
        default=1
    )

    added_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-added_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"],
                name="unique_product_per_cart"
            )
        ]

    @property
    def subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


# ==================================================
# 5. ORDER
# ==================================================

class Order(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    order_number = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders"
    )

    # Explicit seller ownership for reliable order management.
    # Nullable to preserve existing orders whose seller cannot
    # be determined from historical order items.
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sales",
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00"))
        ]
    )

    fulfilment_location = models.CharField(
        max_length=200,
        blank=True
    )

    buyer_note = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.order_number}"


# ==================================================
# 6. ORDER ITEM
# ==================================================

class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items"
    )

    product_name = models.CharField(
        max_length=200
    )

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01"))
        ]
    )

    quantity = models.PositiveIntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"],
                name="unique_product_per_order"
            )
        ]

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.product_name} - {self.quantity}"
