import { AlertCircle, CheckCircle2, Loader2, XCircle } from "lucide-react";
import { cn } from "../../utils/helpers";

/**
 * ProcessingStatusBadge component
 * Displays the processing status of a dataset with appropriate icon and color
 */
const ProcessingStatusBadge = ({ status, progress = 0, className = "" }) => {
  const getStatusConfig = () => {
    switch (status) {
      case "completed":
        return {
          icon: CheckCircle2,
          text: "Ready",
          color: "text-green-400",
          bg: "bg-green-500/10",
          border: "border-green-500/30",
        };
      case "processing":
        return {
          icon: Loader2,
          text: `Processing ${progress}%`,
          color: "text-blue-400",
          bg: "bg-blue-500/10",
          border: "border-blue-500/30",
          animate: true,
        };
      case "pending":
        return {
          icon: AlertCircle,
          text: "Pending",
          color: "text-yellow-400",
          bg: "bg-yellow-500/10",
          border: "border-yellow-500/30",
        };
      case "failed":
        return {
          icon: XCircle,
          text: "Failed",
          color: "text-red-400",
          bg: "bg-red-500/10",
          border: "border-red-500/30",
        };
      default:
        return {
          icon: AlertCircle,
          text: "Unknown",
          color: "text-gray-400",
          bg: "bg-gray-500/10",
          border: "border-gray-500/30",
        };
    }
  };

  const config = getStatusConfig();
  const Icon = config.icon;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium",
        config.bg,
        config.border,
        config.color,
        className
      )}
    >
      <Icon className={cn("w-3.5 h-3.5", config.animate && "animate-spin")} />
      <span>{config.text}</span>
      {status === "processing" && progress > 0 && (
        <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden ml-1">
          <div
            className="h-full bg-blue-400 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </div>
  );
};

export default ProcessingStatusBadge;
