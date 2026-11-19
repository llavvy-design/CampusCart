import { useEffect, useMemo, useState } from "react";
import {
  ArrowDownUp,
  ArrowRight,
  ImagePlus,
  Search,
  ShoppingCart,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { Link } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";
import { api, getApiErrorMessage } from "../../services/api";

const CONDITIONS = [
  { value: "new", label: "Brand new" },
  { value: "like_new", label: "Like new" },
  { value: "good", label: "Good" },
  { value: "fair", label: "Fair" },
];

const INITIAL_FORM = {
  name: "",
  description: "",
  price: "",
  category: "",
  condition: "good",
  stock: "1",
  location: "",
};

const formatPrice = (price) =>
  new Intl.NumberFormat("en-KE", {
    style: "currency",
    currency: "KES",
    maximumFractionDigits: 0,
  }).format(Number(price));

const getProducts = (data) => data?.products ?? [];

const getImageUrl = (imageUrl) => {
  if (!imageUrl) return "";

  if (imageUrl.startsWith("http")) return imageUrl;

  return `${import.meta.env.VITE_BACKEND_URL}${imageUrl}`;
};

const MarketplacePage = () => {
  const { isAuthenticated } = useAuth();

  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [count, setCount] = useState(0);
  const [nextPage, setNextPage] = useState(null);
  const [previousPage, setPreviousPage] = useState(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [condition, setCondition] = useState("");
  const [location, setLocation] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [ordering, setOrdering] = useState("-created_at");
  const [showFilters, setShowFilters] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [form, setForm] = useState(INITIAL_FORM);
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [addingProduct, setAddingProduct] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [cartMessage, setCartMessage] = useState("");

  const categoryOptions = useMemo(
    () => categories,
    [categories],
  );

  useEffect(() => {
    let active = true;

    const loadCategories = async () => {
      try {
        const response = await api.get("/marketplace/categories/");

        if (active) {
          setCategories(response.data);
        }
      } catch {
        if (active) {
          setCategories([]);
        }
      }
    };

    loadCategories();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    const loadProducts = async () => {
      setIsLoading(true);
      setError("");

      const params = {
        page,
        page_size: 10,
        ordering,
      };

      if (search.trim()) params.search = search.trim();
      if (category) params.category = category;
      if (condition) params.condition = condition;
      if (location.trim()) params.location = location.trim();
      if (minPrice !== "") params.min_price = minPrice;
      if (maxPrice !== "") params.max_price = maxPrice;

      try {
        const response = await api.get("/marketplace/products/", {
          params,
        });

        if (!active) return;

        setProducts(getProducts(response.data));
        setCount(response.data.count ?? 0);
        setNextPage(response.data.next);
        setPreviousPage(response.data.previous);
      } catch (requestError) {
        if (active) {
          setError(getApiErrorMessage(requestError));
          setProducts([]);
          setCount(0);
          setNextPage(null);
          setPreviousPage(null);
        }
      } finally {
        if (active) setIsLoading(false);
      }
    };

    loadProducts();

    return () => {
      active = false;
    };
  }, [
    page,
    search,
    category,
    condition,
    location,
    minPrice,
    maxPrice,
    ordering,
  ]);

  useEffect(() => {
    return () => {
      if (imagePreview) URL.revokeObjectURL(imagePreview);
    };
  }, [imagePreview]);

  const updateForm = (event) => {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  };

  const handleImageChange = (event) => {
    const selectedFile = event.target.files?.[0];

    if (!selectedFile) return;

    if (!selectedFile.type.startsWith("image/")) {
      setError("Please choose a valid image file.");
      return;
    }

    if (selectedFile.size > 5 * 1024 * 1024) {
      setError("The image must be 5 MB or smaller.");
      return;
    }

    if (imagePreview) URL.revokeObjectURL(imagePreview);

    setImage(selectedFile);
    setImagePreview(URL.createObjectURL(selectedFile));
    setError("");
  };

  const resetFilters = () => {
    setSearch("");
    setCategory("");
    setCondition("");
    setLocation("");
    setMinPrice("");
    setMaxPrice("");
    setOrdering("-created_at");
    setPage(1);
  };

  const handleCreateProduct = async (event) => {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (!form.category) {
      setError("Please select a product category.");
      return;
    }

    if (!form.price || Number(form.price) <= 0) {
      setError("Enter a price greater than zero.");
      return;
    }

    if (!Number.isInteger(Number(form.stock)) || Number(form.stock) < 1) {
      setError("Stock must be a whole number of at least one.");
      return;
    }

    const formData = new FormData();

    Object.entries(form).forEach(([key, value]) => {
      formData.append(key, value);
    });

    formData.append("is_available", "true");

    if (image) formData.append("image", image);

    setIsSubmitting(true);

    try {
      await api.post("/marketplace/products/", formData);

      setSuccess("Your product listing has been published.");
      setForm(INITIAL_FORM);
      setImage(null);
      setImagePreview("");
      setShowCreateForm(false);
      resetFilters();

      const response = await api.get("/marketplace/products/", {
        params: { page: 1, page_size: 10, ordering: "-created_at" },
      });

      setProducts(getProducts(response.data));
      setCount(response.data.count ?? 0);
      setNextPage(response.data.next);
      setPreviousPage(response.data.previous);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAddToCart = async (product) => {
    setError("");
    setSuccess("");
    setCartMessage("");
    setAddingProduct(product.id);

    try {
      const response = await api.post("/marketplace/cart/", {
        product_id: product.id,
        quantity: 1,
      });

      setCartMessage(`${product.name} added to your cart.`);
      setSuccess(response.data.message || "Product added to cart.");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setAddingProduct(null);
    }
  };

  return (
    <main className="marketplace-page">
      <section className="marketplace-heading">
        <div>
          <span className="marketplace-eyebrow">THE CAMPUS EXCHANGE</span>
          <h1>Find your next <span>good thing.</span></h1>
          <p>
            Student finds, useful essentials and pre-loved favourites.
            All from your campus community.
          </p>
        </div>

        <div className="marketplace-heading-actions">
          {isAuthenticated && (
            <Link to="/cart" className="marketplace-cart-button">
              <ShoppingCart size={19} />
              My cart
            </Link>
          )}

          {isAuthenticated ? (
            <button
              type="button"
              className="marketplace-sell-button"
              onClick={() => {
                setShowCreateForm((current) => !current);
                setError("");
                setSuccess("");
              }}
            >
              {showCreateForm ? <X size={18} /> : <ImagePlus size={18} />}
              {showCreateForm ? "Close form" : "Sell an item"}
            </button>
          ) : (
            <Link to="/login" className="marketplace-sell-button">
              Sign in to sell <ArrowRight size={18} />
            </Link>
          )}
        </div>
      </section>

      {success && (
        <div className="marketplace-alert marketplace-alert-success">
          {success}
        </div>
      )}

      {cartMessage && (
        <div className="marketplace-cart-feedback">
          <ShoppingCart size={18} />
          <span>{cartMessage}</span>
          <Link to="/cart">View cart <ArrowRight size={15} /></Link>
        </div>
      )}

      {error && (
        <div className="marketplace-alert marketplace-alert-error">
          {error}
        </div>
      )}

      {showCreateForm && isAuthenticated && (
        <section className="marketplace-create-panel">
          <div className="marketplace-panel-heading">
            <div>
              <span className="marketplace-eyebrow">MAKE A LISTING</span>
              <h2>Put it up for grabs.</h2>
            </div>
            <button
              type="button"
              className="marketplace-close-button"
              onClick={() => setShowCreateForm(false)}
              aria-label="Close listing form"
            >
              <X size={21} />
            </button>
          </div>

          <form className="marketplace-form" onSubmit={handleCreateProduct}>
            <label className="marketplace-image-upload">
              {imagePreview ? (
                <img src={imagePreview} alt="Product preview" />
              ) : (
                <>
                  <ImagePlus size={30} />
                  <strong>Add a product photo</strong>
                  <span>JPG, PNG or WebP · Max 5 MB</span>
                </>
              )}
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleImageChange}
              />
            </label>

            <div className="marketplace-form-fields">
              <label>
                Product name
                <input
                  name="name"
                  value={form.name}
                  onChange={updateForm}
                  placeholder="What are you selling?"
                  maxLength={200}
                  required
                />
              </label>

              <label>
                Description
                <textarea
                  name="description"
                  value={form.description}
                  onChange={updateForm}
                  placeholder="Describe the item, its features and anything buyers should know."
                  rows={4}
                  required
                />
              </label>

              <div className="marketplace-form-row">
                <label>
                  Price (KSh)
                  <input
                    name="price"
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={form.price}
                    onChange={updateForm}
                    placeholder="e.g. 1500"
                    required
                  />
                </label>

                <label>
                  Category
                  <select
                    name="category"
                    value={form.category}
                    onChange={updateForm}
                    required
                  >
                    <option value="">Choose a category</option>
                    {categoryOptions.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="marketplace-form-row">
                <label>
                  Condition
                  <select
                    name="condition"
                    value={form.condition}
                    onChange={updateForm}
                  >
                    {CONDITIONS.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Quantity available
                  <input
                    name="stock"
                    type="number"
                    min="1"
                    step="1"
                    value={form.stock}
                    onChange={updateForm}
                    required
                  />
                </label>
              </div>

              <label>
                Campus / pickup location
                <input
                  name="location"
                  value={form.location}
                  onChange={updateForm}
                  placeholder="e.g. Main campus"
                  maxLength={150}
                />
              </label>
            </div>

            <button
              type="submit"
              className="marketplace-submit-button"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Publishing listing..." : "Publish listing"}
              {!isSubmitting && <ArrowRight size={18} />}
            </button>
          </form>
        </section>
      )}

      <section className="marketplace-toolbar">
        <div className="marketplace-search">
          <Search size={19} />
          <input
            type="search"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
            placeholder="Search books, electronics, clothes..."
            aria-label="Search products"
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch("")}
              aria-label="Clear search"
            >
              <X size={17} />
            </button>
          )}
        </div>

        <button
          type="button"
          className={`marketplace-filter-button ${showFilters ? "active" : ""}`}
          onClick={() => setShowFilters((current) => !current)}
        >
          <SlidersHorizontal size={17} />
          Filters
        </button>

        <label className="marketplace-sort">
          <ArrowDownUp size={16} />
          <select
            value={ordering}
            onChange={(event) => {
              setOrdering(event.target.value);
              setPage(1);
            }}
            aria-label="Sort products"
          >
            <option value="-created_at">Newest first</option>
            <option value="created_at">Oldest first</option>
            <option value="price">Price: low to high</option>
            <option value="-price">Price: high to low</option>
            <option value="name">Name: A to Z</option>
            <option value="-name">Name: Z to A</option>
          </select>
        </label>
      </section>

      {showFilters && (
        <section className="marketplace-filters">
          <label>
            Category
            <select
              value={category}
              onChange={(event) => {
                setCategory(event.target.value);
                setPage(1);
              }}
            >
              <option value="">All categories</option>
              {categoryOptions.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Condition
            <select
              value={condition}
              onChange={(event) => {
                setCondition(event.target.value);
                setPage(1);
              }}
            >
              <option value="">Any condition</option>
              {CONDITIONS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Location
            <input
              value={location}
              onChange={(event) => {
                setLocation(event.target.value);
                setPage(1);
              }}
              placeholder="Search location"
            />
          </label>

          <label>
            Minimum price
            <input
              type="number"
              min="0"
              value={minPrice}
              onChange={(event) => {
                setMinPrice(event.target.value);
                setPage(1);
              }}
              placeholder="KSh"
            />
          </label>

          <label>
            Maximum price
            <input
              type="number"
              min="0"
              value={maxPrice}
              onChange={(event) => {
                setMaxPrice(event.target.value);
                setPage(1);
              }}
              placeholder="KSh"
            />
          </label>

          <button
            type="button"
            className="marketplace-reset-button"
            onClick={resetFilters}
          >
            Reset filters
          </button>
        </section>
      )}

      <section className="marketplace-results">
        <div className="marketplace-results-heading">
          <div>
            <span className="marketplace-eyebrow">THE LATEST FINDS</span>
            <h2>Browse the marketplace</h2>
          </div>
          <span className="marketplace-result-count">
            {count} {count === 1 ? "listing" : "listings"}
          </span>
        </div>

        {isLoading ? (
          <div className="marketplace-loading">
            <span className="marketplace-spinner" />
            <p>Finding good things...</p>
          </div>
        ) : error && products.length === 0 ? (
          <div className="marketplace-empty">
            <h3>We couldn't load the listings.</h3>
            <p>{error}</p>
            <button
              type="button"
              onClick={() => setPage((current) => current + 1)}
            >
              Try again
            </button>
          </div>
        ) : products.length === 0 ? (
          <div className="marketplace-empty">
            <div className="marketplace-empty-icon">
              <Search size={28} />
            </div>
            <h3>No listings found.</h3>
            <p>
              Try a different search or clear some filters.
              The next great find might be one search away.
            </p>
            <button type="button" onClick={resetFilters}>
              Clear filters
            </button>
          </div>
        ) : (
          <div className="marketplace-product-grid">
            {products.map((product, index) => (
              <article
                className="marketplace-product-card"
                key={product.id}
                style={{ "--product-index": index }}
              >
                <div className="marketplace-product-image">
                  {product.image ? (
                    <img
                      src={getImageUrl(product.image)}
                      alt={product.name}
                      loading="lazy"
                    />
                  ) : (
                    <div className="marketplace-no-image">
                      <ImagePlus size={30} />
                      <span>Photo coming soon</span>
                    </div>
                  )}
                  <span className="marketplace-condition">
                    {CONDITIONS.find(
                      (item) => item.value === product.condition,
                    )?.label ?? product.condition}
                  </span>
                </div>

                <div className="marketplace-product-info">
                  <span className="marketplace-product-category">
                    {product.category_name || "Campus find"}
                  </span>
                  <h3>{product.name}</h3>
                  <p className="marketplace-product-description">
                    {product.description}
                  </p>
                  <div className="marketplace-product-meta">
                    <span>{product.location || "Campus pickup"}</span>
                    <span>{product.stock} available</span>
                  </div>
                  <div className="marketplace-product-bottom">
                    <strong>{formatPrice(product.price)}</strong>
                    <span>by {product.seller_username}</span>
                  </div>

                  {isAuthenticated ? (
                    <button
                      type="button"
                      className="marketplace-add-cart-button"
                      onClick={() => handleAddToCart(product)}
                      disabled={addingProduct === product.id}
                    >
                      <ShoppingCart size={17} />
                      {addingProduct === product.id
                        ? "Adding..."
                        : "Add to cart"}
                    </button>
                  ) : (
                    <Link
                      to="/login"
                      className="marketplace-add-cart-button"
                    >
                      Sign in to buy <ArrowRight size={17} />
                    </Link>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}

        {!isLoading && products.length > 0 && (
          <div className="marketplace-pagination">
            <button
              type="button"
              disabled={!previousPage}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
            >
              Previous
            </button>
            <span>Page {page}</span>
            <button
              type="button"
              disabled={!nextPage}
              onClick={() => setPage((current) => current + 1)}
            >
              Next <ArrowRight size={16} />
            </button>
          </div>
        )}
      </section>
    </main>
  );
};

export default MarketplacePage;
