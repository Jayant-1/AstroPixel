import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import api from "../services/api";
import { debounce } from "../utils/helpers";

const AppContext = createContext(null);

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within AppProvider");
  }
  return context;
};

export const AppProvider = ({ children }) => {
  // Datasets
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Annotations
  const [annotations, setAnnotations] = useState([]);
  const [selectedAnnotation, setSelectedAnnotation] = useState(null);
  const [annotationsLoading, setAnnotationsLoading] = useState(false);
  const [hiddenAnnotations, setHiddenAnnotations] = useState(new Set());

  // UI State
  const [viewMode, setViewMode] = useState("explore"); // explore, annotate, compare
  const [sidebarOpen, setSidebarOpen] = useState({ left: true, right: true });
  const [searchQuery, setSearchQuery] = useState("");
  const [filterCategory, setFilterCategory] = useState(null);
  const [searchResults, setSearchResults] = useState([]);

  // Comparison state
  const [comparisonDatasets, setComparisonDatasets] = useState([]);

  // Load datasets
  const loadDatasets = useCallback(async (category = null) => {
    try {
      setLoading(true);
      setError(null);
      const params = category ? { category } : {};
      const data = await api.fetchDatasets(params);

      // Filter out datasets that are still processing or failed (optional)
      const validDatasets = data.filter(
        (ds) =>
          ds.processing_status === "completed" ||
          ds.processing_status === "processing"
      );

      setDatasets(validDatasets);
    } catch (err) {
      setError(err.message || "Failed to load datasets");
      console.error("Error loading datasets:", err);
      // Fallback to empty array instead of demo data for production
      setDatasets([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load annotations
  const loadAnnotations = useCallback(async (datasetId) => {
    try {
      setAnnotationsLoading(true);
      const data = await api.fetchAnnotations(datasetId);
      setAnnotations(data);
    } catch (err) {
      console.error("Error loading annotations:", err);
      setAnnotations([]);
    } finally {
      setAnnotationsLoading(false);
    }
  }, []);

  // Create annotation
  const createAnnotation = useCallback(
    async (annotation) => {
      try {
        console.log(
          "🔄 AppContext: Creating annotation via API...",
          annotation
        );

        const payload = {
          ...annotation,
          dataset_id: selectedDataset.id,
          user_id: "demo-user", // Replace with actual user ID
        };

        console.log(
          "📦 AppContext: Sending payload to backend:",
          JSON.stringify(payload, null, 2)
        );

        const created = await api.createAnnotation(payload);
        console.log(
          "✅ AppContext: Annotation created, adding to list:",
          created
        );
        setAnnotations((prev) => {
          const updated = [...prev, created];
          console.log(
            "📋 AppContext: Updated annotations list, total:",
            updated.length
          );
          return updated;
        });
        return created;
      } catch (err) {
        console.error("❌ AppContext: Error creating annotation:", err);
        throw err;
      }
    },
    [selectedDataset]
  );

  // Update annotation
  const updateAnnotation = useCallback(async (id, updates) => {
    try {
      const updated = await api.updateAnnotation(id, updates);
      setAnnotations((prev) =>
        prev.map((ann) => (ann.id === id ? updated : ann))
      );
      return updated;
    } catch (err) {
      console.error("Error updating annotation:", err);
      throw err;
    }
  }, []);

  // Delete annotation
  const deleteAnnotation = useCallback(async (id) => {
    try {
      await api.deleteAnnotation(id);
      setAnnotations((prev) => prev.filter((ann) => ann.id !== id));
    } catch (err) {
      console.error("Error deleting annotation:", err);
      throw err;
    }
  }, []);

  // Export annotations
  const exportAnnotations = useCallback(
    async (format = "json") => {
      try {
        const blob = await api.exportAnnotations(selectedDataset.id, format);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `annotations-${selectedDataset.id}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } catch (err) {
        console.error("Error exporting annotations:", err);
        throw err;
      }
    },
    [selectedDataset]
  );

  // Search with debounce
  const performSearch = useCallback(
    (query) => {
      const debouncedSearch = debounce(async (q) => {
        if (!q.trim()) {
          setSearchResults([]);
          return;
        }

        try {
          const params = selectedDataset
            ? { dataset_id: selectedDataset.id }
            : {};
          const results = await api.searchFeatures(q, params);
          setSearchResults(results);
        } catch (err) {
          console.error("Search error:", err);
          setSearchResults([]);
        }
      }, 300);

      debouncedSearch(query);
    },
    [selectedDataset]
  );

  // Effect: Search when query changes
  useEffect(() => {
    performSearch(searchQuery);
  }, [searchQuery, performSearch]);

  // Effect: Load datasets on mount
  useEffect(() => {
    loadDatasets(filterCategory);
  }, [filterCategory, loadDatasets]);

  // Effect: Load annotations when dataset changes
  useEffect(() => {
    if (selectedDataset) {
      loadAnnotations(selectedDataset.id);
    } else {
      setAnnotations([]);
    }
  }, [selectedDataset, loadAnnotations]);

  const value = {
    // Data
    datasets,
    selectedDataset,
    setSelectedDataset,
    annotations,
    selectedAnnotation,
    setSelectedAnnotation,
    searchResults,
    comparisonDatasets,
    setComparisonDatasets,

    // Loading states
    loading,
    annotationsLoading,
    error,

    // UI state
    viewMode,
    setViewMode,
    sidebarOpen,
    setSidebarOpen,
    searchQuery,
    setSearchQuery,
    filterCategory,
    setFilterCategory,
    hiddenAnnotations,
    setHiddenAnnotations,

    // Actions
    loadDatasets,
    loadAnnotations,
    createAnnotation,
    updateAnnotation,
    deleteAnnotation,
    exportAnnotations,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};

// Demo datasets fallback
function getDemoDatasets() {
  return [
    {
      id: "demo-earth-1",
      name: "Earth - Blue Marble",
      description: "High-resolution composite image of Earth",
      category: "earth",
      width: 21600,
      height: 10800,
      tile_size: 256,
      max_zoom: 8,
      created_at: "2024-01-01T00:00:00Z",
    },
    {
      id: "demo-mars-1",
      name: "Mars - Valles Marineris",
      description: "Canyon system on Mars",
      category: "mars",
      width: 16384,
      height: 8192,
      tile_size: 256,
      max_zoom: 7,
      created_at: "2024-01-02T00:00:00Z",
    },
    {
      id: "demo-space-1",
      name: "Hubble Deep Field",
      description: "Deep space observation",
      category: "space",
      width: 32768,
      height: 32768,
      tile_size: 256,
      max_zoom: 9,
      created_at: "2024-01-03T00:00:00Z",
    },
  ];
}
