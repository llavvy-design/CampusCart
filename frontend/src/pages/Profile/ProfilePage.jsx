import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  Camera,
  Check,
  ImagePlus,
  Pencil,
  Save,
  Trash2,
  UserRound,
  X,
} from "lucide-react";

import { useAuth } from "../../hooks/useAuth";
import { getApiErrorMessage } from "../../services/api";

const EMPTY_FORM = {
  first_name: "",
  last_name: "",
  institution: "",
  course: "",
  year_of_study: "",
  phone_number: "",
  bio: "",
};

const ALLOWED_IMAGE_TYPES = [
  "image/jpeg",
  "image/png",
  "image/webp",
];

const MAX_AVATAR_SIZE = 5 * 1024 * 1024;

const ProfilePage = () => {
  const { user, profile, updateProfile, logout } = useAuth();

  const currentProfile = profile || user;
  const fileInputRef = useRef(null);

  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isAvatarSaving, setIsAvatarSaving] = useState(false);
  const [selectedAvatar, setSelectedAvatar] = useState(null);
  const [avatarPreview, setAvatarPreview] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [form, setForm] = useState(() => ({
    ...EMPTY_FORM,
    first_name: currentProfile?.first_name || "",
    last_name: currentProfile?.last_name || "",
    institution: currentProfile?.institution || "",
    course: currentProfile?.course || "",
    year_of_study: currentProfile?.year_of_study || "",
    phone_number: currentProfile?.phone_number || "",
    bio: currentProfile?.bio || "",
  }));

  useEffect(() => {
    return () => {
      if (avatarPreview) {
        URL.revokeObjectURL(avatarPreview);
      }
    };
  }, [avatarPreview]);

  const handleChange = (event) => {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  const resetForm = () => {
    setForm({
      ...EMPTY_FORM,
      first_name: currentProfile?.first_name || "",
      last_name: currentProfile?.last_name || "",
      institution: currentProfile?.institution || "",
      course: currentProfile?.course || "",
      year_of_study: currentProfile?.year_of_study || "",
      phone_number: currentProfile?.phone_number || "",
      bio: currentProfile?.bio || "",
    });
  };

  const handleCancel = () => {
    setError("");
    setSuccess("");
    setIsEditing(false);
    resetForm();
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    setError("");
    setSuccess("");
    setIsSaving(true);

    try {
      await updateProfile({
        first_name: form.first_name,
        last_name: form.last_name,
        institution: form.institution,
        course: form.course,
        year_of_study: form.year_of_study
          ? Number(form.year_of_study)
          : null,
        phone_number: form.phone_number,
        bio: form.bio,
      });

      setSuccess("Your profile has been updated successfully.");
      setIsEditing(false);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setIsSaving(false);
    }
  };

  const handleAvatarSelection = (event) => {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    setError("");
    setSuccess("");

    if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
      setError("Please choose a JPG, PNG or WebP image.");
      event.target.value = "";
      return;
    }

    if (file.size > MAX_AVATAR_SIZE) {
      setError("Your profile picture must not exceed 5 MB.");
      event.target.value = "";
      return;
    }

    setSelectedAvatar(file);
    setAvatarPreview(URL.createObjectURL(file));
  };

  const handleAvatarUpload = async () => {
    if (!selectedAvatar) {
      return;
    }

    setError("");
    setSuccess("");
    setIsAvatarSaving(true);

    try {
      const formData = new FormData();
      formData.append("avatar", selectedAvatar);

      await updateProfile(formData);

      setSelectedAvatar(null);
      setAvatarPreview("");

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      setSuccess("Your profile picture has been updated.");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setIsAvatarSaving(false);
    }
  };

  const handleAvatarRemoval = async () => {
    if (!currentProfile?.avatar) {
      return;
    }

    const confirmed = window.confirm(
      "Are you sure you want to remove your profile picture?",
    );

    if (!confirmed) {
      return;
    }

    setError("");
    setSuccess("");
    setIsAvatarSaving(true);

    try {
      await updateProfile({ avatar: null });

      setSelectedAvatar(null);
      setAvatarPreview("");

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      setSuccess("Your profile picture has been removed.");
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setIsAvatarSaving(false);
    }
  };

  const handleDiscardAvatar = () => {
    setSelectedAvatar(null);
    setAvatarPreview("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }

    setError("");
  };

  if (!currentProfile) {
    return (
      <main className="profile-loading">
        <p>Loading your student profile...</p>
      </main>
    );
  }

  const fullName = [
    currentProfile.first_name,
    currentProfile.last_name,
  ]
    .filter(Boolean)
    .join(" ");

  const displayName = fullName || currentProfile.username;

  const displayedAvatar =
    avatarPreview || currentProfile.avatar || null;

  return (
    <main className="profile-page">
      <header className="profile-topbar">
        <Link to="/" className="profile-back-link">
          <ArrowLeft size={18} />
          Back to CampusCart
        </Link>

        <button
          type="button"
          className="profile-logout-button"
          onClick={logout}
        >
          Log out
        </button>
      </header>

      <section className="profile-container">
        <div className="profile-intro">
          <span className="profile-eyebrow">YOUR CAMPUS IDENTITY</span>
          <h1>Your student profile<span>.</span></h1>
          <p>
            This is your space on CampusCart. Tell other students a little
            about yourself.
          </p>
        </div>

        {error && (
          <div className="profile-message profile-message-error">
            {error}
          </div>
        )}

        {success && (
          <div className="profile-message profile-message-success">
            {success}
          </div>
        )}

        <section className="profile-card">
          <div className="profile-card-banner">
            <span className="profile-banner-sticker">CAMPUS CONNECT</span>
          </div>

          <div className="profile-card-content">
            <div className="profile-identity">
              <div className="profile-avatar-area">
                <div className="profile-avatar">
                  {displayedAvatar ? (
                    <img
                      src={displayedAvatar}
                      alt={`${displayName}'s profile`}
                    />
                  ) : (
                    <UserRound size={38} />
                  )}
                </div>

                <button
                  type="button"
                  className="profile-avatar-trigger"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isAvatarSaving || isSaving}
                  aria-label="Choose a profile picture"
                >
                  <Camera size={15} />
                </button>

                <input
                  ref={fileInputRef}
                  className="profile-avatar-input"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleAvatarSelection}
                />
              </div>

              <div className="profile-identity-text">
                <h2>{displayName}</h2>
                <p>@{currentProfile.username}</p>
              </div>

              {!isEditing && (
                <button
                  type="button"
                  className="profile-edit-button"
                  onClick={() => {
                    setError("");
                    setSuccess("");
                    setIsEditing(true);
                  }}
                >
                  <Pencil size={16} />
                  Edit profile
                </button>
              )}
            </div>

            <div className="profile-avatar-controls">
              <div className="profile-avatar-guidance">
                <ImagePlus size={17} />
                <span>JPG, PNG or WebP. Maximum 5 MB.</span>
              </div>

              {selectedAvatar && (
                <div className="profile-avatar-actions">
                  <button
                    type="button"
                    className="profile-avatar-save"
                    onClick={handleAvatarUpload}
                    disabled={isAvatarSaving || isSaving}
                  >
                    {isAvatarSaving ? (
                      "Uploading..."
                    ) : (
                      <>
                        <Check size={15} />
                        Save picture
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    className="profile-avatar-discard"
                    onClick={handleDiscardAvatar}
                    disabled={isAvatarSaving}
                  >
                    <X size={15} />
                    Cancel
                  </button>
                </div>
              )}

              {!selectedAvatar && currentProfile.avatar && (
                <button
                  type="button"
                  className="profile-avatar-remove"
                  onClick={handleAvatarRemoval}
                  disabled={isAvatarSaving || isSaving}
                >
                  <Trash2 size={14} />
                  Remove picture
                </button>
              )}
            </div>

            {isEditing ? (
              <form
                className="profile-edit-form"
                onSubmit={handleSubmit}
              >
                <div className="profile-form-grid">
                  <label className="profile-field">
                    First name
                    <input
                      name="first_name"
                      value={form.first_name}
                      onChange={handleChange}
                      maxLength={150}
                    />
                  </label>

                  <label className="profile-field">
                    Last name
                    <input
                      name="last_name"
                      value={form.last_name}
                      onChange={handleChange}
                      maxLength={150}
                    />
                  </label>

                  <label className="profile-field">
                    Email address
                    <input
                      type="email"
                      value={currentProfile.email || ""}
                      disabled
                    />
                    <small>Email cannot be changed here.</small>
                  </label>

                  <label className="profile-field">
                    Institution
                    <input
                      name="institution"
                      value={form.institution}
                      onChange={handleChange}
                      maxLength={150}
                    />
                  </label>

                  <label className="profile-field">
                    Course or programme
                    <input
                      name="course"
                      value={form.course}
                      onChange={handleChange}
                      maxLength={150}
                    />
                  </label>

                  <label className="profile-field">
                    Year of study
                    <select
                      name="year_of_study"
                      value={form.year_of_study}
                      onChange={handleChange}
                    >
                      <option value="">Select your year</option>
                      {[1, 2, 3, 4, 5].map((year) => (
                        <option key={year} value={year}>
                          Year {year}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="profile-field profile-field-full">
                    Phone number
                    <input
                      name="phone_number"
                      type="tel"
                      value={form.phone_number}
                      onChange={handleChange}
                    />
                  </label>

                  <label className="profile-field profile-field-full">
                    About me
                    <textarea
                      name="bio"
                      value={form.bio}
                      onChange={handleChange}
                      rows={4}
                      maxLength={500}
                      placeholder="Tell the campus community a little about yourself..."
                    />
                    <small>{form.bio.length}/500 characters</small>
                  </label>
                </div>

                <div className="profile-form-actions">
                  <button
                    type="button"
                    className="profile-cancel-button"
                    onClick={handleCancel}
                    disabled={isSaving}
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    className="profile-save-button"
                    disabled={isSaving}
                  >
                    <Save size={16} />
                    {isSaving ? "Saving..." : "Save changes"}
                  </button>
                </div>
              </form>
            ) : (
              <div className="profile-details">
                <div className="profile-detail-item">
                  <span>EMAIL ADDRESS</span>
                  <strong>{currentProfile.email || "Not provided"}</strong>
                </div>

                <div className="profile-detail-item">
                  <span>INSTITUTION</span>
                  <strong>
                    {currentProfile.institution || "Not added yet"}
                  </strong>
                </div>

                <div className="profile-detail-item">
                  <span>COURSE / PROGRAMME</span>
                  <strong>
                    {currentProfile.course || "Not added yet"}
                  </strong>
                </div>

                <div className="profile-detail-item">
                  <span>YEAR OF STUDY</span>
                  <strong>
                    {currentProfile.year_of_study
                      ? `Year ${currentProfile.year_of_study}`
                      : "Not added yet"}
                  </strong>
                </div>

                <div className="profile-detail-item">
                  <span>PHONE NUMBER</span>
                  <strong>
                    {currentProfile.phone_number || "Not provided"}
                  </strong>
                </div>

                <div className="profile-detail-item profile-detail-bio">
                  <span>ABOUT ME</span>
                  <p>
                    {currentProfile.bio ||
                      "Your introduction will appear here. Add a little something about yourself!"}
                  </p>
                </div>
              </div>
            )}
          </div>
        </section>
      </section>
    </main>
  );
};

export default ProfilePage;
