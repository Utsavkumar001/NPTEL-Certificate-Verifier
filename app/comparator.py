"""
Fail-fast field comparison. Returns as soon as first mismatch found.
"""
from dataclasses import dataclass
from typing import List, Optional, Callable, Any
from .pdf_parser import CertificateData


@dataclass
class FieldCheck:
    check: str
    status: str
    reason: Optional[str] = None


def _nt(v): return (str(v) if v is not None else "").strip().lower()
def _nn(v): return round(float(v), 2) if v is not None else None

FIELDS = [
    ("Certificate ID",    lambda d: d.certificate_id,    _nt),
    ("Student Name",      lambda d: d.student_name,      _nt),
    ("Course Name",       lambda d: d.course_name,       _nt),
    ("Assignment Score",  lambda d: d.assignment_score,  _nn),
    ("Exam Score",        lambda d: d.exam_score,        _nn),
    ("Total Score",       lambda d: d.total_score,       _nn),
    ("Session",           lambda d: d.session,           _nt),
    ("Weeks",             lambda d: d.weeks,             _nt),
    ("Credits",           lambda d: d.credits_text,      _nt),
]


def compare_certificates(uploaded: CertificateData, official: CertificateData) -> List[FieldCheck]:
    checks = []
    for label, getter, norm in FIELDS:
        u, o = norm(getter(uploaded)), norm(getter(official))
        if u == o:
            checks.append(FieldCheck(check=f"{label} Match", status="PASS"))
        else:
            checks.append(FieldCheck(
                check=f"{label} Match", status="FAIL",
                reason=f"{label} mismatch: uploaded='{getter(uploaded)}' vs official='{getter(official)}'"
            ))
            return checks  # FAIL-FAST: stop here
    return checks


def all_passed(checks): return all(c.status == "PASS" for c in checks)
def first_failure_reason(checks):
    for c in checks:
        if c.status == "FAIL": return c.reason
    return None
