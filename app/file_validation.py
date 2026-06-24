"""
First gate in the pipeline: reject malformed uploads before doing any
real work. Covers Threats 1, 2, 3, 6 from the threat model (non-PDF
upload, password-protected PDF, corrupted PDF, multi-page mixed PDF).
"""

from dataclasses import dataclass
from typing import Optional
from pypdf import PdfReader
from pypdf.errors import PdfReadError


@dataclass
class FileValidationResult:
    valid: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None


def validate_uploaded_pdf(file_path: str, filename: str) -> FileValidationResult:
    if not filename.lower().endswith(".pdf"):
        return FileValidationResult(
            False, "ERR_009", "Only PDF files are accepted. Please upload the original certificate PDF."
        )

    try:
        reader = PdfReader(file_path)
    except PdfReadError:
        return FileValidationResult(
            False, "ERR_009", "The uploaded file is corrupted or not a valid PDF."
        )
    except Exception:
        return FileValidationResult(
            False, "ERR_009", "The uploaded file could not be read."
        )

    if reader.is_encrypted:
        return FileValidationResult(
            False, "ERR_009", "Password-protected PDFs are not accepted."
        )

    if len(reader.pages) != 1:
        return FileValidationResult(
            False,
            "ERR_009",
            f"NPTEL certificates are single-page documents. Uploaded file has {len(reader.pages)} pages.",
        )

    return FileValidationResult(True)
