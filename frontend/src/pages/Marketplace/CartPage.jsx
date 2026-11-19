import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Clock3,
  Minus,
  Plus,
  ShoppingBag,
  Trash2,
  XCircle,
} from "lucide-react";

import {
  api,
  paymentApi,
  getApiErrorMessage,
} from "../../services/api";

const formatPrice = (price) =>
  new Intl.NumberFormat("en-KE", {
    style: "currency",
    currency: "KES",
    maximumFractionDigits: 2,
  }).format(Number(price));

const getImageUrl = (imageUrl) => {
  if (!imageUrl) return "";

  if (imageUrl.startsWith("http")) return imageUrl;

  return `${import.meta.env.VITE_BACKEND_URL}${imageUrl}`;
};

const CartPage = () => {
  const [cart, setCart] = useState({
    items: [],
    item_count: 0,
    total: "0.00",
  });
  const [fulfilmentLocation, setFulfilmentLocation] = useState("");
  const [buyerNote, setBuyerNote] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [order, setOrder] = useState(null);
  const [payment, setPayment] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [updatingItem, setUpdatingItem] = useState(null);
  const [isCheckingOut, setIsCheckingOut] = useState(false);
  const [isCheckingPayment, setIsCheckingPayment] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    let active = true;

    const fetchCart = async () => {
      try {
        const response = await api.get("/marketplace/cart/");

        if (active) {
          setCart(response.data);
        }
      } catch (requestError) {
        if (active) {
          setError(getApiErrorMessage(requestError));
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    };

    fetchCart();

    return () => {
      active = false;
    };
  }, []);

  const refreshCart = async () => {
    const response = await api.get("/marketplace/cart/");
    setCart(response.data);
  };

  const updateQuantity = async (item, quantity) => {
    if (quantity < 1) return;

    setUpdatingItem(item.id);
    setError("");
    setSuccess("");

    try {
      await api.patch(`/marketplace/cart/items/${item.id}/`, {
        quantity,
      });
      await refreshCart();
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setUpdatingItem(null);
    }
  };

  const removeItem = async (itemId) => {
    setUpdatingItem(itemId);
    setError("");
    setSuccess("");

    try {
      await api.delete(`/marketplace/cart/items/${itemId}/`);
      await refreshCart();
      setSuccess("Item removed from your cart.");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setUpdatingItem(null);
    }
  };

  const clearCart = async () => {
    setError("");
    setSuccess("");

    try {
      await api.delete("/marketplace/cart/clear/");
      await refreshCart();
      setSuccess("Your cart has been cleared.");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    }
  };

  const handleCheckout = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (!phoneNumber.trim()) {
      setError("Enter the M-Pesa phone number you want to use.");
      return;
    }

    if (!order && !fulfilmentLocation.trim()) {
      setError("Enter your preferred fulfilment location.");
      return;
    }

    setIsCheckingOut(true);

    try {
      let currentOrder = order;

      if (!currentOrder) {
        const orderResponse = await api.post("/marketplace/orders/", {
          fulfilment_location: fulfilmentLocation.trim(),
          buyer_note: buyerNote.trim(),
        });

        currentOrder = orderResponse.data.order;
        setOrder(currentOrder);
        setCart({
          items: [],
          item_count: 0,
          total: "0.00",
        });
      }

      const paymentResponse = await api.post(
        `/marketplace/orders/${currentOrder.id}/checkout/`,
        {
          phone_number: phoneNumber.trim(),
        },
      );

      setPayment(paymentResponse.data);
      setSuccess(
        paymentResponse.data.customer_message ||
          "M-Pesa payment prompt requested. Check your phone.",
      );
    } catch (requestError) {
      const responseData = requestError.response?.data;

      if (responseData?.payment_id) {
        setPayment({
          payment_id: responseData.payment_id,
          order_number: order?.order_number,
          amount: order?.total_amount,
          status: "failed",
          message: responseData.detail,
        });
      }

      setError(
        responseData?.reason ||
          getApiErrorMessage(requestError),
      );
    } finally {
      setIsCheckingOut(false);
    }
  };

  const checkPaymentStatus = async () => {
    if (!payment?.payment_id) return;

    setIsCheckingPayment(true);
    setError("");

    try {
      const response = await paymentApi.get(
        `/payments/${payment.payment_id}/status/`,
      );

      setPayment((current) => ({
        ...current,
        ...response.data,
      }));

      if (response.data.status === "successful") {
        setSuccess("Payment confirmed! Your order is now confirmed.");
      } else if (response.data.status === "failed") {
        setError("The payment was not completed. You can try again.");
      } else {
        setSuccess(
          response.data.message ||
            "Payment is still pending. Check again shortly.",
        );
      }
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setIsCheckingPayment(false);
    }
  };

  const retryPayment = async () => {
    if (!order) return;

    setError("");
    setSuccess("");
    setIsCheckingOut(true);

    try {
      const response = await api.post(
        `/marketplace/orders/${order.id}/checkout/`,
        {
          phone_number: phoneNumber.trim(),
        },
      );

      setPayment(response.data);
      setSuccess(
        response.data.customer_message ||
          "A new M-Pesa payment prompt has been requested.",
      );
    } catch (requestError) {
      const responseData = requestError.response?.data;

      if (responseData?.payment_id) {
        setPayment({
          payment_id: responseData.payment_id,
          order_number: order.order_number,
          amount: order.total_amount,
          status: "failed",
          message: responseData.detail,
        });
      }

      setError(
        responseData?.reason ||
          getApiErrorMessage(requestError),
      );
    } finally {
      setIsCheckingOut(false);
    }
  };

  return (
    <main className="cart-page">
      <div className="cart-page-heading">
        <Link to="/marketplace" className="cart-back-link">
          <ArrowLeft size={17} />
          Continue shopping
        </Link>
        <span className="marketplace-eyebrow">YOUR CAMPUS FINDS</span>
        <h1>Your <span>shopping cart.</span></h1>
        <p>Everything you've picked out, in one place.</p>
      </div>

      {error && (
        <div className="marketplace-alert marketplace-alert-error">
          {error}
        </div>
      )}

      {success && (
        <div className="marketplace-alert marketplace-alert-success">
          {success}
        </div>
      )}

      {payment && (
        <section className="cart-payment-status">
          {payment.status === "successful" ? (
            <CheckCircle2 size={28} />
          ) : payment.status === "failed" ? (
            <XCircle size={28} />
          ) : (
            <Clock3 size={28} />
          )}

          <div>
            <strong>
              {payment.status === "successful"
                ? "Payment successful"
                : payment.status === "failed"
                  ? "Payment not completed"
                  : "Payment awaiting confirmation"}
            </strong>
            <p>
              Order {payment.order_number || order?.order_number}
              {payment.amount
                ? ` · ${formatPrice(payment.amount)}`
                : ""}
            </p>
            {payment.receipt_number && (
              <p>M-Pesa receipt: {payment.receipt_number}</p>
            )}
          </div>

          {payment.status === "pending" && (
            <button
              type="button"
              onClick={checkPaymentStatus}
              disabled={isCheckingPayment}
            >
              {isCheckingPayment ? "Checking..." : "Check payment"}
            </button>
          )}
        </section>
      )}

      {isLoading ? (
        <div className="marketplace-loading">
          <span className="marketplace-spinner" />
          <p>Loading your cart...</p>
        </div>
      ) : cart.items.length === 0 && order ? (
        <section className="cart-empty cart-order-created">
          <div className="cart-empty-icon">
            <ShoppingBag size={36} />
          </div>
          <h2>Your order has been created.</h2>
          <p>
            Order {order.order_number} · {formatPrice(order.total_amount)}
          </p>

          {payment?.status === "failed" && (
            <button
              type="button"
              className="cart-primary-button"
              onClick={retryPayment}
              disabled={isCheckingOut}
            >
              {isCheckingOut ? "Requesting payment..." : "Retry M-Pesa payment"}
              <ArrowRight size={18} />
            </button>
          )}

          <Link to="/marketplace" className="cart-back-link">
            Return to marketplace
          </Link>
        </section>
      ) : cart.items.length === 0 ? (
        <section className="cart-empty">
          <div className="cart-empty-icon">
            <ShoppingBag size={36} />
          </div>
          <h2>Your cart is taking a little break.</h2>
          <p>Find something useful, fun or completely unexpected on campus.</p>
          <Link to="/marketplace" className="cart-primary-button">
            Explore marketplace <ArrowRight size={18} />
          </Link>
        </section>
      ) : (
        <div className="cart-layout">
          <section className="cart-items-section">
            <div className="cart-items-heading">
              <div>
                <span className="marketplace-eyebrow">YOUR SELECTION</span>
                <h2>{cart.item_count} items in your cart</h2>
              </div>
              <button
                type="button"
                className="cart-clear-button"
                onClick={clearCart}
                disabled={Boolean(updatingItem)}
              >
                <Trash2 size={16} />
                Clear cart
              </button>
            </div>

            <div className="cart-items-list">
              {cart.items.map((item) => (
                <article className="cart-item" key={item.id}>
                  <div className="cart-item-image">
                    {item.product_image ? (
                      <img
                        src={getImageUrl(item.product_image)}
                        alt={item.product_name}
                      />
                    ) : (
                      <ShoppingBag size={28} />
                    )}
                  </div>

                  <div className="cart-item-details">
                    <span className="cart-item-seller">
                      SOLD BY {item.seller_username}
                    </span>
                    <h3>{item.product_name}</h3>
                    <p>{item.product_location || "Campus pickup"}</p>
                    <strong>{formatPrice(item.product_price)}</strong>

                    <div className="cart-item-actions">
                      <div className="cart-quantity-control">
                        <button
                          type="button"
                          onClick={() =>
                            updateQuantity(item, item.quantity - 1)
                          }
                          disabled={
                            item.quantity <= 1 ||
                            updatingItem === item.id
                          }
                          aria-label="Decrease quantity"
                        >
                          <Minus size={15} />
                        </button>
                        <span>{item.quantity}</span>
                        <button
                          type="button"
                          onClick={() =>
                            updateQuantity(item, item.quantity + 1)
                          }
                          disabled={updatingItem === item.id}
                          aria-label="Increase quantity"
                        >
                          <Plus size={15} />
                        </button>
                      </div>

                      <button
                        type="button"
                        className="cart-remove-button"
                        onClick={() => removeItem(item.id)}
                        disabled={updatingItem === item.id}
                      >
                        <Trash2 size={15} />
                        Remove
                      </button>
                    </div>
                  </div>

                  <strong className="cart-item-subtotal">
                    {formatPrice(item.subtotal)}
                  </strong>
                </article>
              ))}
            </div>
          </section>

          <aside className="cart-summary">
            <span className="marketplace-eyebrow">ORDER SUMMARY</span>
            <h2>Almost yours.</h2>

            <div className="cart-summary-line">
              <span>Items ({cart.item_count})</span>
              <strong>{formatPrice(cart.total)}</strong>
            </div>

            <div className="cart-summary-line cart-summary-total">
              <span>Total</span>
              <strong>{formatPrice(cart.total)}</strong>
            </div>

            <p className="cart-summary-note">
              Your order will be sent to the seller once created. Payment
              will be requested through M-Pesa.
            </p>

            <form className="cart-checkout-form" onSubmit={handleCheckout}>
              <label htmlFor="fulfilment-location">
                Preferred pickup / fulfilment location
              </label>
              <input
                id="fulfilment-location"
                value={fulfilmentLocation}
                onChange={(event) =>
                  setFulfilmentLocation(event.target.value)
                }
                placeholder="e.g. Main campus, library entrance"
                required
              />

              <label htmlFor="buyer-note">Note to seller (optional)</label>
              <textarea
                id="buyer-note"
                value={buyerNote}
                onChange={(event) => setBuyerNote(event.target.value)}
                placeholder="Any additional details..."
                rows={3}
              />

              <label htmlFor="mpesa-phone">M-Pesa phone number</label>
              <input
                id="mpesa-phone"
                type="tel"
                value={phoneNumber}
                onChange={(event) => setPhoneNumber(event.target.value)}
                placeholder="e.g. 0712345678"
                autoComplete="tel"
                required
              />

              <button
                type="submit"
                className="cart-primary-button"
                disabled={isCheckingOut}
              >
                {isCheckingOut
                  ? "Processing checkout..."
                  : "Create order & pay"}
                {!isCheckingOut && <ArrowRight size={18} />}
              </button>
            </form>
          </aside>
        </div>
      )}
    </main>
  );
};

export default CartPage;
