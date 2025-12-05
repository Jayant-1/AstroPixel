import axios from "axios";

// Remove trailing slash from API base URL to prevent double slashes
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/+$/, "");

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 3600000, // Increased to 60 minutes (ms) for very large uploads/operations
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor for adding auth token (future use)
apiClient.interceptors.request.use(
  (config) => {
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error
      const { status, data } = error.response;

      switch (status) {
        case 401:
          // Handle unauthorized
          console.error("Unauthorized access");
          break;
        case 403:
          console.error("Forbidden access");
          break;
        case 404:
          console.error("Resource not found");
          break;
        case 500:
          console.error("Server error");
          break;
        default:
          console.error("API error:", data);
      }
    } else if (error.request) {
      // Request made but no response
      console.error("Network error - no response received");
    } else {
      console.error("Error setting up request:", error.message);
    }

    return Promise.reject(error);
  }
);

// API methods
const api = {
  // Datasets
  async fetchDatasets(params = {}) {
    const response = await apiClient.get("/api/datasets", { params });
    return response.data;
  },

  async fetchDataset(id) {
    const response = await apiClient.get(`/api/datasets/${id}`);
    return response.data;
  },

  async fetchDatasetStats(id) {
    const response = await apiClient.get(`/api/datasets/${id}/stats`);
    return response.data;
  },

  async deleteDataset(id) {
    const response = await apiClient.delete(`/api/datasets/${id}`);
    return response.data;
  },

  // File Upload
  async uploadDataset(file, name, description, category, onUploadProgress) {
    const formData = new FormData();
    formData.append("file", file);

    // Send as query params as per backend API
    const params = new URLSearchParams({
      name: name,
      category: category,
    });

    if (description) {
      params.append("description", description);
    }

    // For large files (>100MB), use chunked upload
    const CHUNK_THRESHOLD = 100 * 1024 * 1024; // 100MB

    if (file.size > CHUNK_THRESHOLD) {
      return this.uploadDatasetChunked(
        file,
        name,
        description,
        category,
        onUploadProgress
      );
    }

    // Very long timeout for large file uploads
    // No practical limit - let it run as long as needed
    const timeout = 0; // 0 = no timeout in axios

    const response = await apiClient.post(
      `/api/datasets/upload?${params.toString()}`,
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        timeout: timeout, // No timeout for uploads
        onUploadProgress: onUploadProgress,
      }
    );
    return response.data;
  },

  // Chunked upload for large files (10GB+)
  async uploadDatasetChunked(
    file,
    name,
    description,
    category,
    onUploadProgress
  ) {
    const CHUNK_SIZE = 8 * 1024 * 1024; // 8MB chunks
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

    console.log(
      `📦 Starting chunked upload: ${file.name} (${(
        file.size /
        1024 ** 3
      ).toFixed(2)} GB, ${totalChunks} chunks)`
    );

    // Step 1: Initialize upload session
    const initResponse = await apiClient.post(
      "/api/datasets/upload/init",
      null,
      {
        params: {
          filename: file.name,
          filesize: file.size,
          total_chunks: totalChunks,
        },
      }
    );

    const { upload_id } = initResponse.data;
    console.log(`✅ Upload initialized: ${upload_id}`);

    // Step 2: Upload chunks
    let uploadedChunks = 0;

    for (let i = 0; i < totalChunks; i++) {
      const start = i * CHUNK_SIZE;
      const end = Math.min(start + CHUNK_SIZE, file.size);
      const chunk = file.slice(start, end);

      const formData = new FormData();
      formData.append("upload_id", upload_id);
      formData.append("chunk_index", i.toString());
      formData.append("chunk", chunk, `chunk_${i}`);

      await apiClient.post("/api/datasets/upload/chunk", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 300000, // 5 min per chunk
      });

      uploadedChunks++;

      // Report progress
      if (onUploadProgress) {
        const progress = Math.round((uploadedChunks / totalChunks) * 100);
        onUploadProgress({
          loaded: end,
          total: file.size,
          progress: progress,
          chunk: uploadedChunks,
          totalChunks: totalChunks,
        });
      }

      if (uploadedChunks % 10 === 0) {
        console.log(
          `📤 Uploaded ${uploadedChunks}/${totalChunks} chunks (${Math.round(
            (uploadedChunks / totalChunks) * 100
          )}%)`
        );
      }
    }

    console.log(`✅ All chunks uploaded. Assembling file...`);

    // Step 3: Complete upload
    const params = new URLSearchParams({
      upload_id: upload_id,
      name: name,
      category: category,
    });
    if (description) params.append("description", description);

    const completeResponse = await apiClient.post(
      `/api/datasets/upload/complete?${params.toString()}`,
      null,
      { timeout: 600000 } // 10 min for assembly
    );

    console.log(`🎉 Chunked upload complete!`);
    return completeResponse.data;
  },

  // Poll dataset processing status (no timeout - waits until completion)
  async pollProcessingStatus(datasetId, onProgress) {
    const pollInterval = 3000; // 3 seconds
    let attempts = 0;

    return new Promise((resolve, reject) => {
      const checkStatus = async () => {
        try {
          attempts++;
          const dataset = await this.fetchDataset(datasetId);

          // Update progress callback
          if (onProgress && dataset.processing_progress !== undefined) {
            onProgress(
              dataset.processing_progress,
              dataset.processing_status,
              attempts
            );
          }

          if (dataset.processing_status === "completed") {
            resolve(dataset);
          } else if (dataset.processing_status === "failed") {
            reject(
              new Error("Tile processing failed. Please check the file format.")
            );
          } else {
            // Continue polling indefinitely until completed or failed
            setTimeout(checkStatus, pollInterval);
          }
        } catch (err) {
          // Network errors - retry after delay
          console.warn(
            `Poll attempt ${attempts} failed, retrying...`,
            err.message
          );
          setTimeout(checkStatus, pollInterval * 2); // Longer delay on error
        }
      };

      // Start polling after a short delay
      setTimeout(checkStatus, 2000);
    });
  },

  // Tiles
  getTileUrl(datasetId, z, x, y) {
    return `${API_BASE_URL}/api/tiles/${datasetId}/${z}/${x}/${y}.png`;
  },

  // Annotations
  async fetchAnnotations(datasetId, params = {}) {
    const response = await apiClient.get(`/api/annotations/${datasetId}`, {
      params,
    });
    return response.data;
  },

  async createAnnotation(annotation) {
    const response = await apiClient.post("/api/annotations", annotation);
    return response.data;
  },

  async updateAnnotation(id, annotation) {
    const response = await apiClient.put(`/api/annotations/${id}`, annotation);
    return response.data;
  },

  async deleteAnnotation(id) {
    const response = await apiClient.delete(`/api/annotations/${id}`);
    return response.data;
  },

  async exportAnnotations(datasetId, format = "json") {
    const response = await apiClient.get(
      `/api/annotations/${datasetId}/export`,
      {
        params: { format },
        responseType: "blob",
      }
    );
    return response.data;
  },

  // Search
  async searchFeatures(query, params = {}) {
    const response = await apiClient.get("/api/search", {
      params: { q: query, ...params },
    });
    return response.data;
  },

  async spatialSearch(datasetId, bbox) {
    const response = await apiClient.post(`/api/search/spatial/${datasetId}`, {
      bbox,
    });
    return response.data;
  },

  // Comparison
  async getComparisonData(datasetIds) {
    const response = await apiClient.get("/api/compare", {
      params: { ids: datasetIds.join(",") },
    });
    return response.data;
  },

  // Health check
  async healthCheck() {
    const response = await apiClient.get("/api/health");
    return response.data;
  },
};

export default api;
export { API_BASE_URL };
