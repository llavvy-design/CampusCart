from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import Category, Product


User = get_user_model()


class ProductManagementAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.seller = User.objects.create_user(
            username="seller_one",
            email="seller@example.com",
            password="TestPassword123!",
        )

        self.other_seller = User.objects.create_user(
            username="seller_two",
            email="seller2@example.com",
            password="TestPassword123!",
        )

        self.buyer = User.objects.create_user(
            username="buyer_one",
            email="buyer@example.com",
            password="TestPassword123!",
        )

        self.category = Category.objects.create(
            name="Electronics",
            description="Electronic devices",
            is_active=True,
        )

        self.inactive_category = Category.objects.create(
            name="Inactive Category",
            description="Unavailable category",
            is_active=False,
        )

        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Scientific Calculator",
            description="A reliable scientific calculator",
            price=Decimal("1500.00"),
            condition=Product.Condition.GOOD,
            stock=3,
            location="Mombasa",
            is_available=True,
        )

        self.product_list_url = reverse(
            "marketplace:product_list_create"
        )

        self.my_products_url = reverse(
            "marketplace:my_product_list"
        )

    def create_product(self, **overrides):
        data = {
            "seller": self.seller,
            "category": self.category,
            "name": "Laptop",
            "description": "A student laptop",
            "price": Decimal("35000.00"),
            "condition": Product.Condition.GOOD,
            "stock": 2,
            "location": "Nairobi",
            "is_available": True,
        }
        data.update(overrides)
        return Product.objects.create(**data)

    def product_detail_url(self, product):
        return reverse(
            "marketplace:product_detail",
            kwargs={"product_id": product.id},
        )

    # --------------------------------------------------
    # PRODUCT CREATION
    # --------------------------------------------------

    def test_authenticated_seller_can_create_product(self):
        self.client.force_authenticate(user=self.seller)

        response = self.client.post(
            self.product_list_url,
            {
                "category": self.category.id,
                "name": "New Laptop",
                "description": "A laptop for university students",
                "price": "45000.00",
                "condition": "good",
                "stock": 2,
                "location": "Nairobi",
                "is_available": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        product = Product.objects.get(name="New Laptop")

        self.assertEqual(product.seller, self.seller)
        self.assertEqual(product.category, self.category)
        self.assertEqual(product.price, Decimal("45000.00"))

    def test_seller_cannot_be_spoofed_during_creation(self):
        self.client.force_authenticate(user=self.seller)

        response = self.client.post(
            self.product_list_url,
            {
                "seller": self.other_seller.id,
                "category": self.category.id,
                "name": "Ownership Test Product",
                "description": "Testing seller ownership",
                "price": "2000.00",
                "condition": "good",
                "stock": 1,
                "location": "Nairobi",
                "is_available": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        product = Product.objects.get(name="Ownership Test Product")
        self.assertEqual(product.seller, self.seller)

    def test_anonymous_user_cannot_create_product(self):
        response = self.client.post(
            self.product_list_url,
            {
                "category": self.category.id,
                "name": "Anonymous Product",
                "description": "Should not be created",
                "price": "1000.00",
                "condition": "good",
                "stock": 1,
            },
            format="json",
        )

        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    def test_product_creation_rejects_inactive_category(self):
        self.client.force_authenticate(user=self.seller)

        response = self.client.post(
            self.product_list_url,
            {
                "category": self.inactive_category.id,
                "name": "Invalid Category Product",
                "description": "Testing inactive category",
                "price": "1000.00",
                "condition": "good",
                "stock": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_product_creation_rejects_zero_price(self):
        self.client.force_authenticate(user=self.seller)

        response = self.client.post(
            self.product_list_url,
            {
                "category": self.category.id,
                "name": "Free Product",
                "description": "Testing price validation",
                "price": "0.00",
                "condition": "good",
                "stock": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --------------------------------------------------
    # PUBLIC PRODUCT BROWSING
    # --------------------------------------------------

    def test_public_user_can_browse_available_products(self):
        response = self.client.get(self.product_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("products", response.data)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_unavailable_products_are_excluded_from_public_listing(self):
        unavailable = self.create_product(
            name="Unavailable Product",
            is_available=False,
        )

        response = self.client.get(self.product_list_url)

        returned_ids = [
            item["id"] for item in response.data["products"]
        ]

        self.assertNotIn(unavailable.id, returned_ids)

    def test_out_of_stock_products_are_excluded_from_public_listing(self):
        out_of_stock = self.create_product(
            name="Out of Stock Product",
            stock=0,
        )

        response = self.client.get(self.product_list_url)

        returned_ids = [
            item["id"] for item in response.data["products"]
        ]

        self.assertNotIn(out_of_stock.id, returned_ids)

    def test_public_user_can_view_available_product_detail(self):
        response = self.client.get(
            self.product_detail_url(self.product)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.product.id)
        self.assertEqual(response.data["name"], self.product.name)

    def test_public_user_cannot_view_unavailable_product_detail(self):
        unavailable = self.create_product(
            name="Hidden Product",
            is_available=False,
        )

        response = self.client.get(
            self.product_detail_url(unavailable)
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --------------------------------------------------
    # PRODUCT PAGINATION
    # --------------------------------------------------

    def test_public_products_use_default_page_size(self):
        for number in range(12):
            self.create_product(name=f"Pagination Product {number}")

        response = self.client.get(self.product_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 13)
        self.assertEqual(len(response.data["products"]), 10)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

    def test_public_products_support_custom_page_size(self):
        for number in range(12):
            self.create_product(name=f"Custom Page Product {number}")

        response = self.client.get(
            self.product_list_url,
            {"page_size": 5},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 13)
        self.assertEqual(len(response.data["products"]), 5)

    def test_public_product_page_size_is_capped_at_50(self):
        for number in range(54):
            self.create_product(name=f"Maximum Page Product {number}")

        response = self.client.get(
            self.product_list_url,
            {"page_size": 100},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 55)
        self.assertEqual(len(response.data["products"]), 50)

    def test_invalid_product_page_returns_404(self):
        response = self.client.get(
            self.product_list_url,
            {"page": 999},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --------------------------------------------------
    # SEARCH AND FILTERS
    # --------------------------------------------------

    def test_products_can_be_searched_by_name(self):
        response = self.client.get(
            self.product_list_url,
            {"search": "Scientific Calculator"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_products_can_be_searched_by_description(self):
        response = self.client.get(
            self.product_list_url,
            {"search": "reliable scientific"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_products_can_be_filtered_by_category(self):
        response = self.client.get(
            self.product_list_url,
            {"category": self.category.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_products_can_be_filtered_by_condition(self):
        response = self.client.get(
            self.product_list_url,
            {"condition": "good"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_products_can_be_filtered_by_location(self):
        response = self.client.get(
            self.product_list_url,
            {"location": "Mombasa"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_products_can_be_filtered_by_price_range(self):
        response = self.client.get(
            self.product_list_url,
            {
                "min_price": "1000",
                "max_price": "2000",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_invalid_condition_filter_is_rejected(self):
        response = self.client.get(
            self.product_list_url,
            {"condition": "INVALID"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_price_filter_is_rejected(self):
        response = self.client.get(
            self.product_list_url,
            {"min_price": "not-a-price"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_minimum_price_cannot_exceed_maximum_price(self):
        response = self.client.get(
            self.product_list_url,
            {
                "min_price": "5000",
                "max_price": "1000",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --------------------------------------------------
    # SELLER'S OWN PRODUCTS
    # --------------------------------------------------

    def test_seller_can_view_own_products(self):
        self.client.force_authenticate(user=self.seller)

        response = self.client.get(self.my_products_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_seller_cannot_view_another_sellers_products(self):
        self.client.force_authenticate(user=self.other_seller)

        response = self.client.get(self.my_products_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_my_products_includes_unavailable_listings(self):
        self.client.force_authenticate(user=self.seller)

        self.create_product(
            name="My Unavailable Product",
            is_available=False,
        )

        response = self.client.get(self.my_products_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_anonymous_user_cannot_view_my_products(self):
        response = self.client.get(self.my_products_url)

        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    def test_seller_products_are_paginated(self):
        self.client.force_authenticate(user=self.seller)

        for number in range(12):
            self.create_product(name=f"Seller Pagination Product {number}")

        response = self.client.get(
            self.my_products_url,
            {"page_size": 5, "page": 2},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 13)
        self.assertEqual(len(response.data["products"]), 5)
        self.assertIsNotNone(response.data["previous"])

    # --------------------------------------------------
    # PRODUCT UPDATES
    # --------------------------------------------------

    def test_seller_can_update_own_product(self):
        self.client.force_authenticate(user=self.seller)

        response = self.client.patch(
            self.product_detail_url(self.product),
            {
                "name": "Updated Calculator",
                "price": "1800.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.product.refresh_from_db()

        self.assertEqual(self.product.name, "Updated Calculator")
        self.assertEqual(self.product.price, Decimal("1800.00"))

    def test_seller_cannot_update_another_sellers_product(self):
        self.client.force_authenticate(user=self.other_seller)

        response = self.client.patch(
            self.product_detail_url(self.product),
            {"name": "Unauthorized Update"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_user_cannot_update_product(self):
        response = self.client.patch(
            self.product_detail_url(self.product),
            {"name": "Anonymous Update"},
            format="json",
        )

        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    # --------------------------------------------------
    # PRODUCT DEACTIVATION
    # --------------------------------------------------

    def test_seller_can_deactivate_own_product(self):
        self.client.force_authenticate(user=self.seller)

        response = self.client.delete(
            self.product_detail_url(self.product)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.product.refresh_from_db()

        self.assertFalse(self.product.is_available)
        self.assertTrue(
            Product.objects.filter(id=self.product.id).exists()
        )

    def test_seller_cannot_deactivate_another_sellers_product(self):
        self.client.force_authenticate(user=self.other_seller)

        response = self.client.delete(
            self.product_detail_url(self.product)
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.product.refresh_from_db()
        self.assertTrue(self.product.is_available)

    def test_anonymous_user_cannot_deactivate_product(self):
        response = self.client.delete(
            self.product_detail_url(self.product)
        )

        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    # --------------------------------------------------
    # STOCK AND AVAILABILITY VALIDATION
    # --------------------------------------------------

    def test_cannot_create_available_product_with_zero_stock(self):
        self.client.force_authenticate(user=self.seller)

        response = self.client.post(
            self.product_list_url,
            {
                "category": self.category.id,
                "name": "Zero Stock Laptop",
                "description": "This listing must be rejected",
                "price": "25000.00",
                "condition": "good",
                "stock": 0,
                "location": "Nairobi",
                "is_available": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stock", response.data)
        self.assertFalse(
            Product.objects.filter(name="Zero Stock Laptop").exists()
        )

    def test_cannot_set_available_product_stock_to_zero(self):
        self.client.force_authenticate(user=self.seller)

        response = self.client.patch(
            self.product_detail_url(self.product),
            {"stock": 0},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stock", response.data)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertTrue(self.product.is_available)

    def test_can_set_stock_to_zero_while_deactivating_product(self):
        self.client.force_authenticate(user=self.seller)

        response = self.client.patch(
            self.product_detail_url(self.product),
            {
                "stock": 0,
                "is_available": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)
        self.assertFalse(self.product.is_available)

    def test_cannot_reactivate_product_with_zero_stock(self):
        self.client.force_authenticate(user=self.seller)

        self.product.stock = 0
        self.product.is_available = False
        self.product.save(update_fields=["stock", "is_available"])

        response = self.client.patch(
            self.product_detail_url(self.product),
            {"is_available": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stock", response.data)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)
        self.assertFalse(self.product.is_available)

    def test_can_update_stock_of_unavailable_product_without_reactivating(self):
        self.client.force_authenticate(user=self.seller)

        self.product.stock = 0
        self.product.is_available = False
        self.product.save(update_fields=["stock", "is_available"])

        response = self.client.patch(
            self.product_detail_url(self.product),
            {"stock": 5},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertFalse(self.product.is_available)

