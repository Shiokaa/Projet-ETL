from etl.extract.extract import extract
from etl.load.load import load
from etl.transform.transform import transform

extract()
transform()
load()
