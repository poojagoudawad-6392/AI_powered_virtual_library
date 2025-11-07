"""
Bulk download HTML files for all books in the Gutenberg dataset.
This script will download HTML files locally so PDFs can be created with full content.
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import requests
import time
from pathlib import Path
from tqdm import tqdm
import os

# Configuration
CSV_PATH = Path('.dist/gutenberg_html_dataset (1).csv')
OUTPUT_DIR = Path('data/books_html')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Progress tracking
PROGRESS_FILE = OUTPUT_DIR / 'download_progress.txt'

def sanitize_filename(name: str) -> str:
    """Create a safe filename."""
    import re
    name = name or "book"
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.strip()[:100]  # Limit length
    return name

def load_progress():
    """Load list of already downloaded book IDs."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_progress(book_id: str):
    """Save progress for a downloaded book."""
    with open(PROGRESS_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{book_id}\n")

def extract_book_id(url: str) -> str:
    """Extract book ID from Gutenberg URL."""
    import re
    match = re.search(r'/epub/(\d+)/', url)
    return match.group(1) if match else None

def download_html(url: str, output_path: Path, max_retries: int = 3) -> bool:
    """Download HTML content from URL with retry logic."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    for attempt in range(max_retries):
        try:
            timeout = 30 + (attempt * 15)  # 30s, 45s, 60s
            resp = requests.get(url, headers=headers, timeout=timeout, stream=True)
            
            if resp.status_code == 200:
                # Save to file
                with open(output_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # Verify file size
                if output_path.stat().st_size > 1000:  # At least 1KB
                    return True
                else:
                    output_path.unlink()  # Delete small file
                    return False
            elif resp.status_code == 404:
                return False  # Don't retry for 404
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
        except Exception as e:
            print(f"    Error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
    
    return False

def main():
    print("=" * 70)
    print("BULK BOOK DOWNLOADER - AI Virtual Library")
    print("=" * 70)
    
    # Load CSV
    print(f"\n📚 Loading book catalog from: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    print(f"   Found {len(df)} books in catalog")
    
    # Load progress
    downloaded = load_progress()
    print(f"   Already downloaded: {len(downloaded)} books")
    
    # Filter books that need downloading
    df['Book_ID'] = df['HTML_Link'].apply(extract_book_id)
    df_to_download = df[~df['Book_ID'].isin(downloaded)].copy()
    
    print(f"   Remaining to download: {len(df_to_download)} books")
    
    if len(df_to_download) == 0:
        print("\n✅ All books already downloaded!")
        return
    
    # Ask for confirmation
    print(f"\n⚠️  This will download {len(df_to_download)} HTML files.")
    print(f"   Estimated time: {len(df_to_download) * 2 / 60:.1f} minutes (at 2 sec/book)")
    print(f"   Storage needed: ~{len(df_to_download) * 0.5:.1f} MB")
    
    response = input("\nProceed with download? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Download cancelled.")
        return
    
    # Download books
    print(f"\n📥 Starting download...\n")
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for idx, row in tqdm(df_to_download.iterrows(), total=len(df_to_download), desc="Downloading"):
        book_id = row['Book_ID']
        title = row.get('Title', 'Unknown')
        author = row.get('Author', 'Unknown')
        html_link = row.get('HTML_Link', '')
        
        if not html_link or not book_id:
            skip_count += 1
            continue
        
        # Create filename
        safe_title = sanitize_filename(title)
        safe_author = sanitize_filename(author)
        filename = f"{book_id}_{safe_title}_{safe_author}.html"
        output_path = OUTPUT_DIR / filename
        
        # Skip if already exists
        if output_path.exists() and output_path.stat().st_size > 1000:
            save_progress(book_id)
            success_count += 1
            continue
        
        # Download
        if download_html(html_link, output_path):
            save_progress(book_id)
            success_count += 1
        else:
            fail_count += 1
        
        # Rate limiting
        time.sleep(0.5)  # Be nice to Gutenberg servers
    
    # Summary
    print("\n" + "=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)
    print(f"✅ Successfully downloaded: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"⏭️  Skipped: {skip_count}")
    print(f"📁 Files saved to: {OUTPUT_DIR.absolute()}")
    print("\n💡 Next step: Update app to use local HTML files")

if __name__ == "__main__":
    main()
