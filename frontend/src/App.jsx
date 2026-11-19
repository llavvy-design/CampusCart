import { useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  Menu,
  ShoppingBag,
  Users,
  X,
} from "lucide-react";
import { Link, NavLink, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./components/common/ProtectedRoute";
import RegisterPage from "./pages/Auth/RegisterPage";
import LoginPage from "./pages/Auth/LoginPage";
import ProfilePage from "./pages/Profile/ProfilePage";
import MarketplacePage from "./pages/Marketplace/MarketplacePage";
import CartPage from "./pages/Marketplace/CartPage";
import CommunityPage from "./pages/Community/CommunityPage";
import { useAuth } from "./hooks/useAuth";

import "./App.css";

const navigation = [
  { label: "Home", path: "/", end: true },
  { label: "Marketplace", path: "/marketplace" },
  { label: "Community", path: "/community" },
  { label: "Events", path: "/events" },
];

const AppNavigation = () => {
  const { isAuthenticated, user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  const closeMenu = () => setMenuOpen(false);

  return (
    <header className="cc-navbar">
      <div className="cc-navbar-inner">
        <Link to="/" className="cc-logo" onClick={closeMenu}>
          <span className="cc-logo-mark">C</span>
          <span>CampusCart<span className="cc-logo-period">.</span></span>
        </Link>

        <nav className={`cc-nav-links ${menuOpen ? "cc-nav-open" : ""}`}>
          {navigation.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.end}
              onClick={closeMenu}
              className={({ isActive }) =>
                isActive ? "cc-nav-link cc-nav-active" : "cc-nav-link"
              }
            >
              {item.label}
            </NavLink>
          ))}

          {isAuthenticated && (
            <NavLink
              to="/profile"
              onClick={closeMenu}
              className={({ isActive }) =>
                isActive ? "cc-nav-link cc-nav-active" : "cc-nav-link"
              }
            >
              My profile
            </NavLink>
          )}

          <div className="cc-mobile-auth">
            {isAuthenticated ? (
              <button
                type="button"
                onClick={() => {
                  closeMenu();
                  logout();
                }}
              >
                Log out
              </button>
            ) : (
              <>
                <Link to="/login" onClick={closeMenu}>Log in</Link>
                <Link to="/register" onClick={closeMenu}>Join CampusCart</Link>
              </>
            )}
          </div>
        </nav>

        <div className="cc-nav-actions">
          {isAuthenticated ? (
            <>
              <Link to="/profile" className="cc-user-link">
                {user?.first_name || user?.username || "My account"}
              </Link>
              <button
                type="button"
                className="cc-nav-join"
                onClick={logout}
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="cc-login-link">Log in</Link>
              <Link to="/register" className="cc-nav-join">
                Join CampusCart <ArrowUpRight size={15} />
              </Link>
            </>
          )}
        </div>

        <button
          type="button"
          className="cc-mobile-toggle"
          onClick={() => setMenuOpen((previous) => !previous)}
          aria-label={menuOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={menuOpen}
        >
          {menuOpen ? <X size={23} /> : <Menu size={23} />}
        </button>
      </div>
    </header>
  );
};

const AppLayout = ({ children }) => {
  return (
    <div className="cc-app">
      <AppNavigation />
      {children}
      <footer className="cc-footer">
        <Link to="/" className="cc-footer-brand">CampusCart.</Link>
        <p>Made for campus life. Built for student connections.</p>
        <span>© {new Date().getFullYear()} CampusCart</span>
      </footer>
    </div>
  );
};

const HomePage = () => {
  const { isAuthenticated, user } = useAuth();

  return (
    <AppLayout>
      <main className="cc-home">
        <section className="cc-hero">
          <div className="cc-hero-copy">
            <span className="cc-hero-kicker">
              <span className="cc-live-dot" />
              YOUR CAMPUS. YOUR COMMUNITY. YOUR MARKETPLACE.
            </span>

            <h1>
              Campus life,
              <br />
              <span>all in one place.</span>
            </h1>

            <p>
              Buy what you need, sell what you don't and connect with
              students who make campus life interesting.
            </p>

            <div className="cc-hero-actions">
              <Link to="/marketplace" className="cc-primary-cta">
                Explore marketplace <ArrowRight size={18} />
              </Link>
              {!isAuthenticated && (
                <Link to="/register" className="cc-secondary-cta">
                  Join the community
                </Link>
              )}
              {isAuthenticated && (
                <Link to="/profile" className="cc-secondary-cta">
                  Welcome back, {user?.first_name || user?.username}
                </Link>
              )}
            </div>

            <div className="cc-hero-note">
              <span>BUY</span>
              <span>SELL</span>
              <span>CONNECT</span>
              <span>DISCOVER</span>
            </div>
          </div>

          <div className="cc-hero-art">
            <div className="cc-art-paper">
              <span className="cc-art-label">THE CAMPUS EXCHANGE</span>
              <div className="cc-art-bag">
                <ShoppingBag size={94} strokeWidth={1.5} />
              </div>
              <div className="cc-art-caption">
                <strong>Good finds.</strong>
                <strong>Great people.</strong>
              </div>
              <span className="cc-art-stamp">CAMPUS<br />APPROVED</span>
            </div>
            <div className="cc-art-tag">YOUR PEOPLE ARE HERE.</div>
          </div>
        </section>

        <section className="cc-discover">
          <div className="cc-section-heading">
            <div>
              <span className="cc-section-kicker">EXPLORE CAMPUSCART</span>
              <h2>What's happening on campus?</h2>
            </div>
            <span className="cc-section-aside">Pick your next move.</span>
          </div>

          <div className="cc-feature-grid">
            <Link to="/marketplace" className="cc-feature cc-feature-market">
              <div className="cc-feature-icon">
                <ShoppingBag size={27} />
              </div>
              <span className="cc-feature-number">01 / MARKETPLACE</span>
              <h3>Find it. Buy it. Sell it.</h3>
              <p>
                Discover affordable student listings or give your
                unused items a new home.
              </p>
              <span className="cc-feature-link">
                Explore marketplace <ArrowUpRight size={18} />
              </span>
            </Link>

            <Link to="/community" className="cc-feature cc-feature-community">
              <div className="cc-feature-icon">
                <Users size={27} />
              </div>
              <span className="cc-feature-number">02 / COMMUNITY</span>
              <h3>Your campus, your people.</h3>
              <p>
                Share ideas, join conversations and connect with
                fellow students.
              </p>
              <span className="cc-feature-link">
                Meet the community <ArrowUpRight size={18} />
              </span>
            </Link>

            <Link to="/events" className="cc-feature cc-feature-events">
              <div className="cc-feature-icon">
                <CalendarDays size={27} />
              </div>
              <span className="cc-feature-number">03 / CAMPUS EVENTS</span>
              <h3>There's more happening.</h3>
              <p>
                Discover campus activities, opportunities and
                things worth showing up for.
              </p>
              <span className="cc-feature-link">
                Discover events <ArrowUpRight size={18} />
              </span>
            </Link>
          </div>
        </section>

        {!isAuthenticated && (
          <section className="cc-join-banner">
            <div>
              <span>YOUR CAMPUS IS WAITING</span>
              <h2>Make campus life a little more connected.</h2>
            </div>
            <Link to="/register">
              Get started <ArrowRight size={18} />
            </Link>
          </section>
        )}
      </main>
    </AppLayout>
  );
};

const PlaceholderPage = ({ title, description }) => {
  return (
    <AppLayout>
      <main className="cc-placeholder">
        <span className="cc-section-kicker">CAMPUSCART</span>
        <h1>{title}</h1>
        <p>{description}</p>
        <Link to="/" className="cc-primary-cta">
          Back to home <ArrowRight size={17} />
        </Link>
      </main>
    </AppLayout>
  );
};

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />

      <Route path="/login" element={<LoginPage />} />

      <Route path="/register" element={<RegisterPage />} />

      <Route
        path="/marketplace"
        element={
          <AppLayout>
            <MarketplacePage />
          </AppLayout>
        }
      />

      <Route
        path="/cart"
        element={
          <ProtectedRoute>
            <AppLayout>
              <CartPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />

      <Route
        path="/community"
        element={
          <AppLayout>
            <CommunityPage />
          </AppLayout>
        }
      />

      <Route
        path="/events"
        element={
          <PlaceholderPage
            title="Discover what's happening."
            description="Find campus activities, opportunities and events."
          />
        }
      />

      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />

      <Route
        path="*"
        element={
          <PlaceholderPage
            title="Page not found."
            description="We couldn't find the page you were looking for."
          />
        }
      />
    </Routes>
  );
}

export default App;
