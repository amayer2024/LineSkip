"""CI helper: validate system.yaml against system.schema.json.

The schema ships from Blackboard. Until it is committed, this is a no-op so the
pipeline stays green; once present, a non-conforming system.yaml fails CI.
"""
import json
import sys

import jsonschema
import yaml

SCHEMA = "system.schema.json"
DOC = "system.yaml"

try:
    schema = json.load(open(SCHEMA))
except FileNotFoundError:
    print(f"{SCHEMA} not present yet - skipping (add it from Blackboard to enforce).")
    sys.exit(0)

jsonschema.validate(yaml.safe_load(open(DOC)), schema)
print(f"{DOC} is valid against {SCHEMA}.")
