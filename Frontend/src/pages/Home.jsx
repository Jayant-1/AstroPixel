import {
  ChevronDown,
  Globe,
  Grid,
  Layers,
  List,
  LogOut,
  Moon,
  Search,
  Sparkles,
  Telescope,
  Trash2,
  User,
} from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import FileUploader from "../components/common/FileUploader";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import ProcessingStatusBadge from "../components/ui/ProcessingStatusBadge";
import { useApp } from "../context/AppContext";
import { useAuth } from "../context/AuthContext";
import api, { API_BASE_URL } from "../services/api";
import { cn, formatNumber, getCategoryColor } from "../utils/helpers";

const Home = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();
  const {
    datasets,
    loading,
    filterCategory,
    setFilterCategory,
    searchQuery,
    setSearchQuery,
    loadDatasets,
  } = useApp();

  const [viewType, setViewType] = useState("grid"); // grid | list
  const [sortBy, setSortBy] = useState("name"); // name | date | size

  const categories = [
    { id: null, name: "All Datasets", icon: Layers, color: "gray" },
    { id: "earth", name: "Earth", icon: Globe, color: "blue" },
    { id: "mars", name: "Mars", icon: Moon, color: "orange" },
    { id: "space", name: "Deep Space", icon: Sparkles, color: "purple" },
  ];

  const filteredDatasets = datasets
    .filter((dataset) =>
      searchQuery
        ? dataset.name.toLowerCase().includes(searchQuery.toLowerCase())
        : true
    )
    .sort((a, b) => {
      if (sortBy === "name") return a.name.localeCompare(b.name);
      if (sortBy === "date")
        return new Date(b.created_at) - new Date(a.created_at);
      if (sortBy === "size") return b.width * b.height - a.width * a.height;
      return 0;
    });

  const handleDatasetClick = (dataset) => {
    navigate(`/viewer/${dataset.id}`);
  };

  const handleFileUpload = async (dataset) => {
    console.log("File uploaded successfully:", dataset);

    // Reload datasets to show the new one
    await loadDatasets(filterCategory);

    // Optionally navigate to the uploaded dataset viewer
    if (dataset && dataset.id) {
      setTimeout(() => {
        navigate(`/viewer/${dataset.id}`);
      }, 1500);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Top Navigation Bar */}
      <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 via-purple-600 to-pink-500 rounded-xl flex items-center justify-center">
              <Telescope className="w-5 h-5" />
            </div>
            <span className="text-xl font-bold">AstroPixel</span>
          </Link>

          <div className="flex items-center gap-4">
            {isAuthenticated ? (
              <>
                <div className="flex items-center gap-2 text-gray-300">
                  <User className="w-4 h-4" />
                  <span className="text-sm">
                    {user?.username || user?.email}
                  </span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={logout}
                  className="gap-2 text-gray-400 hover:text-white"
                >
                  <LogOut className="w-4 h-4" />
                  Logout
                </Button>
              </>
            ) : (
              <>
                <Link to="/login">
                  <Button variant="ghost" size="sm">
                    Sign in
                  </Button>
                </Link>
                <Link to="/signup">
                  <Button size="sm">Get Started</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative bg-gradient-to-br from-gray-900 via-blue-900/20 to-purple-900/20 border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="flex items-center gap-4 mb-6">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 via-purple-600 to-pink-500 rounded-2xl flex items-center justify-center">
              <Telescope className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-4xl font-bold mb-2">
                NASA Gigapixel Explorer
              </h1>
              <p className="text-gray-400">
                Explore high-resolution imagery from NASA missions with advanced
                annotation and analysis tools
              </p>
            </div>
          </div>

          {/* Search Bar and File Upload */}
          <div className="max-w-2xl space-y-4">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <Input
                type="text"
                placeholder="Search datasets by name, description, or mission..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-12 pr-4 py-3 text-lg"
              />
            </div>

            {/* File Upload Section */}
            <FileUploader onUpload={handleFileUpload} />
          </div>
        </div>
      </section>

      {/* Category Filter */}
      <section className="border-b border-gray-800 bg-gray-900/50">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {categories.map((cat) => {
                const Icon = cat.icon;
                return (
                  <button
                    key={cat.id}
                    onClick={() => setFilterCategory(cat.id)}
                    className={cn(
                      "flex items-center gap-2 px-4 py-2 rounded-lg border-2 transition-all",
                      filterCategory === cat.id
                        ? "border-blue-500 bg-blue-500/10 text-blue-400"
                        : "border-gray-700 hover:border-gray-600 text-gray-400"
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="text-sm font-medium">{cat.name}</span>
                  </button>
                );
              })}
            </div>

            <div className="flex items-center gap-3">
              {/* Sort Dropdown */}
              <div className="relative">
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="appearance-none bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="name">Sort by Name</option>
                  <option value="date">Sort by Date</option>
                  <option value="size">Sort by Size</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
              </div>

              {/* View Toggle */}
              <div className="flex bg-gray-800 rounded-lg p-1">
                <button
                  onClick={() => setViewType("grid")}
                  className={cn(
                    "p-2 rounded",
                    viewType === "grid" ? "bg-blue-600" : "hover:bg-gray-700"
                  )}
                >
                  <Grid className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setViewType("list")}
                  className={cn(
                    "p-2 rounded",
                    viewType === "list" ? "bg-blue-600" : "hover:bg-gray-700"
                  )}
                >
                  <List className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Datasets Grid */}
      <section className="max-w-7xl mx-auto px-6 py-8">
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div
                key={i}
                className="h-64 bg-gray-800 animate-pulse rounded-xl"
              />
            ))}
          </div>
        ) : filteredDatasets.length === 0 ? (
          <div className="text-center py-16">
            <Telescope className="w-16 h-16 mx-auto mb-4 text-gray-600" />
            <h2 className="text-xl font-semibold mb-2 text-gray-400">
              No datasets found
            </h2>
            <p className="text-gray-500">
              Try adjusting your search or filter criteria
            </p>
          </div>
        ) : viewType === "grid" ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredDatasets.map((dataset) => (
              <DatasetCard
                key={dataset.id}
                dataset={dataset}
                onClick={() => handleDatasetClick(dataset)}
              />
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            {filteredDatasets.map((dataset) => (
              <DatasetListItem
                key={dataset.id}
                dataset={dataset}
                onClick={() => handleDatasetClick(dataset)}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

// Dataset Card Component
const DatasetCard = ({ dataset, onClick }) => {
  const colors = getCategoryColor(dataset.category);
  const { loadDatasets, filterCategory } = useApp();
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async (e) => {
    e.stopPropagation();

    if (
      !confirm(
        `Are you sure you want to delete "${dataset.name}"? This action cannot be undone.`
      )
    ) {
      return;
    }

    setDeleting(true);
    try {
      await api.deleteDataset(dataset.id);
      await loadDatasets(filterCategory);
    } catch (error) {
      console.error("Failed to delete dataset:", error);
      alert("Failed to delete dataset. Please try again.");
    } finally {
      setDeleting(false);
    }
  };

  // Preview image URL from dataset metadata (stored in R2)
  // Falls back to constructed URL for legacy datasets
  const cacheBust = dataset.updated_at
    ? new Date(dataset.updated_at).getTime()
    : dataset.created_at
    ? new Date(dataset.created_at).getTime()
    : Date.now();

  const previewUrl = dataset.extra_metadata?.preview_url
    ? `${dataset.extra_metadata.preview_url}${
        dataset.extra_metadata.preview_url.includes("?") ? "&" : "?"
      }v=${cacheBust}`
    : dataset.id
    ? `${API_BASE_URL}/api/tiles/${dataset.id}/preview?v=${cacheBust}`
    : null;

  const [imgError, setImgError] = useState(false);

  return (
    <div className="group relative text-left bg-gray-900 border-2 border-gray-800 rounded-xl overflow-hidden hover:border-gray-700 transition-all hover:scale-[1.02]">
      {/* Delete Button (only for non-demo datasets) */}
      {!dataset.is_demo && (
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="absolute top-3 right-3 z-10 p-2 bg-red-500/90 hover:bg-red-600 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-50"
          title="Delete dataset"
        >
          <Trash2 className="w-4 h-4 text-white" />
        </button>
      )}

      <button
        onClick={onClick}
        className="w-full text-left"
        disabled={deleting}
      >
        {/* Thumbnail */}
        <div
          className={cn(
            "h-40 bg-gradient-to-br flex items-center justify-center relative overflow-hidden",
            colors.from,
            colors.to
          )}
        >
          {!imgError && previewUrl ? (
            <img
              src={previewUrl}
              alt={dataset.name + " preview"}
              className="object-cover w-full h-full absolute inset-0"
              onError={() => setImgError(true)}
            />
          ) : (
            <Telescope className="w-12 h-12 opacity-50 z-10" />
          )}
          <div className="absolute inset-0 bg-black/20 group-hover:bg-black/10 transition-colors" />
        </div>

        {/* Content */}
        <div className="p-5">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <h3 className="font-semibold text-lg line-clamp-1">
                {dataset.name}
              </h3>
              {dataset.is_demo && (
                <span className="px-2 py-0.5 text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded">
                  DEMO
                </span>
              )}
            </div>
            {dataset.processing_status && (
              <ProcessingStatusBadge
                status={dataset.processing_status}
                progress={dataset.processing_progress || 0}
              />
            )}
          </div>
          <p className="text-sm text-gray-400 mb-4 line-clamp-2">
            {dataset.description || "High-resolution imagery dataset"}
          </p>

          {/* Expiry Warning (only show if time_until_expiry is present) */}
          {dataset.time_until_expiry && !dataset.is_demo && (
            <div className="mb-3 px-3 py-2 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
              <p className="text-xs text-yellow-500 font-medium">
                ⚠️ Expires in {dataset.time_until_expiry}
              </p>
            </div>
          )}

          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>
              {formatNumber(dataset.width)} × {formatNumber(dataset.height)} px
            </span>
            <span className={cn("capitalize", colors.text)}>
              {dataset.category}
            </span>
          </div>
        </div>
      </button>

      {deleting && (
        <div className="absolute inset-0 bg-gray-900/80 flex items-center justify-center">
          <div className="text-center">
            <div className="w-8 h-8 border-4 border-red-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-sm text-gray-400">Deleting...</p>
          </div>
        </div>
      )}
    </div>
  );
};

// Dataset List Item Component
const DatasetListItem = ({ dataset, onClick }) => {
  const colors = getCategoryColor(dataset.category);
  const { loadDatasets, filterCategory } = useApp();
  const [deleting, setDeleting] = useState(false);
  const Icon =
    dataset.category === "earth"
      ? Globe
      : dataset.category === "mars"
      ? Moon
      : Sparkles;

  const handleDelete = async (e) => {
    e.stopPropagation();

    if (
      !confirm(
        `Are you sure you want to delete "${dataset.name}"? This action cannot be undone.`
      )
    ) {
      return;
    }

    setDeleting(true);
    try {
      await api.deleteDataset(dataset.id);
      await loadDatasets(filterCategory);
    } catch (error) {
      console.error("Failed to delete dataset:", error);
      alert("Failed to delete dataset. Please try again.");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="group relative w-full text-left bg-gray-900 border-2 border-gray-800 rounded-lg p-4 hover:border-gray-700 transition-all">
      <button
        onClick={onClick}
        className="w-full text-left flex items-center gap-4"
        disabled={deleting}
      >
        <div
          className={cn(
            "w-16 h-16 rounded-lg bg-gradient-to-br flex items-center justify-center flex-shrink-0",
            colors.from,
            colors.to
          )}
        >
          <Icon className="w-8 h-8" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold">{dataset.name}</h3>
            {dataset.processing_status && (
              <ProcessingStatusBadge
                status={dataset.processing_status}
                progress={dataset.processing_progress || 0}
              />
            )}
          </div>
          <p className="text-sm text-gray-400 mb-2 line-clamp-1">
            {dataset.description || "High-resolution imagery dataset"}
          </p>
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>
              {formatNumber(dataset.width)} × {formatNumber(dataset.height)} px
            </span>
            <span className={cn("capitalize", colors.text)}>
              • {dataset.category}
            </span>
          </div>
        </div>

        {/* Delete Button */}
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="p-2 bg-red-500/90 hover:bg-red-600 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-50 ml-4"
          title="Delete dataset"
        >
          <Trash2 className="w-4 h-4 text-white" />
        </button>
      </button>

      {deleting && (
        <div className="absolute inset-0 bg-gray-900/80 flex items-center justify-center rounded-lg">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 border-4 border-red-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-gray-400">Deleting...</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default Home;
