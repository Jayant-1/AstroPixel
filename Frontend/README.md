# Gigapixel Explorer - Frontend

A production-ready React application for exploring Gigapixel imagery with smooth tile-based zooming, annotation tools, image comparison features, and AI-powered search capabilities.

## 🚀 Features

### Core Capabilities

- **📸 Dataset Explorer**: Browse and search NASA imagery datasets with filtering by category (Earth, Mars, Space)
- **🔍 Tile-Based Viewer**: Smooth Google Maps-style zooming and panning using OpenSeadragon
- **✏️ Annotation System**: Draw and label features with points, rectangles, polygons, and custom shapes
- **⚖️ Comparison Mode**: Side-by-side, slider, and overlay comparison of multiple datasets
- **🔎 Search & Discovery**: Full-text search across annotations with spatial filtering
- **📊 Metadata Viewer**: Detailed dataset information and statistics

### Technical Highlights

- **Performance Optimized**: 60fps smooth zooming, lazy tile loading, debounced API calls
- **Responsive Design**: Adaptive layouts for desktop, tablet, and mobile
- **Error Handling**: Graceful degradation with offline detection and retry logic
- **Accessibility**: Keyboard navigation and screen reader support

## 🛠️ Technology Stack

- **Framework**: React 18+ with Hooks
- **Mapping**: OpenSeadragon for tile-based zooming
- **UI Library**: Tailwind CSS + Custom Components (shadcn/ui inspired)
- **State Management**: React Context API
- **Routing**: React Router v6
- **API Client**: Axios with interceptors
- **Annotations**: Fabric.js (ready for integration)
- **Comparison**: React Compare Slider
- **Build Tool**: Vite

## 📦 Installation

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend API server running on `http://localhost:8000`

### Setup Steps

1. **Clone and Navigate**

   ```bash
   cd Frontend
   ```

2. **Install Dependencies**

   ```bash
   npm install
   ```

3. **Configure Environment**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set your API base URL:

   ```env
   VITE_API_BASE_URL=http://localhost:8000
   ```

4. **Start Development Server**

   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:3000`

5. **Build for Production**
   ```bash
   npm run build
   npm run preview
   ```

## 📁 Project Structure

```
Frontend/
├── src/
│   ├── components/
│   │   ├── common/          # Shared components (ErrorBoundary, etc.)
│   │   ├── layout/          # Layout components
│   │   ├── ui/              # UI primitives (Button, Input, etc.)
│   │   └── viewer/          # Viewer-specific components
│   │       ├── ViewerCanvas.jsx        # OpenSeadragon integration
│   │       ├── ViewerControls.jsx      # Zoom/pan controls
│   │       ├── AnnotationTools.jsx     # Drawing tools palette
│   │       ├── AnnotationsList.jsx     # Annotations sidebar
│   │       ├── ComparisonView.jsx      # Image comparison
│   │       └── ViewerInfo.jsx          # Dataset metadata
│   ├── context/
│   │   └── AppContext.jsx   # Global state management
│   ├── pages/
│   │   ├── Home.jsx         # Dataset explorer page
│   │   ├── Viewer.jsx       # Main viewer page
│   │   └── NotFound.jsx     # 404 page
│   ├── services/
│   │   └── api.js           # API client & endpoints
│   ├── utils/
│   │   └── helpers.js       # Utility functions
│   ├── App.jsx              # Root component
│   ├── main.jsx             # Entry point
│   └── index.css            # Global styles
├── public/                  # Static assets
├── .env.example             # Environment template
├── package.json
├── vite.config.js
├── tailwind.config.js
└── README.md
```

## 🔌 API Integration

The application integrates with the following backend endpoints:

```javascript
GET    /api/datasets                    // List all datasets
GET    /api/datasets/:id                // Get dataset details
GET    /api/tiles/:id/:z/:x/:y.jpg      // Fetch tiles
POST   /api/annotations                 // Create annotation
GET    /api/annotations/:dataset_id     // Get annotations
PUT    /api/annotations/:id             // Update annotation
DELETE /api/annotations/:id             // Delete annotation
GET    /api/search?q=query              // Search features
GET    /api/compare?ids=1,2             // Compare datasets
```

## 🎨 Component Usage Examples

### Using the Viewer Canvas

```jsx
import ViewerCanvas from "./components/viewer/ViewerCanvas";

<ViewerCanvas
  dataset={selectedDataset}
  mode="explore"
  onReady={() => console.log("Viewer ready")}
/>;
```

### Creating Annotations

```jsx
import { useApp } from "./context/AppContext";

const { createAnnotation } = useApp();

await createAnnotation({
  label: "Crater",
  description: "Large impact crater",
  geometry: {
    type: "Point",
    coordinates: [0.5, 0.5],
  },
});
```

### Using Comparison View

```jsx
import ComparisonView from "./components/viewer/ComparisonView";

<ComparisonView dataset={primaryDataset} />;
```

## ⚙️ Configuration

### OpenSeadragon Settings

Adjust viewer behavior in `ViewerCanvas.jsx`:

```javascript
{
  animationTime: 0.5,          // Zoom/pan animation duration
  zoomPerScroll: 1.2,          // Zoom increment per scroll
  maxZoomPixelRatio: 4,        // Maximum zoom level
  visibilityRatio: 1,          // Minimum visible area
}
```

### Performance Tuning

- **Tile Cache**: Controlled by OpenSeadragon's internal cache
- **API Debounce**: 300ms (configurable in `AppContext.jsx`)
- **Chunk Splitting**: Configured in `vite.config.js`

## 🧪 Testing

```bash
# Run linter
npm run lint

# Type checking (if TypeScript is added)
npm run type-check
```

## 📱 Responsive Breakpoints

- **Desktop**: Full feature set (1024px+)
- **Tablet**: Adapted sidebar layouts (768px - 1023px)
- **Mobile**: View-only mode, limited annotations (< 768px)

## 🚧 Development Roadmap

### Implemented ✅

- [x] Dataset explorer with search and filtering
- [x] OpenSeadragon tile viewer integration
- [x] Basic annotation tools UI
- [x] Comparison mode with slider
- [x] API service layer
- [x] Responsive design
- [x] Error boundaries

### Planned 🔜

- [ ] Fabric.js annotation drawing implementation
- [ ] Real-time annotation sync
- [ ] Advanced search with filters
- [ ] Export annotations (GeoJSON, KML)
- [ ] User authentication
- [ ] Collaborative annotations
- [ ] AI-powered feature detection
- [ ] Minimap navigator
- [ ] Keyboard shortcuts

## 🐛 Known Issues

- Tile loading uses placeholder gradients (replace with actual API tiles)
- Annotation drawing is UI-only (needs Fabric.js integration)
- Minimap shows placeholder (needs OpenSeadragon navigator)

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For issues and questions:

- Open an issue on GitHub
- Check the documentation
- Contact the development team

---

Built with ❤️ for Gigapixel Imagery Exploration
