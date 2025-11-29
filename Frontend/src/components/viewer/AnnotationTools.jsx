import {
  Circle,
  Edit3,
  MapPin,
  Palette,
  Square,
  Tag as TagIcon,
} from "lucide-react";
import React, { useEffect, useState } from "react";
import { useApp } from "../../context/AppContext";
import { cn } from "../../utils/helpers";
import Button from "../ui/Button";

const AnnotationTools = () => {
  console.log("🎨 AnnotationTools component mounted/re-rendered");

  const { createAnnotation, selectedDataset } = useApp();
  const [drawMode, setDrawMode] = useState("point"); // point, rectangle
  const [selectedColor, setSelectedColor] = useState("#3b82f6");
  const [label, setLabel] = useState("");
  const [isDrawing, setIsDrawing] = useState(false);

  const tools = [
    { id: "point", name: "Point", icon: MapPin },
    { id: "rectangle", name: "Rectangle", icon: Square },
    { id: "circle", name: "Circle", icon: Circle },
  ];

  const colors = [
    "#3b82f6", // blue
    "#ef4444", // red
    "#10b981", // green
    "#f59e0b", // yellow
    "#8b5cf6", // purple
    "#ec4899", // pink
  ];

  return (
    <div className="p-4 space-y-5">
      {/* Drawing Tools - Larger, more prominent */}
      <div>
        <h3 className="text-xs uppercase tracking-wider text-gray-400 mb-3 font-semibold">
          Drawing Tool
        </h3>

        <div className="space-y-2">
          {tools.map((tool) => {
            const Icon = tool.icon;
            const isSelected = drawMode === tool.id;
            return (
              <button
                key={tool.id}
                onClick={() => setDrawMode(tool.id)}
                className={cn(
                  "w-full flex items-center gap-3 px-4 py-3 rounded-lg border-2 transition-all text-sm font-medium",
                  isSelected
                    ? "border-blue-500 bg-blue-500/10 text-blue-400 shadow-lg shadow-blue-500/20"
                    : "border-gray-700 hover:border-gray-600 text-gray-300 hover:bg-gray-800/50"
                )}
              >
                <div
                  className={cn(
                    "w-10 h-10 rounded-lg flex items-center justify-center transition-colors",
                    isSelected ? "bg-blue-500/20" : "bg-gray-800"
                  )}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <span>{tool.name}</span>
                {isSelected && (
                  <svg
                    className="w-5 h-5 ml-auto"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Label Input - More prominent */}
      <div>
        <h3 className="text-xs uppercase tracking-wider text-gray-400 mb-3 font-semibold">
          Annotation Label
        </h3>

        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="e.g., Galaxy cluster, Star formation..."
          className="w-full px-4 py-3 bg-gray-800 border-2 border-gray-700 rounded-lg text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
        />
      </div>

      {/* Color Picker - More visual */}
      <div>
        <h3 className="text-xs uppercase tracking-wider text-gray-400 mb-3 font-semibold">
          Color
        </h3>

        <div className="grid grid-cols-6 gap-2">
          {colors.map((color) => (
            <button
              key={color}
              onClick={() => setSelectedColor(color)}
              className={cn(
                "w-full aspect-square rounded-lg border-3 transition-all relative",
                selectedColor === color
                  ? "border-white scale-110 shadow-lg"
                  : "border-gray-700 hover:scale-105 hover:border-gray-500"
              )}
              style={{ backgroundColor: color }}
            >
              {selectedColor === color && (
                <svg
                  className="w-4 h-4 absolute inset-0 m-auto text-white drop-shadow-lg"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Action Button - Prominent CTA */}
      <div className="pt-2">
        <Button
          className="w-full py-3 text-base font-semibold"
          size="sm"
          onClick={handleStartDrawing}
          disabled={!label.trim() || isDrawing}
        >
          {isDrawing ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Drawing on Canvas...
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              <Edit3 className="w-4 h-4" />
              Start Drawing
            </span>
          )}
        </Button>

        {isDrawing && (
          <Button
            className="w-full mt-2 py-2"
            size="sm"
            variant="ghost"
            onClick={handleCancelDrawing}
          >
            Cancel (or press Esc)
          </Button>
        )}
      </div>

      {/* Instructions - Subtle helper */}
      <div className="pt-3 border-t border-gray-800">
        <p className="text-xs text-gray-500 mb-2 font-medium">Quick Guide:</p>
        <div className="text-xs text-gray-500 space-y-1.5">
          <div className="flex items-start gap-2">
            <MapPin className="w-3 h-3 mt-0.5 flex-shrink-0" />
            <span>
              <span className="text-gray-400 font-medium">Point:</span> Click
              once on image
            </span>
          </div>
          <div className="flex items-start gap-2">
            <Square className="w-3 h-3 mt-0.5 flex-shrink-0" />
            <span>
              <span className="text-gray-400 font-medium">Rectangle:</span>{" "}
              Click, drag, release
            </span>
          </div>
          <div className="flex items-start gap-2">
            <Circle className="w-3 h-3 mt-0.5 flex-shrink-0" />
            <span>
              <span className="text-gray-400 font-medium">Circle:</span> Click
              center, drag radius
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  function handleStartDrawing() {
    if (!label.trim()) return;

    setIsDrawing(true);

    // Dispatch event to start drawing on the canvas
    window.dispatchEvent(
      new CustomEvent("annotation-start-drawing", {
        detail: {
          mode: drawMode,
          color: selectedColor,
          label: label.trim(),
        },
      })
    );
  }

  function handleCancelDrawing() {
    setIsDrawing(false);
    window.dispatchEvent(
      new CustomEvent("annotation-cancel-drawing", {
        detail: { source: "annotation-tools" },
      })
    );
  }

  // Listen for drawing completion
  useEffect(() => {
    console.log("🎧 AnnotationTools: Setting up event listeners");

    const handleDrawingComplete = async (event) => {
      console.log("📥 AnnotationTools: Drawing complete event received!");
      console.log("📥 Event detail:", event.detail);

      // Just reset UI - ViewerCanvas handles the actual annotation creation
      setIsDrawing(false);
      setLabel("");
      console.log("✅ AnnotationTools UI reset");
    };

    const handleDrawingCancelled = () => {
      console.log("📥 AnnotationTools: Drawing cancelled event received");
      setIsDrawing(false);
    };

    console.log("🔗 AnnotationTools: Adding event listeners");
    window.addEventListener(
      "annotation-drawing-complete",
      handleDrawingComplete
    );
    window.addEventListener(
      "annotation-drawing-cancelled",
      handleDrawingCancelled
    );

    return () => {
      console.log("🔓 AnnotationTools: Removing event listeners");
      window.removeEventListener(
        "annotation-drawing-complete",
        handleDrawingComplete
      );
      window.removeEventListener(
        "annotation-drawing-cancelled",
        handleDrawingCancelled
      );
    };
  }, [createAnnotation]);
};

export default AnnotationTools;
