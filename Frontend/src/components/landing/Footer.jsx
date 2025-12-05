import { motion } from "framer-motion";
import { Github, Linkedin, Mail, Globe } from "lucide-react";
import { Link } from "react-router-dom";

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <motion.footer
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6 }}
      className="relative py-16 px-4"
    >
      <div className="max-w-7xl mx-auto">
        <div className="glass-panel p-8 md:p-12">
          <div className="flex flex-col md:flex-row items-center justify-between gap-8">
            {/* Brand */}
            <div className="text-center md:text-left">
              <Link to="/" className="flex items-center justify-center md:justify-start gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-400 to-pink-400 flex items-center justify-center">
                  <span className="text-white text-xl">✦</span>
                </div>
                <span className="text-2xl font-bold gradient-text">
                  AstroPixel
                </span>
              </Link>
              <p className="text-zinc-400">
                Explore the Universe, One Pixel at a Time
              </p>
            </div>

            {/* Footer Links */}
            <div className="flex flex-wrap justify-center gap-6 text-zinc-400">
              <Link to="/docs" className="hover:text-white transition-colors">
                Docs
              </Link>
              <Link to="/about" className="hover:text-white transition-colors">
                About
              </Link>
              <Link to="/contact" className="hover:text-white transition-colors">
                Contact
              </Link>
              <Link to="/dashboard" className="hover:text-white transition-colors">
                Dashboard
              </Link>
            </div>

            {/* Social Links */}
            <div className="flex items-center gap-4">
              <a
                href="https://github.com/Jayant-1/AstroPixel"
                target="_blank"
                rel="noopener noreferrer"
                className="glass-panel glass-panel-hover p-3 hover:scale-110 transition-all duration-300"
              >
                <Github className="text-zinc-300 hover:text-white" size={20} />
              </a>
              <a
                href="https://www.linkedin.com/in/jayant-potdar-880a461b8/"
                target="_blank"
                rel="noopener noreferrer"
                className="glass-panel glass-panel-hover p-3 hover:scale-110 transition-all duration-300"
              >
                <Linkedin className="text-zinc-300 hover:text-white" size={20} />
              </a>
              <a
                href="http://jayant-1.vercel.app/"
                target="_blank"
                rel="noopener noreferrer"
                className="glass-panel glass-panel-hover p-3 hover:scale-110 transition-all duration-300"
              >
                <Globe className="text-zinc-300 hover:text-white" size={20} />
              </a>
              <a
                href="mailto:jayantpotdar2006@gmail.com"
                className="glass-panel glass-panel-hover p-3 hover:scale-110 transition-all duration-300"
              >
                <Mail className="text-zinc-300 hover:text-white" size={20} />
              </a>
            </div>
          </div>

          {/* Divider */}
          <div className="my-8 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />

          {/* Copyright */}
          <div className="text-center">
            <p className="text-zinc-500 text-sm">
              © {currentYear} AstroPixel. Built with 💜 by Jayant Potdar
            </p>
          </div>
        </div>
      </div>
    </motion.footer>
  );
};

export default Footer;
