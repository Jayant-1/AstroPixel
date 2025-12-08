import { Cloud, Loader2, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

const TileLoadingOverlay = ({ isLoading }) => {
  const [dots, setDots] = useState("");
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (isLoading) {
      // Show overlay immediately
      setVisible(true);
    } else {
      // Delay hiding to show completion state briefly
      const timeout = setTimeout(() => setVisible(false), 500);
      return () => clearTimeout(timeout);
    }
  }, [isLoading]);

  useEffect(() => {
    if (!visible) return;

    const interval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? "" : prev + "."));
    }, 400);

    return () => clearInterval(interval);
  }, [visible]);

  if (!visible) return null;

  return (
    <div 
      className="fixed inset-0 bg-gray-900/90 backdrop-blur-md z-[100] flex items-center justify-center"
      style={{ 
        animation: "fadeIn 0.2s ease-out",
        pointerEvents: isLoading ? "all" : "none"
      }}
    >
      <div className="flex flex-col items-center gap-6 p-10 bg-gradient-to-br from-gray-800/95 to-gray-900/95 rounded-2xl border-2 border-gray-700/50 shadow-2xl max-w-md backdrop-blur-xl">
        {/* Animated loader with orbiting elements */}
        <div className="relative w-24 h-24">
          {/* Main spinner */}
          <div className="absolute inset-0 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" 
               style={{ animationDuration: "1s" }} 
          />
          
          {/* Inner glow */}
          <div className="absolute inset-2 bg-blue-500/20 rounded-full animate-pulse" />
          
          {/* Orbiting sparkles */}
          <div className="absolute inset-0 animate-spin" style={{ animationDuration: "3s" }}>
            <Sparkles className="absolute -top-2 left-1/2 -translate-x-1/2 w-4 h-4 text-purple-400" />
          </div>
          <div className="absolute inset-0 animate-spin" style={{ animationDuration: "3s", animationDirection: "reverse" }}>
            <Cloud className="absolute top-1/2 -right-2 -translate-y-1/2 w-4 h-4 text-cyan-400" />
          </div>
          
          {/* Center icon */}
          <div className="absolute inset-0 flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin" style={{ animationDuration: "2s" }} />
          </div>
        </div>

        {/* Loading text with animated dots */}
        <div className="text-center space-y-2">
          <h3 className="text-2xl font-bold text-white tracking-tight">
            Loading Tiles{dots}
          </h3>
          <p className="text-sm text-gray-400 max-w-xs">
            Streaming high-resolution imagery from R2 cloud storage
          </p>
        </div>

        {/* Animated progress bar with gradient */}
        <div className="w-72 h-3 bg-gray-700/50 rounded-full overflow-hidden border border-gray-600/50">
          <div
            className="h-full bg-gradient-to-r from-blue-600 via-purple-500 to-pink-500 relative"
            style={{
              width: "100%",
              animation: "shimmer 1.5s ease-in-out infinite",
            }}
          >
            {/* Shine effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                 style={{ animation: "slide 2s ease-in-out infinite" }}
            />
          </div>
        </div>

        {/* Status indicators */}
        <div className="flex gap-2 text-xs text-gray-500">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span>Connected to R2</span>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
          }
          to {
            opacity: 1;
          }
        }

        @keyframes shimmer {
          0%, 100% {
            opacity: 0.8;
          }
          50% {
            opacity: 1;
          }
        }

        @keyframes slide {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(200%);
          }
        }
      `}</style>
    </div>
  );
};

export default TileLoadingOverlay;
