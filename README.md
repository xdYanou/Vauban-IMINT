<p align="center">
  <h1 align="center">VAUBAN</h1>
  <p align="center">
    <strong>IMINT & Military Intelligence Platform</strong><br>
    Satellite imagery analysis for Russian airbase monitoring
  </p>
</p>

---

## Overview

Vauban is a defence-oriented proof of work IMINT (Imagery Intelligence) platform that uses satellite imagery and computer vision to monitor Russian military airbases. The system detects, classifies, and tracks military aircraft deployments over time.

Named after [Sebastien Le Prestre de Vauban](https://en.wikipedia.org/wiki/Vauban), the French military engineer and Marshal of France.

### What it does

- **Monitors 25 Russian military airbases** including Engels-2, Hmeimim, Kubinka, and Crimean bases
- **Fetches satellite imagery** from multiple sources (Sentinel-2, Esri World Imagery tiles)
- **Detects aircraft** using a two-stage ML pipeline (YOLOv8 + EfficientNet)
- **Classifies aircraft types** — Su-34, Tu-95, MiG-31, Ka-52, Il-76, and 30+ more
- **Tracks changes over time** — observation history, aircraft counts, type distribution analytics
- **Bulk capture** all monitored airbases in a single operation

## Architecture

```
                    +------------------+
                    |   React Frontend |
                    |   Leaflet Maps   |
                    |   Recharts       |
                    +--------+---------+
                             |
                    +--------+---------+
                    |   FastAPI Backend |
                    |                  |
                    |  +------------+  |
                    |  | Sentinel-2 |  |  Copernicus Data Space
                    |  | Service    |  |  (10m resolution, free)
                    |  +------------+  |
                    |                  |
                    |  +------------+  |
                    |  | Tile       |  |  Esri World Imagery
                    |  | Service    |  |  (0.5-1.2m resolution)
                    |  +------------+  |
                    |                  |
                    |  +------------+  |
                    |  | Detection  |  |  Two-Stage Pipeline
                    |  | Service    |  |
                    |  +------+-----+  |
                    +---------|--------+
                              |
                 +------------+------------+
                 |                         |
          +------+------+          +------+------+
          | Stage 1     |          | Stage 2     |
          | YOLOv8      |          | EfficientNet|
          | Detection   |   --->   | Classifier  |
          | (7 classes) |          | (35 types)  |
          +-------------+          +-------------+
```

### Two-Stage Detection Pipeline

**Stage 1 — Detection (YOLOv8)**
- Finds aircraft in satellite imagery and draws bounding boxes
- Classifies into broad categories: fighter, bomber, transport, tanker, surveillance, rotary, trainer
- Trained on MAR20 dataset (3,842 satellite images, 22,000+ annotations)

**Stage 2 — Classification (EfficientNet-B0)**
- Crops each detected aircraft and classifies the specific type
- 35 aircraft classes including Russian types (Su-24/25/34/57, MiG-29/31, Tu-95/160/22M, Il-76, Ka-52, Mi-8/24/28)
- Trained on 22,000+ cropped aircraft images

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, Vite, Leaflet, Recharts |
| Backend | Python, FastAPI, SQLAlchemy |
| Database | SQLite (local MVP) |
| ML/CV | PyTorch, YOLOv8 (ultralytics), EfficientNet |
| Satellite | Copernicus/Sentinel-2, Esri World Imagery |
| Training | Google Colab (GPU) |

## Project Structure

```
Vauban/
  backend/
    app/
      api/            # REST endpoints (airbases, observations, sentinel, tiles, analytics, bulk)
      models/          # SQLAlchemy models (Airbase, Observation, Detection)
      services/        # Business logic (detection pipeline, sentinel, tile fetcher)
      data/            # Seed data (25 airbase coordinates)
    .env.example       # Environment variable template
    requirements.txt
  frontend/
    src/
      components/      # Map, gallery, detection overlay, charts, capture UI
      pages/           # Dashboard, AirbaseDetail
      utils/           # API client
  ml/
    scripts/           # Dataset prep, training scripts
    Vauban_Training.ipynb  # Colab notebook for GPU training
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Copernicus Data Space account (free) — [Register here](https://dataspace.copernicus.eu/)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with your Copernicus credentials

# Run
uvicorn app.main:app --reload --reload-dir app --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

### Training Models (Google Colab)

1. Upload `ml/mar20_yolo.zip` and `ml/aircraft_classifier.zip` to Colab
2. Open `ml/Vauban_Training.ipynb`
3. Run all cells (use GPU runtime)
4. Download `vauban_detect_v1.pt` and `vauban_classifier_v1.pt`
5. Place both in `ml/models/`

The detection pipeline automatically uses the trained models when present.

## Monitored Airbases

| Base | Region | Known Aircraft |
|------|--------|---------------|
| Engels-2 | Saratov | Tu-160, Tu-95MS |
| Hmeimim | Syria | Su-35S, Su-34, Su-24M |
| Kubinka | Moscow | Su-35S, MiG-29 |
| Belbek | Crimea | Su-27SM, Su-30SM |
| Saki | Crimea | Su-30SM, Su-24M |
| Lipetsk | Lipetsk | Su-35S, Su-34, Su-57 |
| Besovets | Karelia | Su-35S |
| Mozdok | N. Ossetia | Staging base |
| + 17 more | | |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/airbases/` | List all monitored airbases |
| GET | `/api/airbases/{id}` | Get airbase details |
| PATCH | `/api/airbases/{id}/coords` | Update airbase coordinates |
| POST | `/api/tiles/fetch/{id}` | Capture high-res imagery |
| POST | `/api/sentinel/fetch/{id}` | Fetch Sentinel-2 imagery |
| POST | `/api/bulk/capture` | Bulk capture all airbases |
| GET | `/api/analytics/overview` | Platform statistics |
| GET | `/api/analytics/airbase/{id}/timeline` | Observation history |
| POST | `/api/observations/upload/{id}` | Manual image upload |

## License

This project is for educational and research purposes.

---

*"The art of fortification consists in so disposing the works that the worst of them is better than the place it covers."* — Vauban
