"""
QR code extraction from NPTEL certificate PDFs.

NPTEL certificates embed the QR as a raster image inside the PDF page
content, not as a separate extractable image object in a clean way
(confirmed while inspecting a real sample certificate - pdfimages alone
did not reliably isolate it). The robust approach is to rasterize the
full page to an image and scan it for QR codes.

Uses PyMuPDF (fitz) to rasterize, NOT the poppler `pdftoppm` command-line
tool -- that requires a separate system install + PATH setup (Linux-only
by default, painful on Windows). PyMuPDF is a pure pip package, so this
works identically on Windows/Mac/Linux with zero extra setup.
"""

import io
from typing import Optional

import fitz  # PyMuPDF
from pyzbar.pyzbar import decode
from PIL import Image


class QRExtractionError(Exception):
    pass


def extract_qr_url(pdf_path: str, dpi: int = 200) -> str:
    """
    Rasterizes the first page of the PDF and decodes the QR code on it.
    Returns the raw URL/string encoded in the QR.
    Raises QRExtractionError if no QR code is found.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise QRExtractionError(f"Failed to open PDF for QR scanning: {e}")

    if doc.page_count < 1:
        raise QRExtractionError("PDF has no pages.")

    page = doc[0]
    zoom = dpi / 72  # PDF default is 72 dpi
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    doc.close()

    decoded = decode(img)

    if not decoded:
        raise QRExtractionError(
            "No QR code detected on the certificate. "
            "The certificate may be tampered, corrupted, or not a valid NPTEL PDF."
        )

    # NPTEL certificates have exactly one QR code; take the first.
    return decoded[0].data.decode("utf-8", errors="replace")
