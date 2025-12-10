import { motion } from "framer-motion";
import {
  AlertCircle,
  CheckCircle,
  Github,
  Globe,
  Linkedin,
  Mail,
  MessageCircle,
  Send,
} from "lucide-react";
import { useState } from "react";
import Footer from "../components/landing/Footer";
import Navbar from "../components/landing/Navbar";
import SpaceBackground from "../components/landing/SpaceBackground";
import { sendContactEmail } from "../services/email";

const ContactPage = () => {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    subject: "",
    message: "",
  });
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null); // 'success', 'error', or null
  const [statusMessage, setStatusMessage] = useState("");

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus(null);
    setStatusMessage("");

    try {
      await sendContactEmail(formData);
      setStatus("success");
      setStatusMessage(
        "Message sent successfully! Thank you for reaching out."
      );
      setFormData({ name: "", email: "", subject: "", message: "" });
      setTimeout(() => setStatus(null), 5000);
    } catch (error) {
      setStatus("error");
      setStatusMessage(
        error.message || "Failed to send message. Please try again."
      );
      setTimeout(() => setStatus(null), 5000);
    } finally {
      setLoading(false);
    }
  };
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
                <span className="gradient-text">Contact Us</span>
              </h1>
              <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
                Have questions, feedback, or want to collaborate? Get in touch!
              </p>
            </motion.div>
          </div>
        </section>

        {/* Creator Card */}
        <section className="py-12 px-4">
          <div className="max-w-3xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="glass-panel p-8"
            >
              <div className="flex flex-col md:flex-row items-center gap-8">
                {/* Avatar */}
                <div className="shrink-0">
                  <img
                    src="/jayant-profile.jpg"
                    alt="Jayant Potdar"
                    className="w-32 h-32 rounded-full object-cover shadow-lg shadow-black/30"
                  />
                </div>

                {/* Info */}
                <div className="text-center md:text-left flex-1">
                  <h2 className="text-2xl font-bold text-white mb-2">
                    Jayant Potdar
                  </h2>
                  <p className="text-nebula-purple font-medium mb-4">
                    Creator & Developer
                  </p>
                  <p className="text-zinc-400 mb-6">
                    Full-stack developer passionate about space exploration and
                    building tools that make complex data accessible. AstroPixel
                    is a hackathon project combining my love for astronomy and
                    software development.
                  </p>

                  {/* Social Links */}
                  <div className="flex flex-wrap justify-center md:justify-start gap-3">
                    <a
                      href="mailto:jayantpotdar2006@gmail.com"
                      className="glass-panel glass-panel-hover px-4 py-2 inline-flex items-center gap-2 text-zinc-300 hover:text-white transition-colors"
                    >
                      <Mail size={18} />
                      <span className="text-sm">Email</span>
                    </a>
                    <a
                      href="https://github.com/Jayant-1"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="glass-panel glass-panel-hover px-4 py-2 inline-flex items-center gap-2 text-zinc-300 hover:text-white transition-colors"
                    >
                      <Github size={18} />
                      <span className="text-sm">GitHub</span>
                    </a>
                    <a
                      href="https://www.linkedin.com/in/jayant-potdar-880a461b8/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="glass-panel glass-panel-hover px-4 py-2 inline-flex items-center gap-2 text-zinc-300 hover:text-white transition-colors"
                    >
                      <Linkedin size={18} />
                      <span className="text-sm">LinkedIn</span>
                    </a>
                    <a
                      href="http://jayant-1.vercel.app/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="glass-panel glass-panel-hover px-4 py-2 inline-flex items-center gap-2 text-zinc-300 hover:text-white transition-colors"
                    >
                      <Globe size={18} />
                      <span className="text-sm">Portfolio</span>
                    </a>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        {/* Contact Options */}
        <section className="py-12 px-4">
          <div className="max-w-5xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <motion.a
                href="mailto:jayantpotdar2006@gmail.com"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                className="glass-panel glass-panel-hover p-6 text-center group"
              >
                <div className="w-14 h-14 rounded-full bg-nebula-purple/20 flex items-center justify-center mx-auto mb-4 group-hover:bg-nebula-purple/30 transition-colors">
                  <Mail className="text-nebula-purple" size={28} />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">Email</h3>
                <p className="text-zinc-400 text-sm">
                  jayantpotdar2006@gmail.com
                </p>
              </motion.a>

              <motion.a
                href="https://github.com/Jayant-1/AstroPixel/issues"
                target="_blank"
                rel="noopener noreferrer"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.1 }}
                className="glass-panel glass-panel-hover p-6 text-center group"
              >
                <div className="w-14 h-14 rounded-full bg-cosmic-cyan/20 flex items-center justify-center mx-auto mb-4 group-hover:bg-cosmic-cyan/30 transition-colors">
                  <MessageCircle className="text-cosmic-cyan" size={28} />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  Report Issues
                </h3>
                <p className="text-zinc-400 text-sm">Open an issue on GitHub</p>
              </motion.a>

              <motion.a
                href="https://github.com/Jayant-1/AstroPixel"
                target="_blank"
                rel="noopener noreferrer"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.2 }}
                className="glass-panel glass-panel-hover p-6 text-center group"
              >
                <div className="w-14 h-14 rounded-full bg-nebula-pink/20 flex items-center justify-center mx-auto mb-4 group-hover:bg-nebula-pink/30 transition-colors">
                  <Github className="text-nebula-pink" size={28} />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  Contribute
                </h3>
                <p className="text-zinc-400 text-sm">
                  Fork & submit pull requests
                </p>
              </motion.a>
            </div>
          </div>
        </section>

        {/* Direct Email CTA */}
        <section className="py-12 px-4 mb-8">
          <div className="max-w-3xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="glass-panel p-8"
            >
              <h2 className="text-2xl font-bold text-white mb-6 text-center">
                Send us a Message
              </h2>

              {/* Status Messages */}
              {status === "success" && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-6 p-4 bg-green-500/20 border border-green-500/50 rounded-lg flex items-center gap-3"
                >
                  <CheckCircle size={20} className="text-green-500 shrink-0" />
                  <p className="text-green-300 text-sm">{statusMessage}</p>
                </motion.div>
              )}

              {status === "error" && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-6 p-4 bg-red-500/20 border border-red-500/50 rounded-lg flex items-center gap-3"
                >
                  <AlertCircle size={20} className="text-red-500 shrink-0" />
                  <p className="text-red-300 text-sm">{statusMessage}</p>
                </motion.div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Name */}
                <div>
                  <label className="block text-white text-sm font-medium mb-2">
                    Full Name
                  </label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    required
                    className="w-full px-4 py-2 bg-black/30 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:border-nebula-purple focus:outline-none transition-colors"
                    placeholder="Your name"
                  />
                </div>

                {/* Email */}
                <div>
                  <label className="block text-white text-sm font-medium mb-2">
                    Email Address
                  </label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    required
                    className="w-full px-4 py-2 bg-black/30 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:border-nebula-purple focus:outline-none transition-colors"
                    placeholder="your.email@example.com"
                  />
                </div>

                {/* Subject */}
                <div>
                  <label className="block text-white text-sm font-medium mb-2">
                    Subject
                  </label>
                  <input
                    type="text"
                    name="subject"
                    value={formData.subject}
                    onChange={handleInputChange}
                    required
                    className="w-full px-4 py-2 bg-black/30 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:border-nebula-purple focus:outline-none transition-colors"
                    placeholder="How can we help?"
                  />
                </div>

                {/* Message */}
                <div>
                  <label className="block text-white text-sm font-medium mb-2">
                    Message
                  </label>
                  <textarea
                    name="message"
                    value={formData.message}
                    onChange={handleInputChange}
                    required
                    rows="5"
                    className="w-full px-4 py-2 bg-black/30 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:border-nebula-purple focus:outline-none transition-colors resize-none"
                    placeholder="Tell us what's on your mind..."
                  />
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full gradient-button px-8 py-3 rounded-xl text-white font-semibold inline-flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  <Send size={20} />
                  {loading ? "Sending..." : "Send Message"}
                </button>
              </form>
            </motion.div>
          </div>
        </section>

        <Footer />
      </div>
    </div>
  );
};

export default ContactPage;
