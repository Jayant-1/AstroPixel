import {
  Download,
  Edit2,
  Eye,
  Filter,
  Search,
  Tag,
  Trash2,
} from "lucide-react";
import React, { useState, useMemo } from "react";
import { useApp } from "../../context/AppContext";
import { formatDate } from "../../utils/helpers";
import Button from "../ui/Button";

const AnnotationsList = () => {
  const {
    annotations,
    annotationsLoading,
    deleteAnnotation,
    updateAnnotation,
    exportAnnotations,
    selectedAnnotation,
    setSelectedAnnotation,
    hiddenAnnotations,
    setHiddenAnnotations,
  } = useApp();

  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState("all");
  const [editingId, setEditingId] = useState(null);
  const [editingLabel, setEditingLabel] = useState("");

  // Memoize filtered annotations to avoid recalculation on every render
  const filteredAnnotations = useMemo(() => {
    return annotations.filter((ann) => {
      const matchesSearch = ann.label
        .toLowerCase()
        .includes(searchTerm.toLowerCase());
      const matchesType =
        filterType === "all" || ann.geometry.type === filterType;
      return matchesSearch && matchesType;
    });
  }, [annotations, searchTerm, filterType]);

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (window.confirm("Are you sure you want to delete this annotation?")) {
      try {
        await deleteAnnotation(id);
      } catch (err) {
        console.error("Failed to delete annotation:", err);
      }
    }
  };

  const toggleHide = (id, e) => {
    e.stopPropagation();
    setHiddenAnnotations((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const startEditing = (annotation, e) => {
    e.stopPropagation();
    setEditingId(annotation.id);
    setEditingLabel(annotation.label);
  };

  const handleRename = async (id, e) => {
    e.stopPropagation();
    if (!editingLabel.trim()) return;

    try {
      await updateAnnotation(id, { label: editingLabel.trim() });
      setEditingId(null);
      setEditingLabel("");
    } catch (err) {
      console.error("Failed to rename annotation:", err);
      alert("Failed to rename annotation: " + err.message);
    }
  };

  const cancelEditing = (e) => {
    e.stopPropagation();
    setEditingId(null);
    setEditingLabel("");
  };

  const handleExport = async () => {
    try {
      await exportAnnotations("json");
    } catch (err) {
      console.error("Failed to export annotations:", err);
    }
  };

  if (annotationsLoading) {
    return (
      <div className="p-4">
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-20 bg-gray-800 animate-pulse rounded-lg"
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Search and Filter */}
      <div className="p-4 border-b border-gray-800 space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search annotations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Types</option>
            <option value="Point">Points</option>
            <option value="Rectangle">Rectangles</option>
            <option value="Circle">Circles</option>
          </select>
        </div>
      </div>

      {/* Annotations List */}
      <div className="flex-1 overflow-y-auto p-4">
        {filteredAnnotations.length === 0 ? (
          <div className="text-center py-12">
            <Tag className="w-12 h-12 mx-auto mb-3 text-gray-600" />
            <p className="text-sm text-gray-400">
              {annotations.length === 0
                ? "No annotations yet"
                : "No matching annotations"}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {annotations.length === 0
                ? "Switch to Annotate mode to create annotations"
                : "Try adjusting your search or filter"}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredAnnotations.map((annotation) => (
              <AnnotationCard
                key={annotation.id}
                annotation={annotation}
                isSelected={selectedAnnotation?.id === annotation.id}
                isHidden={hiddenAnnotations.has(annotation.id)}
                isEditing={editingId === annotation.id}
                editingLabel={editingLabel}
                onEditingLabelChange={setEditingLabel}
                onClick={() => setSelectedAnnotation(annotation)}
                onDelete={(e) => handleDelete(annotation.id, e)}
                onToggleHide={(e) => toggleHide(annotation.id, e)}
                onStartEdit={(e) => startEditing(annotation, e)}
                onRename={(e) => handleRename(annotation.id, e)}
                onCancelEdit={cancelEditing}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer Stats */}
      {annotations.length > 0 && (
        <div className="p-4 border-t border-gray-800">
          <div className="text-xs text-gray-500 text-center">
            {filteredAnnotations.length} of {annotations.length} annotation
            {annotations.length !== 1 ? "s" : ""}
          </div>
        </div>
      )}
    </div>
  );
};

// Annotation Card Component
const AnnotationCard = ({
  annotation,
  isSelected,
  isHidden,
  isEditing,
  editingLabel,
  onEditingLabelChange,
  onClick,
  onDelete,
  onToggleHide,
  onStartEdit,
  onRename,
  onCancelEdit,
}) => {
  return (
    <div
      onClick={onClick}
      className={`w-full text-left p-3 rounded-lg border-2 transition-all cursor-pointer ${
        isSelected
          ? "border-blue-500 bg-blue-500/10"
          : "border-gray-700 bg-gray-800 hover:border-gray-600"
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {isEditing ? (
            <input
              type="text"
              value={editingLabel}
              onChange={(e) => {
                e.stopPropagation();
                onEditingLabelChange(e.target.value);
              }}
              onKeyDown={(e) => {
                e.stopPropagation();
                if (e.key === "Enter") onRename(e);
                if (e.key === "Escape") onCancelEdit(e);
              }}
              onClick={(e) => e.stopPropagation()}
              className="flex-1 px-2 py-1 bg-gray-700 border border-blue-500 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              autoFocus
            />
          ) : (
            <h3
              className="font-semibold text-sm line-clamp-1"
              style={{ opacity: isHidden ? 0.3 : 1 }}
            >
              {annotation.label}
            </h3>
          )}
        </div>

        <div className="flex items-center gap-1">
          {isEditing ? (
            <>
              <button
                onClick={onRename}
                className="p-1 hover:bg-green-500/20 rounded text-green-400 transition-colors"
                title="Save"
              >
                <svg
                  className="w-3.5 h-3.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </button>
              <button
                onClick={onCancelEdit}
                className="p-1 hover:bg-gray-600 rounded text-gray-400 transition-colors"
                title="Cancel"
              >
                <svg
                  className="w-3.5 h-3.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </>
          ) : (
            <>
              <button
                onClick={onToggleHide}
                className="p-1 hover:bg-blue-500/20 rounded text-blue-400 transition-colors"
                title={isHidden ? "Show annotation" : "Hide annotation"}
              >
                <Eye
                  className="w-3.5 h-3.5"
                  style={{ opacity: isHidden ? 0.3 : 1 }}
                />
              </button>
              <button
                onClick={onStartEdit}
                className="p-1 hover:bg-yellow-500/20 rounded text-yellow-400 transition-colors"
                title="Rename annotation"
              >
                <Edit2 className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={onDelete}
                className="p-1 hover:bg-red-500/20 rounded text-red-400 transition-colors"
                title="Delete annotation"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{annotation.geometry?.type || "Unknown"}</span>
        <span>{formatDate(annotation.created_at, "short")}</span>
      </div>
    </div>
  );
};

export default AnnotationsList;
