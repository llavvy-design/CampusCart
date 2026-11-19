const REFRESH_TOKEN_KEY = "campuscart_refresh_token";

let accessToken = null;

export const tokenStore = {
  getAccessToken() {
    return accessToken;
  },

  setAccessToken(token) {
    accessToken = token;
  },

  getRefreshToken() {
    return sessionStorage.getItem(REFRESH_TOKEN_KEY);
  },

  setRefreshToken(token) {
    if (token) {
      sessionStorage.setItem(REFRESH_TOKEN_KEY, token);
    } else {
      sessionStorage.removeItem(REFRESH_TOKEN_KEY);
    }
  },

  clear() {
    accessToken = null;
    sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};
