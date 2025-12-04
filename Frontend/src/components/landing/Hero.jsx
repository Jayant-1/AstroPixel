import { motion } from "framer-motion";
import { Github, Telescope } from "lucide-react";
import { Link } from "react-router-dom";

const Hero = () => {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
        delayChildren: 0.3,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.6, ease: "easeOut" },
    },
  };

  return (
    <section className="relative min-h-screen flex items-center justify-center pt-24 pb-16 px-4">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="max-w-5xl mx-auto text-center"
      >
        {/* Badge */}
        <motion.div variants={itemVariants} className="mb-8">
          <span className="glass-panel inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-zinc-200">
            <span className="text-lg">🌌</span>
            Explore the Cosmos in High Resolution
          </span>
        </motion.div>

        {/* Main Heading */}
        <motion.h1
          variants={itemVariants}
          className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6"
        >
          <span className="gradient-text">AstroPixel</span>
        </motion.h1>

        {/* Subheading */}
        <motion.p
          variants={itemVariants}
          className="text-lg md:text-xl text-zinc-300 leading-relaxed max-w-3xl mx-auto mb-10"
        >
          A powerful platform for astronomical imagery exploration. Pan, zoom,
          and annotate high-resolution celestial images with ease.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div
          variants={itemVariants}
          className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12"
        >
          {/* Primary CTA */}
          <Link
            to="/dashboard"
            className="gradient-button px-8 py-4 rounded-xl text-white font-semibold text-lg shadow-lg hover:shadow-nebula-purple/30 transition-all duration-300"
          >
            Start Exploring
          </Link>

          {/* Find Space Dataset */}
          <a
            href="https://esahubble.org/images/"
            target="_blank"
            rel="noopener noreferrer"
            className="glass-panel glass-panel-hover px-6 py-4 text-white font-medium inline-flex items-center gap-2 hover:scale-105 transition-all duration-300"
          >
            <Telescope size={20} />
            Find Space Dataset
          </a>

          {/* GitHub CTA */}
          <a
            href="https://github.com/Jayant-1/AstroPixel"
            target="_blank"
            rel="noopener noreferrer"
            className="glass-panel glass-panel-hover px-6 py-4 text-white font-medium inline-flex items-center gap-2 hover:scale-105 transition-all duration-300"
          >
            <Github size={20} />
            View on GitHub
          </a>
        </motion.div>

        {/* Info Banner */}
        <motion.div variants={itemVariants} className="mt-16">
          <div className="glass-panel inline-block px-8 py-4">
            <p className="text-white font-semibold mb-1">
              Journey Through the Stars
            </p>
            <p className="text-zinc-400 text-sm">
              High-resolution tiles, smooth controls, and rich overlays
            </p>
          </div>
        </motion.div>
      </motion.div>
    </section>
  );
};

export default Hero;
