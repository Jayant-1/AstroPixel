import { Crosshair, Home, ZoomIn, ZoomOut } from "lucide-react";
import Button from "../ui/Button";

const ViewerControls = ({ isReady }) => {
  const handleZoomIn = () => {
    window.dispatchEvent(new Event("viewer:zoom-in"));
  };

  const handleZoomOut = () => {
    window.dispatchEvent(new Event("viewer:zoom-out"));
  };

  const handleReset = () => {
    window.dispatchEvent(new Event("viewer:reset"));
  };

  return (
    <div className="absolute bottom-4 right-4 flex flex-col w-1/6 gap-2">
      <div className="bg-gray-800/90 backdrop-blur-sm border border-gray-700 rounded-lg overflow-hidden">
        <Button
          variant="ghost"
          onClick={handleZoomIn}
          disabled={!isReady}
          title="Zoom In"
          className="hover:bg-gray-700 w-full justify-start gap-2 px-4 py-3 rounded-none border-b border-gray-700"
        >
          <ZoomIn className="w-4 h-4" />
          <span className="text-sm font-medium">Zoom In</span>
        </Button>

        <Button
          variant="ghost"
          onClick={handleZoomOut}
          disabled={!isReady}
          title="Zoom Out"
          className="hover:bg-gray-700 w-full justify-start gap-2 px-4 py-3 rounded-none border-b border-gray-700"
        >
          <ZoomOut className="w-4 h-4" />
          <span className="text-sm font-medium">Zoom Out</span>
        </Button>

        <Button
          variant="ghost"
          onClick={handleReset}
          disabled={!isReady}
          title="Reset View"
          className="hover:bg-gray-700 w-full justify-start gap-2 px-4 py-3 rounded-none border-b border-gray-700"
        >
          <Home className="w-4 h-4" />
          <span className="text-sm font-medium">Reset</span>
        </Button>

        <Button
          variant="ghost"
          disabled={!isReady}
          title="Center View"
          className="hover:bg-gray-700 w-full justify-start gap-2 px-4 py-3 rounded-none"
        >
          <Crosshair className="w-4 h-4" />
          <span className="text-sm font-medium">Center</span>
        </Button>
      </div>

      {/* Scale bar */}
      {isReady && (
        <div className="bg-gray-800/90 backdrop-blur-sm border border-gray-700 rounded-lg px-3 py-2">
          <div className="flex items-center gap-2">
            <div className="w-20 h-1 bg-white" />
            <span className="text-xs text-gray-400">1 km</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default ViewerControls;
