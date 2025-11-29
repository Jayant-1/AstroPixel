import { Check, Settings as SettingsIcon, X } from "lucide-react";
import { useState } from "react";
import Button from "../ui/Button";

const SettingsModal = ({ isOpen, onClose }) => {
  const [settings, setSettings] = useState({
    showNavigator: true,
    showGrid: false,
    animationTime: 0.5,
    zoomPerScroll: 1.2,
  });

  if (!isOpen) return null;

  const handleToggle = (key) => {
    const newSettings = {
      ...settings,
      [key]: !settings[key],
    };
    setSettings(newSettings);

    // Dispatch event to update viewer settings
    window.dispatchEvent(
      new CustomEvent("viewer-settings-update", {
        detail: newSettings,
      })
    );
  };

  const handleSliderChange = (key, value) => {
    const newSettings = {
      ...settings,
      [key]: parseFloat(value),
    };
    setSettings(newSettings);

    // Dispatch event to update viewer settings
    window.dispatchEvent(
      new CustomEvent("viewer-settings-update", {
        detail: newSettings,
      })
    );
  };

  const handleReset = () => {
    const defaultSettings = {
      showNavigator: true,
      showGrid: false,
      animationTime: 0.5,
      zoomPerScroll: 1.2,
    };
    setSettings(defaultSettings);

    window.dispatchEvent(
      new CustomEvent("viewer-settings-update", {
        detail: defaultSettings,
      })
    );
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div className="bg-gray-900 border border-gray-800 rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-800 sticky top-0 bg-gray-900 z-10">
            <div className="flex items-center gap-2">
              <SettingsIcon className="w-5 h-5 text-blue-500" />
              <h2 className="text-lg font-semibold">Viewer Settings</h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-800 rounded transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-4 space-y-6">
            {/* Display Settings */}
            <div>
              <h3 className="text-sm font-semibold mb-3 text-gray-300">
                Display Options
              </h3>
              <div className="space-y-3">
                <SettingToggle
                  label="Show Navigator"
                  description="Display minimap navigation overlay in bottom-right corner"
                  checked={settings.showNavigator}
                  onChange={() => handleToggle("showNavigator")}
                />
                <SettingToggle
                  label="Show Grid Overlay"
                  description="Display tile boundaries with zoom level and loading order"
                  checked={settings.showGrid}
                  onChange={() => handleToggle("showGrid")}
                />
              </div>
            </div>

            {/* Navigation Settings */}
            <div>
              <h3 className="text-sm font-semibold mb-3 text-gray-300">
                Navigation Controls
              </h3>
              <div className="space-y-3">
                <SettingSlider
                  label="Animation Speed"
                  description="Duration of zoom and pan animations"
                  value={settings.animationTime}
                  min={0}
                  max={2}
                  step={0.1}
                  onChange={(value) =>
                    handleSliderChange("animationTime", value)
                  }
                  format={(val) =>
                    val === 0 ? "Instant" : `${val.toFixed(1)}s`
                  }
                />
                <SettingSlider
                  label="Scroll Zoom Speed"
                  description="How much to zoom in/out with each scroll"
                  value={settings.zoomPerScroll}
                  min={1.1}
                  max={2.5}
                  step={0.1}
                  onChange={(value) =>
                    handleSliderChange("zoomPerScroll", value)
                  }
                  format={(val) => `${val.toFixed(1)}x`}
                />
              </div>
            </div>

            {/* Info */}
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
              <p className="text-xs text-blue-200">
                💡 <strong>Tip:</strong> Enable &quot;Show Grid Overlay&quot; to
                see tile loading details. Adjust animation speed to 0s for
                instant zoom/pan.
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between p-4 border-t border-gray-800 sticky bottom-0 bg-gray-900">
            <Button variant="ghost" onClick={handleReset} size="sm">
              Reset to Defaults
            </Button>
            <Button onClick={onClose}>Done</Button>
          </div>
        </div>
      </div>
    </>
  );
};

// Toggle Component
const SettingToggle = ({ label, description, checked, onChange }) => {
  return (
    <div className="flex items-start justify-between gap-4 p-3 bg-gray-800 rounded-lg">
      <div className="flex-1">
        <div className="text-sm font-medium mb-1">{label}</div>
        <div className="text-xs text-gray-400">{description}</div>
      </div>
      <button
        onClick={onChange}
        className={`relative w-11 h-6 rounded-full transition-colors flex-shrink-0 ${
          checked ? "bg-blue-600" : "bg-gray-700"
        }`}
      >
        <div
          className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
            checked ? "translate-x-5" : ""
          }`}
        >
          {checked && (
            <Check className="w-3 h-3 text-blue-600 absolute top-0.5 left-0.5" />
          )}
        </div>
      </button>
    </div>
  );
};

// Slider Component
const SettingSlider = ({
  label,
  description,
  value,
  min,
  max,
  step,
  onChange,
  format,
}) => {
  return (
    <div className="p-3 bg-gray-800 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <div className="text-sm font-medium">{label}</div>
        <div className="text-sm text-blue-400 font-mono">
          {format ? format(value) : value}
        </div>
      </div>
      <div className="text-xs text-gray-400 mb-3">{description}</div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
      />
    </div>
  );
};

export default SettingsModal;
