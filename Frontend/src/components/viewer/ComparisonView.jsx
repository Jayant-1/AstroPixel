import OpenSeadragon from "openseadragon";
import { useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "../../services/api";
import ComparisonControls from "./ComparisonControls";

const ComparisonView = ({
  dataset,
  renderControlsOnly = false,
  comparisonMode,
  setComparisonMode,
  secondDataset,
  setSecondDataset,
  opacity,
  setOpacity,
  syncEnabled,
  setSyncEnabled,
}) => {
  const [viewersReady, setViewersReady] = useState(false);

  const viewer1Ref = useRef(null);
  const viewer2Ref = useRef(null);
  const container1Ref = useRef(null);
  const container2Ref = useRef(null);
  const syncHandlersRef = useRef(null);

  // Create tile source helper with cache busting
  const createTileSource = (ds) => {
    const tileSize = ds.tile_size || 256;
    const maxLevel = Math.max(
      0,
      ds.max_zoom ??
        Math.ceil(Math.log2(Math.max(ds.width, ds.height) / tileSize))
    );

    // Add version parameter to prevent tile caching issues when switching datasets
    const cacheBust = ds.updated_at
      ? new Date(ds.updated_at).getTime()
      : ds.created_at
      ? new Date(ds.created_at).getTime()
      : Date.now();

    return {
      height: ds.height,
      width: ds.width,
      tileSize: tileSize,
      tileOverlap: 0,
      minLevel: 0,
      maxLevel: maxLevel,
      getTileUrl: function (level, x, y) {
          const token = localStorage.getItem("astropixel_token");
          const base = `${API_BASE_URL}/api/tiles/${ds.id}/${level}/${x}/${y}.png?v=${cacheBust}`;
          return token ? `${base}&token=${token}` : base;
      },
    };
  };

  // Initialize viewers once when datasets change - NOT when mode changes
  useEffect(() => {
    if (renderControlsOnly || !dataset || !secondDataset) return;
    if (!container1Ref.current) return;

    console.log("🎬 Initializing viewers with datasets");
    setViewersReady(false);

    const commonSettings = {
      prefixUrl:
        "https://cdn.jsdelivr.net/npm/openseadragon@4.1/build/openseadragon/images/",
      showNavigationControl: false,
      showNavigator: false,
      animationTime: 0.5,
      blendTime: 0.1,
      constrainDuringPan: false,
      maxZoomPixelRatio: 2,
      minZoomImageRatio: 0.9,
      visibilityRatio: 1.0,
      zoomPerScroll: 1.2,
      gestureSettingsMouse: {
        clickToZoom: false,
        dblClickToZoom: true,
      },
    };

    let mounted = true;
    let readyTimeout = null;

    // Cleanup function
    const cleanup = () => {
      if (readyTimeout) clearTimeout(readyTimeout);

      // Clean up sync handlers first
      if (syncHandlersRef.current) {
        const { viewer1, viewer2, handlers } = syncHandlersRef.current;
        if (viewer1) {
          try {
            viewer1.removeHandler("zoom", handlers.zoom1To2);
            viewer1.removeHandler("pan", handlers.pan1To2);
          } catch (e) {
            // Handlers already removed or viewer destroyed
          }
        }
        if (viewer2) {
          try {
            viewer2.removeHandler("zoom", handlers.zoom2To1);
            viewer2.removeHandler("pan", handlers.pan2To1);
          } catch (e) {
            // Handlers already removed or viewer destroyed
          }
        }
        syncHandlersRef.current = null;
      }

      // Destroy viewers
      if (viewer1Ref.current) {
        try {
          viewer1Ref.current.destroy();
        } catch (e) {
          console.warn("Error destroying viewer1:", e);
        }
        viewer1Ref.current = null;
      }
      if (viewer2Ref.current) {
        try {
          viewer2Ref.current.destroy();
        } catch (e) {
          console.warn("Error destroying viewer2:", e);
        }
        viewer2Ref.current = null;
      }
    };

    // Cleanup existing viewers first
    cleanup();

    // Immediately initialize viewers without delay
    if (!container1Ref.current || !container2Ref.current) return;

    console.log("🎬 Setting up DUAL VIEWERS for both modes");

    // Initialize BOTH viewers regardless of mode - mode just controls visibility
    viewer1Ref.current = OpenSeadragon({
      ...commonSettings,
      element: container1Ref.current,
      tileSources: createTileSource(dataset),
    });

    viewer2Ref.current = OpenSeadragon({
      ...commonSettings,
      element: container2Ref.current,
      tileSources: createTileSource(secondDataset),
    });

    let viewer1Ready = false;
    let viewer2Ready = false;

    const checkReady = () => {
      if (viewer1Ready && viewer2Ready && mounted) {
        console.log("✅ Both viewers ready!");
        setViewersReady(true);
        if (readyTimeout) clearTimeout(readyTimeout);
      }
    };

    viewer1Ref.current.addOnceHandler("open", () => {
      console.log("✅ Viewer 1 opened");
      viewer1Ready = true;
      checkReady();
    });

    viewer2Ref.current.addOnceHandler("open", () => {
      console.log("✅ Viewer 2 opened");
      viewer2Ready = true;
      checkReady();
    });

    // Fallback timeout if events don't fire
    readyTimeout = setTimeout(() => {
      if (mounted && (!viewer1Ready || !viewer2Ready)) {
        console.log("⏱️ Timeout fallback - forcing ready state");
        setViewersReady(true);
      }
    }, 2000);

    return () => {
      mounted = false;
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataset?.id, secondDataset?.id, renderControlsOnly]);

  // Handle comparison mode changes without destroying viewers
  useEffect(() => {
    if (!viewer1Ref.current || !viewersReady) return;

    if (comparisonMode === "overlay") {
      console.log("🎬 Setting up OVERLAY mode");

      // Check if overlay already exists
      const itemCount = viewer1Ref.current.world.getItemCount();

      // Always remove old overlay if it exists (even if dataset didn't change)
      // to ensure we're loading the correct tile dataset
      if (itemCount > 1) {
        console.log("🗑️ Removing existing overlay");
        try {
          viewer1Ref.current.world.removeItem(
            viewer1Ref.current.world.getItemAt(1)
          );
        } catch (e) {
          console.warn("Could not remove old overlay:", e);
        }
      }

      // Add fresh overlay image with current dataset
      console.log(
        "📸 Adding fresh overlay image for dataset:",
        secondDataset.id
      );
      viewer1Ref.current.addTiledImage({
        tileSource: createTileSource(secondDataset),
        opacity: opacity / 100,
        success: () => {
          console.log("✅ Overlay image added successfully");
        },
        error: (e) => {
          console.error("❌ Failed to add overlay image:", e);
        },
      });
    } else if (comparisonMode === "sideBySide") {
      console.log("🔄 Mode changed to SIDE-BY-SIDE");
      // Remove overlay image if it exists
      const itemCount = viewer1Ref.current.world.getItemCount();
      if (itemCount > 1) {
        console.log("🗑️ Removing overlay image");
        try {
          viewer1Ref.current.world.removeItem(
            viewer1Ref.current.world.getItemAt(1)
          );
        } catch (e) {
          console.warn("Could not remove overlay:", e);
        }
      }
    }
  }, [comparisonMode, viewersReady, secondDataset?.id, opacity]);

  // Set and update overlay opacity
  useEffect(() => {
    if (!viewersReady || comparisonMode !== "overlay" || !viewer1Ref.current) {
      return;
    }

    console.log("🎨 Updating overlay opacity to:", opacity);

    // Get the overlay image (second item in world)
    if (viewer1Ref.current.world.getItemCount() > 1) {
      const overlayItem = viewer1Ref.current.world.getItemAt(1);
      if (overlayItem) {
        overlayItem.setOpacity(opacity / 100);
        console.log("✅ Overlay opacity updated:", opacity / 100);
      }
    }
  }, [opacity, viewersReady, comparisonMode]);

  // Handle synchronization
  useEffect(() => {
    if (
      !viewersReady ||
      comparisonMode !== "sideBySide" ||
      !viewer1Ref.current ||
      !viewer2Ref.current
    ) {
      // Clean up existing handlers if conditions no longer met
      if (syncHandlersRef.current) {
        console.log("🧹 Cleaning up sync handlers (conditions not met)");
        const { viewer1, viewer2, handlers } = syncHandlersRef.current;
        if (viewer1) {
          viewer1.removeHandler("zoom", handlers.zoom1To2);
          viewer1.removeHandler("pan", handlers.pan1To2);
        }
        if (viewer2) {
          viewer2.removeHandler("zoom", handlers.zoom2To1);
          viewer2.removeHandler("pan", handlers.pan2To1);
        }
        syncHandlersRef.current = null;
      }
      return;
    }

    // If sync is disabled, remove handlers
    if (!syncEnabled) {
      console.log("❌ Sync DISABLED - removing synchronization");
      if (syncHandlersRef.current) {
        const { viewer1, viewer2, handlers } = syncHandlersRef.current;
        if (viewer1) {
          viewer1.removeHandler("zoom", handlers.zoom1To2);
          viewer1.removeHandler("pan", handlers.pan1To2);
        }
        if (viewer2) {
          viewer2.removeHandler("zoom", handlers.zoom2To1);
          viewer2.removeHandler("pan", handlers.pan2To1);
        }
        syncHandlersRef.current = null;
      }
      return;
    }

    // If already synced, don't re-add handlers
    if (syncHandlersRef.current) {
      console.log("🔗 Sync handlers already active, skipping re-add");
      return;
    }

    // Enable sync - add handlers
    console.log("✅ Sync ENABLED - adding synchronization handlers");

    const handlers = {
      zoom1To2: (e) => {
        if (!e.immediately && viewer2Ref.current) {
          viewer2Ref.current.viewport.zoomTo(e.zoom, e.refPoint, true);
        }
      },
      pan1To2: (e) => {
        if (!e.immediately && viewer2Ref.current) {
          viewer2Ref.current.viewport.panTo(e.center, true);
        }
      },
      zoom2To1: (e) => {
        if (!e.immediately && viewer1Ref.current) {
          viewer1Ref.current.viewport.zoomTo(e.zoom, e.refPoint, true);
        }
      },
      pan2To1: (e) => {
        if (!e.immediately && viewer1Ref.current) {
          viewer1Ref.current.viewport.panTo(e.center, true);
        }
      },
    };

    // Add synchronization handlers
    viewer1Ref.current.addHandler("zoom", handlers.zoom1To2);
    viewer1Ref.current.addHandler("pan", handlers.pan1To2);
    viewer2Ref.current.addHandler("zoom", handlers.zoom2To1);
    viewer2Ref.current.addHandler("pan", handlers.pan2To1);

    // Store handlers for cleanup
    syncHandlersRef.current = {
      viewer1: viewer1Ref.current,
      viewer2: viewer2Ref.current,
      handlers,
    };

    console.log("✅ Sync handlers added");

    return () => {
      console.log("🧹 Sync effect cleanup");
      if (syncHandlersRef.current) {
        const { viewer1, viewer2, handlers: stored } = syncHandlersRef.current;
        if (viewer1) {
          viewer1.removeHandler("zoom", stored.zoom1To2);
          viewer1.removeHandler("pan", stored.pan1To2);
        }
        if (viewer2) {
          viewer2.removeHandler("zoom", stored.zoom2To1);
          viewer2.removeHandler("pan", stored.pan2To1);
        }
        syncHandlersRef.current = null;
      }
    };
  }, [viewersReady, syncEnabled, comparisonMode]);

  // Render controls only for sidebar
  if (renderControlsOnly) {
    if (!secondDataset) {
      return (
        <div className="p-4 text-center">
          <p className="text-gray-400 text-sm mb-2">No datasets available</p>
          <p className="text-xs text-gray-500">
            Upload more datasets to enable comparison
          </p>
        </div>
      );
    }

    return (
      <ComparisonControls
        dataset={dataset}
        secondDataset={secondDataset}
        setSecondDataset={setSecondDataset}
        comparisonMode={comparisonMode}
        setComparisonMode={setComparisonMode}
        syncEnabled={syncEnabled}
        setSyncEnabled={setSyncEnabled}
        opacity={opacity}
        setOpacity={setOpacity}
      />
    );
  }

  // Show message if no second dataset
  if (!secondDataset) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <p className="text-gray-400 mb-2">No datasets available to compare</p>
          <p className="text-sm text-gray-500">
            Upload more datasets to enable comparison
          </p>
        </div>
      </div>
    );
  }

  // Render comparison view
  return (
    <div className="w-full h-full relative overflow-hidden bg-gray-900">
      {/* Container wrapper that never unmounts - prevents React DOM conflicts */}
      <div className="w-full h-full" suppressHydrationWarning>
        {/* Left Viewer Container - visible in both side-by-side and overlay modes */}
        <div
          key="viewer1-container"
          className={`absolute inset-0 transition-opacity duration-300 ${
            comparisonMode === "sideBySide"
              ? "left-0 right-1/2 border-r border-gray-700 opacity-100"
              : comparisonMode === "overlay"
              ? "left-0 right-0 opacity-100"
              : "opacity-0 pointer-events-none"
          }`}
        >
          <div
            ref={container1Ref}
            className="w-full h-full"
            suppressHydrationWarning
          />
        </div>

        {/* Right Viewer Container - only visible in side-by-side mode */}
        <div
          key="viewer2-container"
          className={`absolute inset-0 left-1/2 right-0 transition-opacity duration-300 ${
            comparisonMode === "sideBySide"
              ? "opacity-100"
              : "opacity-0 pointer-events-none"
          }`}
        >
          <div
            ref={container2Ref}
            className="w-full h-full"
            suppressHydrationWarning
          />
        </div>

        {/* Side-by-side Labels */}
        {comparisonMode === "sideBySide" && (
          <>
            <div className="absolute top-4 left-4 bg-blue-600/90 backdrop-blur-sm px-3 py-1.5 rounded-lg pointer-events-none z-10">
              <span className="text-sm font-medium">{dataset.name}</span>
            </div>
            <div className="absolute top-4 right-4 bg-purple-600/90 backdrop-blur-sm px-3 py-1.5 rounded-lg pointer-events-none z-10">
              <span className="text-sm font-medium">{secondDataset.name}</span>
            </div>
          </>
        )}

        {/* Overlay Labels */}
        {comparisonMode === "overlay" && (
          <div className="absolute top-4 left-4 flex flex-col gap-2 z-10 pointer-events-none">
            <div className="bg-blue-600/90 backdrop-blur-sm px-3 py-1.5 rounded-lg">
              <span className="text-sm font-medium">{dataset.name} (Base)</span>
            </div>
            <div className="bg-purple-600/90 backdrop-blur-sm px-3 py-1.5 rounded-lg">
              <span className="text-sm font-medium">
                {secondDataset.name} (Overlay - {opacity}%)
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ComparisonView;
