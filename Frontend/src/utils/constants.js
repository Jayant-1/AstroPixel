// Application constants

export const APP_NAME = "AstroPixel";
export const APP_VERSION = "1.0.0";

// API Configuration
export const API_TIMEOUT = 30000; // 30 seconds
export const DEBOUNCE_DELAY = 300; // 300ms
export const RETRY_ATTEMPTS = 3;
export const RETRY_DELAY = 1000; // 1 second

// Viewer Configuration
export const VIEWER_CONFIG = {
  DEFAULT_ZOOM: 1,
  MIN_ZOOM: 0.5,
  MAX_ZOOM: 20,
  ZOOM_PER_CLICK: 1.4,
  ZOOM_PER_SCROLL: 1.2,
  ANIMATION_TIME: 0.5,
  BLEND_TIME: 0.1,
  TILE_SIZE: 256,
};

// Annotation Configuration
export const ANNOTATION_TYPES = {
  POINT: "Point",
  RECTANGLE: "Rectangle",
  CIRCLE: "Circle",
  POLYGON: "Polygon",
  FREEHAND: "Freehand",
};

export const ANNOTATION_COLORS = [
  "#3b82f6", // blue
  "#ef4444", // red
  "#10b981", // green
  "#f59e0b", // yellow
  "#8b5cf6", // purple
  "#ec4899", // pink
  "#06b6d4", // cyan
  "#f97316", // orange
];

// Dataset Categories
export const CATEGORIES = {
  EARTH: "earth",
  MARS: "mars",
  SPACE: "space",
  ALL: null,
};

export const CATEGORY_LABELS = {
  [CATEGORIES.EARTH]: "Earth",
  [CATEGORIES.MARS]: "Mars",
  [CATEGORIES.SPACE]: "Deep Space",
  [CATEGORIES.ALL]: "All Datasets",
};

// View Modes
export const VIEW_MODES = {
  EXPLORE: "explore",
  ANNOTATE: "annotate",
  COMPARE: "compare",
};

// Comparison Modes
export const COMPARISON_MODES = {
  SLIDER: "slider",
  SIDE_BY_SIDE: "sideBySide",
  OVERLAY: "overlay",
};

// Sort Options
export const SORT_OPTIONS = {
  NAME: "name",
  DATE: "date",
  SIZE: "size",
};

// View Types
export const VIEW_TYPES = {
  GRID: "grid",
  LIST: "list",
};

// Error Messages
export const ERROR_MESSAGES = {
  NETWORK: "Network error. Please check your connection.",
  TIMEOUT: "Request timeout. Please try again.",
  NOT_FOUND: "Resource not found.",
  SERVER: "Server error. Please try again later.",
  UNAUTHORIZED: "Unauthorized access.",
  FORBIDDEN: "Access forbidden.",
  UNKNOWN: "An unexpected error occurred.",
};

// Success Messages
export const SUCCESS_MESSAGES = {
  ANNOTATION_CREATED: "Annotation created successfully",
  ANNOTATION_UPDATED: "Annotation updated successfully",
  ANNOTATION_DELETED: "Annotation deleted successfully",
  EXPORT_SUCCESS: "Export completed successfully",
};

// Local Storage Keys
export const STORAGE_KEYS = {
  THEME: "app_theme",
  RECENT_DATASETS: "recent_datasets",
  VIEW_PREFERENCES: "view_preferences",
  USER_SETTINGS: "user_settings",
};

// Performance Thresholds
export const PERFORMANCE = {
  MAX_INITIAL_LOAD_TIME: 3000, // 3 seconds
  MAX_TILE_LOAD_TIME: 500, // 500ms
  TARGET_FPS: 60,
  LAZY_LOAD_THRESHOLD: 200, // pixels
};

// Responsive Breakpoints (matches Tailwind)
export const BREAKPOINTS = {
  SM: 640,
  MD: 768,
  LG: 1024,
  XL: 1280,
  "2XL": 1536,
};

// Feature Flags (for gradual rollout)
export const FEATURES = {
  AI_SEARCH: false,
  COLLABORATIVE_ANNOTATIONS: false,
  REAL_TIME_SYNC: false,
  EXPORT_GEOJSON: true,
  MINIMAP: false,
  OFFLINE_MODE: false,
};

// Export formats
export const EXPORT_FORMATS = {
  JSON: "json",
  GEOJSON: "geojson",
  KML: "kml",
  CSV: "csv",
};

export default {
  APP_NAME,
  APP_VERSION,
  API_TIMEOUT,
  DEBOUNCE_DELAY,
  VIEWER_CONFIG,
  ANNOTATION_TYPES,
  ANNOTATION_COLORS,
  CATEGORIES,
  VIEW_MODES,
  ERROR_MESSAGES,
  SUCCESS_MESSAGES,
  STORAGE_KEYS,
  PERFORMANCE,
  BREAKPOINTS,
  FEATURES,
};
