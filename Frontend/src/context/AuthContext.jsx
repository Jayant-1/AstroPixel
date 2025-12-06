import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import api from "../services/api";

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};

const TOKEN_KEY = "astropixel_token";
const USER_KEY = "astropixel_user";

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const clearAuthData = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  };

  const saveAuthData = (newToken, newUser) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    localStorage.setItem(USER_KEY, JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
  };

  // Initialize auth state from localStorage
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem(TOKEN_KEY);
      const storedUser = localStorage.getItem(USER_KEY);

      if (storedToken && storedUser) {
        try {
          const parsedUser = JSON.parse(storedUser);
          setToken(storedToken);
          setUser(parsedUser);

          // Verify token is still valid
          try {
            const userData = await api.verifyToken(storedToken);
            setUser(userData);
            localStorage.setItem(USER_KEY, JSON.stringify(userData));
          } catch (err) {
            console.error("Token verification failed:", err);
            clearAuthData();
          }
        } catch (e) {
          console.error("Failed to parse stored user:", e);
          clearAuthData();
        }
      }

      setLoading(false);
    };

    initAuth();
  }, []);

  const register = useCallback(async (email, username, password, fullName) => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.register({
        email,
        username,
        password,
        full_name: fullName,
      });

      saveAuthData(response.access_token, response.user);

      return response.user;
    } catch (err) {
      const errorMessage = err.response?.data?.detail || "Registration failed";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (email, password) => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.login({ email, password });

      saveAuthData(response.access_token, response.user);

      return response.user;
    } catch (err) {
      const errorMessage = err.response?.data?.detail || "Login failed";
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      if (token) {
        await api.logout(token);
      }
    } catch (err) {
      console.error("Logout API call failed:", err);
    } finally {
      clearAuthData();
    }
  }, [token]);

  const updateProfile = useCallback(
    async (updates) => {
      try {
        setLoading(true);
        setError(null);

        const updatedUser = await api.updateProfile(updates, token);

        setUser(updatedUser);
        localStorage.setItem(USER_KEY, JSON.stringify(updatedUser));

        return updatedUser;
      } catch (err) {
        const errorMessage =
          err.response?.data?.detail || "Profile update failed";
        setError(errorMessage);
        throw new Error(errorMessage);
      } finally {
        setLoading(false);
      }
    },
    [token]
  );

  const refreshToken = useCallback(async () => {
    try {
      if (!token) return;

      const response = await api.refreshToken(token);
      saveAuthData(response.access_token, response.user);

      return response.access_token;
    } catch (err) {
      console.error("Token refresh failed:", err);
      clearAuthData();
      throw err;
    }
  }, [token]);

  const value = {
    user,
    token,
    loading,
    error,
    isAuthenticated: !!user && !!token,
    register,
    login,
    logout,
    updateProfile,
    refreshToken,
    clearError: () => setError(null),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;
