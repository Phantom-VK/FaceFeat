# FaceFeat

Real-time face detection and ROI analysis pipeline. Upload a video, detect faces frame-by-frame using MediaPipe, and get per-face aggregated summaries — expressions, blink rate, pose estimation — via a REST API.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.12 |
| Face Detection | MediaPipe (BlazeFace + Face Landmarker) |
| Video Processing | imageio, FFmpeg, OpenCV |
| Database | PostgreSQL 16, SQLModel, SQLAlchemy |
| Migrations | Alembic |
| Frontend | HTML / CSS / JavaScript (vanilla) |
| Server | Uvicorn, Nginx (static serving) |
| Containerization | Docker, Docker Compose |
| Dependency Management | uv |

---

## Project Structure

```
FaceFeat/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # upload_video, stream_video, roi
│   │   ├── core/              # config, database
│   │   ├── models/            # Video, VideoFace SQLModel tables
│   │   ├── services/
│   │   │   ├── face_detection/ # MediaPipe detector, landmarker, drawing
│   │   │   └── video_processor.py
│   │   └── main.py
│   ├── mediapipe_models/      # .tflite and .task model files
│   ├── migrations/            # Alembic versions
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── facefeat.html
│       ├── script.js
│       └── style.css
├── docker-compose.yml
└── pyproject.toml
```

---

## Setup

### Prerequisites

- Docker and Docker Compose installed
- No other setup required — all dependencies are containerized

### Run with Docker (recommended)

```bash
git clone https://github.com/your-username/FaceFeat.git
cd FaceFeat
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5500/facefeat.html |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Postgres | localhost:5432 |

Alembic migrations run automatically on backend startup.

### Run locally (without Docker)

**Requirements:** Python 3.12+, PostgreSQL running on `localhost:5432`, FFmpeg installed.

```bash
# Install uv
pip install uv

# Install dependencies
cd backend
uv sync

# Set env
export DATABASE_URL=postgresql://facefeat:facefeat@localhost:5432/facefeat

# Run migrations
uv run alembic upgrade head

# Start server
uv run uvicorn app.main:app --reload --port 8000
```

Open `frontend/src/facefeat.html` via a local server:

```bash
cd frontend/src
python3 -m http.server 5500
```

Then open `http://localhost:5500/facefeat.html`.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/video/upload` | Upload and process a video |
| `GET` | `/api/video/{id}` | Stream the processed video |
| `GET` | `/api/video/{id}/status` | Poll processing status |
| `GET` | `/api/video/{id}/roi` | Per-face ROI summary with pagination |

### ROI Query Params

| Param | Default | Description |
|---|---|---|
| `skip` | `0` | Pagination offset |
| `limit` | `100` | Max records (cap 1000) |
| `landmarks` | `false` | Include 478-point landmark arrays |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://facefeat:facefeat@db:5432/facefeat` | Postgres connection string |

---

## Health Check

```
GET /health  →  { "health": "ok" }
```
