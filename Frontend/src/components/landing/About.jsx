import { motion } from "framer-motion";
import { Rocket, Target, Users } from "lucide-react";

const About = () => {
  return (
    <section id="about" className="relative py-24 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-4">
            <span className="gradient-text">About AstroPixel</span>
          </h2>
          <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
            Built for astronomers, researchers, and space enthusiasts
          </p>
        </motion.div>

        {/* About Content */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="glass-panel p-6 text-center"
          >
            <div className="w-14 h-14 rounded-full bg-nebula-purple/20 flex items-center justify-center mx-auto mb-4">
              <Target className="text-nebula-purple" size={28} />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">
              Our Mission
            </h3>
            <p className="text-zinc-400">
              Make astronomical imagery accessible and interactive for everyone,
              from amateur stargazers to professional researchers.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="glass-panel p-6 text-center"
          >
            <div className="w-14 h-14 rounded-full bg-cosmic-cyan/20 flex items-center justify-center mx-auto mb-4">
              <Rocket className="text-cosmic-cyan" size={28} />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">
              The Project
            </h3>
            <p className="text-zinc-400">
              AstroPixel is a hackathon project that enables seamless
              exploration of high-resolution space imagery with annotation
              capabilities.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="glass-panel p-6 text-center"
          >
            <div className="w-14 h-14 rounded-full bg-nebula-pink/20 flex items-center justify-center mx-auto mb-4">
              <Users className="text-nebula-pink" size={28} />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">
              Open Source
            </h3>
            <p className="text-zinc-400">
              AstroPixel is open source. Contribute, suggest features, or use it
              for your own astronomical research projects.
            </p>
          </motion.div>
        </div>

        {/* Tech Stack */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="glass-panel p-8 text-center"
        >
          <h3 className="text-xl font-semibold text-white mb-4">Built With</h3>
          <div className="flex flex-wrap justify-center gap-4">
            {[
              "React",
              "Vite",
              "Tailwind CSS",
              "OpenSeadragon",
              "FastAPI",
              "Python",
              "Cloudflare R2",
            ].map((tech) => (
              <span
                key={tech}
                className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-zinc-300 hover:bg-white/10 transition-colors"
              >
                {tech}
              </span>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default About;
