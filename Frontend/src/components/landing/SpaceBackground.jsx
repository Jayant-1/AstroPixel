import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

const SpaceBackground = ({ backgroundImage = "/space-bg.jpg" }) => {
  const containerRef = useRef(null);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isHovering, setIsHovering] = useState(false);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setMousePosition({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top,
        });
      }
    };

    const handleMouseEnter = () => setIsHovering(true);
    const handleMouseLeave = () => setIsHovering(false);

    const container = containerRef.current;
    if (container) {
      container.addEventListener("mousemove", handleMouseMove);
      container.addEventListener("mouseenter", handleMouseEnter);
      container.addEventListener("mouseleave", handleMouseLeave);
    }

    return () => {
      if (container) {
        container.removeEventListener("mousemove", handleMouseMove);
        container.removeEventListener("mouseenter", handleMouseEnter);
        container.removeEventListener("mouseleave", handleMouseLeave);
      }
    };
  }, []);

  // Generate random stars
  const stars = Array.from({ length: 150 }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    size: Math.random() * 3 + 1,
    delay: Math.random() * 3,
    duration: Math.random() * 2 + 2,
  }));

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 overflow-hidden pointer-events-auto"
      style={{ zIndex: 0 }}
    >
      {/* Base dark background */}
      <div className="absolute inset-0 bg-space-900" />

      {/* Space background image with spotlight effect */}
      <div
        className="absolute inset-0 transition-opacity duration-300"
        style={{
          backgroundImage: `url(${backgroundImage})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          opacity: 0,
        }}
      />

      {/* Spotlight reveal layer */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: `url(${backgroundImage})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          maskImage: isHovering
            ? `radial-gradient(circle 250px at ${mousePosition.x}px ${mousePosition.y}px, black 0%, transparent 100%)`
            : "none",
          WebkitMaskImage: isHovering
            ? `radial-gradient(circle 250px at ${mousePosition.x}px ${mousePosition.y}px, black 0%, transparent 100%)`
            : "none",
          opacity: isHovering ? 1 : 0,
          transition: "opacity 0.3s ease",
        }}
      />

      {/* Animated glow at cursor position */}
      {isHovering && (
        <motion.div
          className="absolute pointer-events-none"
          animate={{
            x: mousePosition.x - 150,
            y: mousePosition.y - 150,
          }}
          transition={{ type: "spring", damping: 30, stiffness: 200 }}
          style={{
            width: 300,
            height: 300,
            background:
              "radial-gradient(circle, rgba(124, 58, 237, 0.15) 0%, rgba(236, 72, 153, 0.1) 40%, transparent 70%)",
            borderRadius: "50%",
          }}
        />
      )}

      {/* Decorative radial gradients */}
      <div
        className="absolute top-0 left-1/4 w-[600px] h-[600px] opacity-30"
        style={{
          background:
            "radial-gradient(circle, rgba(59, 130, 246, 0.22) 0%, transparent 70%)",
          transform: "translate(-50%, -50%)",
        }}
      />
      <div
        className="absolute top-1/2 right-0 w-[800px] h-[800px] opacity-30"
        style={{
          background:
            "radial-gradient(circle, rgba(124, 58, 237, 0.22) 0%, transparent 70%)",
          transform: "translate(30%, -50%)",
        }}
      />
      <div
        className="absolute bottom-0 left-1/2 w-[700px] h-[700px] opacity-30"
        style={{
          background:
            "radial-gradient(circle, rgba(236, 72, 153, 0.22) 0%, transparent 70%)",
          transform: "translate(-50%, 30%)",
        }}
      />

      {/* Animated stars */}
      {stars.map((star) => (
        <motion.div
          key={star.id}
          className="absolute rounded-full bg-white"
          style={{
            left: `${star.x}%`,
            top: `${star.y}%`,
            width: star.size,
            height: star.size,
          }}
          animate={{
            opacity: [0.3, 1, 0.3],
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: star.duration,
            delay: star.delay,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      ))}

      {/* Subtle grid overlay */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)
          `,
          backgroundSize: "100px 100px",
        }}
      />
    </div>
  );
};

export default SpaceBackground;
