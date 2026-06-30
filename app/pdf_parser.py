"""
NPTEL certificate PDF parser.

Both the student-uploaded PDF and the official PDF fetched from NPTEL's
server are generated from the SAME template (confirmed by inspecting a
real sample certificate + a real official certificate fetched from
archive.nptel.ac.in). Field text-extraction ORDER is not reliable across
the two sources (pdftotext vs different extractors return words in
different sequences), so we extract using Y-coordinate bands instead of
relying on text order. Coordinates are normalized as a fraction of page
height so small page-size variations don't break extraction.

If NPTEL ever changes their certificate template, only the ROW_BANDS
below need to be re-calibrated against a fresh sample certificate.
"""

import re
from dataclasses import dataclass, asdict
from typing import Optional

import pdfplumber

# Normalized Y-position bands (fraction of page height), calibrated from
# a real sample certificate (Deep Learning for NLP, Jan-Apr 2026).
# tolerance is added on both sides when matching words to a band.
ROW_BANDS = {
    "student_name": 0.2668,
    "course_name": 0.3795,
    "total_score": 0.4609,
    "assignment_exam": 0.5179,
    "total_candidates": 0.5879,
    "session": 0.7077,
    "weeks": 0.7553,
    "footer": 0.9429,  # Roll No / Certificate ID / Credits line
}
BAND_TOLERANCE = 0.02


@dataclass
class CertificateData:
    certificate_id: Optional[str] = None
    student_name: Optional[str] = None
    course_name: Optional[str] = None
    total_score: Optional[float] = None
    assignment_score: Optional[float] = None
    assignment_max: Optional[float] = None
    exam_score: Optional[float] = None
    exam_max: Optional[float] = None
    total_candidates: Optional[int] = None
    session: Optional[str] = None
    weeks: Optional[int] = None
    credits_text: Optional[str] = None  # raw text, e.g. "4" or "2 or 3"

    def to_dict(self):
        return asdict(self)


def _group_words_by_row(words, page_height):
    """Bucket words into the known field rows using normalized Y position."""
    rows = {band: [] for band in ROW_BANDS}
    for w in words:
        norm_top = w["top"] / page_height
        for band_name, band_y in ROW_BANDS.items():
            if abs(norm_top - band_y) <= BAND_TOLERANCE:
                rows[band_name].append(w)
                break
    # sort each row left-to-right so multi-word fields read correctly
    for band_name in rows:
        rows[band_name].sort(key=lambda w: w["x0"])
    return rows


def extract_certificate_data(pdf_path_or_bytes) -> CertificateData:
    """
    Extract structured fields from an NPTEL certificate PDF.
    Accepts a file path (str) or raw PDF bytes.
    """
    data = CertificateData()

    if isinstance(pdf_path_or_bytes, (bytes, bytearray)):
        import io
        pdf_source = io.BytesIO(pdf_path_or_bytes)
    else:
        pdf_source = pdf_path_or_bytes

    with pdfplumber.open(pdf_source) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        rows = _group_words_by_row(words, page.height)

    # --- Student Name ---
    if rows["student_name"]:
        data.student_name = " ".join(w["text"] for w in rows["student_name"]).strip()

    # --- Course Name ---
    if rows["course_name"]:
        data.course_name = " ".join(w["text"] for w in rows["course_name"]).strip()

    # --- Total Score (consolidated %, plain number on its own row) ---
    if rows["total_score"]:
        m = re.search(r"\d+(\.\d+)?", " ".join(w["text"] for w in rows["total_score"]))
        if m:
            data.total_score = float(m.group())

    # --- Assignment / Exam scores (e.g. "24.38/25" and "39.75/75") ---
    if rows["assignment_exam"]:
        line = " ".join(w["text"] for w in rows["assignment_exam"])
        fractions = re.findall(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", line)
        # The /25 fraction is always the assignment score, /75 is the exam score
        for num, den in fractions:
            if den == "25":
                data.assignment_score, data.assignment_max = float(num), float(den)
            elif den == "75":
                data.exam_score, data.exam_max = float(num), float(den)

    # --- Total candidates certified ---
    if rows["total_candidates"]:
        m = re.search(r"\d+", " ".join(w["text"] for w in rows["total_candidates"]))
        if m:
            data.total_candidates = int(m.group())

    # --- Session, e.g. "Jan-Apr 2026" ---
    if rows["session"]:
        data.session = " ".join(w["text"] for w in rows["session"]).strip()

    # --- Weeks, e.g. "(12 week course)" ---
    if rows["weeks"]:
        line = " ".join(w["text"] for w in rows["weeks"])
        m = re.search(r"(\d+)\s*week", line)
        if m:
            data.weeks = int(m.group(1))

    # --- Footer: Certificate ID + Credits recommended ---
    if rows["footer"]:
        line = " ".join(w["text"] for w in rows["footer"])
        id_match = re.search(r"\b(NPTEL|NOC)\d{2}[A-Z]{2,3}\d{2}S\d+\b", line)
        if id_match:
            data.certificate_id = id_match.group()
        credits_match = re.search(
            r"recommended:\s*([\d]+(?:\s*or\s*\d+)?)", line
        )
        if credits_match:
            data.credits_text = credits_match.group(1).strip()

    return data
