import json
from pathlib import Path


config_path = Path(__file__).with_name('config.json')
with config_path.open() as f:
    config = json.load(f)

DB_CONFIG = config['localhost']
