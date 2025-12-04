import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import ErrorBoundary from "./components/common/ErrorBoundary";
import Layout from "./components/layout/Layout";
import { AppProvider } from "./context/AppContext";
import AboutPage from "./pages/AboutPage";
import ContactPage from "./pages/ContactPage";
import DocsPage from "./pages/DocsPage";
import Home from "./pages/Home";
import LandingPage from "./pages/LandingPage";
import NotFound from "./pages/NotFound";
import Viewer from "./pages/Viewer";

function App() {
  return (
    <ErrorBoundary>
      <AppProvider>
        <Routes>
          {/* Landing Page - No Layout wrapper */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/docs" element={<DocsPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/contact" element={<ContactPage />} />

          {/* App Routes with Layout */}
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<Home />} />
            <Route path="viewer/:datasetId" element={<Viewer />} />
            <Route path="404" element={<NotFound />} />
            <Route path="*" element={<Navigate to="/404" replace />} />
          </Route>
        </Routes>
      </AppProvider>
    </ErrorBoundary>
  );
}

export default App;
