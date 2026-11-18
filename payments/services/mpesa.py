import os

import requests
import base64
import re

from decimal import Decimal
from urllib.parse import urlparse
from django.utils import timezone
from django.core.cache import cache
from requests.auth import HTTPBasicAuth


class MpesaConfigurationError(Exception):
    """Raised when M-Pesa configuration is missing or invalid."""


class MpesaAPIError(Exception):
    """Raised when communication with the Daraja API fails."""


def get_base_url():
    """Return the Daraja API base URL for the configured environment."""

    environment = os.getenv("MPESA_ENVIRONMENT", "sandbox").lower()

    urls = {
        "sandbox": "https://sandbox.safaricom.co.ke",
        "production": "https://api.safaricom.co.ke",
    }

    if environment not in urls:
        raise MpesaConfigurationError(
            "MPESA_ENVIRONMENT must be sandbox or production."
        )

    return urls[environment]


def get_access_token():
    """
    Obtain an OAuth access token from Safaricom Daraja.

    Reuse a cached token until shortly before it expires.
    """

    consumer_key = os.getenv("MPESA_CONSUMER_KEY")
    consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")
    environment = os.getenv("MPESA_ENVIRONMENT", "sandbox").lower()

    if not consumer_key or not consumer_secret:
        raise MpesaConfigurationError(
            "M-Pesa Consumer Key or Consumer Secret is missing from .env."
        )

    # Reuse an existing token when available.
    cache_key = f"mpesa_access_token_{environment}"
    cached_token = cache.get(cache_key)

    if cached_token:
        return cached_token

    token_url = f"{get_base_url()}/oauth/v1/generate"

    try:
        response = requests.get(
            token_url,
            params={"grant_type": "client_credentials"},
            auth=HTTPBasicAuth(consumer_key, consumer_secret),
            timeout=(5, 20),
        )
        response.raise_for_status()

    except requests.exceptions.RequestException as error:
        raise MpesaAPIError(
            "Could not connect to the Safaricom Daraja authentication API."
        ) from error

    try:
        data = response.json()
    except ValueError as error:
        raise MpesaAPIError(
            "Daraja returned an invalid authentication response."
        ) from error

    access_token = data.get("access_token")

    if not access_token:
        raise MpesaAPIError(
            "Daraja did not return an access token. "
            "Check your sandbox application credentials."
        )

    try:
        expires_in = int(data.get("expires_in", 3600))
    except (TypeError, ValueError):
        expires_in = 3600

    # Refresh the token 60 seconds before its expected expiry.
    cache.set(
        cache_key,
        access_token,
        timeout=max(1, expires_in - 60),
    )

    return access_token

def generate_stk_password():
    """
    Generate the timestamp and Base64 password
    required for an M-Pesa STK Push request.
    """

    shortcode = os.getenv("MPESA_SHORTCODE")
    passkey = os.getenv("MPESA_PASSKEY")

    if not shortcode or not passkey:
        raise MpesaConfigurationError(
            "M-Pesa Shortcode or Passkey is missing from .env."
        )

    # Generate timestamp using Nairobi local time.
    timestamp = timezone.localtime().strftime("%Y%m%d%H%M%S")

    # Combine shortcode, passkey and timestamp.
    password_string = f"{shortcode}{passkey}{timestamp}"

    # Encode the combined value using Base64.
    password = base64.b64encode(
        password_string.encode("utf-8")
    ).decode("utf-8")

    return timestamp, password

def normalize_mpesa_phone(phone_number):
    """
    Convert Kenyan phone numbers into 254XXXXXXXXX format.
    """

    phone = re.sub(r"[\s\-]", "", str(phone_number))

    if re.fullmatch(r"0[17]\d{8}", phone):
        return "254" + phone[1:]

    if re.fullmatch(r"\+?254[17]\d{8}", phone):
        return phone.lstrip("+")

    raise ValueError(
        "Enter a valid Kenyan M-Pesa number, "
        "for example 0712345678 or 254712345678."
    )


def initiate_stk_push(payment):
    """
    Initiate an M-Pesa STK Push for an existing CampusCart payment.

    The payment remains pending until the Safaricom callback
    confirms the actual transaction result.
    """

    shortcode = os.getenv("MPESA_SHORTCODE")
    callback_url = os.getenv("MPESA_CALLBACK_URL", "").strip()

    if not shortcode:
        raise MpesaConfigurationError(
            "MPESA_SHORTCODE is missing from .env."
        )

    # A publicly accessible HTTPS callback is required.
    parsed_url = urlparse(callback_url)

    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise MpesaConfigurationError(
            "A valid HTTPS MPESA_CALLBACK_URL is required."
        )

    # Normalize the customer's phone number.
    phone = normalize_mpesa_phone(payment.phone_number)

    # Daraja STK Push accepts whole-number shilling amounts.
    amount = Decimal(str(payment.amount))

    if amount <= 0 or amount != amount.to_integral_value():
        raise ValueError(
            "M-Pesa STK Push requires a positive whole-number amount."
        )

    timestamp, password = generate_stk_password()
    access_token = get_access_token()

    url = f"{get_base_url()}/mpesa/stkpush/v1/processrequest"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": "CAMPUSCART",
        "TransactionDesc": "Cart payment",
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=(5, 30),
        )
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.RequestException as error:
        raise MpesaAPIError(
            "Could not submit the STK Push request to Safaricom."
        ) from error

    except ValueError as error:
        raise MpesaAPIError(
            "Safaricom returned an invalid STK Push response."
        ) from error

    if str(data.get("ResponseCode")) != "0":
        raise MpesaAPIError(
            data.get("ResponseDescription", "STK Push request was rejected.")
        )

    checkout_id = data.get("CheckoutRequestID")

    if not checkout_id:
        raise MpesaAPIError(
            "Safaricom accepted the request but returned no checkout ID."
        )

    # Save the references returned by Safaricom.
    payment.phone_number = phone
    payment.merchant_request_id = data.get("MerchantRequestID", "")
    payment.checkout_request_id = checkout_id
    payment.result_description = data.get(
        "ResponseDescription",
        "STK Push request accepted for processing."
    )

    # Keep payment status pending until the callback confirms payment.
    payment.save(update_fields=[
        "phone_number",
        "merchant_request_id",
        "checkout_request_id",
        "result_description",
        "updated_at",
    ])

    return data

