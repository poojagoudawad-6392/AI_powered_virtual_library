"""
convert_books_to_pdf.py

Usage examples:
  python scripts\convert_books_to_pdf.py --output-dir output_dir urls.txt
  python scripts\convert_books_to_pdf.py --output-dir output_dir https://www.gutenberg.org/ebooks/1342.txt.utf-8 https://example.com/book.html

Notes:
- Requires `pdfkit` and `wkhtmltopdf` installed and on PATH (or set WKHTMLTOPDF_PATH env var).
- Requires `requests`, `beautifulsoup4`, and `PyPDF2`.

Install dependencies:
  pip install pdfkit requests beautifulsoup4 PyPDF2

On Windows install wkhtmltopdf from https://wkhtmltopdf.org/downloads.html and set PATH or WKHTMLTOPDF_PATH.
"""

import argparse
import os
import sys
import re
import requests
import pdfkit
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader, PdfWriter
from urllib.parse import urlparse
from pathlib import Path
import shutil
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def sanitize_filename(name: str) -> str:
    # Remove unsafe characters
    name = re.sub(r"[\\/:*?\"<>|]+", "", name)
    name = name.strip()
    if not name:
        name = "book"
    return name


def guess_title_author_from_html(html: str, url: str):
    soup = BeautifulSoup(html, 'html.parser')
    title = None
    author = None

    # Try common meta tags
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    meta_author = soup.find('meta', attrs={'name': 'author'}) or soup.find('meta', attrs={'property': 'author'})
    if meta_author and meta_author.get('content'):
        author = meta_author['content'].strip()

    # Open Graph / Twitter fallbacks
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content') and not title:
        title = og_title['content'].strip()

    if not title:
        # Derive from URL path
        parsed = urlparse(url)
        name = os.path.basename(parsed.path)
        title = name or url

    return title, author or ''


def guess_title_author_from_text(text: str, url: str):
    # Look for lines like Title: ..., Author: ... in the first 2000 chars
    head = text[:2000]
    title = None
    author = None
    m_title = re.search(r"^\s*Title\s*[:\-]\s*(.+)$", head, re.IGNORECASE | re.MULTILINE)
    m_author = re.search(r"^\s*Author\s*[:\-]\s*(.+)$", head, re.IGNORECASE | re.MULTILINE)
    if m_title:
        title = m_title.group(1).strip()
    if m_author:
        author = m_author.group(1).strip()

    if not title:
        # fallback to file name or url
        parsed = urlparse(url)
        name = os.path.basename(parsed.path)
        title = name or url

    return title, author or ''


def ensure_wkhtmltopdf_path():
    # Allow override via environment variable
    path = os.environ.get('WKHTMLTOPDF_PATH')
    if path and Path(path).exists():
        return path

    # Try system PATH
    exe = shutil.which('wkhtmltopdf')
    if exe:
        return exe

    # Common Windows location
    common = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
    if Path(common).exists():
        return common

    return None


def convert_url_to_pdf(url: str, output_dir: Path, wkhtmltopdf_path: str = None, timeout: int = 30) -> tuple[str, str, Path] | None:
    """Download a URL (text or HTML) and convert to PDF. Returns (title, author, output_path) on success, None on failure."""
    try:
        logging.info(f"Downloading: {url}")
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to download {url}: {e}")
        return None

    content_type = r.headers.get('Content-Type', '').lower()
    raw = r.content

    try:
        if 'text/html' in content_type or url.lower().endswith('.html') or url.lower().endswith('.htm'):
            html = r.text
            title, author = guess_title_author_from_html(html, url)
            # Ensure HTML has a proper <meta> charset and basic structure
            if not re.search(r'<html', html, re.IGNORECASE):
                html = f"<html><head><meta charset=\"utf-8\"></head><body><pre>{BeautifulSoup(html, 'html.parser').prettify()}</pre></body></html>"
        else:
            # Treat as plain text
            text = r.text
            title, author = guess_title_author_from_text(text, url)
            # Wrap text in simple HTML to render as PDF
            safe_text = BeautifulSoup(text, 'html.parser').get_text()
            # preserve paragraphs
            paragraphs = safe_text.splitlines()
            body = '\n'.join(f"<p>{p}</p>" for p in paragraphs if p.strip())
            html = f"<html><head><meta charset=\"utf-8\"><title>{title}</title></head><body><h1>{title}</h1><h3>{author}</h3>{body}</body></html>"

        # Prepare output filename
        base = sanitize_filename(f"{title} - {author}")
        if not base:
            base = sanitize_filename(Path(urlparse(url).path).stem or 'book')
        out_path = output_dir / f"{base}.pdf"

        # Configure pdfkit
        config = None
        wk = wkhtmltopdf_path or ensure_wkhtmltopdf_path()
        if wk:
            config = pdfkit.configuration(wkhtmltopdf=wk)
        else:
            logging.warning("wkhtmltopdf executable not found. pdfkit may fail unless wkhtmltopdf is installed and on PATH.")

        # Convert
        logging.info(f"Converting to PDF: {out_path}")
        pdfkit.from_string(html, str(out_path), configuration=config)

        # Add metadata using PyPDF2
        try:
            reader = PdfReader(str(out_path))
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            metadata = reader.metadata or {}
            # Overwrite/Add metadata
            meta = {}
            if title:
                meta['/Title'] = title
            if author:
                meta['/Author'] = author
            # Keep other metadata if present
            writer.add_metadata(meta)
            # Write back
            with open(out_path, 'wb') as f_out:
                writer.write(f_out)
        except Exception as e:
            logging.warning(f"Could not add metadata to PDF {out_path}: {e}")

        logging.info(f"Saved PDF: {out_path}")
        return title, author, out_path

    except Exception as e:
        logging.error(f"Failed to convert {url} to PDF: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Download book URLs and convert to PDF')
    parser.add_argument('inputs', nargs='+', help='List of URLs or a text file containing URLs (one per line)')
    parser.add_argument('--output-dir', '-o', default='pdf_output', help='Output directory for PDFs')
    parser.add_argument('--wkhtmltopdf', default=None, help='Path to wkhtmltopdf executable')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build a list of URLs from inputs: if an arg is a file, read lines, otherwise treat as URL
    urls = []
    for item in args.inputs:
        p = Path(item)
        if p.exists() and p.is_file():
            with open(p, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        urls.append(line)
        else:
            urls.append(item)

    wk = args.wkhtmltopdf or ensure_wkhtmltopdf_path()

    results = []
    for url in urls:
        res = convert_url_to_pdf(url, output_dir, wkhtmltopdf_path=wk)
        if res:
            results.append(res)
        else:
            logging.error(f"Failed: {url}")

    logging.info(f"Conversion complete. {len(results)} succeeded, {len(urls)-len(results)} failed.")

if __name__ == '__main__':
    main()
