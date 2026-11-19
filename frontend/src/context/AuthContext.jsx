import {
  useCallback,
  useEffect,
  useState,
} from "react";

import { AuthContext } from "./authContextDefinition";
import { api } from "../services/api";
import { tokenStore } from "../services/tokenStore";

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadProfile = useCallback(async () => {
    const response = await api.get("/accounts/profile/");

    setProfile(response.data);
    setUser(response.data);

    return response.data;
  }, []);

  // Restore the user's session when the application starts.
  useEffect(() => {
    let isMounted = true;

    const restoreSession = async () => {
      const refreshToken = tokenStore.getRefreshToken();

      if (!refreshToken) {
        if (isMounted) {
          setIsLoading(false);
        }
        return;
      }

      try {
        const response = await api.post("/accounts/token/refresh/", {
          refresh: refreshToken,
        });

        const { access, refresh } = response.data;

        tokenStore.setAccessToken(access);

        if (refresh) {
          tokenStore.setRefreshToken(refresh);
        }

        const profileResponse = await api.get("/accounts/profile/");

        if (isMounted) {
          setProfile(profileResponse.data);
          setUser(profileResponse.data);
        }
      } catch {
        tokenStore.clear();

        if (isMounted) {
          setUser(null);
          setProfile(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    restoreSession();

    return () => {
      isMounted = false;
    };
  }, []);

  // Respond when the API client reports an expired session.
  useEffect(() => {
    const handleSessionExpired = () => {
      tokenStore.clear();
      setUser(null);
      setProfile(null);
    };

    window.addEventListener(
      "campuscart:session-expired",
      handleSessionExpired,
    );

    return () => {
      window.removeEventListener(
        "campuscart:session-expired",
        handleSessionExpired,
      );
    };
  }, []);

  // Log in.
  const login = async ({ username, password }) => {
    const response = await api.post("/accounts/login/", {
      username,
      password,
    });

    tokenStore.setAccessToken(response.data.access);
    tokenStore.setRefreshToken(response.data.refresh);

    try {
      await loadProfile();
    } catch (error) {
      tokenStore.clear();
      setUser(null);
      setProfile(null);
      throw error;
    }

    return response.data;
  };

  // Register and automatically log in.
  const register = async (registrationData) => {
    await api.post("/accounts/register/", registrationData);

    return login({
      username: registrationData.username,
      password: registrationData.password,
    });
  };

  // Update the user's profile.
  const updateProfile = async (profileData) => {
    const response = await api.patch(
      "/accounts/profile/",
      profileData,
    );

    setProfile(response.data);
    setUser(response.data);

    return response.data;
  };

  // Log out.
  const logout = async () => {
    const refreshToken = tokenStore.getRefreshToken();

    try {
      if (refreshToken) {
        await api.post("/accounts/logout/", {
          refresh: refreshToken,
        });
      }
    } finally {
      tokenStore.clear();
      setUser(null);
      setProfile(null);
    }
  };

  const value = {
    user,
    profile,
    isLoading,
    isAuthenticated: Boolean(user),
    login,
    register,
    logout,
    loadProfile,
    updateProfile,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
