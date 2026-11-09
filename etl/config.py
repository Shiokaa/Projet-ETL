import os

from dotenv import load_dotenv

from settings import ROOT_DIR

# Au-delà de cette part de lignes brutes rejetées par leur contrat, le pipeline s'arrête.
MAX_REJECT_RATE = 0.05

load_dotenv(ROOT_DIR / ".env")

myToken = os.environ['PANDASCORE_TOKEN']
url = "https://api.pandascore.co/lol"
headers = {"Authorization": f"Bearer {myToken}"}

START_DATE = "2020-01-01T00:00:00Z"
