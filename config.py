import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

myToken = os.environ['PANDASCORE_TOKEN']
url = "https://api.pandascore.co/lol"
headers = {"Authorization": myToken}
