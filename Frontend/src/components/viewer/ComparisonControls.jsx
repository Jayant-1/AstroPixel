import { useState } from "react";
import { useApp } from "../../context/AppContext";
import { cn } from "../../utils/helpers";

const ComparisonControls = ({
  dataset,
  secondDataset,
  setSecondDataset,
  comparisonMode,
  setComparisonMode,
  syncEnabled,
  setSyncEnabled,
  opacity,
  setOpacity,
}) => {
  const { datasets } = useApp();
  const availableDatasets = datasets.filter((d) => d.id !== dataset.id);

  return (
    <div className="p-4 space-y-5">
      {/* Dataset Selection */}
      <div>
        <h3 className="text-xs uppercase tracking-wider text-gray-400 mb-3 font-semibold">
          Select Dataset
        </h3>

        <select
          value={secondDataset?.id || ""}
          onChange={(e) => {
            const selected = datasets.find(
              (d) => d.id === e.target.value || String(d.id) === e.target.value
            );
            setSecondDataset(selected);
          }}
          className="w-full px-4 py-3 bg-gray-800 border-2 border-gray-700 rounded-lg text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
        >
          {availableDatasets.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      </div>

      {/* Comparison Mode */}
      <div>
        <h3 className="text-xs uppercase tracking-wider text-gray-400 mb-3 font-semibold">
          Comparison Mode
        </h3>
        <div className="space-y-2">
          <button
            onClick={() => setComparisonMode("sideBySide")}
            className={cn(
              "w-full px-4 py-3 rounded-lg border-2 transition-all text-left",
              comparisonMode === "sideBySide"
                ? "border-blue-500 bg-blue-500/10 shadow-lg shadow-blue-500/20"
                : "border-gray-700 hover:border-gray-600 hover:bg-gray-800/50"
            )}
          >
            <div className="flex items-center justify-between mb-1">
              <span
                className={cn(
                  "text-sm font-semibold",
                  comparisonMode === "sideBySide"
                    ? "text-blue-400"
                    : "text-gray-300"
                )}
              >
                Side by Side
              </span>
              {comparisonMode === "sideBySide" && (
                <svg
                  className="w-5 h-5 text-blue-400"
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
            </div>
            <p className="text-xs text-gray-500 leading-relaxed">
              View both datasets side by side with independent or synchronized
              controls
            </p>
          </button>

          <button
            onClick={() => setComparisonMode("overlay")}
            className={cn(
              "w-full px-4 py-3 rounded-lg border-2 transition-all text-left",
              comparisonMode === "overlay"
                ? "border-blue-500 bg-blue-500/10 shadow-lg shadow-blue-500/20"
                : "border-gray-700 hover:border-gray-600 hover:bg-gray-800/50"
            )}
          >
            <div className="flex items-center justify-between mb-1">
              <span
                className={cn(
                  "text-sm font-semibold",
                  comparisonMode === "overlay"
                    ? "text-blue-400"
                    : "text-gray-300"
                )}
              >
                Overlay
              </span>
              {comparisonMode === "overlay" && (
                <svg
                  className="w-5 h-5 text-blue-400"
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
            </div>
            <p className="text-xs text-gray-500 leading-relaxed">
              Blend both images together with adjustable opacity control
            </p>
          </button>
        </div>
      </div>

      {/* Mode-specific Controls */}
      {comparisonMode === "sideBySide" && (
        <div>
          <h4 className="text-xs uppercase tracking-wider text-gray-400 mb-3 font-semibold">
            Settings
          </h4>
          <label className="flex items-center justify-between p-4 bg-gray-800/40 hover:bg-gray-800/60 border border-gray-700 rounded-lg cursor-pointer transition-all group">
            <div className="flex-1">
              <span className="text-sm text-gray-300 font-medium block group-hover:text-white transition-colors">
                Sync Navigation
              </span>
              <span className="text-xs text-gray-500 block mt-1">
                Keep both views in sync
              </span>
            </div>
            <input
              type="checkbox"
              checked={syncEnabled}
              onChange={(e) => setSyncEnabled(e.target.checked)}
              className="w-5 h-5 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-2 focus:ring-blue-500 cursor-pointer ml-3"
            />
          </label>
        </div>
      )}

      {comparisonMode === "overlay" && (
        <div>
          <h4 className="text-xs uppercase tracking-wider text-gray-400 mb-3 font-semibold">
            Settings
          </h4>
          <div className="p-4 bg-gray-800/40 border border-gray-700 rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm text-gray-300 font-medium">
                Overlay Opacity
              </label>
              <span className="text-sm text-blue-400 font-semibold min-w-[3rem] text-right">
                {opacity}%
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={opacity}
              onChange={(e) => setOpacity(Number(e.target.value))}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
              style={{
                background: `linear-gradient(to right, rgb(59 130 246) 0%, rgb(59 130 246) ${opacity}%, rgb(55 65 81) ${opacity}%, rgb(55 65 81) 100%)`,
              }}
            />
            <div className="flex justify-between text-xs text-gray-500">
              <span>Base Only</span>
              <span>50/50</span>
              <span>Overlay Only</span>
            </div>
          </div>
        </div>
      )}

      {/* Current Selection Info */}
      <div>
        <h4 className="text-xs uppercase tracking-wider text-gray-400 mb-3 font-semibold">
          Active Comparison
        </h4>
        <div className="space-y-2">
          <div className="flex items-center gap-3 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-blue-400 mb-0.5">Base Dataset</p>
              <p className="text-sm text-white font-medium truncate">
                {dataset.name}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-purple-500/10 border border-purple-500/20 rounded-lg">
            <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-purple-400 mb-0.5">Compare Dataset</p>
              <p className="text-sm text-white font-medium truncate">
                {secondDataset.name}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ComparisonControls;
