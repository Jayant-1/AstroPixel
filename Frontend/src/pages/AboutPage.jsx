import { motion } from "framer-motion";
import { Code, Github, Heart, Rocket, Target, Users } from "lucide-react";
import { Link } from "react-router-dom";
import Footer from "../components/landing/Footer";
import Navbar from "../components/landing/Navbar";
import SpaceBackground from "../components/landing/SpaceBackground";

const techStack = [
  { name: "React", category: "Frontend" },
  { name: "Vite", category: "Build Tool" },
  { name: "Tailwind CSS", category: "Styling" },
  { name: "Framer Motion", category: "Animations" },
  { name: "OpenSeadragon", category: "Image Viewer" },
  { name: "FastAPI", category: "Backend" },
  { name: "Python", category: "Backend" },
  { name: "Cloudflare R2", category: "Storage" },
];

const AboutPage = () => {
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
              <h1 className="text-4xl md:text-5xl font-extrabold mb-6">
                <span className="gradient-text">About AstroPixel</span>
              </h1>
              <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
                A platform built for exploring the cosmos, one pixel at a time
              </p>
            </motion.div>
          </div>
        </section>

        {/* Mission, Project, Open Source */}
        <section className="py-12 px-4">
          <div className="max-w-5xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                className="glass-panel p-6 text-center"
              >
                <div className="w-16 h-16 rounded-full bg-nebula-purple/20 flex items-center justify-center mx-auto mb-4">
                  <Target className="text-nebula-purple" size={32} />
                </div>
                <h3 className="text-xl font-bold text-white mb-3">
                  Our Mission
                </h3>
                <p className="text-zinc-400">
                  Make astronomical imagery accessible and interactive for
                  everyone, from amateur stargazers to professional researchers.
                </p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.1 }}
                className="glass-panel p-6 text-center"
              >
                <div className="w-16 h-16 rounded-full bg-cosmic-cyan/20 flex items-center justify-center mx-auto mb-4">
                  <Rocket className="text-cosmic-cyan" size={32} />
                </div>
                <h3 className="text-xl font-bold text-white mb-3">
                  The Project
                </h3>
                <p className="text-zinc-400">
                  AstroPixel is a hackathon project enabling seamless
                  exploration of high-resolution space imagery with powerful
                  annotation tools.
                </p>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.2 }}
                className="glass-panel p-6 text-center"
              >
                <div className="w-16 h-16 rounded-full bg-nebula-pink/20 flex items-center justify-center mx-auto mb-4">
                  <Code className="text-nebula-pink" size={32} />
                </div>
                <h3 className="text-xl font-bold text-white mb-3">
                  Open Source
                </h3>
                <p className="text-zinc-400">
                  AstroPixel is fully open source. Contribute, suggest features,
                  or fork it for your own astronomical research.
                </p>
              </motion.div>
            </div>
          </div>
        </section>

        {/* What You Can Do */}
        <section className="py-12 px-4">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="glass-panel p-8"
            >
              <h2 className="text-2xl font-bold text-white mb-6 text-center">
                What You Can Do with AstroPixel
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="flex items-start gap-4">
                  <span className="text-2xl">🔭</span>
                  <div>
                    <h3 className="text-lg font-semibold text-white">
                      Explore High-Res Images
                    </h3>
                    <p className="text-zinc-400 text-sm">
                      Pan and zoom through gigapixel astronomical imagery with
                      smooth tile-based rendering.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <span className="text-2xl">✏️</span>
                  <div>
                    <h3 className="text-lg font-semibold text-white">
                      Annotate Discoveries
                    </h3>
                    <p className="text-zinc-400 text-sm">
                      Mark celestial objects with points, rectangles, and
                      circles. Add labels and descriptions.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <span className="text-2xl">📤</span>
                  <div>
                    <h3 className="text-lg font-semibold text-white">
                      Upload Your Images
                    </h3>
                    <p className="text-zinc-400 text-sm">
                      Upload TIFF, PNG, JPEG, or FITS files. Images are
                      automatically processed for optimal viewing.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-4">
                  <span className="text-2xl">💾</span>
                  <div>
                    <h3 className="text-lg font-semibold text-white">
                      Export & Share
                    </h3>
                    <p className="text-zinc-400 text-sm">
                      Export your work and share your astronomical discoveries
                      with others.
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        {/* Tech Stack */}
        <section className="py-12 px-4">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
            >
              <h2 className="text-2xl font-bold text-white mb-6 text-center">
                Built With
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {techStack.map((tech) => (
                  <div
                    key={tech.name}
                    className="glass-panel glass-panel-hover p-4 text-center"
                  >
                    <p className="text-white font-semibold">{tech.name}</p>
                    <p className="text-zinc-500 text-xs">{tech.category}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
        </section>

        {/* GitHub CTA */}
        <section className="py-12 px-4 mb-8">
          <div className="max-w-5xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="glass-panel p-8 text-center"
            >
              <Github className="w-12 h-12 text-white mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-white mb-4">
                Contribute to AstroPixel
              </h2>
              <p className="text-zinc-400 mb-6 max-w-xl mx-auto">
                AstroPixel is open source and we welcome contributions! Check
                out the repository, report issues, or submit pull requests.
              </p>
              <a
                href="https://github.com/Jayant-1/AstroPixel"
                target="_blank"
                rel="noopener noreferrer"
                className="gradient-button px-8 py-4 rounded-xl text-white font-semibold inline-flex items-center gap-2"
              >
                <Github size={20} />
                View on GitHub
              </a>
            </motion.div>
          </div>
        </section>

        <Footer />
      </div>
    </div>
  );
};

export default AboutPage;
