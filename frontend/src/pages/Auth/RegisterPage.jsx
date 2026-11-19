import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff, ArrowLeft, ArrowRight, Check } from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { getApiErrorMessage } from "../../services/api";

const initialForm = {
  username: "",
  email: "",
  password: "",
  confirm_password: "",
  first_name: "",
  last_name: "",
  student_id: "",
  institution: "",
  course: "",
  year_of_study: "",
  phone_number: "",
};

const RegisterPage = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState(initialForm);
  const [step, setStep] = useState(1);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (event) => {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));

    if (error) setError("");
  };

  const continueToDetails = (event) => {
    event.preventDefault();
    setError("");

    if (form.password !== form.confirm_password) {
      setError("Your passwords do not match.");
      return;
    }

    if (form.password.length < 8) {
      setError("Your password must contain at least 8 characters.");
      return;
    }

    setStep(2);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    const registrationData = {
      ...form,
      student_id: form.student_id.trim() || null,
      year_of_study: form.year_of_study
        ? Number(form.year_of_study)
        : null,
    };

    try {
      await register(registrationData);
      navigate("/profile", { replace: true });
    } catch (registrationError) {
      setError(getApiErrorMessage(registrationError));
      setStep(1);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="auth-page register-page">
      <section className="auth-showcase">
        <Link to="/" className="auth-brand">
          <span className="brand-mark">C.</span>
          <span>CampusCart</span>
        </Link>

        <div className="showcase-content">
          <p className="showcase-kicker">MADE FOR CAMPUS LIFE</p>

          <h1>
            Your campus.
            <br />
            Your people.
            <br />
            <span>Your world.</span>
          </h1>

          <p className="showcase-description">
            Find what you need, share what you know and discover
            what is happening around your campus.
          </p>

          <div className="showcase-activity">
            <span>BUY</span>
            <span>SELL</span>
            <span>CONNECT</span>
          </div>
        </div>

        <div className="showcase-footer">
          <span>01 / 03</span>
          <p>More than a marketplace. Your campus community.</p>
        </div>
      </section>

      <section className="auth-form-section">
        <div className="auth-form-container">
          <div className="auth-mobile-brand">
            <span className="brand-mark">C.</span>
            <span>CampusCart</span>
          </div>

          <div className="auth-heading">
            <span className="eyebrow">
              {step === 1 ? "LET'S GET YOU STARTED" : "ALMOST THERE"}
            </span>
            <h2>
              {step === 1 ? "Create your account" : "Your campus details"}
              <span>.</span>
            </h2>
            <p>
              {step === 1
                ? "Start with your account information."
                : "Tell us a little about your campus life."}
            </p>
          </div>

          <div className="registration-progress">
            <div className="registration-progress-labels">
              <span className={step === 1 ? "active" : "complete"}>
                <span>{step > 1 ? <Check size={14} /> : "01"}</span>
                Your account
              </span>
              <span className={step === 2 ? "active" : ""}>
                <span>02</span>
                Campus details
              </span>
            </div>
            <div className="registration-progress-track">
              <span className={step === 2 ? "progress-complete" : ""} />
            </div>
          </div>

          {error && (
            <div className="auth-error" role="alert">
              {error}
            </div>
          )}

          {step === 1 ? (
            <form onSubmit={continueToDetails} className="auth-form">
              <div className="form-section-heading">
                <span>01</span>
                <h3>Your account</h3>
              </div>

              <div className="form-grid">
                <div className="form-field">
                  <label htmlFor="first_name">First name</label>
                  <input
                    id="first_name"
                    name="first_name"
                    value={form.first_name}
                    onChange={handleChange}
                    placeholder="Your first name"
                    autoComplete="given-name"
                  />
                </div>

                <div className="form-field">
                  <label htmlFor="last_name">Last name</label>
                  <input
                    id="last_name"
                    name="last_name"
                    value={form.last_name}
                    onChange={handleChange}
                    placeholder="Your last name"
                    autoComplete="family-name"
                  />
                </div>
              </div>

              <div className="form-field">
                <label htmlFor="username">Username *</label>
                <input
                  id="username"
                  name="username"
                  value={form.username}
                  onChange={handleChange}
                  placeholder="Choose a username"
                  autoComplete="username"
                  required
                />
              </div>

              <div className="form-field">
                <label htmlFor="email">Email address *</label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={form.email}
                  onChange={handleChange}
                  placeholder="you@example.com"
                  autoComplete="email"
                  required
                />
              </div>

              <div className="form-grid">
                <div className="form-field">
                  <label htmlFor="password">Password *</label>
                  <div className="password-input">
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      value={form.password}
                      onChange={handleChange}
                      placeholder="At least 8 characters"
                      autoComplete="new-password"
                      minLength={8}
                      required
                    />
                    <button
                      type="button"
                      className="password-toggle"
                      onClick={() => setShowPassword((value) => !value)}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>

                <div className="form-field">
                  <label htmlFor="confirm_password">Confirm password *</label>
                  <div className="password-input">
                    <input
                      id="confirm_password"
                      name="confirm_password"
                      type={showConfirmPassword ? "text" : "password"}
                      value={form.confirm_password}
                      onChange={handleChange}
                      placeholder="Repeat password"
                      autoComplete="new-password"
                      required
                    />
                    <button
                      type="button"
                      className="password-toggle"
                      onClick={() => setShowConfirmPassword((value) => !value)}
                      aria-label={
                        showConfirmPassword ? "Hide password" : "Show password"
                      }
                    >
                      {showConfirmPassword ? (
                        <EyeOff size={18} />
                      ) : (
                        <Eye size={18} />
                      )}
                    </button>
                  </div>
                </div>
              </div>

              <button type="submit" className="auth-submit-button">
                Continue to campus details
                <ArrowRight size={19} />
              </button>

              <p className="auth-switch">
                Already part of the community? <Link to="/login">Log in</Link>
              </p>
            </form>
          ) : (
            <form onSubmit={handleSubmit} className="auth-form">
              <div className="form-section-heading">
                <span>02</span>
                <h3>Your campus details</h3>
                <small>All fields on this step are optional.</small>
              </div>

              <div className="form-field">
                <label htmlFor="institution">Institution</label>
                <input
                  id="institution"
                  name="institution"
                  value={form.institution}
                  onChange={handleChange}
                  placeholder="University or college"
                />
              </div>

              <div className="form-field">
                <label htmlFor="course">Course / Programme</label>
                <input
                  id="course"
                  name="course"
                  value={form.course}
                  onChange={handleChange}
                  placeholder="e.g. Computer Science"
                />
              </div>

              <div className="form-grid">
                <div className="form-field">
                  <label htmlFor="student_id">Student ID</label>
                  <input
                    id="student_id"
                    name="student_id"
                    value={form.student_id}
                    onChange={handleChange}
                    placeholder="Your student number"
                  />
                </div>

                <div className="form-field">
                  <label htmlFor="year_of_study">Year of study</label>
                  <select
                    id="year_of_study"
                    name="year_of_study"
                    value={form.year_of_study}
                    onChange={handleChange}
                  >
                    <option value="">Select year</option>
                    <option value="1">Year 1</option>
                    <option value="2">Year 2</option>
                    <option value="3">Year 3</option>
                    <option value="4">Year 4</option>
                    <option value="5">Year 5</option>
                  </select>
                </div>
              </div>

              <div className="form-field">
                <label htmlFor="phone_number">Phone number</label>
                <input
                  id="phone_number"
                  name="phone_number"
                  type="tel"
                  value={form.phone_number}
                  onChange={handleChange}
                  placeholder="e.g. 07XXXXXXXX"
                  autoComplete="tel"
                />
              </div>

              <div className="registration-actions">
                <button
                  type="button"
                  className="auth-back-button"
                  onClick={() => {
                    setError("");
                    setStep(1);
                  }}
                  disabled={isSubmitting}
                >
                  <ArrowLeft size={18} />
                  Back
                </button>

                <button
                  type="submit"
                  className="auth-submit-button"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <span className="button-spinner" />
                      Creating account
                    </>
                  ) : (
                    <>
                      Create my account
                      <ArrowRight size={19} />
                    </>
                  )}
                </button>
              </div>

              <button
                type="button"
                className="skip-campus-details"
                onClick={handleSubmit}
                disabled={isSubmitting}
              >
                Skip campus details
              </button>
            </form>
          )}

          <p className="auth-legal">
            By creating an account, you agree to use CampusCart
            responsibly and respectfully.
          </p>
        </div>
      </section>
    </main>
  );
};

export default RegisterPage;
