"""
Python script to load config.
"""
import json

with open('config.json') as f:
    config = json.load(f)

DB_CONFIG = config['localhost']