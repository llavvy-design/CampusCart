import { useEffect, useState } from "react";
import {
  MessageCircle,
  Heart,
  ImagePlus,
  Send,
  Trash2,
  Users,
  X,
  LoaderCircle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Link } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";
import { api, getApiErrorMessage } from "../../services/api";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

const getImageUrl = (image) => {
  if (!image) return "";

  if (image.startsWith("http")) return image;

  return `${BACKEND_URL}${image.startsWith("/") ? "" : "/"}${image}`;
};

const getInitials = (name) => {
  return (name || "S")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
};

const formatDate = (date) => {
  const value = new Date(date);
  const now = new Date();
  const difference = Math.floor((now - value) / 1000);

  if (difference < 60) return "Just now";
  if (difference < 3600) return `${Math.floor(difference / 60)}m ago`;
  if (difference < 86400) return `${Math.floor(difference / 3600)}h ago`;
  if (difference < 604800) return `${Math.floor(difference / 86400)}d ago`;

  return value.toLocaleDateString("en-KE", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
};

const CommunityPage = () => {
  const { isAuthenticated, user } = useAuth();

  const [posts, setPosts] = useState([]);
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [nextPage, setNextPage] = useState(null);
  const [previousPage, setPreviousPage] = useState(null);
  const [content, setContent] = useState("");
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState("");
  const [comments, setComments] = useState({});
  const [commentInputs, setCommentInputs] = useState({});
  const [expandedPost, setExpandedPost] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCommenting, setIsCommenting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadPosts = async (currentPage = page) => {
    setIsLoading(true);
    setError("");

    try {
      const response = await api.get("/community/posts/", {
        params: {
          page: currentPage,
          page_size: 10,
        },
      });

      const data = response.data;
      const results = data.results ?? data;

      setPosts(results);
      setCount(data.count ?? results.length);
      setNextPage(data.next ?? null);
      setPreviousPage(data.previous ?? null);
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let active = true;

    const fetchPosts = async () => {
      setIsLoading(true);
      setError("");

      try {
        const response = await api.get("/community/posts/", {
          params: {
            page,
            page_size: 10,
          },
        });

        const data = response.data;
        const results = data.results ?? data;

        if (active) {
          setPosts(results);
          setCount(data.count ?? results.length);
          setNextPage(data.next ?? null);
          setPreviousPage(data.previous ?? null);
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

    fetchPosts();

    return () => {
      active = false;
    };
  }, [page]);

  const handleImageChange = (event) => {
    const selectedImage = event.target.files?.[0];

    if (!selectedImage) return;

    if (selectedImage.size > 5 * 1024 * 1024) {
      setError("Images must be 5 MB or smaller.");
      return;
    }

    setImage(selectedImage);
    setImagePreview(URL.createObjectURL(selectedImage));
    setError("");
  };

  const handleCreatePost = async (event) => {
    event.preventDefault();

    if (!content.trim() && !image) {
      setError("Write something or add an image before posting.");
      return;
    }

    setIsSubmitting(true);
    setError("");
    setSuccess("");

    const formData = new FormData();
    formData.append("content", content);

    if (image) {
      formData.append("image", image);
    }

    try {
      await api.post("/community/posts/", formData);

      setContent("");
      setImage(null);
      setImagePreview("");
      setSuccess("Your post is now live.");

      if (page !== 1) {
        setPage(1);
      } else {
        await loadPosts(1);
      }
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLike = async (postId) => {
    if (!isAuthenticated) {
      setError("Log in to like posts.");
      return;
    }

    try {
      const response = await api.post(
        `/community/posts/${postId}/like/`,
      );

      setPosts((currentPosts) =>
        currentPosts.map((post) =>
          post.id === postId
            ? {
                ...post,
                is_liked: response.data.liked,
                likes_count: response.data.likes_count,
              }
            : post,
        ),
      );
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    }
  };

  const loadComments = async (postId) => {
    try {
      const response = await api.get(
        `/community/posts/${postId}/comments/`,
      );

      const data = response.data;

      setComments((current) => ({
        ...current,
        [postId]: data.results ?? data,
      }));
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    }
  };

  const toggleComments = async (postId) => {
    if (expandedPost === postId) {
      setExpandedPost(null);
      return;
    }

    setExpandedPost(postId);
    await loadComments(postId);
  };

  const handleComment = async (event, postId) => {
    event.preventDefault();

    const comment = commentInputs[postId]?.trim();

    if (!comment) return;

    setIsCommenting(true);
    setError("");

    try {
      const response = await api.post(
        `/community/posts/${postId}/comments/`,
        {
          content: comment,
        },
      );

      setComments((current) => ({
        ...current,
        [postId]: [...(current[postId] ?? []), response.data],
      }));

      setCommentInputs((current) => ({
        ...current,
        [postId]: "",
      }));

      setPosts((currentPosts) =>
        currentPosts.map((post) =>
          post.id === postId
            ? {
                ...post,
                comments_count: post.comments_count + 1,
              }
            : post,
        ),
      );
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    } finally {
      setIsCommenting(false);
    }
  };

  const handleDeletePost = async (postId) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this post?",
    );

    if (!confirmed) return;

    try {
      await api.delete(`/community/posts/${postId}/`);

      setPosts((current) =>
        current.filter((post) => post.id !== postId),
      );

      setCount((current) => Math.max(0, current - 1));
    } catch (requestError) {
      setError(getApiErrorMessage(requestError));
    }
  };

  return (
    <main className="cc-community">
      <section className="cc-community-hero">
        <div className="cc-community-hero-copy">
          <span className="cc-community-kicker">
            <Users size={15} />
            THE STUDENT SPACE
          </span>

          <h1>
            Your campus.
            <br />
            <span>Your people.</span>
          </h1>

          <p>
            Share ideas, ask questions, celebrate wins and
            stay connected to what's happening around campus.
          </p>
        </div>

        <div className="cc-community-hero-art">
          <div className="cc-community-art-card">
            <span>GOOD IDEAS</span>
            <strong>START HERE.</strong>
            <div className="cc-community-art-icon">
              <Users size={62} strokeWidth={1.5} />
            </div>
            <span>CONNECT · SHARE · GROW</span>
          </div>
        </div>
      </section>

      <section className="cc-community-content">
        <div className="cc-community-heading">
          <div>
            <span className="cc-community-section-label">
              THE CAMPUS CONVERSATION
            </span>
            <h2>Community feed</h2>
          </div>

          <span className="cc-community-post-count">
            {count} {count === 1 ? "post" : "posts"}
          </span>
        </div>

        {error && (
          <div className="cc-community-alert cc-community-error">
            <span>{error}</span>
            <button
              type="button"
              onClick={() => setError("")}
              aria-label="Dismiss error"
            >
              <X size={17} />
            </button>
          </div>
        )}

        {success && (
          <div className="cc-community-alert cc-community-success">
            <span>{success}</span>
            <button
              type="button"
              onClick={() => setSuccess("")}
              aria-label="Dismiss message"
            >
              <X size={17} />
            </button>
          </div>
        )}

        <section className="cc-create-post">
          <div className="cc-create-post-heading">
            <div className="cc-avatar cc-avatar-current">
              {getInitials(
                user?.first_name || user?.username || "Student",
              )}
            </div>

            <div>
              <strong>
                {isAuthenticated
                  ? `What's happening, ${user?.first_name || user?.username}?`
                  : "Join the conversation"}
              </strong>
              <span>Share something with your campus community.</span>
            </div>
          </div>

          {isAuthenticated ? (
            <form onSubmit={handleCreatePost}>
              <textarea
                value={content}
                onChange={(event) => setContent(event.target.value)}
                placeholder="What's on your mind?"
                rows={3}
                maxLength={3000}
              />

              {imagePreview && (
                <div className="cc-post-image-preview">
                  <img src={imagePreview} alt="Selected post preview" />
                  <button
                    type="button"
                    onClick={() => {
                      setImage(null);
                      setImagePreview("");
                    }}
                    aria-label="Remove selected image"
                  >
                    <X size={18} />
                  </button>
                </div>
              )}

              <div className="cc-create-post-actions">
                <label className="cc-add-image">
                  <ImagePlus size={18} />
                  Add image
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageChange}
                  />
                </label>

                <button
                  type="submit"
                  className="cc-post-submit"
                  disabled={
                    isSubmitting || (!content.trim() && !image)
                  }
                >
                  {isSubmitting ? (
                    <LoaderCircle size={17} className="cc-spinning" />
                  ) : (
                    <Send size={16} />
                  )}
                  {isSubmitting ? "Publishing..." : "Publish post"}
                </button>
              </div>
            </form>
          ) : (
            <div className="cc-community-join">
              <p>Log in to share your thoughts and interact with students.</p>
              <Link to="/login">Log in to post</Link>
            </div>
          )}
        </section>

        <div className="cc-post-feed">
          {isLoading ? (
            <div className="cc-community-loading">
              <LoaderCircle size={30} className="cc-spinning" />
              <span>Loading campus conversations...</span>
            </div>
          ) : posts.length === 0 ? (
            <div className="cc-community-empty">
              <div>
                <MessageCircle size={35} />
              </div>
              <h3>It's quiet around here.</h3>
              <p>Be the first to start a conversation with your campus.</p>
            </div>
          ) : (
            posts.map((post) => (
              <article className="cc-post-card" key={post.id}>
                <div className="cc-post-header">
                  <div className="cc-avatar">
                    {getInitials(post.author_username)}
                  </div>

                  <div className="cc-post-author">
                    <strong>{post.author_username}</strong>
                    <span>{formatDate(post.created_at)}</span>
                  </div>

                  {user?.username === post.author_username && (
                    <button
                      type="button"
                      className="cc-post-delete"
                      onClick={() => handleDeletePost(post.id)}
                      aria-label="Delete post"
                      title="Delete post"
                    >
                      <Trash2 size={17} />
                    </button>
                  )}
                </div>

                {post.content && (
                  <p className="cc-post-content">{post.content}</p>
                )}

                {post.image && (
                  <div className="cc-post-image">
                    <img
                      src={getImageUrl(post.image)}
                      alt="Post attachment"
                      loading="lazy"
                    />
                  </div>
                )}

                <div className="cc-post-stats">
                  <span>{post.likes_count} likes</span>
                  <span>
                    {post.comments_count}{" "}
                    {post.comments_count === 1 ? "comment" : "comments"}
                  </span>
                </div>

                <div className="cc-post-actions">
                  <button
                    type="button"
                    className={post.is_liked ? "cc-post-liked" : ""}
                    onClick={() => handleLike(post.id)}
                  >
                    <Heart
                      size={19}
                      fill={post.is_liked ? "currentColor" : "none"}
                    />
                    Like
                  </button>

                  <button
                    type="button"
                    onClick={() => toggleComments(post.id)}
                  >
                    <MessageCircle size={19} />
                    Comment
                  </button>
                </div>

                {expandedPost === post.id && (
                  <div className="cc-comments-section">
                    <div className="cc-comments-list">
                      {(comments[post.id] ?? []).map((comment) => (
                        <div className="cc-comment" key={comment.id}>
                          <div className="cc-avatar cc-avatar-small">
                            {getInitials(comment.author_username)}
                          </div>
                          <div className="cc-comment-body">
                            <div className="cc-comment-bubble">
                              <strong>{comment.author_username}</strong>
                              <p>{comment.content}</p>
                            </div>
                            <span>{formatDate(comment.created_at)}</span>
                          </div>
                        </div>
                      ))}

                      {comments[post.id]?.length === 0 && (
                        <p className="cc-no-comments">
                          No comments yet. Start the conversation.
                        </p>
                      )}
                    </div>

                    {isAuthenticated ? (
                      <form
                        className="cc-comment-form"
                        onSubmit={(event) =>
                          handleComment(event, post.id)
                        }
                      >
                        <input
                          type="text"
                          value={commentInputs[post.id] ?? ""}
                          onChange={(event) =>
                            setCommentInputs((current) => ({
                              ...current,
                              [post.id]: event.target.value,
                            }))
                          }
                          placeholder="Write a comment..."
                          maxLength={2000}
                        />
                        <button
                          type="submit"
                          disabled={
                            isCommenting ||
                            !commentInputs[post.id]?.trim()
                          }
                          aria-label="Send comment"
                        >
                          <Send size={17} />
                        </button>
                      </form>
                    ) : (
                      <p className="cc-comment-login">
                        <Link to="/login">Log in</Link> to leave a comment.
                      </p>
                    )}
                  </div>
                )}
              </article>
            ))
          )}
        </div>

        {!isLoading && posts.length > 0 && (
          <div className="cc-community-pagination">
            <button
              type="button"
              disabled={!previousPage}
              onClick={() => setPage((current) => current - 1)}
            >
              <ChevronLeft size={18} />
              Previous
            </button>

            <span>Page {page}</span>

            <button
              type="button"
              disabled={!nextPage}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
              <ChevronRight size={18} />
            </button>
          </div>
        )}
      </section>
    </main>
  );
};

export default CommunityPage;
