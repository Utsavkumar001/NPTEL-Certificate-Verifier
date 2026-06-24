from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

USED_CERTIFICATES_PATH = str(DATA_DIR / "used_certificates.json")
