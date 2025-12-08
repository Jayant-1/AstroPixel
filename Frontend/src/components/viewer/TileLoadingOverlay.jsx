import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

const TileLoadingOverlay = ({ isLoading }) => {
  const [dots, setDots] = useState("");

  useEffect(() => {
    if (!isLoading) return;

    const interval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? "" : prev + "."));
    }, 500);

    return () => clearInterval(interval);
  }, [isLoading]);

  if (!isLoading) return null;

  return (
    <div className="absolute inset-0 bg-gray-900/80 backdrop-blur-sm z-50 flex items-center justify-center pointer-events-none">
      <div className="flex flex-col items-center gap-4 p-8 bg-gray-800/90 rounded-xl border border-gray-700 shadow-2xl">
        {/* Animated loader icon */}
        <div className="relative">
          <Loader2 className="w-16 h-16 text-blue-500 animate-spin" />
          <div className="absolute inset-0 w-16 h-16 bg-blue-500/20 rounded-full animate-ping" />
        </div>

        {/* Loading text with animated dots */}
        <div className="text-center">
          <h3 className="text-xl font-semibold text-white mb-2">
            Loading Tiles{dots}
          </h3>
          <p className="text-sm text-gray-400">
            Fetching high-resolution imagery from cloud storage
          </p>
        </div>

        {/* Animated progress bar */}
        <div className="w-64 h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 animate-pulse"
            style={{
              width: "100%",
              animation: "shimmer 2s ease-in-out infinite",
            }}
          />
        </div>
      </div>

      <style jsx>{`
        @keyframes shimmer {
          0%,
          100% {
            opacity: 0.5;
            transform: translateX(-100%);
          }
          50% {
            opacity: 1;
            transform: translateX(100%);
          }
        }
      `}</style>
    </div>
  );
};

export default TileLoadingOverlay;
