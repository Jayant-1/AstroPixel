import { AlertCircle, Eye, EyeOff, Lock, LogIn, Telescope } from "lucide-react";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import { useAuth } from "../context/AuthContext";

const LoginPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, loading, error, clearError } = useAuth();

  const [loginMode, setLoginMode] = useState("user"); // "user" or "admin"
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    adminPassword: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState("");
  const [adminLoading, setAdminLoading] = useState(false);

  // Get redirect path from location state or default to dashboard
  const from = location.state?.from?.pathname || "/dashboard";

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setFormError("");
    clearError();
  };

  const handleUserSubmit = async (e) => {
    e.preventDefault();
    setFormError("");

    // Validation
    if (!formData.email || !formData.password) {
      setFormError("Please fill in all fields");
      return;
    }

    try {
      await login(formData.email, formData.password);
      navigate(from, { replace: true });
    } catch (err) {
      setFormError(err.message);
    }
  };

  const handleAdminSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    setAdminLoading(true);

    if (!formData.adminPassword) {
      setFormError("Please enter the admin password");
      setAdminLoading(false);
      return;
    }

    try {
      // Use shared auth flow so context state updates immediately
      const adminUser = await login(
        "admin@astropixel.local",
        formData.adminPassword
      );

      if (adminUser?.username !== "Admin") {
        setFormError("Only the Admin user can access the admin panel");
        return;
      }

      navigate("/admin", { replace: true });
    } catch (err) {
      const errorMsg =
        err.response?.data?.detail || err.message || "Admin login failed";
      setFormError(errorMsg);
    } finally {
      setAdminLoading(false);
    }
  };

  const handleModeSwitch = (mode) => {
    setLoginMode(mode);
    setFormData({
      email: "",
      password: "",
      adminPassword: "",
    });
    setFormError("");
    clearError();
  };

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        {/* Logo */}
        <Link to="/" className="flex justify-center items-center gap-3 mb-8">
          <div className="w-12 h-12 bg-gradient-to-br from-blue-500 via-purple-600 to-pink-500 rounded-xl flex items-center justify-center">
            <Telescope className="w-6 h-6 text-white" />
          </div>
          <span className="text-2xl font-bold text-white">AstroPixel</span>
        </Link>

        <h2 className="text-center text-3xl font-bold text-white">
          {loginMode === "user" ? "Welcome back" : "Admin Panel"}
        </h2>
        <p className="mt-2 text-center text-sm text-gray-400">
          {loginMode === "user"
            ? "Don't have an account? "
            : "Restricted access only"}
          {loginMode === "user" && (
            <Link
              to="/signup"
              className="font-medium text-blue-400 hover:text-blue-300 transition-colors"
            >
              Sign up for free
            </Link>
          )}
        </p>

        {/* Mode Tabs */}
        <div className="mt-6 flex gap-2 bg-gray-800/50 p-1 rounded-lg">
          <button
            onClick={() => handleModeSwitch("user")}
            className={`flex-1 py-2 px-4 rounded-md font-medium transition-all ${
              loginMode === "user"
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:text-gray-300"
            }`}
          >
            User Login
          </button>
          <button
            onClick={() => handleModeSwitch("admin")}
            className={`flex-1 py-2 px-4 rounded-md font-medium transition-all flex items-center justify-center gap-2 ${
              loginMode === "admin"
                ? "bg-red-600 text-white"
                : "text-gray-400 hover:text-gray-300"
            }`}
          >
            <Lock className="w-4 h-4" />
            Admin
          </button>
        </div>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="bg-gray-900 border border-gray-800 py-8 px-6 shadow-xl rounded-2xl sm:px-10">
          {loginMode === "user" ? (
            // User Login Form
            <form className="space-y-6" onSubmit={handleUserSubmit}>
              {/* Error Alert */}
              {(formError || error) && (
                <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-400">{formError || error}</p>
                </div>
              )}

              {/* Email */}
              <div>
                <label
                  htmlFor="email"
                  className="block text-sm font-medium text-gray-300 mb-2"
                >
                  Email address
                </label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="you@example.com"
                  className="w-full"
                />
              </div>

              {/* Password */}
              <div>
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-gray-300 mb-2"
                >
                  Password
                </label>
                <div className="relative">
                  <Input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    required
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="••••••••"
                    className="w-full pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-300"
                  >
                    {showPassword ? (
                      <EyeOff className="w-5 h-5" />
                    ) : (
                      <Eye className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center items-center gap-2"
              >
                {loading ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <LogIn className="w-5 h-5" />
                    Sign in
                  </>
                )}
              </Button>
            </form>
          ) : (
            // Admin Login Form
            <form className="space-y-6" onSubmit={handleAdminSubmit}>
              {/* Error Alert */}
              {formError && (
                <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-400">{formError}</p>
                </div>
              )}

              {/* Admin Password */}
              <div>
                <label
                  htmlFor="adminPassword"
                  className="block text-sm font-medium text-gray-300 mb-2"
                >
                  Password
                </label>
                <div className="relative">
                  <Input
                    id="adminPassword"
                    name="adminPassword"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    required
                    value={formData.adminPassword}
                    onChange={handleChange}
                    placeholder="••••••••"
                    className="w-full pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-300"
                  >
                    {showPassword ? (
                      <EyeOff className="w-5 h-5" />
                    ) : (
                      <Eye className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                disabled={adminLoading}
                className="w-full flex justify-center items-center gap-2 bg-red-600 hover:bg-red-700"
              >
                {adminLoading ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    <Lock className="w-5 h-5" />
                    Admin Login
                  </>
                )}
              </Button>
            </form>
          )}

          {/* Divider - Only show for user mode */}
          {loginMode === "user" && (
            <>
              <div className="mt-6">
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-gray-700" />
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-2 bg-gray-900 text-gray-400">
                      Or continue as
                    </span>
                  </div>
                </div>

                <div className="mt-6">
                  <Link to="/dashboard">
                    <Button variant="outline" className="w-full">
                      Guest (View Only)
                    </Button>
                  </Link>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
