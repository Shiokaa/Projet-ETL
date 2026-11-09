from etl.extract.extract import extract
from etl.load.load import load
from etl.transform.transform import transform
from etl.validate.validate import RAW_SCHEMAS, validate_source

extract()
for name in RAW_SCHEMAS:
    validate_source(name)
transform()
load()
