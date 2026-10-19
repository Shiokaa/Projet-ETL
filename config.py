import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
RAW_DIR = ROOT_DIR / "data" / "raw"

load_dotenv(ROOT_DIR / ".env")

myToken = os.environ['PANDASCORE_TOKEN']
url = "https://api.pandascore.co/lol"
headers = {"Authorization": f"Bearer {myToken}"}

START_DATE = "2020-01-01T00:00:00Z"
