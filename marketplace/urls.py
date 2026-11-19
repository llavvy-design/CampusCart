from django.urls import path

from .views import (
    OrderCheckoutView,
    OrderCreateView,
    SellerOrderCancellationView,
    SellerOrderDetailView,
    SellerOrderListView,
    SellerOrderStatusUpdateView,
)


app_name = "marketplace"

urlpatterns = [
    # Buyer order creation and checkout.
    path(
        "orders/",
        OrderCreateView.as_view(),
        name="order_create",
    ),
    path(
        "orders/<int:order_id>/checkout/",
        OrderCheckoutView.as_view(),
        name="order_checkout",
    ),

    # Seller order management.
    path(
        "seller/orders/",
        SellerOrderListView.as_view(),
        name="seller_order_list",
    ),
    path(
        "seller/orders/<int:order_id>/",
        SellerOrderDetailView.as_view(),
        name="seller_order_detail",
    ),
    path(
        "seller/orders/<int:order_id>/status/",
        SellerOrderStatusUpdateView.as_view(),
        name="seller_order_status_update",
    ),
    path(
        "seller/orders/<int:order_id>/cancel/",
        SellerOrderCancellationView.as_view(),
        name="seller_order_cancel",
    ),
]
