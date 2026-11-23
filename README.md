<p align="center">
  <h1 align="center">VAUBAN</h1>
  <p align="center">
    <strong>IMINT & Military Intelligence Platform</strong><br>
    Satellite imagery analysis for global military airbase monitoring
  </p>
</p>

---

## Overview

Vauban is a defence-oriented IMINT (Imagery Intelligence) platform that uses satellite imagery and computer vision to monitor military airbases worldwide. The system detects, classifies, and tracks military aircraft deployments across **160 airbases in 35 countries**.

Named after [Sebastien Le Prestre de Vauban](https://en.wikipedia.org/wiki/Vauban), the French military engineer and Marshal of France.

### What it does

- **Monitors 159 military airbases** across Russia, USA, UK, France, Germany, China, Iran, Israel, and 27 more countries
- **Fetches high-resolution satellite imagery** from Esri World Imagery tiles (~0.6-1.2m/px)
- **Detects aircraft** using YOLOv8 trained on satellite imagery (20 aircraft types)
- **Intelligent classification** — country-aware filtering maps detections to locally plausible types (Typhoon for UK, Rafale for France, J-20 for China, etc.)
- **Tracks changes over time** — observation history, aircraft counts, type distribution analytics
- **Multi-zone capture** — define custom capture rectangles per base to cover entire facilities
- **Aircraft intelligence encyclopedia** — specs, weapons, role, and operational context for every detected type
- **Bulk capture** — image all monitored airbases in a single operation

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
                    |  | Multi-Src  |  |  Esri, Google, Bing
                    |  | Tile Svc   |  |  (0.6-1.2m resolution)
                    |  +------------+  |
                    |                  |
                    |  +------------+  |
                    |  | Detection  |  |
                    |  | Pipeline   |  |
                    |  +------+-----+  |
                    +---------|--------+
                              |
              +---------------+---------------+
              |                               |
       +------+------+               +-------+-------+
       | YOLOv8s     |               | Country-Aware |
       | Detection   |      --->     | Reclassifier  |
       | (20 types)  |               | (35 countries)|
       +-------------+               +---------------+
```

### Detection Pipeline

**Stage 1 — SAHI + YOLOv8 Detection**
- **Sliced Aided Hyper Inference (SAHI)**: Images are split into overlapping 640x640 patches
- Each patch is run through YOLOv8 at native resolution — no downscaling
- Aircraft appear ~2x larger relative to input, dramatically improving small object detection
- Results merged across slices with cross-slice NMS to remove duplicates
- Classifies into 20 types trained on MAR20 satellite dataset
- YOLOv8s model (11M params), trained at 960px with augmented oversampling

**Stage 2 — Intelligent Reclassification**
- **Base-specific context**: Known order of battle per base (Engels-2 → Tu-95MS, Tu-160)
- **Country-level filtering**: Removes implausible detections (no Su-35 at US bases)
- **Country defaults**: Maps shapes to local types (UK fighter → Typhoon, France → Rafale, China → J-20)

### Aircraft Types

**20 YOLO-detected types:** Su-35, Su-34, Su-24, Tu-95, Tu-160, Tu-22M, F-15, F-16, F-22, F/A-18, B-52, B-1B, C-130, C-17, C-5, KC-135, KC-10, E-3, E-8, P-3C

**Country reclassification adds:** Typhoon, Rafale, Tornado, Gripen, J-20, J-16, H-6K, F-35, Mirage 2000, MiG-29, MiG-31, F-14 Tomcat, and 30+ more regional types

## Monitored Countries

| Region | Countries | Bases |
|--------|-----------|-------|
| **Russia** | Russia | 25 |
| **North America** | USA, Canada, Mexico | 24 |
| **Europe** | UK, France, Germany, Italy, Spain, Portugal, Norway, Netherlands, Belgium, Poland, Czech Republic, Lithuania, Estonia, Bulgaria, Romania | 33 |
| **Middle East** | Iran, Israel, Saudi Arabia, UAE, Egypt, Jordan, Turkey | 29 |
| **Asia-Pacific** | China, Taiwan, Japan, South Korea, India, Pakistan, Australia | 28 |
| **South America** | Brazil, Argentina | 6 |
| **Africa** | Djibouti (US, France, China, Japan bases) | 4 |
| **NATO** | Multi-national (Baltic Air Policing, Al Udeid) | 3 |
| | **Total** | **160** |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, Vite, Leaflet, Recharts |
| Backend | Python, FastAPI, SQLAlchemy, SQLite |
| ML/CV | PyTorch, YOLOv8 (ultralytics) |
| Satellite | Esri, Google, Bing tile servers (multi-source) |
| Training | Google Colab (GPU) |

## Project Structure

```
Vauban/
  backend/
    app/
      api/            # REST endpoints
      models/          # SQLAlchemy models (Airbase, CaptureZone, Observation, Detection)
      services/        # Detection pipeline, multi-source tile fetcher
      data/            # Seed data, aircraft specs, base context, zone backups
    storage/
      images/          # Captured satellite imagery
      aircraft_images/ # Reference photos for aircraft intel cards
  frontend/
    src/
      components/      # Map, gallery, detection overlay, analytics, zone editor
      pages/           # Dashboard, AirbaseDetail
  ml/
    scripts/           # Dataset prep, training scripts
    models/            # Trained .pt model files
    metrics/           # Training curves, confusion matrices
    Vauban_Training_v3.ipynb  # Latest training notebook
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure credentials
cp .env.example .env

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

1. Open `ml/Vauban_Training_v3.ipynb` in Colab (free T4 GPU)
2. Run all cells — downloads dataset via Kaggle API
3. Download `vauban_detect_v3.pt`
4. Place in `backend/ml/models/`
5. Restart backend — model loads automatically

## Key Features

### Multi-Zone Capture
Each base supports multiple capture zones with configurable zoom levels. Zones are placed visually on a satellite map with drag-and-drop positioning. Covers entire facilities including dispersal areas, hardened shelters, and secondary aprons.

### Country-Aware Intelligence
The system knows what aircraft each country operates. A "fighter" detection at a French base becomes "Rafale", at a UK base becomes "Typhoon", at a Chinese base becomes "J-20". Base-specific overrides provide even finer granularity (Engels-2 → Tu-95MS/Tu-160).

### Aircraft Encyclopedia
Every detected type links to a detailed intel card with:
- Reference photo
- Role, generation, country of origin
- Performance specs (speed, range, ceiling, payload)
- Full weapons loadout
- Operational context and combat history

### Analytics Dashboard
- Detection timeline with per-type stacked charts
- Type distribution pie charts
- Capture-aggregated statistics
- Per-base aircraft count tracking over time

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/airbases/` | List all 160 monitored airbases |
| GET | `/api/airbases/{id}` | Airbase details with capture zones |
| PATCH | `/api/airbases/{id}/coords` | Update coordinates |
| POST | `/api/airbases/{id}/zones` | Add capture zone |
| DELETE | `/api/airbases/{id}/zones/{zid}` | Remove capture zone |
| POST | `/api/tiles/fetch/{id}` | Capture all zones for a base |
| POST | `/api/bulk/capture` | Bulk capture all bases |
| GET | `/api/analytics/overview` | Platform-wide statistics |
| GET | `/api/analytics/airbase/{id}/timeline` | Observation history |
| GET | `/api/aircraft/specs` | Aircraft encyclopedia data |

## Model Versions

| Version | Architecture | imgsz | Classes | Status |
|---------|-------------|-------|---------|--------|
| v1 | YOLOv8n (3M) | 640 | 7 broad categories | Retired |
| v2 | YOLOv8n (3M) | 640→1280 | 20 specific types | Previous |
| v3 | YOLOv8s (11M) | 960 | 20 types + oversampling | **Current** |

## License

This project is for educational and research purposes.

---

*"The art of fortification consists in so disposing the works that the worst of them is better than the place it covers."* — Vauban
