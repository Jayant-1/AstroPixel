import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

// Utility for merging Tailwind CSS classes
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// Debounce function
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Throttle function
export function throttle(func, limit) {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

// Format file size
export function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
}

// Format number with commas
export function formatNumber(num) {
  return num?.toLocaleString() || "0";
}

// Calculate zoom level from scale
export function scaleToZoom(scale, maxZoom = 20) {
  return Math.max(0, Math.min(maxZoom, Math.log2(scale)));
}

// Calculate scale from zoom level
export function zoomToScale(zoom) {
  return Math.pow(2, zoom);
}

// Get tile coordinates for a given position
export function getTileCoords(x, y, zoom, tileSize = 256) {
  const scale = zoomToScale(zoom);
  const tileX = Math.floor((x * scale) / tileSize);
  const tileY = Math.floor((y * scale) / tileSize);
  return { tileX, tileY, zoom: Math.floor(zoom) };
}

// Convert viewport coordinates to image coordinates
export function viewportToImageCoords(viewportX, viewportY, viewport) {
  const point = viewport.pointFromPixel({ x: viewportX, y: viewportY });
  return { x: point.x, y: point.y };
}

// Convert image coordinates to viewport coordinates
export function imageToViewportCoords(imageX, imageY, viewport) {
  const point = viewport.pixelFromPoint({ x: imageX, y: imageY });
  return { x: point.x, y: point.y };
}

// Calculate bounding box from coordinates
export function calculateBBox(coords) {
  const xs = coords.map((c) => c.x);
  const ys = coords.map((c) => c.y);
  return {
    minX: Math.min(...xs),
    minY: Math.min(...ys),
    maxX: Math.max(...xs),
    maxY: Math.max(...ys),
  };
}

// Check if point is inside polygon
export function pointInPolygon(point, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].x;
    const yi = polygon[i].y;
    const xj = polygon[j].x;
    const yj = polygon[j].y;

    const intersect =
      yi > point.y !== yj > point.y &&
      point.x < ((xj - xi) * (point.y - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

// Generate unique ID
export function generateId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// Deep clone object
export function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

// Download file
export function downloadFile(content, filename, type = "text/plain") {
  const blob = new Blob([content], { type });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

// Format date
export function formatDate(date, format = "short") {
  const d = new Date(date);
  if (isNaN(d.getTime())) return "Invalid date";

  if (format === "short") {
    return d.toLocaleDateString();
  } else if (format === "long") {
    return d.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } else if (format === "time") {
    return d.toLocaleString();
  }
  return d.toISOString();
}

// Get category color
export function getCategoryColor(category) {
  const colors = {
    earth: { from: "from-blue-500", to: "to-green-600", text: "text-blue-400" },
    mars: {
      from: "from-orange-500",
      to: "to-red-600",
      text: "text-orange-400",
    },
    space: {
      from: "from-purple-500",
      to: "to-indigo-600",
      text: "text-purple-400",
    },
  };
  return (
    colors[category] || {
      from: "from-gray-500",
      to: "to-gray-600",
      text: "text-gray-400",
    }
  );
}

// Retry function for failed requests
export async function retry(fn, retries = 3, delay = 1000) {
  try {
    return await fn();
  } catch (error) {
    if (retries === 0) throw error;
    await new Promise((resolve) => setTimeout(resolve, delay));
    return retry(fn, retries - 1, delay * 2);
  }
}

// Check if online
export function isOnline() {
  return navigator.onLine;
}

// Local storage helpers
export const storage = {
  get(key, defaultValue = null) {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch {
      return defaultValue;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error("LocalStorage error:", error);
    }
  },
  remove(key) {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error("LocalStorage error:", error);
    }
  },
};
