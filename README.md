# NPTEL Certificate Verification & Credit Transfer Management System

A pilot web application for Manav Rachna International Institute of Research & Studies that handles the complete NPTEL credit transfer lifecycle — from course registration to certificate verification and credit processing.

## What it does

Students can request NPTEL courses, get faculty approval, and submit certificates for automated verification. Faculty manages approvals for their department. Admin has a full overview of all students across departments with credit processing controls.

## User Roles

**Student**
- Register and log in with roll number
- Request NPTEL courses (when faculty opens the window)
- Confirm NPTEL registration
- Upload certificate for automated verification
- Track credits earned per course

**Faculty**
- Open / close course request window for their department
- Approve or reject individual course requests
- View all students in their department with semester filter
- Allow re-upload if a certificate was rejected

**Admin**
- View all students across departments with school / department / semester filters
- Create and remove faculty accounts
- Reset passwords for students and faculty
- Mark credits as processed after verification

## Verification Pipeline

Upload → File Validation → QR Extraction → QR URL Validation → Fetch Official NPTEL Certificate → Field-by-Field Comparison (Certificate ID, Name, Course, Scores, Session, Weeks, Credits) → EMS Name Match → Course Name Triple Check (uploaded vs official vs requested) → Duplicate Certificate Check → Verdict

Handles: tampered certificates, wrong course certificates, reused certificates, fake QR codes, scanned PDFs, friend's genuine certificate, and more.

## Tech Stack

- **Backend:** FastAPI + SQLite
- **Frontend:** Jinja2 templates + plain CSS
- **Verification:** PyMuPDF, pyzbar, pdfplumber, requests

## Setup

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`

Default admin credentials — username: `admin` password: `admin123`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Session signing key | fallback hardcoded key |

Set `SECRET_KEY` as an environment variable in production.

## Credit Calculation

| Course Duration | Credits |
|----------------|---------|
| 12 weeks | 4 |
| 8 weeks | 3 |
| 4 weeks | 2 |

## Status

Pilot phase — currently being tested before integration with the college EMS.