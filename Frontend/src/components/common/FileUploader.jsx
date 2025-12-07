import { Check, LogIn, UploadCloud, X } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import api from "../../services/api";
import Button from "../ui/Button";
import Input from "../ui/Input";

/**
 * FileUploader component
 * Allows user to upload GeoTIFF files with metadata
 * The backend will process the file and generate tiles
 * Requires user to be authenticated
 */
const FileUploader = ({ onUpload }) => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [showSignInPopup, setShowSignInPopup] = useState(false);
  const [file, setFile] = useState(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("earth");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0); // 0-100 for file upload
  const [processingProgress, setProcessingProgress] = useState(0); // 0-100 for tile generation
  const [statusMessage, setStatusMessage] = useState("");
  const [processingStatus, setProcessingStatus] = useState(null); // null, 'uploading', 'processing', 'completed', 'failed'

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    // Validate file type - support TIFF and PSB/PSD files
    if (!selectedFile.name.match(/\.(tif|tiff|psb|psd)$/i)) {
      setError(
        "Unsupported file format. Supported formats: .tif, .tiff, .psb, .psd"
      );
      return;
    }

    setFile(selectedFile);
    setError(null);
    setSuccess(false);

    // Auto-populate name from filename
    if (!name) {
      const fileName = selectedFile.name.replace(/\.(tif|tiff|psb|psd)$/i, "");
      setName(fileName);
    }
  };

  const handleUpload = async () => {
    // Check if user is authenticated
    if (!isAuthenticated) {
      setShowSignInPopup(true);
      return;
    }

    if (!file || !name || !category) {
      setError("Please provide a file, name, and category");
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(false);
    setUploadProgress(0);
    setProcessingProgress(0);
    setProcessingStatus("uploading");
    setStatusMessage("Uploading file...");

    try {
      // Upload file with progress tracking
      const response = await api.uploadDataset(
        file,
        name,
        description,
        category,
        (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setUploadProgress(percentCompleted);
          setStatusMessage(`Uploading file... ${percentCompleted}%`);
        }
      );

      setUploadProgress(100);
      setProcessingStatus("processing");
      setStatusMessage("Processing tiles...");

      // Poll for processing status with progress updates (no timeout - waits until done)
      const dataset = await api.pollProcessingStatus(
        response.id,
        (progress, status, attempts) => {
          setProcessingProgress(progress);
          setProcessingStatus(status);
          const elapsedMinutes = Math.floor((attempts * 3) / 60);
          const elapsedSeconds = (attempts * 3) % 60;
          const timeStr =
            elapsedMinutes > 0
              ? `${elapsedMinutes}m ${elapsedSeconds}s`
              : `${elapsedSeconds}s`;
          if (progress > 0) {
            setStatusMessage(`Processing tiles... ${progress}% (${timeStr})`);
          } else {
            setStatusMessage(`Processing tiles... (${timeStr})`);
          }
        }
      );

      // Success!
      setSuccess(true);
      setProcessingProgress(100);
      setProcessingStatus("completed");
      setStatusMessage("Upload complete! Tiles are ready.");

      if (onUpload) onUpload(dataset);

      // Reset form after delay
      setTimeout(() => {
        setFile(null);
        setName("");
        setDescription("");
        setCategory("earth");
        setSuccess(false);
        setUploadProgress(0);
        setProcessingProgress(0);
        setStatusMessage("");
        setProcessingStatus(null);
      }, 3000);
    } catch (err) {
      console.error("Upload error:", err);
      setError(err.response?.data?.detail || err.message || "Upload failed");
      setProcessingStatus("failed");
      setStatusMessage("");
    } finally {
      setUploading(false);
    }
  };

  const handleCancel = () => {
    setFile(null);
    setName("");
    setDescription("");
    setCategory("earth");
    setError(null);
    setSuccess(false);
    setUploadProgress(0);
    setProcessingProgress(0);
    setStatusMessage("");
    setProcessingStatus(null);
  };

  return (
    <div className="w-full p-6 border-2 border-dashed border-gray-700 rounded-lg bg-gray-800/50 hover:border-blue-500/50 transition-colors">
      {!file ? (
        // File selection
        <label className="flex flex-col items-center gap-3 cursor-pointer">
          <UploadCloud className="w-12 h-12 text-gray-500" />
          <div className="text-center">
            <p className="text-lg font-medium text-gray-300">Upload Dataset</p>
            <p className="text-sm text-gray-500 mt-1">
              Click to select a .tif, .tiff, .psb, or .psd file (supports files
              up to 40GB)
            </p>
          </div>
          <input
            type="file"
            accept=".tif,.tiff,.psb,.psd"
            className="hidden"
            onChange={handleFileSelect}
            disabled={uploading}
          />
        </label>
      ) : (
        // File details and metadata form
        <div className="space-y-4">
          {/* File info */}
          <div className="flex items-center justify-between p-3 bg-gray-900 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                <UploadCloud className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-200">{file.name}</p>
                <p className="text-xs text-gray-500">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            {!uploading && !uploadProgress && (
              <button
                onClick={handleCancel}
                className="text-gray-500 hover:text-red-400 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>

          {/* Metadata form */}
          <div className="space-y-3">
            <Input
              type="text"
              placeholder="Dataset name (required)"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={uploading || uploadProgress}
              className="w-full"
            />

            <Input
              type="text"
              placeholder="Description (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={uploading || uploadProgress}
              className="w-full"
            />

            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              disabled={uploading || uploadProgress}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="earth">Earth</option>
              <option value="mars">Mars</option>
              <option value="space">Deep Space</option>
            </select>
          </div>

          {/* Status messages */}
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
              <X className="w-5 h-5 text-red-400" />
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {success && (
            <div className="flex items-center gap-2 p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
              <Check className="w-5 h-5 text-green-400" />
              <p className="text-sm text-green-400">
                Upload successful! Tiles are ready to view.
              </p>
            </div>
          )}

          {processingStatus && processingStatus !== "failed" && (
            <div className="space-y-3">
              {/* Status Message */}
              <div className="flex items-center gap-3 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                <p className="text-sm text-blue-400">{statusMessage}</p>
              </div>

              {/* Upload Progress Bar */}
              {processingStatus === "uploading" && uploadProgress > 0 && (
                <div className="space-y-1">
                  <div className="flex justify-between text-xs text-gray-400">
                    <span>Uploading</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2.5 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-blue-500 to-cyan-500 h-full transition-all duration-300 ease-out"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Processing Progress Bar */}
              {processingStatus === "processing" && processingProgress > 0 && (
                <div className="space-y-1">
                  <div className="flex justify-between text-xs text-gray-400">
                    <span>Generating Tiles</span>
                    <span>{processingProgress}%</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2.5 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-purple-500 to-pink-500 h-full transition-all duration-500 ease-out"
                      style={{ width: `${processingProgress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Upload button */}
          {!success && !processingStatus && (
            <div className="flex gap-3">
              <Button
                onClick={handleUpload}
                disabled={uploading || !name || !category}
                className="flex-1"
              >
                {uploading ? "Uploading..." : "Upload & Process"}
              </Button>
              <Button onClick={handleCancel} variant="outline">
                Cancel
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Sign In Required Popup */}
      {showSignInPopup && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-gray-900 rounded-lg p-8 max-w-md w-full mx-4 border border-gray-700 shadow-xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-blue-500/20 rounded-lg flex items-center justify-center">
                <LogIn className="w-6 h-6 text-blue-400" />
              </div>
              <h2 className="text-2xl font-bold text-white">
                Sign In Required
              </h2>
            </div>

            <p className="text-gray-300 mb-6">
              You need to sign in to upload datasets. Create an account or sign
              in with your existing credentials.
            </p>

            <div className="flex gap-3">
              <Button
                onClick={() => {
                  setShowSignInPopup(false);
                  navigate("/login");
                }}
                className="flex-1"
              >
                Sign In
              </Button>
              <Button
                onClick={() => setShowSignInPopup(false)}
                variant="outline"
                className="flex-1"
              >
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUploader;
