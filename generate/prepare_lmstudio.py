#!/usr/bin/env python3
"""Explicit model loading, or read-only verification with --check."""
import argparse
import json
from pathlib import Path

from dotenv import load_dotenv
from config import MODELS, ROOT_DIR
from lmstudio_runtime import Runtime, connection, load_profile, validate_runtime


def main():
    load_dotenv(Path(ROOT_DIR) / '.env')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', choices=[name for name, (provider, _) in MODELS.items() if provider == 'lmstudio'])
    parser.add_argument('--check', action='store_true', help='Inspect only; never load or unload')
    args = parser.parse_args()
    profile = load_profile(MODELS[args.model][1])
    base_url, identifier = connection(profile)
    runtime = Runtime(profile, base_url, identifier)
    state = runtime.inspect() if args.check else runtime.prepare()
    validate_runtime(profile, state)
    print(json.dumps({'model': args.model, 'sampling': profile['sampling'],
                      'api': profile['api'], 'runtime': state}, indent=2))


if __name__ == '__main__':
    main()
