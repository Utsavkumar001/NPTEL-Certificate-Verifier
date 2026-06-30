"""
Resolves a QR-decoded URL into the official certificate PDF bytes.

VERIFIED AGAINST LIVE NPTEL INFRASTRUCTURE (tested manually, June 2026):

1. The QR on an NPTEL certificate encodes a URL of the form:
       https://nptel.ac.in/noc/E_Certificate/<QR_ID>
   Note: <QR_ID> is NOT identical to the Roll No printed on the
   certificate body. Confirmed on two independent real certificates that
   the QR id = printed_roll_no (prefix sometimes shown as NOC instead of
   NPTEL) + an extra ~8-digit suffix. Because of this, we do NOT compare
   the QR-embedded id against the printed Certificate ID field -- the QR
   id is only used as a lookup key. The printed "Certificate ID" field
   (visible in both the uploaded PDF and the fetched official PDF) is
   what gets field-by-field compared in comparator.py.

2. The real verification endpoint that returns a usable result is:
       https://archive.nptel.ac.in/noc/Ecertificate/?q=<QR_ID>
   This returns a tiny HTML page containing a single link to the actual
   official certificate PDF, hosted at a predictable but non-formulaic
   path under archive.nptel.ac.in/content/noc/... (varies by batch/dept/
   course code, so it must be scraped from this page, not constructed).

3. That linked PDF is fetched directly and parsed with the SAME
   pdf_parser used for the uploaded certificate, since both come from
   the same FPDF-generated template.

NOTE: This module makes real outbound HTTP calls to nptel.ac.in /
archive.nptel.ac.in and could not be exercised inside this sandbox
(domain isn't on the sandbox's network allowlist). The logic here is
built directly from the verified real responses above. Test this module
against the live endpoints as soon as it runs somewhere with normal
internet access, before relying on it.
"""

import re
import requests
from urllib.parse import urljoin

ALLOWED_QR_PATTERNS = [
    re.compile(r"^https://nptel\.ac\.in/noc/E_Certificate/([A-Za-z0-9]+)$"),
    re.compile(r"^https://archive\.nptel\.ac\.in/noc/E_Certificate/([A-Za-z0-9]+)$"),
    re.compile(r"^https://archive\.nptel\.ac\.in/noc/Ecertificate/\?q=([A-Za-z0-9]+)$"),
]

VERIFICATION_ENDPOINT = "https://archive.nptel.ac.in/noc/Ecertificate/?q={qr_id}"
# NPTEL's server returns href without quotes (e.g. href=../../content/x.pdf),
# so the regex must accept optional quotes, not require them.
PDF_LINK_RE = re.compile(r'href\s*=\s*(["\']?)([^"\'>\s]+\.pdf)\1', re.IGNORECASE)

# Plain `requests` defaults to a "python-requests/x.x" User-Agent, which
# some servers (including NPTEL's) treat differently from a real browser
# request and may return an empty/blocked page for. Send a normal
# browser UA so the response matches what you'd see opening the link
# in Chrome/Firefox yourself.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


class OfficialFetchError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def validate_and_extract_qr_id(qr_url: str) -> str:
    """
    Only accepts URLs that exactly match a known official NPTEL pattern.
    No redirects/shorteners/lookalike domains allowed (Threat 5 from the
    threat model: QR redirects are rejected even if they eventually land
    on nptel.ac.in).
    """
    qr_url = (qr_url or "").strip()
    for pattern in ALLOWED_QR_PATTERNS:
        m = pattern.match(qr_url)
        if m:
            return m.group(1)
    raise OfficialFetchError(
        "ERR_001",
        "Invalid QR URL. The QR code does not point to an official NPTEL verification page.",
    )


def fetch_official_pdf(qr_url: str, timeout: int = 30) -> bytes:
    """
    Fetches the official certificate PDF.

    Kya kiya: 2026 certificates ke liye NPTEL ka backend change ho gaya hai
    (Google Cloud Storage pe signed URLs use karta hai, purana
    archive.nptel.ac.in/noc/Ecertificate/?q= flow sirf 2025 aur usse purane
    certificates ke liye kaam karta hai). nptel.ac.in/noc/E_Certificate/{id}
    ko Referer header ke saath hit karne par requests library khud hi poori
    redirect chain (nptel.ac.in -> archive.nptel.ac.in/certificate.php ->
    storage.googleapis.com signed URL) follow karke seedha PDF bytes de
    deti hai -- bina manually signed URL parse kiye.

    Kya hoga: dono purane (2025) aur naye (2026) certificates ab is single
    flow se verify ho sakenge, kyunki nptel.ac.in/noc/E_Certificate/{id}
    dono cases mein valid entry point hai.
    """
    qr_id = validate_and_extract_qr_id(qr_url)

    direct_url = f"https://nptel.ac.in/noc/E_Certificate/{qr_id}"
    headers_with_referer = {**HEADERS, "Referer": "https://nptel.ac.in/"}

    try:
        with requests.Session() as session:
            session.headers.update(headers_with_referer)
            wrapper_resp = session.get(direct_url, timeout=timeout, allow_redirects=True)

            # Kya kiya: wrapper HTML se <iframe src="..."> nikal ke us URL ko
            #           alag se fetch kiya
            # Kya hoga: nptel.ac.in sirf ek iframe wrapper deta hai (2026
            #           certificates ke liye); requests library iframe ko
            #           khud follow nahi karti (sirf browsers karte hain),
            #           isliye iframe src manually extract karke fetch
            #           karna padta hai
            if wrapper_resp.status_code == 200 and "text/html" in wrapper_resp.headers.get("Content-Type", ""):
                iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', wrapper_resp.text, re.IGNORECASE)
                if iframe_match:
                    iframe_url = iframe_match.group(1)
                    resp = session.get(iframe_url, timeout=timeout, allow_redirects=True)
                else:
                    resp = wrapper_resp
            else:
                resp = wrapper_resp
    except requests.RequestException as e:
        raise OfficialFetchError(
            "ERR_002", f"Could not reach NPTEL verification server: {e}"
        )

    if resp.status_code == 200 and resp.content[:4] == b"%PDF":
        return resp.content
    

    # Fallback: older archive.nptel.ac.in/noc/Ecertificate/?q= flow
    verify_url = VERIFICATION_ENDPOINT.format(qr_id=qr_id)

    try:
        resp = requests.get(verify_url, timeout=timeout, allow_redirects=True, headers=HEADERS)
    except requests.RequestException as e:
        raise OfficialFetchError(
            "ERR_002", f"Could not reach NPTEL verification server: {e}"
        )

    if resp.status_code != 200:
        raise OfficialFetchError(
            "ERR_002", f"Official NPTEL certificate could not be found (HTTP {resp.status_code})."
        )

    pdf_link_match = PDF_LINK_RE.search(resp.text)
    if not pdf_link_match:
        snippet = resp.text.strip().replace("\n", " ")[:300]
        raise OfficialFetchError(
            "ERR_002",
            "Could not locate the official certificate PDF on NPTEL's verification page. "
            f"Certificate ID may not exist. [debug] verify_url={verify_url} | "
            f"response_snippet={snippet!r}",
        )

    pdf_url = urljoin(verify_url, pdf_link_match.group(2))

    try:
        pdf_resp = requests.get(pdf_url, timeout=timeout, headers=HEADERS)
    except requests.RequestException as e:
        raise OfficialFetchError(
            "ERR_002", f"Could not download official certificate PDF: {e}"
        )

    if pdf_resp.status_code != 200 or not pdf_resp.content:
        raise OfficialFetchError(
            "ERR_002", "Official NPTEL certificate PDF could not be downloaded."
        )

    return pdf_resp.content