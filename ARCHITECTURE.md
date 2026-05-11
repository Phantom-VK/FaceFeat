# FaceFeat — Architecture

## Overview

FaceFeat is a video face analysis pipeline. A video is uploaded via REST API, processed frame-by-frame using MediaPipe face detection and landmarking, results are persisted to PostgreSQL, and surfaced through a ROI aggregation API consumed by a vanilla JS frontend.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Compose                           │
│                                                                 │
│  ┌──────────────┐    HTTP     ┌──────────────────────────────┐  │
│  │   Frontend   │ ──────────▶ │         Backend              │  │
│  │  Nginx:80    │ ◀────────── │      FastAPI :8000           │  │
│  │  (port 5500) │             │                              │  │
│  └──────────────┘             │  ┌────────┐  ┌───────────┐  │  │
│                               │  │ Routes │  │ Services  │  │  │
│                               │  └────────┘  └───────────┘  │  │
│                               └──────────────┬───────────────┘  │
│                                              │ SQLAlchemy        │
│                               ┌──────────────▼───────────────┐  │
│                               │     PostgreSQL :5432         │  │
│                               │   videos + video_faces       │  │
│                               └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Request Flow — Video Upload & Processing

```
Browser                  FastAPI              VideoProcessor        Database
  │                         │                       │                  │
  │  POST /api/video/upload  │                       │                  │
  │ ──────────────────────▶ │                       │                  │
  │                         │  INSERT video row     │                  │
  │                         │ ─────────────────────────────────────▶  │
  │                         │                       │                  │
  │                         │  process_video(path)  │                  │
  │                         │ ─────────────────────▶│                  │
  │                         │                       │ read frames      │
  │                         │                       │ ──────────────▶  │
  │                         │                       │                  │
  │                         │                       │ BlazeFace detect │
  │                         │                       │ ◀──────────────  │
  │                         │                       │                  │
  │                         │                       │ Landmarker 478pt │
  │                         │                       │ ──────────────▶  │
  │                         │                       │                  │
  │                         │                       │ draw overlays    │
  │                         │                       │ write frame      │
  │                         │                       │                  │
  │                         │                       │ INSERT VideoFace │
  │                         │ ◀─────────────────────│ per face/frame   │
  │                         │    done, path set     │ ─────────────────▶
  │ ◀────────────────────── │                       │                  │
  │  { video_id }           │                       │                  │
```

---

## Request Flow — Poll Status & Load ROI

```
Browser                         FastAPI                    Database
  │                                │                           │
  │  GET /api/video/{id}/status    │                           │
  │ ─────────────────────────────▶ │                           │
  │                                │  SELECT processed_path    │
  │                                │ ─────────────────────────▶│
  │ ◀───────────────────────────── │ ◀─────────────────────────│
  │  { status: "processing" }      │                           │
  │                                │                           │
  │  ... poll every 2s ...         │                           │
  │                                │                           │
  │  GET /api/video/{id}/status    │                           │
  │ ─────────────────────────────▶ │                           │
  │ ◀───────────────────────────── │                           │
  │  { status: "done" }            │                           │
  │                                │                           │
  │  GET /api/video/{id}           │                           │
  │ ─────────────────────────────▶ │  StreamingResponse        │
  │ ◀───────────────────────────── │  (processed video)        │
  │                                │                           │
  │  GET /api/video/{id}/roi       │                           │
  │ ─────────────────────────────▶ │                           │
  │                                │  SELECT VideoFace         │
  │                                │  paginate + aggregate     │
  │                                │ ─────────────────────────▶│
  │ ◀───────────────────────────── │ ◀─────────────────────────│
  │  { faces[], summary[] }        │                           │
```

---

## Face Detection Pipeline (Per Frame)

```
Raw Frame (BGR)
      │
      ▼
┌─────────────────────┐
│   BlazeFace Detect  │  blaze_face_full_range.tflite
│   (detector.py)     │  → bounding boxes, confidence
└──────────┬──────────┘
           │  face crops
           ▼
┌─────────────────────┐
│  Face Landmarker    │  face_landmarker_full.task
│  (landmarker.py)    │  → 478 landmarks, blendshapes,
└──────────┬──────────┘    pose matrix (pitch/yaw/roll)
           │
           ▼
┌─────────────────────┐
│  Expression Extract │  blendshape coefficients →
│  (utils.py)         │  smile, blink_l, blink_r,
└──────────┬──────────┘  brow_raise scores (0–1)
           │
           ▼
┌─────────────────────┐
│  Overlay Drawing    │  bounding box, landmarks,
│  (drawing.py)       │  expression labels on frame
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  VideoFace INSERT   │  one row per detected face
│  (video_processor)  │  per frame → PostgreSQL
└─────────────────────┘
```

---

## ROI Aggregation — `/api/video/{id}/roi`

```
VideoFace rows (N frames × M faces)
           │
           │  GROUP BY face_index
           ▼
┌──────────────────────────────────────┐
│  Per-face aggregation (roi.py)       │
│                                      │
│  avg_confidence    ← mean(confidence)│
│  avg_smile         ← mean(smile)     │
│  avg_blink_left    ← mean(blink_l)   │
│  avg_blink_right   ← mean(blink_r)   │
│  avg_brow_raise    ← mean(brow_raise)│
│  avg_pitch/yaw/roll← mean(pose)      │
│  frames_detected   ← count(rows)     │
└──────────────────────┬───────────────┘
                       │
                       ▼
          { summary: [ FaceCard × M ] }
                       │
                       ▼
             Frontend Face Cards UI
```

---

## Database Schema

```
┌──────────────────────────────┐       ┌──────────────────────────────────────┐
│           videos             │       │            video_faces               │
├──────────────────────────────┤       ├──────────────────────────────────────┤
│ id            UUID  PK       │──────▶│ id              UUID  PK             │
│ original_path VARCHAR        │  1:N  │ video_id         UUID  FK            │
│ processed_path VARCHAR NULL  │       │ face_index       INT                 │
│ created_at    TIMESTAMP      │       │ frame_index      INT                 │
└──────────────────────────────┘       │ confidence       FLOAT               │
                                       │ bbox_x/y/w/h     FLOAT               │
                                       │ smile            FLOAT               │
                                       │ blink_left       FLOAT               │
                                       │ blink_right      FLOAT               │
                                       │ brow_raise       FLOAT               │
                                       │ pitch/yaw/roll   FLOAT               │
                                       │ landmarks        JSON  (optional)    │
                                       └──────────────────────────────────────┘
```

---

## API Routes Map

```
app/
└── main.py  (FastAPI + CORSMiddleware + lifespan)
      │
      └── api_router  (router.py)
            ├── POST   /api/video/upload       → upload_video.py
            ├── GET    /api/video/{id}          → stream_video.py
            ├── GET    /api/video/{id}/status   → stream_video.py
            └── GET    /api/video/{id}/roi      → roi.py
                         ├── _get_video_or_404
                         ├── _fetch_faces        (paginated)
                         ├── _serialize_face
                         └── _aggregate_faces    (group by face_index)
```

---

## Docker Compose Service Graph

```
          ┌─────────────┐
          │   frontend  │  nginx:alpine
          │  port 5500  │  serves ./frontend/src/
          └──────┬──────┘
                 │ HTTP :8000
          ┌──────▼──────┐
          │   backend   │  python:3.12-slim
          │  port 8000  │  uvicorn + FastAPI
          └──────┬──────┘
    depends_on   │ healthcheck
    (healthy)    │ postgresql://facefeat@db:5432/facefeat
          ┌──────▼──────┐
          │     db      │  postgres:16-alpine
          │  port 5432  │  volume: postgres_data
          └─────────────┘

Named volumes:
  postgres_data  → DB persistence
  uploads_data   → raw + processed video files
```
