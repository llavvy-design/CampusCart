
import io
import shutil
import tempfile

from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from PIL import Image

from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import Category, Product


User = get_user_model()


class ProductImageUploadTests(APITestCase):
    def setUp(self):
        self.temporary_media = tempfile.mkdtemp()

        self.media_override = override_settings(
            MEDIA_ROOT=self.temporary_media,
        )
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(
            lambda: shutil.rmtree(
                self.temporary_media,
                ignore_errors=True,
            )
        )

        self.client = APIClient()

        self.seller = User.objects.create_user(
            username="image_seller",
            email="image_seller@example.com",
            password="TestPassword123!",
        )

        self.category = Category.objects.create(
            name="Image Test Electronics",
            description="Category for image upload tests",
            is_active=True,
        )

        self.product_list_url = reverse(
            "marketplace:product_list_create",
        )

    def create_test_image(self):
        image = Image.new(
            "RGB",
            (100, 100),
            color="blue",
        )

        image_buffer = io.BytesIO()
        image.save(image_buffer, format="PNG")
        image_buffer.seek(0)

        return SimpleUploadedFile(
            name="test-product.png",
            content=image_buffer.read(),
            content_type="image/png",
        )

    def create_product_data(self):
        return {
            "category": self.category.id,
            "name": "Test Image Product",
            "description": "A product used to test image uploads",
            "price": "1500.00",
            "condition": "good",
            "stock": 2,
            "location": "Nairobi",
            "is_available": True,
        }

    def test_authenticated_seller_can_upload_product_image(self):
        self.client.force_authenticate(user=self.seller)

        data = self.create_product_data()
        data["image"] = self.create_test_image()

        response = self.client.post(
            self.product_list_url,
            data,
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        product = Product.objects.get(
            name="Test Image Product",
        )

        self.assertTrue(product.image)
        self.assertTrue(
            Path(product.image.path).exists(),
        )

    def test_product_image_upload_returns_absolute_image_url(self):
        self.client.force_authenticate(user=self.seller)

        data = self.create_product_data()
        data["image"] = self.create_test_image()

        response = self.client.post(
            self.product_list_url,
            data,
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        image_url = response.data["product"]["image"]

        self.assertTrue(image_url)
        self.assertTrue(image_url.startswith("http://"))
        self.assertIn("/media/products/", image_url)

    def test_product_creation_rejects_non_image_file(self):
        self.client.force_authenticate(user=self.seller)

        invalid_file = SimpleUploadedFile(
            name="not-an-image.txt",
            content=b"This is not an image.",
            content_type="text/plain",
        )

        data = self.create_product_data()
        data["image"] = invalid_file

        response = self.client.post(
            self.product_list_url,
            data,
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("image", response.data)

        self.assertFalse(
            Product.objects.filter(
                name="Test Image Product",
            ).exists(),
        )

    def test_product_creation_rejects_image_larger_than_5_mb(self):
        self.client.force_authenticate(user=self.seller)

        oversized_image = SimpleUploadedFile(
            name="oversized-image.png",
            content=b"x" * (5 * 1024 * 1024 + 1),
            content_type="image/png",
        )

        data = self.create_product_data()
        data["image"] = oversized_image

        response = self.client.post(
            self.product_list_url,
            data,
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("image", response.data)

        self.assertFalse(
            Product.objects.filter(
                name="Test Image Product",
            ).exists(),
        )
