import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, LockKeyhole, Mail } from "lucide-react";

import { useAuth } from "../../hooks/useAuth";
import { getApiErrorMessage } from "../../services/api";

const LoginPage = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [formData, setFormData] = useState({
    username: "",
    password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const destination = location.state?.from?.pathname || "/marketplace";

  const handleChange = (event) => {
    setFormData((previous) => ({
      ...previous,
      [event.target.name]: event.target.value,
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      await login(formData);
      navigate(destination, { replace: true });
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="cc-auth-page">
      <section className="cc-auth-panel">
        <Link to="/" className="cc-auth-brand">
          <span className="cc-logo-mark">C</span>
          CampusCart<span>.</span>
        </Link>

        <div className="cc-auth-heading">
          <span className="cc-section-kicker">GOOD TO HAVE YOU BACK</span>
          <h1>Welcome back.</h1>
          <p>Sign in and get back to your campus world.</p>
        </div>

        <form className="cc-auth-form" onSubmit={handleSubmit}>
          <label htmlFor="username">Username</label>
          <div className="cc-auth-input-wrap">
            <Mail size={19} />
            <input
              id="username"
              name="username"
              type="text"
              placeholder="Enter your username"
              value={formData.username}
              onChange={handleChange}
              autoComplete="username"
              required
            />
          </div>

          <label htmlFor="password">Password</label>
          <div className="cc-auth-input-wrap">
            <LockKeyhole size={19} />
            <input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              value={formData.password}
              onChange={handleChange}
              autoComplete="current-password"
              required
            />
            <button
              type="button"
              className="cc-password-toggle"
              onClick={() => setShowPassword((previous) => !previous)}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
            </button>
          </div>

          {error && (
            <p className="cc-auth-error" role="alert">{error}</p>
          )}

          <button
            type="submit"
            className="cc-auth-submit"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Signing you in..." : "Log in"}
            {!isSubmitting && <ArrowRight size={18} />}
          </button>
        </form>

        <p className="cc-auth-switch">
          New to CampusCart? <Link to="/register">Create an account</Link>
        </p>
      </section>

      <aside className="cc-auth-art">
        <span className="cc-auth-art-label">YOUR CAMPUS. YOUR PEOPLE.</span>
        <div className="cc-auth-art-content">
          <span className="cc-auth-art-number">01 — CONNECT</span>
          <h2>There's always something happening here.</h2>
          <p>Find great deals, meet other students and make more of campus life.</p>
        </div>
        <span className="cc-auth-art-stamp">CAMPUS<br />APPROVED</span>
      </aside>
    </main>
  );
};

export default LoginPage;
