# 🚀 NASA Gigapixel Explorer - Backend API

FastAPI backend for processing and serving NASA gigapixel imagery.

## ✅ Quick Start

### 1. Start the Server

```powershell
.\start_server.ps1
```

### 2. Access the API

- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health

## 📦 Environment

- **Python**: 3.11.13 (conda environment: `astropixel`)
- **Database**: SQLite (development mode)
- **Framework**: FastAPI 0.109.0

## 🛠️ Configuration

Edit `.env` file for settings:

- Database URL
- CORS origins
- Upload/storage paths
- Tile generation settings

## 🔌 API Endpoints

### Datasets

- `POST /api/datasets` - Upload dataset
- `GET /api/datasets` - List datasets
- `GET /api/datasets/{id}` - Get dataset details
- `DELETE /api/datasets/{id}` - Delete dataset

### Tiles

- `GET /api/tiles/{dataset_id}/{z}/{x}/{y}` - Get tile
- `GET /api/tiles/{dataset_id}/metadata` - Get tile metadata

### Search

- `GET /api/search` - Search datasets
- `GET /api/search/category/{category}` - Search by category

### Health

- `GET /health` - Server health check

## 📁 Project Structure

```
Backend/
├── app/
│   ├── routers/        # API endpoints
│   ├── services/       # Business logic
│   ├── config.py       # Configuration
│   ├── database.py     # Database setup
│   ├── models.py       # Database models
│   └── schemas.py      # Pydantic schemas
├── .env                # Environment variables
├── requirements.txt    # Python dependencies
└── start_server.ps1    # Server startup script
```

## 🔄 Development

### Install Dependencies

```powershell
conda activate astropixel
pip install -r requirements.txt
```

### Run Tests

```powershell
pytest
```

### Format Code

```powershell
black app/
flake8 app/
```

## 📝 Notes

- **Annotations**: Disabled (requires PostgreSQL with PostGIS)
- **Spatial Features**: Limited in SQLite mode
- **For Production**: Consider PostgreSQL + PostGIS + Redis

## 🆘 Support

Check server logs for errors. Most issues are related to:

1. Conda environment not activated
2. Missing dependencies
3. Database connection issues
