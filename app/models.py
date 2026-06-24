from typing import List, Optional
from pydantic import BaseModel


class ValidationLogEntry(BaseModel):
    check: str
    status: str  # "PASS" or "FAIL"
    reason: Optional[str] = None


class ErrorDetail(BaseModel):
    code: str
    message: str


class VerificationResponse(BaseModel):
    certificate_status: str  # "VERIFIED" or "REJECTED"
    credit_transfer_status: Optional[str] = None  # "ELIGIBLE" / "NOT_ELIGIBLE" / None
    course_name: Optional[str] = None
    course_code: Optional[str] = None
    credits: Optional[int] = None
    certificate_id: Optional[str] = None
    error: Optional[ErrorDetail] = None
    validations: List[ValidationLogEntry] = []
