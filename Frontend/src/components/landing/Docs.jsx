import { motion } from "framer-motion";
import { BookOpen, FileText, Layers, MousePointer, Upload } from "lucide-react";

const docs = [
  {
    icon: Upload,
    title: "Getting Started",
    description:
      "Upload TIFF images from sources like ESA Hubble. The platform automatically tiles your images for smooth viewing.",
  },
  {
    icon: MousePointer,
    title: "Navigation",
    description:
      "Use mouse wheel to zoom, click and drag to pan. Double-click to zoom in on areas of interest.",
  },
  {
    icon: Layers,
    title: "Annotations",
    description:
      "Create points, rectangles, and circles to mark celestial objects. Add labels and descriptions to your annotations.",
  },
  {
    icon: FileText,
    title: "Export",
    description:
      "Export your annotated images and data. Share your discoveries with the community.",
  },
];

const Docs = () => {
  return (
    <section id="docs" className="relative py-24 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 mb-4">
            <BookOpen className="text-nebula-purple" size={28} />
            <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight">
              <span className="gradient-text">Documentation</span>
            </h2>
          </div>
          <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
            Quick guide to get you started with AstroPixel
          </p>
        </motion.div>

        {/* Docs Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {docs.map((doc, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="glass-panel glass-panel-hover p-6 group"
            >
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-lg bg-nebula-purple/20 text-nebula-purple group-hover:bg-nebula-purple/30 transition-colors">
                  <doc.icon size={24} />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-white mb-2">
                    {doc.title}
                  </h3>
                  <p className="text-zinc-400 leading-relaxed">
                    {doc.description}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Supported Formats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-12 text-center"
        >
          <div className="glass-panel inline-block px-8 py-4">
            <p className="text-white font-semibold mb-2">Supported Formats</p>
            <div className="flex flex-wrap justify-center gap-3">
              {["TIFF", "PNG", "JPEG", "FITS"].map((format) => (
                <span
                  key={format}
                  className="px-3 py-1 rounded-full bg-white/10 text-zinc-300 text-sm"
                >
                  {format}
                </span>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default Docs;
