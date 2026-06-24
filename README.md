# NPTEL Certificate Verification & Credit Transfer Eligibility API

FastAPI service implementing the frozen pipeline: file validation → QR
extraction → official certificate fetch (NPTEL servers) → field-by-field
integrity comparison → EMS name match → duplicate-use check → course
eligibility (Excel) → credit calculation → verdict.

## Setup

```bash
pip install -r requirements.txt
# also needs poppler-utils (pdftoppm) on the system, already present on most Linux setups
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive API testing.

## Endpoint

`POST /verify-certificate` (multipart form)
- `file`: the certificate PDF
- `ems_student_name`: name of the currently logged-in EMS student
- `student_roll`: roll number, used for duplicate-use tracking

Returns JSON matching `app/models.py::VerificationResponse` — includes
`certificate_status`, `credit_transfer_status`, `error`, and a full
`validations` log (PASS/FAIL per check) for transparency/debugging.

## What's been tested in this sandbox (against the real sample certificate)

- File validation (PDF/encryption/page-count checks)
- QR extraction (rasterize + pyzbar) — correctly decoded the real QR
- Field extraction from the PDF text layer (coordinate-based, not
  order-dependent) — all 9 fields extracted correctly
- Field-by-field comparator — correctly passes on a genuine match and
  correctly flags a tampered name
- Course eligibility lookup against the dummy Excel
- Credit calculation
- Duplicate-certificate tracking (JSON store)
- FastAPI app boots and registers routes correctly

## What could NOT be tested in this sandbox

`app/official_fetch.py` makes real HTTP calls to `nptel.ac.in` /
`archive.nptel.ac.in`. This sandbox's network allowlist doesn't include
those domains, so the actual HTTP round-trip is untested here. The
logic is built directly from manually-verified live responses (see
the docstring in that file for exact URLs/responses I checked), but
**test this module for real as soon as you run it somewhere with normal
internet access** — ideally against 3–4 different real certificates
before trusting it.

## Important real-world finding

The QR code does NOT encode the same ID as the Roll No printed on the
certificate — it's the printed ID plus an extra ~8-digit suffix (and
sometimes a different prefix, NOC vs NPTEL). Confirmed this isn't unique
to your sample — found the same pattern on other real NPTEL certificates
via search. So the QR-embedded ID is used only as a lookup key to fetch
the official record; the actual "Certificate ID" field that gets
compared between uploaded vs official is the printed Roll No from each
PDF's text layer.

Also: the official PDF for one real certificate showed "No. of credits
recommended: 2 or 3" (a range, not a fixed number) — worth deciding
whether `credits = weeks // 4` (current implementation, per your
instruction) should instead defer to the certificate's own printed
recommendation when it's a clean single number. Flagging this since
your sample cert prints "4" while `weeks // 4` computes "3" for a
12-week course.

## Not yet implemented (next steps)

- Real EMS integration (currently `ems_student_name`/`student_roll` are
  passed as raw form fields — in production these should come from the
  logged-in session, not user input)
- Persistent DB for used-certificate tracking (currently a flat JSON file)
- Tests against a tampered QR / fake-domain certificate to confirm
  `official_fetch.py`'s URL allowlist rejects it correctly
