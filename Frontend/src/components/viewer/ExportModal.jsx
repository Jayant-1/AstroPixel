import { Download, Image, Loader2, X } from "lucide-react";
import { useState } from "react";
import Button from "../ui/Button";

const ExportModal = ({ isOpen, onClose, dataset, viewerRef }) => {
  const [exportFormat, setExportFormat] = useState("png");
  const [exportQuality, setExportQuality] = useState("high");
  const [exportRegion, setExportRegion] = useState("current");
  const [exporting, setExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState("");

  if (!isOpen) return null;

  const getQualityValue = () => {
    const qualities = { low: 0.6, medium: 0.8, high: 1.0 };
    return qualities[exportQuality] || 1.0;
  };

  const exportCurrentView = async () => {
    if (!viewerRef?.current) {
      alert("Viewer not ready. Please try again.");
      return;
    }

    setExportProgress("Capturing current view...");

    try {
      const viewer = viewerRef.current;
      const canvas = viewer.drawer.canvas;

      // Get the canvas from OpenSeadragon
      const exportCanvas = document.createElement("canvas");
      const ctx = exportCanvas.getContext("2d");

      // Set canvas size to match viewport
      exportCanvas.width = canvas.width;
      exportCanvas.height = canvas.height;

      // Draw the current view
      ctx.drawImage(canvas, 0, 0);

      setExportProgress("Generating image...");

      // Convert to blob
      const quality = getQualityValue();
      const mimeType = exportFormat === "jpg" ? "image/jpeg" : "image/png";

      exportCanvas.toBlob(
        (blob) => {
          if (blob) {
            setExportProgress("Downloading...");

            // Create download link
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `${
              dataset.name
            }_export_${Date.now()}.${exportFormat}`;
            link.click();

            // Cleanup
            URL.revokeObjectURL(url);
            setExportProgress("Export complete!");

            setTimeout(() => {
              onClose();
              setExporting(false);
              setExportProgress("");
            }, 1000);
          } else {
            throw new Error("Failed to create blob");
          }
        },
        mimeType,
        quality
      );
    } catch (error) {
      console.error("Export error:", error);
      alert(`Export failed: ${error.message}`);
      setExporting(false);
      setExportProgress("");
    }
  };

  const exportFullImage = async () => {
    setExportProgress("Fetching full resolution image...");

    try {
      // For full image export, we'll download the highest zoom level tiles
      // and stitch them together or use the backend API

      // Option 1: Use backend API to generate full image (if available)
      // Option 2: Download and stitch tiles client-side

      // For now, we'll download the base level tile
      const response = await fetch(
        `${window.location.origin}/api/tiles/${dataset.id}/0/0/0.${exportFormat}`,
        { credentials: "include" }
      );

      if (!response.ok) throw new Error("Failed to fetch image");

      setExportProgress("Downloading...");
      const blob = await response.blob();

      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${dataset.name}_full.${exportFormat}`;
      link.click();

      URL.revokeObjectURL(url);
      setExportProgress("Export complete!");

      setTimeout(() => {
        onClose();
        setExporting(false);
        setExportProgress("");
      }, 1000);
    } catch (error) {
      console.error("Export error:", error);
      alert(
        `Export failed: ${error.message}. Try exporting current view instead.`
      );
      setExporting(false);
      setExportProgress("");
    }
  };

  const handleExport = async () => {
    setExporting(true);

    try {
      if (exportRegion === "current") {
        await exportCurrentView();
      } else {
        await exportFullImage();
      }
    } catch (error) {
      console.error("Export error:", error);
      alert(`Export failed: ${error.message}`);
      setExporting(false);
      setExportProgress("");
    }
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

          {/* Export Progress */}
          {exporting && (
            <div className="px-4 pb-2">
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
                <div className="flex items-center gap-2 text-blue-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">{exportProgress}</span>
                </div>
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-end gap-2 p-4 border-t border-gray-800">
            <Button variant="ghost" onClick={onClose} disabled={exporting}>
              Cancel
            </Button>
            <Button
              onClick={handleExport}
              className="gap-2"
              disabled={exporting}
            >
              {exporting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              {exporting ? "Exporting..." : "Export"}
            </Button>
          </div>
        </div>
      </div>
    </>
  );
};

export default ExportModal;
