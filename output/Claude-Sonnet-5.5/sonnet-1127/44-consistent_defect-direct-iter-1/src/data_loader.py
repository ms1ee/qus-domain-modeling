"""Loads subway data from JSON."""
import json
import os

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
