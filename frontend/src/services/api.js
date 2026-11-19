import axios from "axios";
import { tokenStore } from "./tokenStore";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;
const API_BASE_URL = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const paymentApi = axios.create({
  baseURL: BACKEND_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

const attachAccessToken = (config) => {
  const accessToken = tokenStore.getAccessToken();

  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }

  if (
    typeof FormData !== "undefined" &&
    config.data instanceof FormData
  ) {
    config.headers.delete("Content-Type");
  }

  return config;
};

api.interceptors.request.use(attachAccessToken);
paymentApi.interceptors.request.use(attachAccessToken);

let refreshPromise = null;

const refreshAccessToken = async () => {
  const refreshToken = tokenStore.getRefreshToken();

  if (!refreshToken) {
    throw new Error("No refresh token is available.");
  }

  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${API_BASE_URL}/accounts/token/refresh/`, {
        refresh: refreshToken,
      })
      .then((response) => {
        const { access, refresh } = response.data;

        tokenStore.setAccessToken(access);

        if (refresh) {
          tokenStore.setRefreshToken(refresh);
        }

        return access;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
};

const createUnauthorizedHandler = (client) => async (error) => {
  const originalRequest = error.config;

  if (
    error.response?.status !== 401 ||
    !originalRequest ||
    originalRequest._retry ||
    originalRequest.url?.includes("/accounts/login/") ||
    originalRequest.url?.includes("/accounts/token/refresh/")
  ) {
    return Promise.reject(error);
  }

  originalRequest._retry = true;

  try {
    const newAccessToken = await refreshAccessToken();

    originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;

    return client(originalRequest);
  } catch (refreshError) {
    tokenStore.clear();

    window.dispatchEvent(new Event("campuscart:session-expired"));

    return Promise.reject(refreshError);
  }
};

api.interceptors.response.use(
  (response) => response,
  createUnauthorizedHandler(api),
);

paymentApi.interceptors.response.use(
  (response) => response,
  createUnauthorizedHandler(paymentApi),
);

export const getApiErrorMessage = (error) => {
  const data = error.response?.data;

  if (!data) {
    return "Unable to connect to CampusCart. Please check your connection.";
  }

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (typeof data.error === "string") {
    return data.error;
  }

  if (typeof data.message === "string") {
    return data.message;
  }

  if (typeof data === "object") {
    return Object.entries(data)
      .map(([field, messages]) => {
        const message = Array.isArray(messages)
          ? messages.join(" ")
          : String(messages);

        return `${field}: ${message}`;
      })
      .join(" ");
  }

  return "Something went wrong. Please try again.";
};
