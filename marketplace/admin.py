
from django.contrib import admin
from .models import (
    Category,
    Product,
    Cart,
    CartItem,
    Order,
    OrderItem,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "seller",
        "category",
        "price",
        "condition",
        "stock",
        "is_available",
    )
    search_fields = ("name", "seller__username")
    list_filter = ("category", "condition", "is_available")
    readonly_fields = ("created_at", "updated_at")


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "updated_at")
    search_fields = ("user__username",)
    inlines = [CartItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "product_name",
        "unit_price",
        "quantity",
    )
    search_fields = ("product_name",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "buyer",
        "total_amount",
        "status",
        "created_at",
    )
    search_fields = ("order_number", "buyer__username")
    list_filter = ("status", "created_at")
    readonly_fields = (
        "order_number",
        "total_amount",
        "created_at",
        "updated_at",
    )
    inlines = [OrderItemInline]
