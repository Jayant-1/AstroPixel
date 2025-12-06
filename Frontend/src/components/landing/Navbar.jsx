import { motion } from "framer-motion";
import { LogIn, Menu, User, X } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { isAuthenticated, user } = useAuth();

  const navLinks = [
    { name: "Features", href: "/#features", isHash: true },
    { name: "Docs", href: "/docs", isHash: false },
    { name: "About", href: "/about", isHash: false },
    { name: "Contact", href: "/contact", isHash: false },
  ];

  return (
    <motion.nav
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="fixed top-0 left-0 right-0 z-50"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="glass-panel mt-4 px-6 py-3">
          <div className="flex items-center justify-between">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 group">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-400 to-pink-400 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                <span className="text-white text-xl">✦</span>
              </div>
              <span className="text-xl font-bold text-white">AstroPixel</span>
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center gap-8">
              {navLinks.map((link) =>
                link.isHash ? (
                  <a
                    key={link.name}
                    href={link.href}
                    className="text-zinc-300 hover:text-white font-medium transition-colors duration-300 relative group"
                  >
                    {link.name}
                    <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-gradient-to-r from-sky-400 to-pink-400 group-hover:w-full transition-all duration-300" />
                  </a>
                ) : (
                  <Link
                    key={link.name}
                    to={link.href}
                    className="text-zinc-300 hover:text-white font-medium transition-colors duration-300 relative group"
                  >
                    {link.name}
                    <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-gradient-to-r from-sky-400 to-pink-400 group-hover:w-full transition-all duration-300" />
                  </Link>
                )
              )}
            </div>

            {/* Auth & CTA Buttons */}
            <div className="hidden md:flex items-center gap-3">
              {isAuthenticated ? (
                <>
                  <Link
                    to="/dashboard"
                    className="flex items-center gap-2 text-zinc-300 hover:text-white font-medium transition-colors"
                  >
                    <User className="w-4 h-4" />
                    {user?.username || "Profile"}
                  </Link>
                  <Link
                    to="/dashboard"
                    className="glass-panel glass-panel-hover px-5 py-2.5 text-white font-medium hover:scale-105 transition-all duration-300 inline-flex items-center gap-2"
                  >
                    <span>Dashboard</span>
                    <span className="text-lg">🚀</span>
                  </Link>
                </>
              ) : (
                <>
                  <Link
                    to="/login"
                    className="flex items-center gap-2 text-zinc-300 hover:text-white font-medium transition-colors px-4 py-2"
                  >
                    <LogIn className="w-4 h-4" />
                    Sign in
                  </Link>
                  <Link
                    to="/signup"
                    className="glass-panel glass-panel-hover px-5 py-2.5 text-white font-medium hover:scale-105 transition-all duration-300 inline-flex items-center gap-2"
                  >
                    <span>Get Started</span>
                  </Link>
                </>
              )}
            </div>

            {/* Mobile Menu Button */}
            <button
              className="md:hidden text-white p-2"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
            >
              {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>

          {/* Mobile Menu */}
          {isMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="md:hidden mt-4 pt-4 border-t border-white/10"
            >
              <div className="flex flex-col gap-4">
                {navLinks.map((link) =>
                  link.isHash ? (
                    <a
                      key={link.name}
                      href={link.href}
                      className="text-zinc-300 hover:text-white font-medium transition-colors"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      {link.name}
                    </a>
                  ) : (
                    <Link
                      key={link.name}
                      to={link.href}
                      className="text-zinc-300 hover:text-white font-medium transition-colors"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      {link.name}
                    </Link>
                  )
                )}
                <div className="border-t border-white/10 pt-4 mt-2 flex flex-col gap-3">
                  {isAuthenticated ? (
                    <Link
                      to="/dashboard"
                      className="glass-panel glass-panel-hover px-5 py-2.5 text-white font-medium text-center"
                      onClick={() => setIsMenuOpen(false)}
                    >
                      Dashboard 🚀
                    </Link>
                  ) : (
                    <>
                      <Link
                        to="/login"
                        className="text-zinc-300 hover:text-white font-medium text-center py-2"
                        onClick={() => setIsMenuOpen(false)}
                      >
                        Sign in
                      </Link>
                      <Link
                        to="/signup"
                        className="glass-panel glass-panel-hover px-5 py-2.5 text-white font-medium text-center"
                        onClick={() => setIsMenuOpen(false)}
                      >
                        Get Started
                      </Link>
                    </>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </motion.nav>
  );
};

export default Navbar;
