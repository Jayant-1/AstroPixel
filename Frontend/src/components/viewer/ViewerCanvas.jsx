import OpenSeadragon from "openseadragon";
import { useEffect, useRef, useState } from "react";
import { useApp } from "../../context/AppContext";
import { API_BASE_URL } from "../../services/api";
import TileLoadingOverlay from "./TileLoadingOverlay";

const ViewerCanvas = ({
  dataset,
  onReady,
  mode,
  viewerRef: externalViewerRef,
}) => {
  const internalViewerRef = useRef(null);
  const viewerRef = externalViewerRef || internalViewerRef;
  const containerRef = useRef(null);
  const onReadyRef = useRef(onReady);
  const [viewer, setViewer] = useState(null);
  const initializedDatasetIdRef = useRef(null);
  const overlayRef = useRef(null);
  const [isDrawingActive, setIsDrawingActive] = useState(false);
  const drawingStateRef = useRef({
    isDrawing: false,
    mode: null,
    color: null,
    label: null,
    points: [],
    startPoint: null,
  });
  const { annotations, createAnnotation, hiddenAnnotations } = useApp();
  const [tilesLoading, setTilesLoading] = useState(false);
  const loadingTilesRef = useRef(new Set());

  // Track settings state for viewer configuration
  const [viewerSettings, setViewerSettings] = useState({
    showGrid: false,
    showNavigator: true,
    animationTime: 0.5,
    zoomPerScroll: 1.2,
  });

  // Track last showGrid value to detect changes
  const lastShowGridRef = useRef(viewerSettings.showGrid);

  // Update the onReady ref when it changes
  useEffect(() => {
    onReadyRef.current = onReady;
  }, [onReady]);

  useEffect(() => {
    // Check if showGrid changed - force re-initialization
    const showGridChanged = lastShowGridRef.current !== viewerSettings.showGrid;

    // Prevent re-initialization if already initialized for this dataset AND showGrid hasn't changed
    if (
      !containerRef.current ||
      !dataset ||
      (initializedDatasetIdRef.current === dataset.id && !showGridChanged)
    ) {
      return; // Don't re-initialize for same dataset unless showGrid changed
    }

    // IMPORTANT: Destroy existing viewer FIRST before creating new one
    if (viewerRef.current) {
      console.log("🧹 Destroying previous viewer before creating new one");
      try {
        // Clear tile loading state before destroying viewer
        loadingTilesRef.current.clear();
        setTilesLoading(false);

        viewerRef.current.destroy();
        viewerRef.current = null;
      } catch (error) {
        console.warn("⚠️ Error destroying viewer:", error);
        viewerRef.current = null;
      }
    }

    // Always show loading state while initializing a new dataset viewer
    setTilesLoading(true);

    // Update showGrid tracking
    lastShowGridRef.current = viewerSettings.showGrid;

    console.log(
      "🔄 Initializing viewer for dataset:",
      dataset.id,
      "showGrid:",
      viewerSettings.showGrid
    );

    // Clear existing viewer content before creating new one
    const container = document.getElementById("openseadragon-viewer");
    if (container) {
      // Use a safer method to clear content
      while (container.firstChild) {
        container.removeChild(container.firstChild);
      }
    }

    // Calculate max zoom level based on image dimensions
    const tileSize = dataset.tile_size || 256;
    const maxLevel = Math.max(
      0,
      dataset.max_zoom ??
        Math.ceil(Math.log2(Math.max(dataset.width, dataset.height) / tileSize))
    );

    // Initialize OpenSeadragon
    let viewerInstance;
    try {
      viewerInstance = OpenSeadragon({
        id: "openseadragon-viewer",
        prefixUrl:
          "https://cdn.jsdelivr.net/npm/openseadragon@4.1/build/openseadragon/images/",

        // CORS configuration for canvas export
        crossOriginPolicy: "Anonymous",
        ajaxWithCredentials: false,

        // Tile source configuration
        tileSources: {
          height: dataset.height,
          width: dataset.width,
          tileSize: tileSize,
          tileOverlap: 0,
          minLevel: 0,
          maxLevel: maxLevel,
          getTileUrl: function (level, x, y) {
            // Use png format to match tiles stored in R2
            const token = localStorage.getItem("astropixel_token");
            const version = dataset.updated_at
              ? new Date(dataset.updated_at).getTime()
              : dataset.created_at
              ? new Date(dataset.created_at).getTime()
              : Date.now();
            const base = `${API_BASE_URL}/api/tiles/${dataset.id}/${level}/${x}/${y}.png?v=${version}`;
            return token ? `${base}&token=${token}` : base;
          },
        },

        // Viewer settings
        showNavigationControl: true,
        showNavigator: viewerSettings.showNavigator,
        navigatorPosition: "BOTTOM_RIGHT",
        navigatorSizeRatio: 0.15,

        // Zoom and pan settings
        animationTime: viewerSettings.animationTime,
        blendTime: 0.1,
        constrainDuringPan: false,
        maxZoomPixelRatio: 2,
        minZoomImageRatio: 0.9,
        visibilityRatio: 1.0,
        zoomPerClick: 2.0,
        zoomPerScroll: viewerSettings.zoomPerScroll,

        // Gesture settings
        gestureSettingsMouse: {
          scrollToZoom: true,
          clickToZoom: false,
          dblClickToZoom: true,
        },

        // Tile loading settings
        immediateRender: false,
        loadTilesWithAjax: false,
        timeout: 30000,

        // Debug grid (controlled by settings)
        debugMode: viewerSettings.showGrid,
        debugGridColor: ["#08F", "#0F8", "#F08", "#F80", "#80F", "#8F0"],

        // Custom debug info - only show Level and Order
        drawDebuggingInfo: function (tile, ctx, tileCoordinates) {
          if (!tile) return;

          // Get tile info
          const level = tileCoordinates.level;
          const order = tile.loadingOrder || 0;

          // Set text style
          ctx.fillStyle = "#FFF";
          ctx.strokeStyle = "#000";
          ctx.lineWidth = 2;
          ctx.font = "bold 14px Arial";
          ctx.textAlign = "left";
          ctx.textBaseline = "top";

          // Display Level and Order only
          const text = `Level: ${level}\nOrder: ${order}`;
          const lines = text.split("\n");

          let y_offset = 5;
          lines.forEach((line) => {
            // Draw text outline (stroke)
            ctx.strokeText(line, 5, y_offset);
            // Draw text fill
            ctx.fillText(line, 5, y_offset);
            y_offset += 18;
          });
        },
      });

      console.log("✅ OpenSeadragon viewer created successfully");
    } catch (error) {
      console.error("❌ Failed to create OpenSeadragon viewer:", error);
      return;
    }

    // Event handlers
    viewerInstance.addHandler("open", () => {
      console.log("✅ Viewer opened successfully");
      initializedDatasetIdRef.current = dataset.id;
      if (onReadyRef.current) onReadyRef.current();
    });

    // Track tile loading for overlay - show loading animation when tiles are being fetched
    let loadingDebounceTimer = null;
    let initialLoadComplete = false;
    let loadingFallbackTimer = null;

    viewerInstance.addHandler("tile-loading", (event) => {
      if (event.tile) {
        loadingTilesRef.current.add(event.tile);
        // Show loading immediately when tiles start loading
        setTilesLoading(true);
        // Clear any pending hide timers when new tiles start loading
        clearTimeout(loadingDebounceTimer);
        clearTimeout(loadingFallbackTimer);
      }
    });

    viewerInstance.addHandler("tile-loaded", (event) => {
      if (event.tile) {
        loadingTilesRef.current.delete(event.tile);
      }

      // Use longer debounce (1s) to wait for all tiles to finish loading
      // Only hide when no tiles are loading and debounce expires
      clearTimeout(loadingDebounceTimer);
      loadingDebounceTimer = setTimeout(() => {
        if (loadingTilesRef.current.size === 0) {
          console.log("✅ All tiles loaded, hiding loader");
          setTilesLoading(false);
          initialLoadComplete = true;
        }
      }, 1000);
    });

    viewerInstance.addHandler("tile-load-failed", (event) => {
      if (event.tile) {
        loadingTilesRef.current.delete(event.tile);
      }

      // Use longer debounce (1s) even for failed tiles
      clearTimeout(loadingDebounceTimer);
      loadingDebounceTimer = setTimeout(() => {
        if (loadingTilesRef.current.size === 0) {
          console.log("✅ Tile loading complete (with failures), hiding loader");
          setTilesLoading(false);
        }
      }, 1000);
    });

    // Show loading on viewport changes (pan/zoom) when new tiles need to load
    viewerInstance.addHandler("animation-start", () => {
      if (loadingTilesRef.current.size > 0) {
        console.log("🔄 Pan/zoom detected, showing loader again");
        setTilesLoading(true);
      }
    });

    // When animation finishes, if no tiles are loading, hide the loader
    viewerInstance.addHandler("animation-finish", () => {
      clearTimeout(loadingDebounceTimer);
      loadingDebounceTimer = setTimeout(() => {
        if (loadingTilesRef.current.size === 0) {
          console.log("✅ Animation finished, all tiles loaded - hiding loader");
          setTilesLoading(false);
        }
      }, 800);
    });

    // Fallback: if no tile events fire (cached tiles), hide loader after a delay once open
    viewerInstance.addHandler("open", () => {
      clearTimeout(loadingFallbackTimer);
      loadingFallbackTimer = setTimeout(() => {
        if (loadingTilesRef.current.size === 0) {
          console.log("✅ Viewer opened, no pending tiles - hiding loader");
          setTilesLoading(false);
        }
      }, 1500);
    });
    });

    viewerInstance.addHandler("open-failed", (event) => {
      console.error("❌ Viewer failed to open:", event);
    });

    // Dispatch viewport updates for status bar
    const dispatchViewportUpdate = () => {
      if (!viewerInstance.viewport) return;

      const viewport = viewerInstance.viewport;
      const zoom = viewport.getZoom(true);
      const center = viewport.getCenter(true);

      window.dispatchEvent(
        new CustomEvent("viewer-viewport-update", {
          detail: {
            zoom: zoom.toFixed(2),
            center: {
              x: Math.round(center.x * 1000) / 1000,
              y: Math.round(center.y * 1000) / 1000,
            },
          },
        })
      );
    };

    viewerInstance.addHandler("animation", dispatchViewportUpdate);
    viewerInstance.addHandler("zoom", dispatchViewportUpdate);
    viewerInstance.addHandler("pan", dispatchViewportUpdate);

    // Initial viewport update
    viewerInstance.addHandler("open", () => {
      setTimeout(dispatchViewportUpdate, 100);
    });

    viewerRef.current = viewerInstance;
    setViewer(viewerInstance);

    // Create custom SVG overlay for annotations
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.style.position = "absolute";
    svg.style.top = "0";
    svg.style.left = "0";
    svg.style.width = "100%";
    svg.style.height = "100%";
    svg.style.pointerEvents = "none";
    svg.style.zIndex = "1000";

    const overlayElement = viewerInstance.element.querySelector(
      ".openseadragon-canvas"
    );
    if (overlayElement && overlayElement.parentNode) {
      overlayElement.parentNode.appendChild(svg);
    }

    overlayRef.current = {
      node: () => svg,
      clear: () => {
        while (svg.firstChild) {
          svg.removeChild(svg.firstChild);
        }
      },
    };

    // Cleanup
    return () => {
      console.log("🧹 Cleaning up viewer instance for dataset:", dataset?.id);

      // Clear any pending debounce timers
      if (loadingDebounceTimer) {
        clearTimeout(loadingDebounceTimer);
      }
      if (loadingFallbackTimer) {
        clearTimeout(loadingFallbackTimer);
      }

      // Clear tile loading state
      loadingTilesRef.current.clear();
      setTilesLoading(false);

      // Safely remove SVG overlay
      try {
        if (svg && svg.parentNode) {
          svg.parentNode.removeChild(svg);
        }
      } catch (error) {
        console.warn("⚠️ Error removing SVG overlay:", error);
      }

      // Safely destroy viewer
      try {
        if (viewerInstance) {
          viewerInstance.destroy();
        }
      } catch (error) {
        console.warn("⚠️ Error destroying viewer instance:", error);
      }

      // Reset ALL refs so re-initialization happens cleanly
      viewerRef.current = null;
      initializedDatasetIdRef.current = null; // Reset to allow new dataset to initialize
      setViewer(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataset && dataset.id, viewerSettings.showGrid]); // Re-initialize only when dataset or showGrid changes

  // Separate effect for settings updates - runs independently of dataset changes
  useEffect(() => {
    const handleSettingsUpdate = (event) => {
      const settings = event.detail;
      console.log("⚙️ Received settings update:", settings);

      const viewerInstance = viewerRef.current;

      // Update showGrid - requires re-initialization
      if (
        settings.showGrid !== undefined &&
        settings.showGrid !== viewerSettings.showGrid
      ) {
        console.log(
          "🔧 Updating showGrid to:",
          settings.showGrid,
          "(will re-initialize viewer)"
        );
        setViewerSettings((prev) => ({ ...prev, showGrid: settings.showGrid }));
      }

      // Update other settings dynamically without re-initialization
      if (viewerInstance) {
        // Update navigator visibility
        if (settings.showNavigator !== undefined) {
          viewerInstance.navigator.setVisible(settings.showNavigator);
          setViewerSettings((prev) => ({
            ...prev,
            showNavigator: settings.showNavigator,
          }));
        }

        // Update animation settings
        if (settings.animationTime !== undefined) {
          viewerInstance.animationTime = settings.animationTime;
          setViewerSettings((prev) => ({
            ...prev,
            animationTime: settings.animationTime,
          }));
        }

        // Update zoom per scroll
        if (settings.zoomPerScroll !== undefined) {
          viewerInstance.zoomPerScroll = settings.zoomPerScroll;
          setViewerSettings((prev) => ({
            ...prev,
            zoomPerScroll: settings.zoomPerScroll,
          }));
        }

        console.log("✅ Settings applied");
      }
    };

    window.addEventListener("viewer-settings-update", handleSettingsUpdate);

    return () => {
      window.removeEventListener(
        "viewer-settings-update",
        handleSettingsUpdate
      );
    };
  }, [viewerSettings.showGrid]); // Include showGrid to detect changes

  // Handle annotation drawing
  useEffect(() => {
    const viewerInstance = viewerRef.current;
    if (!viewerInstance || mode !== "annotate") {
      console.log(
        "❌ Annotation disabled - mode:",
        mode,
        "viewer:",
        !!viewerInstance
      );
      return;
    }

    console.log("✅ Annotation system initialized");
    let tempRect = null;

    const handleStartDrawing = (event) => {
      const { mode: drawMode, color, label } = event.detail;
      console.log(
        "🎨 START DRAWING:",
        drawMode,
        "Color:",
        color,
        "Label:",
        label
      );

      drawingStateRef.current = {
        isDrawing: true,
        mode: drawMode,
        color: color,
        label: label,
        points: [],
        startPoint: null,
      };

      setIsDrawingActive(true);
      // DON'T disable mouse navigation - it blocks canvas events
      console.log("✅ Drawing mode active");
    };

    const handleCancelDrawing = () => {
      drawingStateRef.current.isDrawing = false;
      drawingStateRef.current.points = [];
      drawingStateRef.current.startPoint = null;
      setIsDrawingActive(false);

      if (tempRect) {
        tempRect.remove();
        tempRect = null;
      }

      const svg = overlayRef.current?.node();
      if (svg) {
        svg.querySelectorAll(".temp-annotation").forEach((el) => el.remove());
      }

      window.dispatchEvent(new CustomEvent("annotation-drawing-cancelled"));
    };

    const getImageCoordinates = (viewerEvent) => {
      const webPoint = viewerEvent.position;
      const viewportPoint = viewerInstance.viewport.pointFromPixel(webPoint);
      return viewerInstance.viewport.viewportToImageCoordinates(viewportPoint);
    };

    const getPixelCoordinates = (imageX, imageY) => {
      const vpPoint = viewerInstance.viewport.imageToViewportCoordinates(
        imageX,
        imageY
      );
      return viewerInstance.viewport.viewportToViewerElementCoordinates(
        vpPoint
      );
    };

    const completeAnnotation = async (geometry) => {
      console.log("🎯 completeAnnotation called with geometry:", geometry);

      // Map frontend mode to backend annotation_type
      const mode = drawingStateRef.current.mode;
      const annotationType =
        mode === "rectangle"
          ? "rectangle"
          : mode === "circle"
          ? "circle"
          : "point";

      const annotationData = {
        label: drawingStateRef.current.label,
        geometry: geometry,
        annotation_type: annotationType, // Required: "point", "polygon", "rectangle", or "circle"
        description: `${drawingStateRef.current.mode} annotation`,
        confidence: 1.0, // Optional, defaults to 1.0
        properties: {
          color: drawingStateRef.current.color, // Store color in properties for rendering
        },
      };

      console.log("📝 Creating annotation directly:", annotationData);

      try {
        const created = await createAnnotation(annotationData);
        console.log("✅ Annotation created successfully:", created);
        console.log(
          "✅ Annotation should now appear in the list and on canvas"
        );
      } catch (err) {
        console.error("❌ Failed to create annotation:", err);
        console.error("❌ Error response:", err.response?.data);
        console.error("❌ Error detail:", err.response?.data?.detail);

        const errorMsg = err.response?.data?.detail?.[0]?.msg || err.message;
        alert("Failed to create annotation: " + errorMsg);
      }

      // Reset drawing state
      drawingStateRef.current.isDrawing = false;
      drawingStateRef.current.points = [];
      drawingStateRef.current.startPoint = null;
      drawingStateRef.current.mode = null;
      drawingStateRef.current.color = null;
      drawingStateRef.current.label = null;
      setIsDrawingActive(false);

      console.log("✅ Drawing state reset");

      // Clean up temporary elements
      if (tempRect) {
        tempRect.remove();
        tempRect = null;
      }

      const svg = overlayRef.current?.node();
      if (svg) {
        svg.querySelectorAll(".temp-annotation").forEach((el) => el.remove());
      }

      // Dispatch event for AnnotationTools to reset UI (if mounted)
      window.dispatchEvent(
        new CustomEvent("annotation-drawing-complete", {
          detail: { success: true },
        })
      );
    };

    // POINT MODE: Click once to place
    const handlePointClick = (event) => {
      const imagePoint = getImageCoordinates(event);
      console.log("📍 POINT created at:", imagePoint);

      // Store point as a small area (50 pixel radius in image space)
      // This makes it scale with zoom like rectangles
      const pointRadius = 50; // Image space radius
      completeAnnotation({
        type: "Point",
        coordinates: [imagePoint.x, imagePoint.y, pointRadius],
      });
    };

    // RECTANGLE MODE: Press, drag, release
    const handleRectanglePress = (event) => {
      const imagePoint = getImageCoordinates(event);
      drawingStateRef.current.startPoint = imagePoint;

      const svg = overlayRef.current?.node();
      if (svg) {
        tempRect = document.createElementNS(
          "http://www.w3.org/2000/svg",
          "rect"
        );
        tempRect.setAttribute("class", "temp-annotation");
        tempRect.setAttribute("fill", drawingStateRef.current.color);
        tempRect.setAttribute("fill-opacity", "0.3");
        tempRect.setAttribute("stroke", drawingStateRef.current.color);
        tempRect.setAttribute("stroke-width", "2");
        svg.appendChild(tempRect);
      }
    };

    const handleRectangleDrag = (event) => {
      if (!drawingStateRef.current.startPoint || !tempRect) return;

      const imagePoint = getImageCoordinates(event);
      const start = getPixelCoordinates(
        drawingStateRef.current.startPoint.x,
        drawingStateRef.current.startPoint.y
      );
      const end = getPixelCoordinates(imagePoint.x, imagePoint.y);

      const x = Math.min(start.x, end.x);
      const y = Math.min(start.y, end.y);
      const width = Math.abs(end.x - start.x);
      const height = Math.abs(end.y - start.y);

      tempRect.setAttribute("x", x);
      tempRect.setAttribute("y", y);
      tempRect.setAttribute("width", width);
      tempRect.setAttribute("height", height);
    };

    const handleRectangleRelease = (event) => {
      if (!drawingStateRef.current.startPoint) return;

      const imagePoint = getImageCoordinates(event);
      const start = drawingStateRef.current.startPoint;

      console.log("✅ Rectangle complete - auto-finishing");

      completeAnnotation({
        type: "Rectangle",
        coordinates: [
          [Math.min(start.x, imagePoint.x), Math.min(start.y, imagePoint.y)],
          [Math.max(start.x, imagePoint.x), Math.max(start.y, imagePoint.y)],
        ],
      });

      // Reset drawing state immediately after completing
      drawingStateRef.current = {
        isDrawing: false,
        mode: null,
        color: null,
        label: null,
        points: [],
        startPoint: null,
      };
      setIsDrawingActive(false);
    };

    // CIRCLE MODE: Press, drag, release (creates circle from center and radius)
    let tempCircle = null;

    const handleCirclePress = (event) => {
      const imagePoint = getImageCoordinates(event);
      drawingStateRef.current.startPoint = imagePoint;

      const svg = overlayRef.current?.node();
      if (svg) {
        tempCircle = document.createElementNS(
          "http://www.w3.org/2000/svg",
          "circle"
        );
        tempCircle.setAttribute("class", "temp-annotation");
        tempCircle.setAttribute("fill", drawingStateRef.current.color);
        tempCircle.setAttribute("fill-opacity", "0.3");
        tempCircle.setAttribute("stroke", drawingStateRef.current.color);
        tempCircle.setAttribute("stroke-width", "2");
        const pixelStart = getPixelCoordinates(imagePoint.x, imagePoint.y);
        tempCircle.setAttribute("cx", pixelStart.x);
        tempCircle.setAttribute("cy", pixelStart.y);
        tempCircle.setAttribute("r", "0");
        svg.appendChild(tempCircle);
      }
    };

    const handleCircleDrag = (event) => {
      if (!drawingStateRef.current.startPoint || !tempCircle) return;

      const imagePoint = getImageCoordinates(event);
      const start = getPixelCoordinates(
        drawingStateRef.current.startPoint.x,
        drawingStateRef.current.startPoint.y
      );
      const end = getPixelCoordinates(imagePoint.x, imagePoint.y);

      // Calculate radius from center to current point
      const radius = Math.sqrt(
        Math.pow(end.x - start.x, 2) + Math.pow(end.y - start.y, 2)
      );

      tempCircle.setAttribute("r", radius);
    };

    const handleCircleRelease = (event) => {
      if (!drawingStateRef.current.startPoint) return;

      const imagePoint = getImageCoordinates(event);
      const start = drawingStateRef.current.startPoint;

      // Calculate radius in image coordinates
      const radiusX = Math.abs(imagePoint.x - start.x);
      const radiusY = Math.abs(imagePoint.y - start.y);
      const radius = Math.sqrt(radiusX * radiusX + radiusY * radiusY);

      console.log("✅ Circle complete - auto-finishing");

      completeAnnotation({
        type: "Circle",
        coordinates: [start.x, start.y, radius], // [centerX, centerY, radius]
      });

      // Clean up temp circle
      if (tempCircle) {
        tempCircle.remove();
        tempCircle = null;
      }

      // Reset drawing state
      drawingStateRef.current = {
        isDrawing: false,
        mode: null,
        color: null,
        label: null,
        points: [],
        startPoint: null,
      };
      setIsDrawingActive(false);
    };

    // Main event handlers
    const clickHandler = (event) => {
      console.log(
        "🖱️ CLICK EVENT - isDrawing:",
        drawingStateRef.current.isDrawing,
        "mode:",
        drawingStateRef.current.mode
      );

      if (!drawingStateRef.current.isDrawing) {
        console.log("⚠️ Ignoring click - not in drawing mode");
        return;
      }

      // Prevent default OpenSeadragon behavior
      event.preventDefaultAction = true;

      const mode = drawingStateRef.current.mode;
      if (mode === "point") {
        console.log("→ Handling as POINT");
        handlePointClick(event);
      }
    };

    const pressHandler = (event) => {
      console.log(
        "🖋️ PRESS EVENT - isDrawing:",
        drawingStateRef.current.isDrawing,
        "mode:",
        drawingStateRef.current.mode
      );
      if (!drawingStateRef.current.isDrawing) return;

      const mode = drawingStateRef.current.mode;
      event.preventDefaultAction = true;

      if (mode === "rectangle") {
        console.log("→ Starting RECTANGLE");
        handleRectanglePress(event);
      } else if (mode === "circle") {
        console.log("→ Starting CIRCLE");
        handleCirclePress(event);
      }
    };

    const dragHandler = (event) => {
      if (!drawingStateRef.current.isDrawing) return;

      const mode = drawingStateRef.current.mode;
      event.preventDefaultAction = true;

      if (mode === "rectangle") {
        handleRectangleDrag(event);
      } else if (mode === "circle") {
        handleCircleDrag(event);
      }
    };

    const releaseHandler = (event) => {
      console.log("🖋️ RELEASE EVENT");
      if (!drawingStateRef.current.isDrawing) return;

      const mode = drawingStateRef.current.mode;
      event.preventDefaultAction = true;

      if (mode === "rectangle") {
        console.log("→ Completing RECTANGLE");
        handleRectangleRelease(event);
      } else if (mode === "circle") {
        console.log("→ Completing CIRCLE");
        handleCircleRelease(event);
      }
    };

    const dblClickHandler = () => {
      // No longer needed - polygon removed
    };

    const keyHandler = (event) => {
      if (event.key === "Escape" && drawingStateRef.current.isDrawing) {
        handleCancelDrawing();
      }
    };

    // Add event listeners
    console.log("🔗 Adding OpenSeadragon event handlers");
    viewerInstance.addHandler("canvas-click", clickHandler);
    viewerInstance.addHandler("canvas-press", pressHandler);
    viewerInstance.addHandler("canvas-drag", dragHandler);
    viewerInstance.addHandler("canvas-release", releaseHandler);
    viewerInstance.addHandler("canvas-double-click", dblClickHandler);
    window.addEventListener("annotation-start-drawing", handleStartDrawing);
    window.addEventListener("annotation-cancel-drawing", handleCancelDrawing);
    window.addEventListener("keydown", keyHandler);
    console.log("✅ All event handlers registered");

    return () => {
      if (viewerInstance) {
        viewerInstance.removeHandler("canvas-click", clickHandler);
        viewerInstance.removeHandler("canvas-press", pressHandler);
        viewerInstance.removeHandler("canvas-drag", dragHandler);
        viewerInstance.removeHandler("canvas-release", releaseHandler);
        viewerInstance.removeHandler("canvas-double-click", dblClickHandler);
      }
      window.removeEventListener(
        "annotation-start-drawing",
        handleStartDrawing
      );
      window.removeEventListener(
        "annotation-cancel-drawing",
        handleCancelDrawing
      );
      window.removeEventListener("keydown", keyHandler);
    };
  }, [mode, viewer]); // Render existing annotations
  useEffect(() => {
    if (!viewer || !overlayRef.current) return;

    const renderAnnotations = () => {
      if (!viewer.element || !overlayRef.current) return;

      const svg = overlayRef.current.node();

      // Clear previous annotations (keep temp ones)
      const existingAnnotations = svg.querySelectorAll(".annotation");
      existingAnnotations.forEach((el) => el.remove());

      // Silently render annotations

      // Render each annotation (skip hidden ones)
      annotations.forEach((annotation) => {
        if (!annotation.geometry) return;
        if (hiddenAnnotations.has(annotation.id)) return; // Skip hidden annotations

        const { type, coordinates } = annotation.geometry;
        const color =
          annotation.properties?.color || annotation.color || "#3b82f6";

        if (type === "Point") {
          const [x, y, radius = 50] = coordinates; // radius in image space
          const vpPoint = viewer.viewport.imageToViewportCoordinates(x, y);
          const pixelPoint =
            viewer.viewport.viewportToViewerElementCoordinates(vpPoint);

          // Calculate scaled radius: create a reference point offset by radius in image space
          const vpRadiusPoint = viewer.viewport.imageToViewportCoordinates(
            x + radius,
            y
          );
          const pixelRadiusPoint =
            viewer.viewport.viewportToViewerElementCoordinates(vpRadiusPoint);
          const scaledRadius = Math.abs(pixelRadiusPoint.x - pixelPoint.x);

          const circle = document.createElementNS(
            "http://www.w3.org/2000/svg",
            "circle"
          );
          circle.setAttribute("cx", pixelPoint.x);
          circle.setAttribute("cy", pixelPoint.y);
          circle.setAttribute("r", scaledRadius);
          circle.setAttribute("fill", color);
          circle.setAttribute("stroke", "white");
          circle.setAttribute("stroke-width", "2");
          circle.setAttribute("class", "annotation");
          svg.appendChild(circle);
        } else if (type === "Rectangle") {
          const [[x1, y1], [x2, y2]] = coordinates;
          const vpPoint1 = viewer.viewport.imageToViewportCoordinates(x1, y1);
          const vpPoint2 = viewer.viewport.imageToViewportCoordinates(x2, y2);
          const pixelPoint1 =
            viewer.viewport.viewportToViewerElementCoordinates(vpPoint1);
          const pixelPoint2 =
            viewer.viewport.viewportToViewerElementCoordinates(vpPoint2);

          const width = Math.abs(pixelPoint2.x - pixelPoint1.x);
          const height = Math.abs(pixelPoint2.y - pixelPoint1.y);

          const rect = document.createElementNS(
            "http://www.w3.org/2000/svg",
            "rect"
          );
          rect.setAttribute("x", Math.min(pixelPoint1.x, pixelPoint2.x));
          rect.setAttribute("y", Math.min(pixelPoint1.y, pixelPoint2.y));
          rect.setAttribute("width", width);
          rect.setAttribute("height", height);
          rect.setAttribute("fill", color);
          rect.setAttribute("fill-opacity", "0.2");
          rect.setAttribute("stroke", color);
          rect.setAttribute("stroke-width", "2");
          rect.setAttribute("class", "annotation");
          svg.appendChild(rect);
        } else if (type === "Circle") {
          const [x, y, radius] = coordinates; // [centerX, centerY, radius in image space]
          const vpCenter = viewer.viewport.imageToViewportCoordinates(x, y);
          const pixelCenter =
            viewer.viewport.viewportToViewerElementCoordinates(vpCenter);

          // Calculate scaled radius
          const vpRadiusPoint = viewer.viewport.imageToViewportCoordinates(
            x + radius,
            y
          );
          const pixelRadiusPoint =
            viewer.viewport.viewportToViewerElementCoordinates(vpRadiusPoint);
          const scaledRadius = Math.abs(pixelRadiusPoint.x - pixelCenter.x);

          const circle = document.createElementNS(
            "http://www.w3.org/2000/svg",
            "circle"
          );
          circle.setAttribute("cx", pixelCenter.x);
          circle.setAttribute("cy", pixelCenter.y);
          circle.setAttribute("r", scaledRadius);
          circle.setAttribute("fill", color);
          circle.setAttribute("fill-opacity", "0.2");
          circle.setAttribute("stroke", color);
          circle.setAttribute("stroke-width", "2");
          circle.setAttribute("class", "annotation");
          svg.appendChild(circle);
        }
      });
    };

    // Initial render
    renderAnnotations();

    // Re-render on viewport change (pan/zoom)
    viewer.addHandler("animation", renderAnnotations);
    viewer.addHandler("animation-finish", renderAnnotations);

    return () => {
      viewer.removeHandler("animation", renderAnnotations);
      viewer.removeHandler("animation-finish", renderAnnotations);
    };
  }, [annotations, viewer, hiddenAnnotations]);

  return (
    <div className="relative w-full h-full">
      <div
        ref={containerRef}
        id="openseadragon-viewer"
        className="absolute inset-0"
        style={{
          background: "#0a0a0f",
          minHeight: "400px",
          cursor: isDrawingActive ? "crosshair" : "default",
        }}
      />

      {/* Drawing mode indicator */}
      {isDrawingActive && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg z-50 flex items-center gap-2">
          <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
          <span className="text-sm font-medium">
            Drawing Mode Active - Click on canvas
          </span>
        </div>
      )}

      {/* Tile loading overlay */}
      <TileLoadingOverlay isLoading={tilesLoading} />

      {/* Loading overlay */}
      {!viewer && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80 pointer-events-none">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-gray-400">Loading viewer...</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default ViewerCanvas;
