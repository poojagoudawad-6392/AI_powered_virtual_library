"""
scripts/gutenberg_download.py

Lightweight wrapper to download a Project Gutenberg ebook (by URL or numeric id)
and save a PDF. This script delegates to `gutenberg_fetch_and_convert.py`'s
`process_gutenberg_url` when available; otherwise it will load the module
from the scripts directory.

Usage:
  python scripts\gutenberg_download.py --id 1342 --output-dir data/pdfs
  python scripts\gutenberg_download.py --url https://www.gutenberg.org/ebooks/1342

Options:
  --id ID           Gutenberg ebook numeric id (builds https://www.gutenberg.org/ebooks/<ID>)
  --url URL         Full Gutenberg ebook page URL
  --output-dir DIR  Output directory (default: data/pdfs)
  --overwrite       Overwrite existing PDF if present
  --verbose         Verbose logging

This wrapper prefers to import process_gutenberg_url from the sibling
`gutenberg_fetch_and_convert.py`. If that file is missing or cannot be
imported, it will raise a helpful error.
"""

from __future__ import annotations
import argparse
import logging
from pathlib import Path
import sys
import importlib
import importlib.util

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Try importing the function from the sibling script
def load_process_func():
    try:
        # First try normal import (when scripts/ is on sys.path)
        mod = importlib.import_module('gutenberg_fetch_and_convert')
        return getattr(mod, 'process_gutenberg_url')
    except Exception:
        # Fallback: load by file path relative to this script
        fn = Path(__file__).resolve()
        scripts_dir = fn.parent
        target = scripts_dir / 'gutenberg_fetch_and_convert.py'
        if not target.exists():
            raise ImportError(f"Could not find helper script: {target}")
        spec = importlib.util.spec_from_file_location('gutenberg_fetch_and_convert', str(target))
        module = importlib.util.module_from_spec(spec)
        loader = spec.loader
        assert loader is not None
        loader.exec_module(module)
        return getattr(module, 'process_gutenberg_url')


def build_gutenberg_url_from_id(eid: int) -> str:
    return f"https://www.gutenberg.org/ebooks/{eid}"


def main():
    parser = argparse.ArgumentParser(description='Download Project Gutenberg ebook as PDF (wrapper)')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--id', type=int, help='Gutenberg ebook numeric id, e.g. 1342')
    group.add_argument('--url', help='Full Gutenberg ebook page URL')
    parser.add_argument('--output-dir', '-o', default='data/pdfs', help='Directory to save PDFs')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing file if present')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')

    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.id:
        url = build_gutenberg_url_from_id(args.id)
    else:
        url = args.url

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        process = load_process_func()
    except Exception as e:
        logging.error(f"Failed to load processing function: {e}")
        sys.exit(2)

    # Call the processing function
    saved = process(url, output_dir)
    if not saved:
        logging.error("Failed to download/convert the Gutenberg ebook")
        sys.exit(1)

    saved_path = Path(saved)
    if saved_path.exists():
        logging.info(f"Saved PDF: {saved_path}")
    else:
        logging.info(f"Processing reported saved path: {saved}")

    # If file exists and overwrite was requested, nothing else to do (process handles overwrite by filename)

if __name__ == '__main__':
    main()
