import { motion } from "framer-motion";
import {
  BookOpen,
  Download,
  FileText,
  Image,
  Layers,
  MousePointer,
  PenTool,
  Settings,
  Upload,
  ZoomIn,
} from "lucide-react";
import { Link } from "react-router-dom";
import Footer from "../components/landing/Footer";
import Navbar from "../components/landing/Navbar";
import SpaceBackground from "../components/landing/SpaceBackground";

const sections = [
  {
    title: "Getting Started",
    icon: Upload,
    items: [
      {
        title: "Upload Images",
        description:
          "Upload TIFF, PNG, JPEG, or FITS images. Large images are automatically tiled for smooth viewing.",
      },
      {
        title: "Find Datasets",
        description:
          "Visit ESA Hubble (esahubble.org/images/) to download high-resolution astronomical TIFF images.",
      },
      {
        title: "Dataset Categories",
        description:
          "Organize your images into categories like Earth, Mars, Deep Space, or create custom categories.",
      },
    ],
  },
  {
    title: "Navigation Controls",
    icon: MousePointer,
    items: [
      {
        title: "Zoom",
        description:
          "Use mouse wheel to zoom in/out. Double-click to zoom into a specific area.",
      },
      {
        title: "Pan",
        description:
          "Click and drag to move around the image. Use the navigator minimap in the corner.",
      },
      {
        title: "Keyboard Shortcuts",
        description:
          "Press + and - to zoom, arrow keys to pan, Home to reset view.",
      },
    ],
  },
  {
    title: "Annotations",
    icon: PenTool,
    items: [
      {
        title: "Point Annotations",
        description:
          "Click to place point markers on celestial objects of interest.",
      },
      {
        title: "Rectangle Annotations",
        description:
          "Draw rectangles to highlight regions like galaxies or nebulae.",
      },
      {
        title: "Circle Annotations",
        description:
          "Create circular annotations for stars or planetary objects.",
      },
      {
        title: "Labels & Colors",
        description:
          "Add descriptive labels and choose colors for your annotations.",
      },
    ],
  },
  {
    title: "Export & Share",
    icon: Download,
    items: [
      {
        title: "Export Annotations",
        description:
          "Export your annotations as JSON for backup or sharing with others.",
      },
      {
        title: "Image Export",
        description:
          "Export the current view with annotations as an image file.",
      },
    ],
  },
];

const supportedFormats = [
  { name: "TIFF", description: "High-resolution astronomical images" },
  { name: "PNG", description: "Lossless compressed images" },
  { name: "JPEG", description: "Standard compressed images" },
  { name: "FITS", description: "Flexible Image Transport System" },
];

const DocsPage = () => {
  return (
    <div className="relative min-h-screen overflow-x-hidden">
      <SpaceBackground backgroundImage="/space-bg.jpg" />

      <div className="relative z-10">
        <Navbar />

        {/* Hero */}
        <section className="pt-32 pb-16 px-4">
          <div className="max-w-5xl mx-auto text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <div className="inline-flex items-center gap-3 mb-6">
                <BookOpen className="text-nebula-purple" size={40} />
                <h1 className="text-4xl md:text-5xl font-extrabold">
                  <span className="gradient-text">Documentation</span>
                </h1>
              </div>
              <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
                Everything you need to know to get started with AstroPixel
              </p>
            </motion.div>
          </div>
        </section>

        {/* Quick Start */}
        <section className="py-12 px-4">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="glass-panel p-8"
            >
              <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                <span className="text-2xl">🚀</span> Quick Start
              </h2>
              <ol className="space-y-4 text-zinc-300">
                <li className="flex items-start gap-3">
                  <span className="w-8 h-8 rounded-full bg-nebula-purple/20 text-nebula-purple flex items-center justify-center font-bold shrink-0">
                    1
                  </span>
                  <div>
                    <strong className="text-white">Go to Dashboard</strong> -
                    Click "Launch App" or navigate to /dashboard
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className="w-8 h-8 rounded-full bg-nebula-purple/20 text-nebula-purple flex items-center justify-center font-bold shrink-0">
                    2
                  </span>
                  <div>
                    <strong className="text-white">Upload an Image</strong> -
                    Drag & drop or click to upload astronomical images
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className="w-8 h-8 rounded-full bg-nebula-purple/20 text-nebula-purple flex items-center justify-center font-bold shrink-0">
                    3
                  </span>
                  <div>
                    <strong className="text-white">Explore</strong> - Pan, zoom,
                    and annotate your images
                  </div>
                </li>
              </ol>
              <div className="mt-6">
                <Link
                  to="/dashboard"
                  className="gradient-button px-6 py-3 rounded-lg text-white font-semibold inline-flex items-center gap-2"
                >
                  Start Exploring
                </Link>
              </div>
            </motion.div>
          </div>
        </section>

        {/* Documentation Sections */}
        {sections.map((section, sectionIndex) => (
          <section key={section.title} className="py-12 px-4">
            <div className="max-w-5xl mx-auto">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: sectionIndex * 0.1 }}
              >
                <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-nebula-purple/20 text-nebula-purple">
                    <section.icon size={24} />
                  </div>
                  {section.title}
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {section.items.map((item, itemIndex) => (
                    <motion.div
                      key={item.title}
                      initial={{ opacity: 0, y: 10 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true }}
                      transition={{ delay: itemIndex * 0.05 }}
                      className="glass-panel glass-panel-hover p-5"
                    >
                      <h3 className="text-lg font-semibold text-white mb-2">
                        {item.title}
                      </h3>
                      <p className="text-zinc-400 text-sm">
                        {item.description}
                      </p>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            </div>
          </section>
        ))}

        {/* Supported Formats */}
        <section className="py-12 px-4">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
            >
              <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                <div className="p-2 rounded-lg bg-cosmic-cyan/20 text-cosmic-cyan">
                  <Image size={24} />
                </div>
                Supported Formats
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {supportedFormats.map((format) => (
                  <div
                    key={format.name}
                    className="glass-panel p-4 text-center"
                  >
                    <p className="text-xl font-bold text-white">
                      {format.name}
                    </p>
                    <p className="text-zinc-400 text-xs mt-1">
                      {format.description}
                    </p>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
        </section>

        {/* Need Help */}
        <section className="py-12 px-4 mb-8">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="glass-panel p-8 text-center"
            >
              <h2 className="text-2xl font-bold text-white mb-4">Need Help?</h2>
              <p className="text-zinc-400 mb-6">
                Have questions or found a bug? Reach out or open an issue on
                GitHub.
              </p>
              <div className="flex flex-wrap justify-center gap-4">
                <a
                  href="https://github.com/Jayant-1/AstroPixel/issues"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="glass-panel glass-panel-hover px-6 py-3 text-white font-medium"
                >
                  Open an Issue
                </a>
                <Link
                  to="/contact"
                  className="glass-panel glass-panel-hover px-6 py-3 text-white font-medium"
                >
                  Contact Us
                </Link>
              </div>
            </motion.div>
          </div>
        </section>

        <Footer />
      </div>
    </div>
  );
};

export default DocsPage;
