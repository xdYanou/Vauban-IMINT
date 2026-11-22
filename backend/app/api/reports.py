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


def _generate_report(airbase, observations, db) -> dict:
    """Generate a PDF intel report for an airbase."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, cm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from io import BytesIO
    from PIL import Image

    report_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{airbase.name.replace(' ', '_')}_INTSUM_{report_id}.pdf"
    filepath = REPORTS_DIR / filename

    doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                            topMargin=15*mm, bottomMargin=15*mm,
                            leftMargin=15*mm, rightMargin=15*mm)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ClassBanner', fontSize=8, alignment=TA_CENTER,
                              textColor=HexColor('#2d7dd2'), fontName='Helvetica-Bold',
                              spaceAfter=6))
    styles.add(ParagraphStyle(name='ReportTitle', fontSize=18, alignment=TA_CENTER,
                              textColor=HexColor('#1a1a2e'), fontName='Helvetica-Bold',
                              spaceAfter=4))
    styles.add(ParagraphStyle(name='ReportSub', fontSize=10, alignment=TA_CENTER,
                              textColor=HexColor('#666666'), fontName='Helvetica',
                              spaceAfter=12))
    styles.add(ParagraphStyle(name='SectionHead', fontSize=12, fontName='Helvetica-Bold',
                              textColor=HexColor('#1a1a2e'), spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name='BodyText2', fontSize=9, fontName='Helvetica',
                              textColor=HexColor('#333333'), spaceAfter=4, leading=13))

    elements = []

    # Classification banner
    elements.append(Paragraph("UNCLASSIFIED // FOR EDUCATIONAL USE ONLY", styles['ClassBanner']))
    elements.append(Spacer(1, 4*mm))

    # Title
    elements.append(Paragraph(f"INTELLIGENCE SUMMARY", styles['ReportTitle']))
    elements.append(Paragraph(f"{airbase.name} ({airbase.icao_code or 'N/A'})", styles['ReportSub']))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y %H:%M UTC')}", styles['ReportSub']))
    elements.append(Spacer(1, 4*mm))

    # Base info table
    base_data = [
        ["LOCATION", f"{airbase.region}, {airbase.country}"],
        ["COORDINATES", f"{airbase.latitude:.4f}°N, {airbase.longitude:.4f}°E"],
        ["ICAO CODE", airbase.icao_code or "N/A"],
        ["KNOWN UNITS", airbase.known_units or "N/A"],
        ["TOTAL CAPTURES", str(len(observations))],
    ]
    t = Table(base_data, colWidths=[45*mm, 130*mm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), HexColor('#2d7dd2')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 6*mm))

    # Aggregate detections across all observations
    all_types = {}
    obs_with_detections = []
    for obs in observations:
        obs_types = {}
        for det in obs.detections:
            all_types[det.aircraft_type] = all_types.get(det.aircraft_type, 0) + 1
            obs_types[det.aircraft_type] = obs_types.get(det.aircraft_type, 0) + 1
        if obs.detections:
            obs_with_detections.append((obs, obs_types))

    # Detection summary
    elements.append(Paragraph("DETECTION SUMMARY", styles['SectionHead']))
    total_det = sum(all_types.values())
    elements.append(Paragraph(
        f"Total aircraft detected across {len(observations)} capture(s): <b>{total_det}</b>",
        styles['BodyText2']))

    if all_types:
        det_data = [["TYPE", "COUNT", "ROLE"]]
        # Load aircraft specs for roles
        specs_path = Path(__file__).parent.parent / "data" / "aircraft_specs.json"
        specs = {}
        if specs_path.exists():
            specs = json.loads(specs_path.read_text())

        for type_name, count in sorted(all_types.items(), key=lambda x: -x[1]):
            role = specs.get(type_name, {}).get("role", "Unknown")
            det_data.append([type_name, str(count), role])

        dt = Table(det_data, colWidths=[50*mm, 25*mm, 100*mm])
        dt.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2d7dd2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#f8f9fa'), HexColor('#ffffff')]),
        ]))
        elements.append(dt)
        elements.append(Spacer(1, 6*mm))

    # Observation images with detections
    elements.append(Paragraph("IMAGERY & DETECTIONS", styles['SectionHead']))

    for obs, obs_types in obs_with_detections[:6]:  # Limit to 6 images
        img_path = Path(obs.image_path)
        if not img_path.exists():
            continue

        # Resize image for PDF
        try:
            pil_img = Image.open(img_path)
            max_w = 170 * mm / (72 / 96)  # Approximate
            ratio = min(500 / pil_img.width, 350 / pil_img.height)
            new_size = (int(pil_img.width * ratio), int(pil_img.height * ratio))
            pil_img = pil_img.resize(new_size, Image.LANCZOS)

            tmp_path = REPORTS_DIR / f"tmp_{obs.id}.jpg"
            pil_img.save(str(tmp_path), "JPEG", quality=85)

            rl_img = RLImage(str(tmp_path), width=170*mm, height=170*mm * new_size[1] / new_size[0])
            elements.append(rl_img)

            # Detection label
            type_str = ", ".join(f"{t}: {c}" for t, c in sorted(obs_types.items(), key=lambda x: -x[1]))
            date_str = obs.observation_date.strftime("%Y-%m-%d %H:%M")
            elements.append(Paragraph(
                f"<i>{date_str} | {obs.source} | Zone: {obs.zone_label or 'default'} | "
                f"Detections: {type_str}</i>",
                styles['BodyText2']))
            elements.append(Spacer(1, 4*mm))
        except Exception as e:
            logger.warning(f"Failed to add image {obs.id}: {e}")

    # Footer
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph("— END OF REPORT —", styles['ClassBanner']))
    elements.append(Paragraph("UNCLASSIFIED // FOR EDUCATIONAL USE ONLY", styles['ClassBanner']))

    doc.build(elements)

    # Clean tmp images
    for tmp in REPORTS_DIR.glob("tmp_*.jpg"):
        tmp.unlink(missing_ok=True)

    logger.info(f"Report generated: {filepath}")

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
    """Generate an intel report PDF for an airbase."""
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

    # Save report metadata
    meta_path = REPORTS_DIR / f"{result['id']}_meta.json"
    meta_path.write_text(json.dumps({
        **result,
        "airbase_id": airbase_id,
    }, indent=2))

    return result


@router.get("/list/{airbase_id}")
def list_reports(airbase_id: int):
    """List all generated reports for an airbase."""
    reports = []
    for meta_file in sorted(REPORTS_DIR.glob("*_meta.json"), reverse=True):
        meta = json.loads(meta_file.read_text())
        if meta.get("airbase_id") == airbase_id:
            reports.append(meta)
    return reports


@router.get("/download/{filename}")
def download_report(filename: str):
    """Download a report PDF."""
    filepath = REPORTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(filepath, media_type="application/pdf", filename=filename)


@router.delete("/{report_id}")
def delete_report(report_id: str):
    """Delete a report PDF and its metadata."""
    meta_path = REPORTS_DIR / f"{report_id}_meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    meta = json.loads(meta_path.read_text())
    pdf_path = REPORTS_DIR / meta["filename"]
    pdf_path.unlink(missing_ok=True)
    meta_path.unlink(missing_ok=True)
    return {"status": "deleted"}
