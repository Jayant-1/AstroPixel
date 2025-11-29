import { Download, Image, X } from "lucide-react";
import { useState } from "react";
import Button from "../ui/Button";

const ExportModal = ({ isOpen, onClose, dataset }) => {
  const [exportFormat, setExportFormat] = useState("png");
  const [exportQuality, setExportQuality] = useState("high");
  const [exportRegion, setExportRegion] = useState("current");

  if (!isOpen) return null;

  const handleExport = () => {
    // Get current viewport if exporting current view
    const event = new CustomEvent("viewer-export-request", {
      detail: {
        format: exportFormat,
        quality: exportQuality,
        region: exportRegion,
        datasetId: dataset.id,
      },
    });
    window.dispatchEvent(event);

    // For now, just show alert
    alert(
      `Export requested:\nFormat: ${exportFormat}\nQuality: ${exportQuality}\nRegion: ${exportRegion}`
    );
    onClose();
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
        <div className="bg-gray-900 border border-gray-800 rounded-lg shadow-xl max-w-md w-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-800">
            <div className="flex items-center gap-2">
              <Download className="w-5 h-5 text-blue-500" />
              <h2 className="text-lg font-semibold">Export Image</h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-800 rounded transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-4 space-y-4">
            {/* Export Region */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Export Region
              </label>
              <div className="space-y-2">
                <label className="flex items-center gap-2 p-3 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-750 transition-colors">
                  <input
                    type="radio"
                    name="region"
                    value="current"
                    checked={exportRegion === "current"}
                    onChange={(e) => setExportRegion(e.target.value)}
                    className="w-4 h-4"
                  />
                  <div>
                    <div className="text-sm font-medium">Current View</div>
                    <div className="text-xs text-gray-400">
                      Export what you see in the viewport
                    </div>
                  </div>
                </label>
                <label className="flex items-center gap-2 p-3 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-750 transition-colors">
                  <input
                    type="radio"
                    name="region"
                    value="full"
                    checked={exportRegion === "full"}
                    onChange={(e) => setExportRegion(e.target.value)}
                    className="w-4 h-4"
                  />
                  <div>
                    <div className="text-sm font-medium">Full Image</div>
                    <div className="text-xs text-gray-400">
                      Export entire {dataset.width} × {dataset.height} px image
                    </div>
                  </div>
                </label>
              </div>
            </div>

            {/* Format */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Image Format
              </label>
              <div className="grid grid-cols-3 gap-2">
                {["png", "jpg", "tiff"].map((format) => (
                  <button
                    key={format}
                    onClick={() => setExportFormat(format)}
                    className={`p-3 rounded-lg border-2 transition-all ${
                      exportFormat === format
                        ? "border-blue-500 bg-blue-500/10"
                        : "border-gray-700 bg-gray-800 hover:border-gray-600"
                    }`}
                  >
                    <Image className="w-5 h-5 mx-auto mb-1" />
                    <div className="text-xs font-medium uppercase">
                      {format}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Quality */}
            <div>
              <label className="block text-sm font-medium mb-2">Quality</label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { value: "low", label: "Low" },
                  { value: "medium", label: "Medium" },
                  { value: "high", label: "High" },
                ].map((quality) => (
                  <button
                    key={quality.value}
                    onClick={() => setExportQuality(quality.value)}
                    className={`p-2 rounded-lg border-2 transition-all text-sm ${
                      exportQuality === quality.value
                        ? "border-blue-500 bg-blue-500/10"
                        : "border-gray-700 bg-gray-800 hover:border-gray-600"
                    }`}
                  >
                    {quality.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Info */}
            <div className="bg-gray-800 rounded-lg p-3">
              <div className="text-xs text-gray-400 space-y-1">
                <div className="flex justify-between">
                  <span>Dataset:</span>
                  <span className="text-white">{dataset.name}</span>
                </div>
                <div className="flex justify-between">
                  <span>Dimensions:</span>
                  <span className="text-white">
                    {dataset.width?.toLocaleString()} ×{" "}
                    {dataset.height?.toLocaleString()} px
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Estimated Size:</span>
                  <span className="text-white">
                    {exportRegion === "full" ? "~500 MB" : "~10 MB"}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-2 p-4 border-t border-gray-800">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button onClick={handleExport} className="gap-2">
              <Download className="w-4 h-4" />
              Export
            </Button>
          </div>
        </div>
      </div>
    </>
  );
};

export default ExportModal;
