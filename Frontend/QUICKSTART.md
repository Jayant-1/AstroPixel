# NASA Gigapixel Explorer - Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### Step 1: Install Dependencies

```bash
npm install
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and set your backend URL (default is http://localhost:8000)
```

### Step 3: Start Development Server

```bash
npm run dev
```

Visit `http://localhost:3000` in your browser!

## 📋 Available Scripts

- `npm run dev` - Start development server (port 3000)
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## 🔧 Common Issues & Solutions

### Port Already in Use

If port 3000 is taken, Vite will automatically use the next available port. Check the terminal output for the actual URL.

### API Connection Failed

1. Ensure backend is running on `http://localhost:8000`
2. Check CORS settings on backend
3. Verify `VITE_API_BASE_URL` in `.env`

### Tiles Not Loading

The app uses demo placeholders. To see actual tiles:

1. Ensure backend implements `/api/tiles/:id/:z/:x/:y.jpg` endpoint
2. Check browser console for tile loading errors
3. Verify dataset has correct tile_size and max_zoom values

### Module Not Found Errors

```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

## 🎯 Next Steps

1. **Connect to Backend**: Update API_BASE_URL in `.env`
2. **Test API Integration**: Check browser DevTools Network tab
3. **Customize Branding**: Update logo and colors in tailwind.config.js
4. **Add Real Tiles**: Implement tile server endpoints
5. **Enable Annotations**: Integrate Fabric.js for drawing

## 📚 Key Files to Understand

- `src/App.jsx` - Application routes
- `src/context/AppContext.jsx` - Global state management
- `src/services/api.js` - API endpoints
- `src/components/viewer/ViewerCanvas.jsx` - OpenSeadragon integration
- `src/pages/Home.jsx` - Dataset explorer
- `src/pages/Viewer.jsx` - Main viewer page

## 🔗 Helpful Resources

- [OpenSeadragon Docs](https://openseadragon.github.io/)
- [React Router](https://reactrouter.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Vite Guide](https://vitejs.dev/guide/)

## 💡 Pro Tips

1. **Hot Module Replacement**: Changes auto-reload in dev mode
2. **React DevTools**: Install browser extension for debugging
3. **Network Tab**: Monitor API calls and tile loading
4. **Console**: Watch for errors and warnings

Happy Exploring! 🛰️
