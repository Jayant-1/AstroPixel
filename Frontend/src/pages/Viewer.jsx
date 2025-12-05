import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Download,
  Eye,
  GitCompare,
  Maximize2,
  Settings,
  Tag,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Button from "../components/ui/Button";
import AnnotationTools from "../components/viewer/AnnotationTools";
import AnnotationsList from "../components/viewer/AnnotationsList";
import ComparisonControls from "../components/viewer/ComparisonControls";
import ComparisonView from "../components/viewer/ComparisonView";
import ExportModal from "../components/viewer/ExportModal";
import SettingsModal from "../components/viewer/SettingsModal";
import ViewerCanvas from "../components/viewer/ViewerCanvas";
import ViewerInfo from "../components/viewer/ViewerInfo";
import { useApp } from "../context/AppContext";
import { cn } from "../utils/helpers";

const Viewer = () => {
  const { datasetId } = useParams();
  const navigate = useNavigate();
  const {
    datasets,
    selectedDataset,
    setSelectedDataset,
    viewMode,
    setViewMode,
    sidebarOpen,
    setSidebarOpen,
    loading,
  } = useApp();

  const [isFullscreen, setIsFullscreen] = useState(false); // eslint-disable-line no-unused-vars
  const [viewerReady, setViewerReady] = useState(false);
  const [viewportInfo, setViewportInfo] = useState({
    zoom: "1.0",
    position: { x: 0, y: 0 },
  });
  const [showExportModal, setShowExportModal] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);

  // Comparison view state - shared between sidebar and main canvas
  const [comparisonMode, setComparisonMode] = useState("sideBySide");
  const [secondDataset, setSecondDataset] = useState(null);
  const [opacity, setOpacity] = useState(50);
  const [syncEnabled, setSyncEnabled] = useState(true);

  // Clear selectedDataset immediately when datasetId changes to prevent overlap
  useEffect(() => {
    // If the URL datasetId doesn't match the current selectedDataset, clear it
    if (selectedDataset && String(selectedDataset.id) !== String(datasetId)) {
      console.log("🔄 Dataset ID changed, clearing old dataset");
      setSelectedDataset(null);
    }
  }, [datasetId, selectedDataset, setSelectedDataset]);

  useEffect(() => {
    // Wait for datasets to load before checking
    if (loading) return;

    // Find and set the dataset - handle both string and number IDs
    const dataset = datasets.find((d) => {
      // Try both strict match and type-converted match
      return (
        d.id === datasetId ||
        d.id === Number(datasetId) ||
        String(d.id) === datasetId
      );
    });

    if (dataset) {
      setSelectedDataset(dataset);
    } else if (datasets.length > 0) {
      // Only redirect to 404 if datasets are loaded and dataset not found
      console.error(
        `Dataset not found: ${datasetId}. Available IDs:`,
        datasets.map((d) => d.id)
      );
      navigate("/404");
    }
  }, [datasetId, datasets, setSelectedDataset, navigate, loading]);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () =>
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  // Listen for viewport updates from ViewerCanvas
  useEffect(() => {
    const handleViewportUpdate = (event) => {
      const { zoom, center } = event.detail;
      setViewportInfo({
        zoom: zoom,
        position: center,
      });
    };

    window.addEventListener("viewer-viewport-update", handleViewportUpdate);
    return () => {
      window.removeEventListener(
        "viewer-viewport-update",
        handleViewportUpdate
      );
    };
  }, []);

  // Auto-manage sidebar state based on view mode
  useEffect(() => {
    if (viewMode === "explore") {
      // Explore: No sidebars by default
      setSidebarOpen({ left: false, right: false });
    } else if (viewMode === "annotate") {
      // Annotate: Both sidebars open
      setSidebarOpen({ left: true, right: true });
    } else if (viewMode === "compare") {
      // Compare: Left sidebar for controls, right closed
      setSidebarOpen({ left: true, right: false });
    }
  }, [viewMode, setSidebarOpen]);

  // Initialize comparison datasets when entering compare mode
  useEffect(() => {
    if (viewMode === "compare" && secondDataset === null && selectedDataset) {
      const availableDatasets = datasets.filter(
        (d) => d.id !== selectedDataset.id
      );
      if (availableDatasets.length > 0) {
        console.log(
          "🎯 Initializing secondDataset with:",
          availableDatasets[0].name
        );
        setSecondDataset(availableDatasets[0]);
      }
    }
  }, [viewMode, selectedDataset, datasets, secondDataset]);

  // CRITICAL: Check if selectedDataset matches URL datasetId
  // This prevents rendering ViewerCanvas with wrong dataset (causes image overlap)
  const isCorrectDataset =
    selectedDataset &&
    (String(selectedDataset.id) === String(datasetId) ||
      selectedDataset.id === Number(datasetId));

  if (!selectedDataset || !isCorrectDataset) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-950">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading dataset...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-950 text-white overflow-hidden">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          {/* Left: Back & Title */}
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate("/dashboard")}
              className="gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </Button>

            <div className="h-8 w-px bg-gray-700" />

            <div>
              <h1 className="text-lg font-semibold">{selectedDataset.name}</h1>
              <p className="text-xs text-gray-400">
                {selectedDataset.width?.toLocaleString()} ×{" "}
                {selectedDataset.height?.toLocaleString()} px
              </p>
            </div>
          </div>

          {/* Center: View Mode Tabs */}
          <div className="flex items-center gap-2 bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => setViewMode("explore")}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-md transition-all text-sm",
                viewMode === "explore"
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white"
              )}
            >
              <Eye className="w-4 h-4" />
              Explore
            </button>
            <button
              onClick={() => setViewMode("annotate")}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-md transition-all text-sm",
                viewMode === "annotate"
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white"
              )}
            >
              <Tag className="w-4 h-4" />
              Annotate
            </button>
            <button
              onClick={() => setViewMode("compare")}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-md transition-all text-sm",
                viewMode === "compare"
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white"
              )}
            >
              <GitCompare className="w-4 h-4" />
              Compare
            </button>
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={toggleFullscreen}>
              <Maximize2 className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowExportModal(true)}
            >
              <Download className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowSettingsModal(true)}
            >
              <Settings className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        {sidebarOpen.left ? (
          <aside className="w-80 bg-gray-900 border-r border-gray-800 flex flex-col">
            <div className="p-4 border-b border-gray-800 flex items-center justify-between">
              <h2 className="font-semibold flex items-center gap-2">
                {viewMode === "annotate" && <Tag className="w-5 h-5" />}
                {viewMode === "compare" && <GitCompare className="w-5 h-5" />}
                {viewMode === "explore" && <Eye className="w-5 h-5" />}
                {viewMode === "annotate" && "Annotation Tools"}
                {viewMode === "compare" && "Comparison"}
                {viewMode === "explore" && "Dataset Info"}
              </h2>
              <button
                onClick={() =>
                  setSidebarOpen((prev) => ({ ...prev, left: false }))
                }
                className="p-1 hover:bg-gray-800 rounded"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar">
              {viewMode === "annotate" && <AnnotationTools />}
              {viewMode === "explore" && (
                <ViewerInfo dataset={selectedDataset} />
              )}
              {viewMode === "compare" && (
                <ComparisonView
                  dataset={selectedDataset}
                  renderControlsOnly={true}
                  comparisonMode={comparisonMode}
                  setComparisonMode={setComparisonMode}
                  secondDataset={secondDataset}
                  setSecondDataset={setSecondDataset}
                  opacity={opacity}
                  setOpacity={setOpacity}
                  syncEnabled={syncEnabled}
                  setSyncEnabled={setSyncEnabled}
                />
              )}
            </div>
          </aside>
        ) : (
          <button
            onClick={() => setSidebarOpen((prev) => ({ ...prev, left: true }))}
            className="w-12 bg-gray-900 border-r border-gray-800 flex items-center justify-center hover:bg-gray-800"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        )}

        {/* Viewer Canvas */}
        <div className="flex-1 relative bg-gray-900">
          {viewMode === "compare" ? (
            <ComparisonView
              key={`compare-${selectedDataset.id}`}
              dataset={selectedDataset}
              renderControlsOnly={false}
              comparisonMode={comparisonMode}
              setComparisonMode={setComparisonMode}
              secondDataset={secondDataset}
              setSecondDataset={setSecondDataset}
              opacity={opacity}
              setOpacity={setOpacity}
              syncEnabled={syncEnabled}
              setSyncEnabled={setSyncEnabled}
            />
          ) : (
            <ViewerCanvas
              key={`viewer-${selectedDataset.id}`}
              dataset={selectedDataset}
              mode={viewMode}
              onReady={() => setViewerReady(true)}
            />
          )}
        </div>

        {/* Right Sidebar - Only in Annotate mode */}
        {viewMode === "annotate" && (
          <>
            {sidebarOpen.right ? (
              <aside className="w-80 bg-gray-900 border-l border-gray-800 flex flex-col">
                <div className="p-4 border-b border-gray-800 flex items-center justify-between">
                  <h2 className="font-semibold flex items-center gap-2">
                    <Tag className="w-5 h-5" />
                    Annotations
                  </h2>
                  <button
                    onClick={() =>
                      setSidebarOpen((prev) => ({ ...prev, right: false }))
                    }
                    className="p-1 hover:bg-gray-800 rounded"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto custom-scrollbar">
                  <AnnotationsList />
                </div>
              </aside>
            ) : (
              <button
                onClick={() =>
                  setSidebarOpen((prev) => ({ ...prev, right: true }))
                }
                className="w-12 bg-gray-900 border-l border-gray-800 flex items-center justify-center hover:bg-gray-800"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
            )}
          </>
        )}
      </div>

      {/* Status Bar */}
      <footer className="bg-gray-900 border-t border-gray-800 px-6 py-2 flex items-center justify-between text-xs text-gray-400 flex-shrink-0">
        <div className="flex items-center gap-4">
          <span className="text-green-400">● Ready</span>
          <span>•</span>
          <span>Zoom: {viewerReady ? `${viewportInfo.zoom}x` : "-"}</span>
          <span>•</span>
          <span>
            Position:{" "}
            {viewerReady
              ? `${viewportInfo.position.x.toFixed(
                  3
                )}, ${viewportInfo.position.y.toFixed(3)}`
              : "-"}
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span>{selectedDataset.category?.toUpperCase()}</span>
          <span>•</span>
          <span>
            {selectedDataset.width?.toLocaleString()} ×{" "}
            {selectedDataset.height?.toLocaleString()} px
          </span>
        </div>
      </footer>

      {/* Modals */}
      <ExportModal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        dataset={selectedDataset}
      />
      <SettingsModal
        isOpen={showSettingsModal}
        onClose={() => setShowSettingsModal(false)}
      />
    </div>
  );
};

export default Viewer;
