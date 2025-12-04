import Features from "../components/landing/Features";
import Footer from "../components/landing/Footer";
import Hero from "../components/landing/Hero";
import Navbar from "../components/landing/Navbar";
import SpaceBackground from "../components/landing/SpaceBackground";

const LandingPage = () => {
  return (
    <div className="relative min-h-screen overflow-x-hidden">
      {/* Space Background with Mouse Spotlight */}
      <SpaceBackground backgroundImage="/space-bg.jpg" />

      {/* Content Layer */}
      <div className="relative z-10">
        {/* Navigation */}
        <Navbar />

        {/* Hero Section */}
        <Hero />

        {/* Features Section */}
        <Features />

        {/* Footer */}
        <Footer />
      </div>
    </div>
  );
};

export default LandingPage;
