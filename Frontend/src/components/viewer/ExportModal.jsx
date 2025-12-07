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

    setExportProgress("Preparing export...");

    try {
      const viewer = viewerRef.current;
      const viewport = viewer.viewport;
      const tiledImage = viewer.world.getItemAt(0);

      if (!tiledImage) {
        throw new Error("No image loaded in viewer");
      }

      // Get viewport bounds in image coordinates
      const viewportBounds = viewport.getBounds(true);
      const imageBounds = tiledImage.viewportToImageRectangle(viewportBounds);

      // Calculate dimensions based on quality
      const quality = getQualityValue();
      const scaleFactor = quality === 1.0 ? 1.0 : quality === 0.8 ? 0.75 : 0.5;

      const width = Math.floor(imageBounds.width * scaleFactor);
      const height = Math.floor(imageBounds.height * scaleFactor);

      setExportProgress(`Fetching tiles (${width}×${height})...`);

      // Create canvas for export
      const exportCanvas = document.createElement("canvas");
      exportCanvas.width = width;
      exportCanvas.height = height;
      const ctx = exportCanvas.getContext("2d");

      // Set white background instead of black
      ctx.fillStyle = "#FFFFFF";
      ctx.fillRect(0, 0, width, height);

      // Get current zoom level - use the lowest level (0) which has all tiles
      // Level 0 is the base level that covers entire image
      const currentLevel = 0;

      // Calculate tile coordinates for level 0
      const tileSize = dataset.tile_size || 256;
      const tilesX = Math.ceil(dataset.width / tileSize);
      const tilesY = Math.ceil(dataset.height / tileSize);

      // Get viewport bounds to determine which tiles to fetch
      const viewportBounds = viewport.getBounds(true);
      const tiledImage = viewer.world.getItemAt(0);
      const imageBounds = tiledImage.viewportToImageRectangle(viewportBounds);

      const startX = Math.max(0, Math.floor(imageBounds.x / tileSize));
      const startY = Math.max(0, Math.floor(imageBounds.y / tileSize));
      const endX = Math.min(
        tilesX,
        Math.ceil((imageBounds.x + imageBounds.width) / tileSize)
      );
      const endY = Math.min(
        tilesY,
        Math.ceil((imageBounds.y + imageBounds.height) / tileSize)
      );

      const totalTiles = (endX - startX) * (endY - startY);
      let loadedTiles = 0;

      setExportProgress(
        `Fetching ${totalTiles} tiles from level ${currentLevel}...`
      );
      const tilePromises = [];

      for (let x = startX; x < endX; x++) {
        for (let y = startY; y < endY; y++) {
          const tilePromise = (async () => {
            try {
              const tileUrl = `${window.location.origin}/api/tiles/${dataset.id}/${currentLevel}/${x}/${y}.png`;

              const response = await fetch(tileUrl, { credentials: "include" });
              if (!response.ok) {
                console.debug(
                  `Tile ${currentLevel}/${x}/${y} not available (status ${response.status})`
                );
                return;
              }

              const blob = await response.blob();
              const img = await createImageBitmap(blob);

              // Calculate position on canvas
              const canvasX = (x * tileSize - imageBounds.x) * scaleFactor;
              const canvasY = (y * tileSize - imageBounds.y) * scaleFactor;
              const canvasTileSize = tileSize * scaleFactor;

              ctx.drawImage(
                img,
                canvasX,
                canvasY,
                canvasTileSize,
                canvasTileSize
              );

              loadedTiles++;
              if (loadedTiles % 5 === 0 || loadedTiles === totalTiles) {
                setExportProgress(
                  `Loading tiles... ${loadedTiles}/${totalTiles}`
                );
              }
            } catch (err) {
              console.debug(
                `Failed to load tile ${currentLevel}/${x}/${y}:`,
                err.message
              );
            }
          })();

          tilePromises.push(tilePromise);
        }
      }

      // Wait for all tiles to load
      await Promise.all(tilePromises);

      setExportProgress("Generating image...");

      // Convert to blob based on format
      const mimeType =
        exportFormat === "jpg"
          ? "image/jpeg"
          : exportFormat === "tiff"
          ? "image/tiff"
          : "image/png";
      const qualityValue =
        exportFormat === "jpg" ? getQualityValue() : undefined;

      const blob = await new Promise((resolve, reject) => {
        exportCanvas.toBlob(
          (blob) => {
            if (blob) resolve(blob);
            else reject(new Error("Failed to create blob"));
          },
          mimeType,
          qualityValue
        );
      });

      setExportProgress("Downloading...");

      // Download the file
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${dataset.name}_export_${Date.now()}.${exportFormat}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Cleanup
      URL.revokeObjectURL(url);
      setExportProgress("Export complete!");

      setTimeout(() => {
        onClose();
        setExporting(false);
        setExportProgress("");
      }, 1500);
    } catch (error) {
      console.error("Export error:", error);
      alert(`Export failed: ${error.message}`);
      setExporting(false);
      setExportProgress("");
    }
  };

  const exportFullImage = async () => {
    setExportProgress("Preparing full image export...");

    try {
      // Get quality settings
      const quality = getQualityValue();
      const scaleFactor = quality === 1.0 ? 1.0 : quality === 0.8 ? 0.75 : 0.5;

      // Calculate canvas dimensions based on quality
      const canvasWidth = Math.floor(dataset.width * scaleFactor);
      const canvasHeight = Math.floor(dataset.height * scaleFactor);

      // Limit maximum export size to prevent browser crash
      const maxDimension = 16384; // Most browsers support up to 16384px
      if (canvasWidth > maxDimension || canvasHeight > maxDimension) {
        throw new Error(
          `Image too large for full export. Use "Current View" mode or select "Low" quality. Max dimension: ${maxDimension}px`
        );
      }

      setExportProgress(`Creating canvas (${canvasWidth}×${canvasHeight})...`);

      // Create canvas
      const exportCanvas = document.createElement("canvas");
      exportCanvas.width = canvasWidth;
      exportCanvas.height = canvasHeight;
      const ctx = exportCanvas.getContext("2d");

      // Fill with white background
      ctx.fillStyle = "#FFFFFF";
      ctx.fillRect(0, 0, canvasWidth, canvasHeight);

      // Determine optimal zoom level - level 0 covers entire image
      const tileSize = dataset.tile_size || 256;
      const optimalLevel = 0; // Always use level 0 which has complete coverage

      // Calculate tiles needed at level 0
      const tilesX = Math.ceil(dataset.width / tileSize);
      const tilesY = Math.ceil(dataset.height / tileSize);
      const totalTiles = tilesX * tilesY;

      let loadedTiles = 0;

      setExportProgress(
        `Loading ${totalTiles} tiles from level ${optimalLevel}...`
      );

      // Load and stitch tiles
      const tilePromises = [];

      for (let x = 0; x < tilesX; x++) {
        for (let y = 0; y < tilesY; y++) {
          const tilePromise = (async () => {
            try {
              const tileUrl = `${window.location.origin}/api/tiles/${dataset.id}/${optimalLevel}/${x}/${y}.png`;

              const response = await fetch(tileUrl, { credentials: "include" });
              if (!response.ok) {
                console.debug(
                  `Tile ${optimalLevel}/${x}/${y} not found (status ${response.status})`
                );
                return;
              }

              const blob = await response.blob();
              if (blob.size === 0) {
                console.debug(`Tile ${optimalLevel}/${x}/${y} is empty`);
                return;
              }

              const img = await createImageBitmap(blob);

              // Calculate position on canvas
              const canvasX = x * tileSize * scaleFactor;
              const canvasY = y * tileSize * scaleFactor;
              const canvasTileSize = tileSize * scaleFactor;

              ctx.drawImage(
                img,
                canvasX,
                canvasY,
                canvasTileSize,
                canvasTileSize
              );

              loadedTiles++;
              if (loadedTiles % 10 === 0 || loadedTiles === totalTiles) {
                setExportProgress(
                  `Loading tiles... ${loadedTiles}/${totalTiles}`
                );
              }
            } catch (err) {
              console.debug(
                `Failed to load tile ${optimalLevel}/${x}/${y}:`,
                err.message
              );
            }
          })();

          tilePromises.push(tilePromise);
        }
      }

      // Wait for all tiles
      await Promise.all(tilePromises);

      setExportProgress("Generating image file...");

      // Convert to blob based on format
      const mimeType =
        exportFormat === "jpg"
          ? "image/jpeg"
          : exportFormat === "tiff"
          ? "image/tiff"
          : "image/png";
      const qualityValue =
        exportFormat === "jpg" ? getQualityValue() : undefined;

      const blob = await new Promise((resolve, reject) => {
        exportCanvas.toBlob(
          (blob) => {
            if (blob) resolve(blob);
            else reject(new Error("Failed to create blob"));
          },
          mimeType,
          qualityValue
        );
      });

      setExportProgress("Downloading...");

      // Download
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${dataset.name}_full_${Date.now()}.${exportFormat}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      URL.revokeObjectURL(url);
      setExportProgress("Export complete!");

      setTimeout(() => {
        onClose();
        setExporting(false);
        setExportProgress("");
      }, 1500);
    } catch (error) {
      console.error("Full export error:", error);
      alert(`Export failed: ${error.message}`);
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
                  <span>Format:</span>
                  <span className="text-white uppercase">{exportFormat}</span>
                </div>
                <div className="flex justify-between">
                  <span>Quality:</span>
                  <span className="text-white capitalize">{exportQuality}</span>
                </div>
                <div className="flex justify-between">
                  <span>Original Size:</span>
                  <span className="text-white">
                    {dataset.width?.toLocaleString()} ×{" "}
                    {dataset.height?.toLocaleString()} px
                  </span>
                </div>
                {exportRegion === "full" && (
                  <div className="flex justify-between">
                    <span>Export Size:</span>
                    <span className="text-white">
                      {(() => {
                        const scale =
                          exportQuality === "high"
                            ? 1.0
                            : exportQuality === "medium"
                            ? 0.75
                            : 0.5;
                        const w = Math.floor(dataset.width * scale);
                        const h = Math.floor(dataset.height * scale);
                        return `${w.toLocaleString()} × ${h.toLocaleString()} px`;
                      })()}
                    </span>
                  </div>
                )}
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
