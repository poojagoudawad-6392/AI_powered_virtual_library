"""
Update the CSV file to include local HTML file paths.
This allows the app to use downloaded files instead of fetching from network.
"""
import pandas as pd
from pathlib import Path
import re

# Configuration
CSV_PATH = Path('.dist/gutenberg_html_dataset (1).csv')
OUTPUT_CSV = Path('.dist/gutenberg_html_dataset_local.csv')
HTML_DIR = Path('data/books_html')

def extract_book_id(url: str) -> str:
    """Extract book ID from Gutenberg URL."""
    match = re.search(r'/epub/(\d+)/', url)
    return match.group(1) if match else None

def find_local_file(book_id: str, html_dir: Path) -> str:
    """Find local HTML file for a book ID."""
    if not book_id:
        return ''
    
    # Look for files starting with book_id
    matches = list(html_dir.glob(f"{book_id}_*.html"))
    if matches:
        return str(matches[0].absolute())
    return ''

def main():
    print("=" * 70)
    print("UPDATE CSV WITH LOCAL FILE PATHS")
    print("=" * 70)
    
    # Load CSV
    print(f"\n📚 Loading: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    print(f"   Total books: {len(df)}")
    
    # Extract book IDs
    print("\n🔍 Extracting book IDs...")
    df['Book_ID'] = df['HTML_Link'].apply(extract_book_id)
    
    # Find local files
    print(f"🔍 Searching for local HTML files in: {HTML_DIR}")
    if not HTML_DIR.exists():
        print(f"   ⚠️  Directory not found. Run bulk_download_books.py first!")
        return
    
    local_files = list(HTML_DIR.glob("*.html"))
    print(f"   Found {len(local_files)} local HTML files")
    
    # Add local path column
    print("\n📝 Adding local file paths to CSV...")
    df['Local_HTML_Path'] = df['Book_ID'].apply(lambda bid: find_local_file(bid, HTML_DIR))
    
    # Count matches
    has_local = df['Local_HTML_Path'].str.len() > 0
    print(f"   ✅ Matched {has_local.sum()} books with local files")
    print(f"   ⚠️  {(~has_local).sum()} books still need network fetch")
    
    # Save updated CSV
    print(f"\n💾 Saving updated CSV to: {OUTPUT_CSV}")
    df.to_csv(OUTPUT_CSV, index=False)
    
    print("\n✅ Done! CSV updated with local file paths.")
    print(f"\n💡 Next: Update load_books() in app_enhanced.py to use '{OUTPUT_CSV.name}'")

if __name__ == "__main__":
    main()
