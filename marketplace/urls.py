from django.urls import path

from .views import (
    BuyerOrderCancellationView,
    BuyerOrderDetailView,
    BuyerOrderListView,
    MyProductListView,
    OrderCheckoutView,
    OrderCreateView,
    ProductDetailView,
    ProductListCreateView,
    SellerOrderCancellationView,
    SellerOrderDetailView,
    SellerOrderListView,
    SellerOrderStatusUpdateView,
)


app_name = "marketplace"

urlpatterns = [
    # Public product browsing and seller product management.
    path(
        "products/",
        ProductListCreateView.as_view(),
        name="product_list_create",
    ),
    path(
        "products/<int:product_id>/",
        ProductDetailView.as_view(),
        name="product_detail",
    ),
    path(
        "my-products/",
        MyProductListView.as_view(),
        name="my_product_list",
    ),

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

    # Buyer order management.
    path(
        "my-orders/",
        BuyerOrderListView.as_view(),
        name="buyer_order_list",
    ),
    path(
        "my-orders/<int:order_id>/",
        BuyerOrderDetailView.as_view(),
        name="buyer_order_detail",
    ),
    path(
        "my-orders/<int:order_id>/cancel/",
        BuyerOrderCancellationView.as_view(),
        name="buyer_order_cancel",
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
