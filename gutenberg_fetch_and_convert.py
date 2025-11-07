"""
gutenberg_fetch_and_convert.py

Given a Project Gutenberg ebook page URL (https://www.gutenberg.org/ebooks/<id>),
this script will:
- Analyze the ebook page for a direct PDF download link and download it if found.
- Otherwise, attempt to find and download the plain-text version of the book.
- Convert the plain text into a readable PDF using FPDF, adding Title/Author metadata.
- Save the resulting PDF to the specified output folder.

Usage:
  python scripts\gutenberg_fetch_and_convert.py <gutenberg_url> --output-dir data/pdfs

Dependencies:
  pip install requests beautifulsoup4 fpdf PyPDF2

Notes:
- Project Gutenberg sometimes provides direct PDF/EPUB files in the "Download This eBook" area.
- For plain text, this script tries several common Gutenberg text file URL patterns.
"""

from __future__ import annotations
import argparse
import logging
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import unicodedata
from PyPDF2 import PdfReader, PdfWriter
import time

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

HEADERS = {"User-Agent": "AI-Virtual-Library/1.0 (+https://example.org)"}


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(name: str) -> str:
    # Keep it filesystem-safe
    name = name or "book"
    # replace problematic chars
    return re.sub(r"[^A-Za-z0-9 _\-\.]+", "", name).strip().replace(' ', '_')


def fetch_ebook_page(ebook_url: str) -> str | None:
    try:
        r = requests.get(ebook_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logging.error(f"Failed to fetch ebook page {ebook_url}: {e}")
        return None


def find_direct_pdf_on_page(html: str, base_url: str) -> str | None:
    soup = BeautifulSoup(html, 'html.parser')

    # 1. Look for link or a tags with type application/pdf
    link = soup.find('a', attrs={'type': 'application/pdf'})
    if link and link.get('href'):
        return urljoin(base_url, link['href'])

    # 2. Look for anchors whose text mentions PDF
    for a in soup.find_all('a', href=True):
        txt = (a.get_text() or '').strip().lower()
        href = a['href']
        if 'pdf' in txt or href.lower().endswith('.pdf') or 'format=pdf' in href.lower():
            return urljoin(base_url, href)

    # 3. Some Gutenberg pages include a link list with class 'download'
    for a in soup.select('a[href]'):
        href = a['href']
        if href and href.lower().endswith('.pdf'):
            return urljoin(base_url, href)

    return None


def _gutenberg_text_candidates(ebook_url: str) -> list[str]:
    # Try to extract the ebook id from /ebooks/<id>
    m = re.search(r"/ebooks/(\d+)", ebook_url)
    candidates: list[str] = []
    if m:
        eid = m.group(1)
        candidates += [
            f"https://www.gutenberg.org/files/{eid}/{eid}-0.txt",
            f"https://www.gutenberg.org/files/{eid}/{eid}.txt",
            f"https://www.gutenberg.org/cache/epub/{eid}/pg{eid}.txt",
            f"https://www.gutenberg.org/ebooks/{eid}.txt",
        ]
    # also try the page itself
    candidates.append(ebook_url)
    return candidates


def fetch_gutenberg_text(ebook_url: str, timeout: int = 20) -> str | None:
    for url in _gutenberg_text_candidates(ebook_url):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200 and r.text and len(r.text.strip()) > 100:
                logging.info(f"Fetched text from: {url}")
                return r.text
        except Exception:
            time.sleep(0.5)
            continue
    logging.warning("Could not find plain text using common Gutenberg patterns")
    return None


class SimpleTextPDF(FPDF):
    def __init__(self, title: str = '', author: str = '', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.author = author
        self.set_auto_page_break(auto=True, margin=15)
        # Try to add a TrueType font that supports Unicode
        self._unicode_font = None
        font_paths = []
        # Allow overriding via env var
        from os import environ
        if environ.get('PDF_FONT_PATH'):
            font_paths.append(environ.get('PDF_FONT_PATH'))
        # Common system font locations
        font_paths += [
            r"C:\Windows\Fonts\DejaVuSans.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        for p in font_paths:
            try:
                if p and Path(p).exists():
                    # Register font as 'DejaVuUnicode'
                    self.add_font('DejaVuUnicode', '', p, uni=True)
                    self._unicode_font = 'DejaVuUnicode'
                    break
            except Exception:
                continue

    def header(self):
        # optional header with title
        if self.title:
            self.set_font('Arial', 'B', 12)
            self.cell(0, 8, self.title[:90], ln=True, align='C')
            self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, 'AI Virtual Library', align='C')

    def add_text(self, text: str):
        self.add_page()
        # Use a unicode-capable font if available, otherwise fall back to Times
        if self._unicode_font:
            self.set_font(self._unicode_font, size=12)
        else:
            self.set_font('Times', size=12)
        # Split into paragraphs to preserve some structure
        paragraphs = text.split('\n\n')
        for p in paragraphs:
            p = p.strip('\n')
            if not p.strip():
                continue
            # wrap lines
            # If we don't have a unicode font, normalize some common smart quotes
            if not self._unicode_font:
                p = p.replace('\u2018', "'").replace('\u2019', "'")
                p = p.replace('\u201c', '"').replace('\u201d', '"')
            self.multi_cell(0, 6, p)
            self.ln(2)


def text_to_pdf_bytes(text: str, title: str = '', author: str = '') -> bytes:
    pdf = SimpleTextPDF(title=title, author=author)
    pdf.add_text(text)
    try:
        out = pdf.output(dest='S')
        if isinstance(out, (bytes, bytearray)):
            return bytes(out)
        return out.encode('latin-1')
    except UnicodeEncodeError as e:
        # FPDF couldn't encode some characters. Try to normalize to ASCII and retry.
        logging.warning(f"FPDF encoding error: {e}. Attempting ASCII-fallback normalization.")
        try:
            ascii_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
            pdf2 = SimpleTextPDF(title=title, author=author)
            pdf2.add_text(ascii_text)
            out2 = pdf2.output(dest='S')
            if isinstance(out2, (bytes, bytearray)):
                return bytes(out2)
            return out2.encode('latin-1')
        except Exception:
            # Last resort: try using reportlab if available (better UTF-8 support)
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
            except Exception:
                raise

            from io import BytesIO
            buffer = BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            # Simple layout: title and author, then body text
            y = height - 72
            c.setFont('Helvetica-Bold', 14)
            c.drawString(72, y, (title or '').strip()[:200])
            y -= 20
            c.setFont('Helvetica', 10)
            if author:
                c.drawString(72, y, f"Author: {author}")
                y -= 24

            text_obj = c.beginText(72, y)
            text_obj.setFont('Times-Roman', 10)
            # Wrap lines simply
            for line in text.splitlines():
                # If y too low, start new page
                if text_obj.getY() < 72:
                    c.drawText(text_obj)
                    c.showPage()
                    text_obj = c.beginText(72, height - 72)
                    text_obj.setFont('Times-Roman', 10)
                text_obj.textLine(line[:1000])
            c.drawText(text_obj)
            c.save()
            pdf_bytes = buffer.getvalue()
            buffer.close()
            return pdf_bytes


def save_pdf_bytes_with_metadata(pdf_bytes: bytes, out_path: Path, title: str = '', author: str = '') -> Path:
    # First write the bytes
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(pdf_bytes)

    # Add metadata using PyPDF2
    try:
        reader = PdfReader(str(out_path))
        writer = PdfWriter()
        for p in reader.pages:
            writer.add_page(p)
        meta = {}
        if title:
            meta['/Title'] = title
        if author:
            meta['/Author'] = author
        writer.add_metadata(meta)
        with open(out_path, 'wb') as f:
            writer.write(f)
    except Exception as e:
        logging.warning(f"Failed to set metadata on {out_path}: {e}")

    return out_path


def download_file(url: str, out_path: Path, timeout: int = 30) -> bool:
    try:
        logging.info(f"Downloading file: {url}")
        r = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
        r.raise_for_status()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'wb') as fh:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    fh.write(chunk)
        return True
    except Exception as e:
        logging.error(f"Failed to download {url}: {e}")
        return False


def process_gutenberg_url(ebook_url: str, output_dir: Path) -> Path | None:
    logging.info(f"Processing: {ebook_url}")
    html = fetch_ebook_page(ebook_url)
    title = ''
    author = ''

    if html:
        soup = BeautifulSoup(html, 'html.parser')
        # Try to extract title and author from meta tags or page header
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        author_meta = soup.find('meta', attrs={'name': 'author'})
        if author_meta and author_meta.get('content'):
            author = author_meta['content'].strip()
        # Gutenberg specific header
        h1 = soup.find('h1')
        if h1 and not title:
            title = h1.get_text().strip()
        # find author in h2 or byline
        h2 = soup.find('h2')
        if h2 and not author:
            author = h2.get_text().strip()

        # Look for direct PDF link
        pdf_link = find_direct_pdf_on_page(html, ebook_url)
        if pdf_link:
            logging.info(f"Found direct PDF link: {pdf_link}")
            parsed = urlparse(pdf_link)
            filename = Path(parsed.path).name or sanitize_filename(title or 'book') + '.pdf'
            out_path = output_dir / filename
            ok = download_file(pdf_link, out_path)
            if ok:
                logging.info(f"Saved remote PDF to: {out_path}")
                # attempt to set metadata
                try:
                    save_pdf_bytes_with_metadata(out_path.read_bytes(), out_path, title=title, author=author)
                except Exception:
                    pass
                return out_path

    # If we didn't find a PDF, try to fetch plain text
    text = fetch_gutenberg_text(ebook_url)
    if not text:
        logging.error("Could not fetch text for Gutenberg ebook")
        return None

    # Try to extract title/author from the text header if missing
    if not title or not author:
        # look for Title and Author lines in first 2000 chars
        head = text[:2000]
        m_title = re.search(r"^\s*Title\s*[:\-]\s*(.+)$", head, re.IGNORECASE | re.MULTILINE)
        m_author = re.search(r"^\s*Author\s*[:\-]\s*(.+)$", head, re.IGNORECASE | re.MULTILINE)
        if m_title:
            title = m_title.group(1).strip()
        if m_author:
            author = m_author.group(1).strip()

    if not title:
        title = f"gutenberg_{int(time.time())}"
    base = sanitize_filename(f"{title} - {author}")
    out_path = output_dir / f"{base}.pdf"

    pdf_bytes = text_to_pdf_bytes(text, title=title, author=author)
    saved = save_pdf_bytes_with_metadata(pdf_bytes, out_path, title=title, author=author)
    logging.info(f"Saved PDF: {saved}")
    return saved


def main():
    parser = argparse.ArgumentParser(description='Fetch Project Gutenberg book (PDF or text) and generate a PDF with metadata')
    parser.add_argument('url', help='Project Gutenberg ebook page URL (e.g. https://www.gutenberg.org/ebooks/1342)')
    parser.add_argument('--output-dir', '-o', default='data/pdfs', help='Directory where PDFs will be saved')
    args = parser.parse_args()

    outdir = ensure_output_dir(Path(args.output_dir))
    res = process_gutenberg_url(args.url, outdir)
    if res:
        logging.info(f"Done: {res}")
    else:
        logging.error("Failed to process the Gutenberg URL")


if __name__ == '__main__':
    main()
