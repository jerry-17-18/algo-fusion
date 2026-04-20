from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.patient import Patient
from app.models.record import Record
from app.schemas.record import StructuredClinicalData


@dataclass
class VisitReportPayload:
    patient_name: str
    patient_external_id: str
    age: str
    gender: str
    visit_date: str
    symptoms: str
    duration: str
    diagnosis: str
    medications: str


class ReportService:
    def build_visit_report_pdf(self, patient: Patient, record: Record) -> bytes:
        structured = StructuredClinicalData.model_validate(record.structured_data or {})
        payload = VisitReportPayload(
            patient_name=patient.full_name,
            patient_external_id=patient.external_id,
            age=str(patient.age) if patient.age is not None else "Not provided",
            gender=(patient.gender or "Not provided").title(),
            visit_date=record.created_at.strftime("%d %b %Y, %I:%M %p"),
            symptoms=", ".join(structured.symptoms) or "Not captured",
            duration=structured.duration or "Not captured",
            diagnosis=structured.diagnosis or record.suggested_diagnosis or "Not captured",
            medications=", ".join(structured.medications) or "Not captured",
        )

        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontSize=22,
            leading=28,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=8,
        )
        section_style = ParagraphStyle(
            "SectionTitle",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#0f766e"),
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "BodyTextCustom",
            parent=styles["BodyText"],
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#334155"),
        )

        story = [
            Paragraph("Clinical Visit Report", title_style),
            Paragraph(
                f"Patient ID: <b>{payload.patient_external_id}</b> &nbsp;&nbsp; Visit: <b>{payload.visit_date}</b>",
                body_style,
            ),
            Spacer(1, 10),
            Paragraph("Patient Details", section_style),
            self._build_table(
                [
                    ["Name", payload.patient_name],
                    ["Age", payload.age],
                    ["Sex", payload.gender],
                ]
            ),
            Spacer(1, 12),
            Paragraph("Visit Summary", section_style),
            self._build_table(
                [
                    ["Symptoms", payload.symptoms],
                    ["Duration", payload.duration],
                    ["Diagnosis", payload.diagnosis],
                    ["Medications", payload.medications],
                ]
            ),
        ]

        document.build(story)
        return buffer.getvalue()

    @staticmethod
    def _build_table(rows: list[list[str]]) -> Table:
        table = Table(rows, colWidths=[42 * mm, 120 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e2e8f0")),
                    ("BACKGROUND", (1, 0), (1, -1), colors.white),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("LEADING", (0, 0), (-1, -1), 14),
                    ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return table
