import logging
import json
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.airbase import Airbase, Observation, Detection
from app.config import settings

logger = logging.getLogger("vauban.reports")

router = APIRouter(prefix="/api/reports", tags=["reports"])

REPORTS_DIR = Path(settings.image_storage_path).parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _group_captures(observations):
    """Group observations into capture sessions (within 60s)."""
    if not observations:
        return []
    captures = []
    current = [observations[0]]
    for obs in observations[1:]:
        if abs((obs.observation_date - current[-1].observation_date).total_seconds()) < 60:
            current.append(obs)
        else:
            captures.append(current)
            current = [obs]
    captures.append(current)
    return captures


def _generate_chart_image(captures, chart_type, filepath):
    """Generate a chart as a PNG image for embedding in the PDF."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=(7, 2.5))
    fig.patch.set_facecolor('#0d1118')
    ax.set_facecolor('#0d1118')

    if chart_type == "timeline":
        dates = [c[0].observation_date.strftime("%b %d") for c in captures]
        totals = [sum(len(o.detections) for o in c) for c in captures]
        ax.fill_between(range(len(dates)), totals, alpha=0.3, color='#2d7dd2')
        ax.plot(range(len(dates)), totals, color='#2d7dd2', linewidth=2, marker='o', markersize=4)
        ax.set_xticks(range(len(dates)))
        ax.set_xticklabels(dates, fontsize=7, color='#7a8ba0')
        ax.set_title('AIRCRAFT COUNT OVER TIME', fontsize=8, color='#7a8ba0', fontweight='bold', loc='left')

    elif chart_type == "types":
        all_types = {}
        for cap in captures:
            for obs in cap:
                for det in obs.detections:
                    all_types[det.aircraft_type] = all_types.get(det.aircraft_type, 0) + 1
        if all_types:
            sorted_types = sorted(all_types.items(), key=lambda x: -x[1])[:10]
            names = [t[0] for t in sorted_types]
            counts = [t[1] for t in sorted_types]
            bars = ax.barh(range(len(names)), counts, color='#2d7dd2', height=0.6)
            ax.set_yticks(range(len(names)))
            ax.set_yticklabels(names, fontsize=7, color='#d0d8e4', fontfamily='monospace')
            for bar, count in zip(bars, counts):
                ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                        str(count), va='center', fontsize=7, color='#7a8ba0')
            ax.set_title('TOP DETECTED TYPES', fontsize=8, color='#7a8ba0', fontweight='bold', loc='left')
            ax.invert_yaxis()

    ax.tick_params(colors='#4a5a70', labelsize=7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#1b2535')
    ax.spines['left'].set_color('#1b2535')
    ax.grid(axis='x', color='#1b2535', linewidth=0.5)

    plt.tight_layout()
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='#0d1118')
    plt.close()


def _generate_report(airbase, observations, db) -> dict:
    """Generate a compact 1-2 page intel report PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from PIL import Image

    report_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{airbase.name.replace(' ', '_')}_INTSUM_{report_id}.pdf"
    filepath = REPORTS_DIR / filename

    doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                            topMargin=10*mm, bottomMargin=10*mm,
                            leftMargin=12*mm, rightMargin=12*mm)

    styles = getSampleStyleSheet()
    s = styles
    s.add(ParagraphStyle(name='CB', fontSize=7, alignment=TA_CENTER, textColor=HexColor('#2d7dd2'), fontName='Helvetica-Bold', spaceAfter=3))
    s.add(ParagraphStyle(name='RT', fontSize=16, alignment=TA_CENTER, textColor=HexColor('#1a1a2e'), fontName='Helvetica-Bold', spaceAfter=2))
    s.add(ParagraphStyle(name='RS', fontSize=9, alignment=TA_CENTER, textColor=HexColor('#666666'), fontName='Helvetica', spaceAfter=8))
    s.add(ParagraphStyle(name='SH', fontSize=10, fontName='Helvetica-Bold', textColor=HexColor('#1a1a2e'), spaceBefore=8, spaceAfter=4))
    s.add(ParagraphStyle(name='BT', fontSize=8, fontName='Helvetica', textColor=HexColor('#333333'), spaceAfter=3, leading=11))

    elements = []

    # Header
    elements.append(Paragraph("UNCLASSIFIED // FOR EDUCATIONAL USE ONLY", s['CB']))
    elements.append(Paragraph("INTELLIGENCE SUMMARY", s['RT']))
    elements.append(Paragraph(
        f"{airbase.name} ({airbase.icao_code or 'N/A'}) — "
        f"{airbase.region}, {airbase.country} — "
        f"{airbase.latitude:.4f}°N, {airbase.longitude:.4f}°E", s['RS']))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y %H:%M UTC')} | Known Units: {airbase.known_units or 'N/A'}", s['BT']))
    elements.append(Spacer(1, 2*mm))

    # Group into captures
    captures = _group_captures(sorted(observations, key=lambda o: o.observation_date))

    # Aggregate detections
    all_types = {}
    for obs in observations:
        for det in obs.detections:
            all_types[det.aircraft_type] = all_types.get(det.aircraft_type, 0) + 1
    total_det = sum(all_types.values())

    # Summary stats as compact table
    summary_data = [[
        f"Captures: {len(captures)}",
        f"Total Detections: {total_det}",
        f"Unique Types: {len(all_types)}",
        f"Latest: {observations[0].observation_date.strftime('%d %b %Y') if observations else 'N/A'}",
    ]]
    st = Table(summary_data, colWidths=[45*mm]*4)
    st.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('TEXTCOLOR', (0,0), (-1,-1), HexColor('#2d7dd2')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOX', (0,0), (-1,-1), 0.5, HexColor('#dddddd')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, HexColor('#eeeeee')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(st)
    elements.append(Spacer(1, 3*mm))

    # Generate charts
    if len(captures) > 1:
        timeline_chart = REPORTS_DIR / f"tmp_timeline_{report_id}.png"
        _generate_chart_image(captures, "timeline", str(timeline_chart))
        elements.append(Paragraph("SITUATION OVERVIEW", s['SH']))
        elements.append(RLImage(str(timeline_chart), width=180*mm, height=60*mm))
        elements.append(Spacer(1, 2*mm))

    if all_types:
        types_chart = REPORTS_DIR / f"tmp_types_{report_id}.png"
        _generate_chart_image(captures, "types", str(types_chart))
        elements.append(RLImage(str(types_chart), width=180*mm, height=60*mm))
        elements.append(Spacer(1, 2*mm))

    # Detection table — compact
    if all_types:
        elements.append(Paragraph("DETECTION BREAKDOWN", s['SH']))
        specs_path = Path(__file__).parent.parent / "data" / "aircraft_specs.json"
        specs = json.loads(specs_path.read_text()) if specs_path.exists() else {}

        det_data = [["TYPE", "COUNT", "ROLE"]]
        for type_name, count in sorted(all_types.items(), key=lambda x: -x[1]):
            role = specs.get(type_name, {}).get("role", "—")
            det_data.append([type_name, str(count), role[:40]])

        dt = Table(det_data, colWidths=[40*mm, 18*mm, 125*mm])
        dt.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 7),
            ('BACKGROUND', (0,0), (-1,0), HexColor('#2d7dd2')),
            ('TEXTCOLOR', (0,0), (-1,0), HexColor('#ffffff')),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LINEBELOW', (0,0), (-1,-1), 0.3, HexColor('#dddddd')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [HexColor('#f8f9fa'), HexColor('#ffffff')]),
        ]))
        elements.append(dt)
        elements.append(Spacer(1, 3*mm))

    # Key imagery — only images WITH detections, max 4, compact
    obs_with_det = [(obs, len(obs.detections)) for obs in observations if obs.detections]
    obs_with_det.sort(key=lambda x: -x[1])

    if obs_with_det:
        elements.append(Paragraph("KEY IMAGERY", s['SH']))

        for obs, det_count in obs_with_det[:4]:
            img_path = Path(obs.image_path)
            if not img_path.exists():
                continue
            try:
                pil_img = Image.open(img_path)
                ratio = min(400 / pil_img.width, 280 / pil_img.height)
                new_w = int(pil_img.width * ratio)
                new_h = int(pil_img.height * ratio)
                pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)

                tmp_path = REPORTS_DIR / f"tmp_img_{obs.id}_{report_id}.jpg"
                pil_img.save(str(tmp_path), "JPEG", quality=80)

                rl_img = RLImage(str(tmp_path), width=min(180*mm, new_w * 0.26*mm), height=min(120*mm, new_h * 0.26*mm))
                elements.append(rl_img)

                type_counts = {}
                for det in obs.detections:
                    type_counts[det.aircraft_type] = type_counts.get(det.aircraft_type, 0) + 1
                type_str = ", ".join(f"{t}: {c}" for t, c in sorted(type_counts.items(), key=lambda x: -x[1]))
                elements.append(Paragraph(
                    f"<i>{obs.observation_date.strftime('%d %b %Y %H:%M')} | {obs.source} | "
                    f"Zone: {obs.zone_label or 'default'} | {type_str}</i>", s['BT']))
                elements.append(Spacer(1, 2*mm))
            except Exception as e:
                logger.warning(f"Image {obs.id}: {e}")

    # Footer
    elements.append(Spacer(1, 4*mm))
    elements.append(Paragraph("— END OF REPORT —", s['CB']))
    elements.append(Paragraph("UNCLASSIFIED // FOR EDUCATIONAL USE ONLY", s['CB']))

    doc.build(elements)

    # Clean tmp files
    for tmp in REPORTS_DIR.glob(f"tmp_*_{report_id}.*"):
        tmp.unlink(missing_ok=True)

    return {
        "id": report_id,
        "filename": filename,
        "generated_at": datetime.now().isoformat(),
        "airbase": airbase.name,
        "total_detections": total_det,
        "aircraft_types": all_types,
    }


@router.post("/generate/{airbase_id}")
def generate_report(airbase_id: int, db: Session = Depends(get_db)):
    airbase = db.query(Airbase).filter(Airbase.id == airbase_id).first()
    if not airbase:
        raise HTTPException(status_code=404, detail="Airbase not found")

    observations = (
        db.query(Observation)
        .filter(Observation.airbase_id == airbase_id)
        .order_by(Observation.observation_date.desc())
        .all()
    )
    if not observations:
        raise HTTPException(status_code=400, detail="No observations to report on")

    result = _generate_report(airbase, observations, db)

    meta_path = REPORTS_DIR / f"{result['id']}_meta.json"
    meta_path.write_text(json.dumps({**result, "airbase_id": airbase_id}, indent=2))

    return result


@router.get("/list/{airbase_id}")
def list_reports(airbase_id: int):
    reports = []
    for meta_file in sorted(REPORTS_DIR.glob("*_meta.json"), reverse=True):
        meta = json.loads(meta_file.read_text())
        if meta.get("airbase_id") == airbase_id:
            reports.append(meta)
    return reports


@router.get("/download/{filename}")
def download_report(filename: str):
    filepath = REPORTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(filepath, media_type="application/pdf", filename=filename)
