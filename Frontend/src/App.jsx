import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import ErrorBoundary from "./components/common/ErrorBoundary";
import ProtectedRoute from "./components/common/ProtectedRoute";
import Layout from "./components/layout/Layout";
import { AppProvider } from "./context/AppContext";
import { AuthProvider } from "./context/AuthContext";
import AboutPage from "./pages/AboutPage";
import AdminPanel from "./pages/AdminPanel";
import ContactPage from "./pages/ContactPage";
import DocsPage from "./pages/DocsPage";
import Home from "./pages/Home";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import NotFound from "./pages/NotFound";
import SignupPage from "./pages/SignupPage";
import Viewer from "./pages/Viewer";

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AppProvider>
          <Routes>
            {/* Landing Page - No Layout wrapper */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/docs" element={<DocsPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/contact" element={<ContactPage />} />

            {/* Auth Routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />

            {/* Protected Admin Route */}
            <Route
              path="/admin"
              element={
                <ProtectedRoute requireAdmin={true}>
                  <AdminPanel />
                </ProtectedRoute>
              }
            />

            {/* App Routes with Layout */}
            <Route element={<Layout />}>
              <Route path="/dashboard" element={<Home />} />
              <Route path="viewer/:datasetId" element={<Viewer />} />
              <Route path="404" element={<NotFound />} />
              <Route path="*" element={<Navigate to="/404" replace />} />
            </Route>
          </Routes>
        </AppProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
