import { Calendar, Info, Layers, MapPin, Ruler } from "lucide-react";
import { API_BASE_URL } from "../../services/api";
import {
  formatDate,
  formatNumber,
  getCategoryColor,
} from "../../utils/helpers";

const ViewerInfo = ({ dataset }) => {
  const colors = getCategoryColor(dataset.category);

  const infoItems = [
    {
      icon: Ruler,
      label: "Resolution",
      value: `${formatNumber(dataset.width)} × ${formatNumber(
        dataset.height
      )} px`,
    },
    {
      icon: Layers,
      label: "Tile Size",
      value: `${dataset.tile_size || 256} px`,
    },
    {
      icon: MapPin,
      label: "Category",
      value: dataset.category?.toUpperCase() || "UNKNOWN",
      className: colors.text,
    },
    {
      icon: Calendar,
      label: "Created",
      value: formatDate(dataset.created_at, "long"),
    },
  ];

  return (
    <div className="p-4 space-y-5">
      {/* Dataset Header with larger preview */}
      <div>
        <div
          className={`w-full h-40 rounded-xl bg-gradient-to-br ${colors.from} ${colors.to} mb-4 flex items-center justify-center overflow-hidden shadow-lg relative group`}
        >
          {dataset.id ? (
            <img
              src={`${API_BASE_URL}/datasets/${dataset.id}_preview.jpg`}
              alt={`${dataset.name} preview`}
              className="w-full h-full object-cover transition-transform group-hover:scale-105 duration-300"
              onError={(e) => {
                e.target.style.display = "none";
                e.target.parentElement.innerHTML = `
                  <div class="text-center">
                    <svg class="w-12 h-12 mx-auto mb-2 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <p class="text-sm text-gray-300">No preview available</p>
                  </div>
                `;
              }}
            />
          ) : (
            <div className="text-center">
              <svg
                className="w-12 h-12 mx-auto mb-2 text-gray-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
              <p className="text-sm text-gray-300">No preview available</p>
            </div>
          )}
        </div>

        <div className="space-y-1">
          <h3 className="font-semibold text-base text-white">{dataset.name}</h3>
          {dataset.description && (
            <p className="text-xs text-gray-400 leading-relaxed">
              {dataset.description}
            </p>
          )}
        </div>
      </div>

      {/* Info Cards - More visual separation */}
      <div>
        <h4 className="text-xs uppercase tracking-wider text-gray-400 mb-3 font-semibold">
          Dataset Information
        </h4>
        <div className="grid grid-cols-2 gap-3">
          {infoItems.map((item, index) => {
            const Icon = item.icon;
            return (
              <div
                key={index}
                className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-3 border border-gray-700/50 hover:border-gray-600 transition-colors"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-3.5 h-3.5 text-gray-400" />
                  <p className="text-xs text-gray-500">{item.label}</p>
                </div>
                <p
                  className={`text-xs font-semibold leading-tight ${
                    item.className || "text-white"
                  }`}
                >
                  {item.value}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Metadata */}
      {dataset.metadata && (
        <div className="pt-3 border-t border-gray-800">
          <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
            <Info className="w-4 h-4" />
            Additional Metadata
          </h4>
          <div className="text-xs text-gray-400 space-y-1">
            {Object.entries(dataset.metadata).map(([key, value]) => (
              <div key={key} className="flex justify-between">
                <span className="text-gray-500">{key}:</span>
                <span>{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Stats - Highlighted */}
      <div>
        <h4 className="text-xs uppercase tracking-wider text-gray-400 mb-3 font-semibold">
          Quick Stats
        </h4>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border border-blue-500/20 rounded-lg p-4 text-center">
            <p className="text-xs text-blue-400 mb-1 font-medium">Max Zoom</p>
            <p className="text-2xl font-bold text-blue-400">
              {dataset.max_zoom || 8}
              <span className="text-base">x</span>
            </p>
          </div>
          <div className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border border-purple-500/20 rounded-lg p-4 text-center">
            <p className="text-xs text-purple-400 mb-1 font-medium">
              Annotations
            </p>
            <p className="text-2xl font-bold text-purple-400">0</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ViewerInfo;
