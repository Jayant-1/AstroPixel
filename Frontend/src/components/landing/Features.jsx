import { motion } from "framer-motion";

const features = [
  {
    icon: "🔭",
    title: "High-Resolution Imaging",
    description:
      "Explore astronomical imagery with seamless pan and zoom capabilities powered by advanced tile-based rendering.",
  },
  {
    icon: "✏️",
    title: "Annotations",
    description:
      "Create and manage annotations on astronomical images. Mark points, rectangles, and circles on areas of interest.",
  },
  {
    icon: "📤",
    title: "Easy Upload",
    description:
      "Upload your own astronomical images and have them automatically tiled for smooth viewing at any zoom level.",
  },
  {
    icon: "🔍",
    title: "Smooth Navigation",
    description:
      "Navigate through gigapixel images with responsive controls, intuitive gestures, and customizable zoom settings.",
  },
  {
    icon: "📊",
    title: "Dataset Management",
    description:
      "Organize and manage your astronomical datasets with categories, metadata, and easy browsing.",
  },
  {
    icon: "💾",
    title: "Export Options",
    description:
      "Export your annotated images and data in various formats for further analysis or sharing.",
  },
];

const Features = () => {
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2,
      },
    },
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, ease: "easeOut" },
    },
  };

  return (
    <section id="features" className="relative py-24 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-4">
            <span className="gradient-text">Powerful Features</span>
          </h2>
          <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
            Everything you need to explore, analyze, and discover the wonders of
            the universe.
          </p>
        </motion.div>

        {/* Features Grid */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {features.map((feature, index) => (
            <motion.div
              key={index}
              variants={cardVariants}
              whileHover={{ y: -5, scale: 1.02 }}
              className="glass-panel glass-panel-hover p-6 group cursor-pointer"
            >
              <div className="text-4xl mb-4 group-hover:scale-110 group-hover:rotate-3 transition-transform duration-300 inline-block">
                {feature.icon}
              </div>
              <h3 className="text-xl font-semibold text-white mb-3">
                {feature.title}
              </h3>
              <p className="text-zinc-400 leading-relaxed">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};

export default Features;
