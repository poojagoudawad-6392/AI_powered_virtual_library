"""
Enhanced AI-Powered Virtual Library
Includes all new features: Story Generation, Collaborative Writing, Mood-Based Recommendations, 
Gamification, and Data Analytics
"""
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import custom modules
from models.recommender import BookRecommender
from models.summarizer import BookSummarizer
from models.sentiment import SentimentAnalyzer
from models.translator import BookTranslator
from models.chat_assistant import ChatAssistant
from models.story_generator import StoryGenerator
from models.collaborative_story import CollaborativeStory
from models.mood_recommender import MoodRecommender
from models.gamification import GamificationSystem
from models.data_analytics import DataAnalytics
from utils.auth import authenticate_user, register_user, create_users_table
from utils.pdf_utils import get_book_content, create_pdf_bytes, make_filename, _sanitize_filename, fetch_gutenberg_text, extract_text_from_html, create_styled_pdf_from_html, get_gutenberg_html_url
import streamlit.components.v1 as components
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="AI Virtual Library - Enhanced",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        padding: 20px;
        font-weight: bold;
    }
    .book-card {
        padding: 15px;
        background-color: #f0f2f6;
        border-radius: 10px;
        margin: 10px 0;
    }
    .stat-card {
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        text-align: center;
    }
    .badge-card {
        padding: 10px;
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        border-radius: 8px;
        text-align: center;
        margin: 5px;
    }
    .story-card {
        padding: 15px;
        background-color: #e8f4f8;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    
    create_users_table()
    
    c.execute('''CREATE TABLE IF NOT EXISTS reading_history
                 (user_id TEXT, book_title TEXT, author TEXT, 
                  date_added TEXT, rating INTEGER, review TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS bookmarks
                 (user_id TEXT, book_title TEXT, author TEXT, 
                  link TEXT, bookshelf TEXT, date_added TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS reading_activities
                 (username TEXT, book_title TEXT, activity_type TEXT,
                  timestamp TEXT, genre TEXT DEFAULT 'General',
                  duration_minutes INTEGER DEFAULT 30)''')
    
    # User stats and activity tables
    c.execute('''CREATE TABLE IF NOT EXISTS user_stats
                 (username TEXT PRIMARY KEY,
                  total_books_read INTEGER DEFAULT 0,
                  total_pages_read INTEGER DEFAULT 0,
                  total_reading_time INTEGER DEFAULT 0,
                  current_streak INTEGER DEFAULT 0,
                  longest_streak INTEGER DEFAULT 0,
                  last_activity_date TEXT,
                  level INTEGER DEFAULT 1,
                  experience_points INTEGER DEFAULT 0)''')
    
    # Create gamification tables
    c.execute('''CREATE TABLE IF NOT EXISTS user_badges
                 (username TEXT,
                  badge_id TEXT,
                  badge_name TEXT,
                  badge_description TEXT,
                  badge_icon TEXT,
                  earned_date TEXT,
                  PRIMARY KEY (username, badge_id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_challenges
                 (username TEXT,
                  challenge_id TEXT,
                  progress INTEGER DEFAULT 0,
                  status TEXT DEFAULT 'active',
                  completed_date TEXT,
                  PRIMARY KEY (username, challenge_id))''')
    
    conn.commit()
    conn.close()

# Load book dataset
@st.cache_data
def load_books():
    """Load the HTML dataset and normalize column names to the app's expectations.

    Expected source columns (example): Title, Author, HTML_Link, Link, Bookshelf, Local_HTML_Path
    This function will create/ensure the following columns: Title, Author, HTML_Path, Link, Bookshelf
    """
    try:
        # Allow different filenames, prioritize local version
        dist_dir = Path('.dist')
        
        # First try to load CSV with local paths
        local_csv = dist_dir / 'gutenberg_html_dataset_local.csv'
        if local_csv.exists():
            csv_path = local_csv
        else:
            # Fallback to original CSV
            csv_candidates = list(dist_dir.glob('gutenberg_html_dataset*.csv'))
            if csv_candidates:
                csv_path = csv_candidates[0]
            else:
                csv_path = dist_dir / 'gutenberg_html_dataset.csv'
        
        df = pd.read_csv(csv_path)

        # Prioritize Local_HTML_Path over HTML_Link if it exists
        if 'Local_HTML_Path' in df.columns:
            # Use local path if it exists and file is accessible, otherwise fall back to HTML_Link
            df['HTML_Path'] = df.apply(
                lambda row: row['Local_HTML_Path'] if pd.notna(row.get('Local_HTML_Path')) and 
                           row.get('Local_HTML_Path', '').strip() and 
                           Path(row.get('Local_HTML_Path', '')).exists() 
                           else row.get('HTML_Link', ''),
                axis=1
            )
        elif 'HTML_Link' in df.columns:
            df['HTML_Path'] = df['HTML_Link']
        elif 'html_link' in df.columns:
            df['HTML_Path'] = df['html_link']

        # Ensure Title and Link exist (case-insensitive fallback)
        if 'Title' not in df.columns and 'title' in df.columns:
            df['Title'] = df['title']
        if 'Link' not in df.columns and 'link' in df.columns:
            df['Link'] = df['link']

        # Ensure Author and Bookshelf exist
        if 'Author' not in df.columns:
            df['Author'] = df['Author'] if 'Author' in df.columns else (df['author'] if 'author' in df.columns else 'Unknown')
        if 'Bookshelf' not in df.columns:
            df['Bookshelf'] = df['Bookshelf'] if 'Bookshelf' in df.columns else (df['bookshelf'] if 'bookshelf' in df.columns else 'General')

        # Some datasets might already have HTML_Path under a slightly different name
        if 'HTML_Path' not in df.columns:
            # try common alternatives
            for alt in ['html_path', 'htmlfile', 'html_file', 'html_link']:
                if alt in df.columns:
                    df['HTML_Path'] = df[alt]
                    break

        # Final defaults for missing expected columns
        for col, default in [('Title', ''), ('Author', 'Unknown'), ('Link', ''), ('HTML_Path', ''), ('Bookshelf', 'General')]:
            if col not in df.columns:
                df[col] = default

        return df
    except Exception as e:
        st.error(f"Error loading dataset: {e}")
        return pd.DataFrame()

# Initialize session state
def init_session_state():
    # Core session flags
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "📚 Book Catalog"

    # Initialize widget-backed keys to avoid Streamlit KeyError
    widget_defaults = {
        'login_user': "",
        'login_pass': "",
        'reg_user': "",
        'reg_pass': "",
        'reg_confirm': "",
        'content_temp': "",
    }
    for k, v in widget_defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# Main app
def main():
    init_db()
    init_session_state()
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("## 🔐 User Profile")
        
        if not st.session_state.logged_in:
            # Login/Register
            tab1, tab2 = st.tabs(["Login", "Register"])
            
            with tab1:
                username = st.text_input("Username", key="login_user")
                password = st.text_input("Password", type="password", key="login_pass")
                if st.button("Login"):
                    if authenticate_user(username, password):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
            
            with tab2:
                new_username = st.text_input("New Username", key="reg_user")
                new_password = st.text_input("New Password", type="password", key="reg_pass")
                confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
                if st.button("Register"):
                    if new_password == confirm_password:
                        if register_user(new_username, new_password):
                            st.success("Registration successful! Please login.")
                        else:
                            st.error("Username already exists")
                    else:
                        st.error("Passwords don't match")
        else:
            st.success(f"Welcome, {st.session_state.username}! 👋")
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.username = None
                st.rerun()
        
        st.markdown("---")
        st.markdown("## 📖 Navigation")
        
        pages = [
            "📚 Book Catalog",
            "✨ AI Story Generator",
            "👥 Collaborative Stories",
            "🎭 Mood Recommendations",
            "🏆 Achievements",
            "📊 Analytics Dashboard",
            "💬 AI Chat Assistant",
            "🧾 Book Summary",
            "🌐 Translate Book",
            "📈 Sentiment Analysis",
            "🎯 Recommendations",
            "👤 My Profile"
        ]
        
        for page in pages:
            if st.button(page, key=page, use_container_width=True):
                st.session_state.current_page = page
                st.rerun()
    
    # Main content area
    st.markdown('<h1 class="main-header">📚 AI-Powered Virtual Library</h1>', unsafe_allow_html=True)
    
    # Load books data
    books_df = load_books()
    
    # Page routing
    current_page = st.session_state.current_page
    
    if current_page == "📚 Book Catalog":
        show_book_catalog(books_df)
    elif current_page == "✨ AI Story Generator":
        show_story_generator()
    elif current_page == "👥 Collaborative Stories":
        show_collaborative_stories()
    elif current_page == "🎭 Mood Recommendations":
        show_mood_recommendations(books_df)
    elif current_page == "🏆 Achievements":
        show_achievements()
    elif current_page == "📊 Analytics Dashboard":
        show_analytics_dashboard(books_df)
    elif current_page == "💬 AI Chat Assistant":
        show_chat_assistant(books_df)
    elif current_page == "🧾 Book Summary":
        show_summarizer(books_df)
    elif current_page == "🌐 Translate Book":
        show_translator(books_df)
    elif current_page == "📈 Sentiment Analysis":
        show_sentiment_analysis(books_df)
    elif current_page == "🎯 Recommendations":
        show_recommendations(books_df)
    elif current_page == "👤 My Profile":
        show_user_profile()

def show_book_catalog(books_df):
    """Display book catalog with search and filter"""
    st.header("📚 Book Catalog")
    
    # Debug info
    st.write("Dataset columns:", books_df.columns.tolist())
    
    # Statistics
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="stat-card"><h3>{len(books_df)}</h3><p>Total Books</p></div>', 
                    unsafe_allow_html=True)
    with col2:
        available_html = len(books_df[books_df['HTML_Path'].notna()]) if 'HTML_Path' in books_df.columns else 0
        st.markdown(f'<div class="stat-card"><h3>{available_html}</h3><p>Available HTML Books</p></div>', 
                    unsafe_allow_html=True)
    
    st.markdown("---")
    

    # Search and filter
    st.subheader("🔍 Search Books")
    
    # Search box with voice and photo icons
    col1, col2, col3 = st.columns([6, 0.5, 0.5])
    
    search_query = ""
    
    with col1:
        search_query = st.text_input("Search by Title or Author", "", placeholder="Type or use voice/photo search...", label_visibility="collapsed")
    
    with col2:
        if st.button("🎤", key="voice_search_btn", help="Voice Search"):
            st.info("🎤 Voice search: Speak to search (requires microphone access)")
    
    with col3:
        if st.button("📷", key="photo_search_btn", help="Photo Search"):
            st.session_state['show_photo_upload'] = True
    
    # Show photo upload if button clicked
    if st.session_state.get('show_photo_upload', False):
        with st.expander("📷 Photo Search - Upload Image", expanded=True):
            uploaded_image = st.file_uploader("Upload an image with book title or author", type=['jpg', 'jpeg', 'png'], key="photo_search_upload")
            
            if uploaded_image is not None:
                col_img1, col_img2 = st.columns([1, 1])
                with col_img1:
                    st.image(uploaded_image, caption="Uploaded Image", use_column_width=True)
                with col_img2:
                    if st.button("🔍 Extract Text", key="extract_text_btn"):
                        with st.spinner("Extracting text from image..."):
                            try:
                                from PIL import Image
                                import pytesseract
                                
                                image = Image.open(uploaded_image)
                                extracted_text = pytesseract.image_to_string(image)
                                
                                if extracted_text.strip():
                                    st.success("✅ Text extracted!")
                                    search_query = extracted_text.strip()
                                    st.session_state['extracted_search'] = search_query
                                    st.info(f"Searching for: {search_query}")
                                else:
                                    st.warning("⚠️ No text found in image")
                            except ImportError:
                                st.error("📦 Install pytesseract: pip install pytesseract")
                            except Exception as e:
                                st.error(f"Error: {e}")
            
            if st.button("❌ Close", key="close_photo_search"):
                st.session_state['show_photo_upload'] = False
                st.rerun()
    
    # Use extracted search if available
    if 'extracted_search' in st.session_state and st.session_state['extracted_search']:
        search_query = st.session_state['extracted_search']
    
    st.markdown("---")
    
    # Advanced Filter controls
    st.subheader("🎯 Filters & Sorting")
    
    # Main filters row
    col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.5, 1.5, 1])

    with col1:
        if search_query:
            st.info(f"🔍 Searching for: {search_query}")
        else:
            st.write("")

    with col2:
        genres = ["All"]
        if 'Bookshelf' in books_df.columns:
            genres += sorted(books_df['Bookshelf'].dropna().unique().tolist())
        selected_genre = st.selectbox("📂 Category", genres)

    with col3:
        # Reading status filter
        status_filter = st.selectbox("📖 Status", ["All Books", "Want to Read", "Currently Reading", "Completed"])
    
    with col4:
        # Author filter
        authors = ["All Authors"]
        if 'Author' in books_df.columns:
            unique_authors = books_df['Author'].dropna().unique().tolist()
            authors += sorted([a for a in unique_authors if a and str(a).strip()])[:50]  # Limit to 50 authors
        selected_author = st.selectbox("✍️ Author", authors)

    with col5:
        sort_by = st.selectbox("🔄 Sort", ["Title A-Z", "Title Z-A", "Latest", "Popular", "Author"])
    
    # Additional filters in expander
    with st.expander("⚙️ More Filters", expanded=False):
        adv_col1, adv_col2, adv_col3, adv_col4 = st.columns(4)
        
        with adv_col1:
            book_length = st.select_slider(
                "📏 Book Length",
                options=["All", "Short (<200 pages)", "Medium (200-400)", "Long (>400)"]
            )
        
        with adv_col2:
            language_filter = st.selectbox(
                "🌍 Language",
                ["All", "English", "French", "German", "Spanish", "Italian", "Portuguese", "Other"]
            )
        
        with adv_col3:
            # Publication period filter
            publication_period = st.selectbox(
                "📅 Publication Period",
                ["All Time", "Classic (Before 1900)", "Early 1900s (1900-1950)", "Modern (1950-2000)", "Contemporary (After 2000)"]
            )
        
        with adv_col4:
            # Reading difficulty
            difficulty_level = st.selectbox(
                "📊 Reading Level",
                ["All Levels", "Beginner", "Intermediate", "Advanced", "Expert"]
            )
        
        # Second row of advanced filters
        adv_col5, adv_col6, adv_col7, adv_col8 = st.columns(4)
        
        with adv_col5:
            show_only_html = st.checkbox("📱 Has Online Reading", value=False)
        
        with adv_col6:
            show_only_rated = st.checkbox("⭐ Only Rated Books", value=False)
        
        with adv_col7:
            show_bookmarked = st.checkbox("🔖 My Bookmarks Only", value=False)
        
        with adv_col8:
            items_per_page_filter = st.selectbox(
                "📄 Items Per Page",
                [10, 20, 50, 100],
                index=1
            ) 
    
    # Filter books
    filtered_books = books_df.copy()
    
    # Search filter
    if search_query:
        title_ser = filtered_books['Title'] if 'Title' in filtered_books else pd.Series([''] * len(filtered_books))
        author_ser = filtered_books['Author'] if 'Author' in filtered_books else pd.Series([''] * len(filtered_books))
        filtered_books = filtered_books[
            title_ser.str.contains(search_query, case=False, na=False) |
            author_ser.str.contains(search_query, case=False, na=False)
        ]

    # Genre filter
    if 'Bookshelf' in filtered_books and selected_genre != "All":
        filtered_books = filtered_books[filtered_books['Bookshelf'] == selected_genre]
    
    # Author filter
    if selected_author != "All Authors" and 'Author' in filtered_books.columns:
        filtered_books = filtered_books[filtered_books['Author'] == selected_author]
    
    # HTML availability filter
    if show_only_html and 'HTML_Path' in filtered_books.columns:
        filtered_books = filtered_books[filtered_books['HTML_Path'].notna() & (filtered_books['HTML_Path'] != '')]
    
    # Rated books filter
    if show_only_rated:
        # Filter books that have been rated by the user
        rated_indices = [idx for idx in filtered_books.index if st.session_state.get(f"rating_{idx}", 0) > 0]
        if rated_indices:
            filtered_books = filtered_books.loc[rated_indices]
        else:
            filtered_books = filtered_books.iloc[0:0]  # Empty dataframe
    
    # Bookmarked books filter
    if show_bookmarked and st.session_state.logged_in:
        bookmarks = get_bookmarks(st.session_state.username)
        bookmarked_titles = [b[0] for b in bookmarks]
        if bookmarked_titles:
            filtered_books = filtered_books[filtered_books['Title'].isin(bookmarked_titles)]
        else:
            filtered_books = filtered_books.iloc[0:0]  # Empty dataframe
    
    # Sort
    if sort_by == "Title A-Z":
        if 'Title' in filtered_books.columns:
            filtered_books = filtered_books.sort_values('Title', na_position='last')
    elif sort_by == "Title Z-A":
        if 'Title' in filtered_books.columns:
            filtered_books = filtered_books.sort_values('Title', ascending=False, na_position='last')
    elif sort_by == "Author":
        if 'Author' in filtered_books.columns:
            filtered_books = filtered_books.sort_values('Author', na_position='last')
    elif sort_by == "Popular":
        # Sort by index (assuming lower index = more popular)
        filtered_books = filtered_books.sort_index()
    else:  # Latest
        filtered_books = filtered_books.sort_index(ascending=False)
    
    # Display results
    st.write(f"**Found {len(filtered_books)} books**")
    
    # Pagination
    items_per_page = items_per_page_filter if 'items_per_page_filter' in locals() else 20
    total_pages = (len(filtered_books) - 1) // items_per_page + 1
    page = st.number_input("Page", min_value=1, max_value=max(1, total_pages), value=1, step=1)
    
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    # Display books
    for idx, row in filtered_books.iloc[start_idx:end_idx].iterrows():
        with st.container():
            # Book card with rating
            rating_key = f"rating_{idx}"
            user_rating = st.session_state.get(rating_key, 0)
            stars = "⭐" * user_rating if user_rating > 0 else "☆☆☆☆☆"
            
            st.markdown(f"""
            <div class="book-card">
                <h3>📖 {row['Title']}</h3>
                <p><strong>Author:</strong> {row['Author'] if row['Author'] else 'Unknown'}</p>
                <p><strong>Category:</strong> {row['Bookshelf'] if pd.notna(row['Bookshelf']) else 'General'}</p>
                <p><strong>Rating:</strong> {stars}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Quick View button
            if st.button("👁️ Quick View", key=f"quick_view_{idx}"):
                st.session_state[f'show_preview_{idx}'] = not st.session_state.get(f'show_preview_{idx}', False)
            
            # Show preview if toggled
            if st.session_state.get(f'show_preview_{idx}', False):
                with st.expander("📚 Book Details", expanded=True):
                    preview_col1, preview_col2 = st.columns([2, 1])
                    with preview_col1:
                        st.write(f"**Title:** {row['Title']}")
                        st.write(f"**Author:** {row['Author'] if row['Author'] else 'Unknown'}")
                        st.write(f"**Category:** {row['Bookshelf'] if pd.notna(row['Bookshelf']) else 'General'}")
                        link = row.get('Link', '')
                        if link:
                            st.write(f"**Source:** [Project Gutenberg]({link})")
                    
                    with preview_col2:
                        st.write("**Rate this book:**")
                        new_rating = st.select_slider(
                            "Stars",
                            options=[0, 1, 2, 3, 4, 5],
                            value=user_rating,
                            key=f"rate_slider_{idx}",
                            label_visibility="collapsed"
                        )
                        if new_rating != user_rating:
                            st.session_state[rating_key] = new_rating
                            st.success(f"Rated {new_rating} stars!")
                    
                    # Reading status
                    st.write("**Reading Status:**")
                    status = st.radio(
                        "Status",
                        ["Want to Read", "Currently Reading", "Completed"],
                        key=f"status_{idx}",
                        horizontal=True,
                        label_visibility="collapsed"
                    )
            
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            
            title = row.get('Title', '')
            author = row.get('Author', '')
            html_file = (row.get('HTML_Path') or '').strip()  # path or URL from dataset if present
            link = row.get('Link', '')
            
            with col1:
                # When Download PDF is clicked, fetch full content and create styled PDF
                if st.button("📥 Download PDF", key=f"download_pdf_{idx}"):
                    try:
                        with st.spinner("Fetching book content and creating PDF with full text..."):
                            html_content = None
                            book_text = None
                            pdf_bytes = None
                            
                            # Priority 1: Try to get HTML content from dataset
                            if html_file:
                                st.info(f"📄 Fetching from: {html_file[:80]}...")
                                try:
                                    content, _, mime_type = get_book_content(
                                        title=title,
                                        author=author,
                                        link=link,
                                        html_path=html_file
                                    )
                                    if content and len(content) > 500:  # Check for substantial content
                                        html_content = content.decode('utf-8', errors='ignore') if isinstance(content, (bytes, bytearray)) else str(content)
                                        # Verify it's not just the fallback template
                                        if len(html_content) > 500:
                                            st.success(f"✅ Loaded HTML content ({len(html_content):,} characters)")
                                        else:
                                            st.warning("⚠️ Could not fetch HTML content from URL (network timeout or unavailable)")
                                            html_content = None
                                    else:
                                        st.warning("⚠️ Could not fetch HTML content from URL (network timeout or unavailable)")
                                except Exception as html_error:
                                    st.warning(f"⚠️ Network error: {str(html_error)}")
                            
                            # Priority 2: If we have HTML content, extract text and create PDF
                            if html_content:
                                st.info("📝 Extracting text from HTML...")
                                try:
                                    # Extract text from HTML
                                    book_text = extract_text_from_html(html_content)
                                    
                                    if book_text and len(book_text.strip()) > 100:
                                        st.success(f"✅ Extracted {len(book_text):,} characters of text")
                                        
                                        # Create PDF with full text
                                        st.info("📄 Creating PDF with full book content...")
                                        pdf_bytes = create_pdf_bytes(
                                            title=title,
                                            author=author,
                                            link=link,
                                            full_text=book_text
                                        )
                                    else:
                                        st.warning("⚠️ Extracted text too short, trying styled HTML PDF...")
                                        # Try styled PDF from HTML
                                        base_url = html_file if html_file.lower().startswith('http') else None
                                        pdf_bytes = create_styled_pdf_from_html(html_content, title, author, base_url=base_url)
                                        
                                except Exception as extract_error:
                                    st.warning(f"Text extraction failed: {str(extract_error)}, trying styled PDF...")
                                    try:
                                        base_url = html_file if html_file.lower().startswith('http') else None
                                        pdf_bytes = create_styled_pdf_from_html(html_content, title, author, base_url=base_url)
                                    except Exception as styled_error:
                                        st.error(f"Styled PDF also failed: {str(styled_error)}")
                            
                            # Priority 3: Try Gutenberg text format if no HTML or HTML failed
                            if not pdf_bytes and link:
                                st.info("📚 Trying to fetch from Project Gutenberg...")
                                try:
                                    book_text = fetch_gutenberg_text(link)
                                    
                                    if book_text and len(book_text.strip()) > 100:
                                        st.success(f"✅ Fetched {len(book_text):,} characters from Gutenberg")
                                        pdf_bytes = create_pdf_bytes(
                                            title=title,
                                            author=author,
                                            link=link,
                                            full_text=book_text
                                        )
                                except Exception as gutenberg_error:
                                    st.warning(f"Gutenberg fetch failed: {str(gutenberg_error)}")
                            
                            # Last resort: Create metadata-only PDF
                            if not pdf_bytes:
                                st.warning("⚠️ Could not fetch full book content due to network issues.")
                                st.info("💡 **Tip:** You can read the full book online using the '📖 Read Online' button!")
                                st.info("Creating a metadata PDF with book information...")
                                pdf_bytes = create_pdf_bytes(
                                    title=title,
                                    author=author,
                                    link=link,
                                    full_text=None
                                )
                            
                            # Generate filename and trigger download
                            if pdf_bytes:
                                base_name = _sanitize_filename(f"{title} - {author}" if author else title)
                                pdf_filename = f"{base_name}.pdf"
                                
                                st.download_button(
                                    "📥 Download Complete Book PDF",
                                    data=pdf_bytes,
                                    file_name=pdf_filename,
                                    mime="application/pdf",
                                    key=f"save_pdf_{idx}"
                                )
                                st.success("✨ PDF ready! Click above to download.")
                            else:
                                st.error("❌ Failed to create PDF")
                                
                    except Exception as e:
                        st.error(f"Error creating PDF: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
            
            with col2:
                # Read Online button - opens HTML file from dataset
                if html_file and html_file.strip():
                    # Use the HTML_Path from dataset
                    st.link_button("📖 Read Online", html_file, use_container_width=True, type="primary")
                elif link and link.strip():
                    # Fallback to Gutenberg URL if no HTML_Path
                    html_url = get_gutenberg_html_url(link)
                    st.link_button("📖 Read Online", html_url, use_container_width=True, type="primary")
                else:
                    st.button("📖 Read Online", disabled=True, key=f"read_catalog_{idx}", help="No online link available", use_container_width=True)
            with col3:
                if st.session_state.logged_in:
                    if st.button("🔖 Bookmark", key=f"bookmark_{idx}"):
                        save_bookmark(row)
                        # Log activity for gamification
                        gamification = GamificationSystem()
                        gamification.log_reading_activity(
                            st.session_state.username,
                            row['Title'],
                            "bookmark",
                            row['Bookshelf'] if pd.notna(row['Bookshelf']) else 'General'
                        )
                        st.success("Bookmarked!")

def show_story_generator():
    """AI Story Generator Page"""
    st.header("✨ AI Story Generator")
    st.write("Create unique stories with AI assistance!")
    
    story_gen = StoryGenerator()
    
    tab1, tab2, tab3 = st.tabs(["🎨 Generate Story", "💡 Story Ideas", "📖 Continue Story"])
    
    with tab1:
        st.subheader("Generate a New Story")
        
        col1, col2 = st.columns(2)
        with col1:
            genre = st.selectbox("Genre", [
                "Fantasy", "Sci-Fi", "Mystery", "Romance", 
                "Horror", "Adventure", "Drama", "Comedy"
            ])
            length = st.selectbox("Story Length", ["short", "medium", "long"])
        
        with col2:
            style = st.selectbox("Writing Style", [
                "narrative", "descriptive", "dialogue-heavy", "poetic"
            ])
        
        prompt = st.text_area("Story Prompt", 
                             placeholder="E.g., A detective discovers a hidden world beneath the city...",
                             height=100)
        
        if st.button("🎭 Generate Story", type="primary"):
            if prompt:
                with st.spinner("Creating your story..."):
                    story = story_gen.generate_story(prompt, genre, length, style)
                    
                    st.success("Story generated!")
                    st.markdown(f"## {story['title']}")
                    st.markdown(f"**Genre:** {story['genre']} | **Words:** {story['word_count']}")
                    st.markdown("---")
                    st.write(story['content'])
                    
                    # Save option
                    if st.session_state.logged_in and st.button("💾 Save to My Stories"):
                        st.success("Story saved!")
            else:
                st.warning("Please enter a story prompt")
    
    with tab2:
        st.subheader("💡 Get Story Ideas")
        
        idea_genre = st.selectbox("Select Genre for Ideas", 
            ["Fantasy", "Sci-Fi", "Mystery", "Romance", "Adventure", 
             "Historical Fiction", "Literary Fiction", "Horror"])
        
        # Initialize story generator
        story_gen = StoryGenerator()
        
        if st.button("Generate Story Ideas"):
            with st.spinner("Generating creative ideas..."):
                ideas = story_gen.generate_story_ideas(idea_genre)
                st.write(f"### {idea_genre} Story Ideas:")
                for i, idea in enumerate(ideas, 1):
                    st.write(f"{i}. {idea}")
        
        st.divider()
        st.subheader("📚 My Bookmarked Books")
        
        # Get user's bookmarks
        if st.session_state.logged_in:
            conn = sqlite3.connect('library.db')
            c = conn.cursor()
            c.execute('''SELECT book_title, author, link FROM bookmarks 
                        WHERE user_id = ?''', (st.session_state.username,))
            bookmarks = c.fetchall()
            conn.close()
            
            if bookmarks:
                for bookmark in bookmarks:
                    st.write(f"📖 **{bookmark[0]}** by {bookmark[1]}")
                    link = bookmark[2]
                    local_pdf = None
                    
                    try:
                        p = Path(link)
                        if p.exists():
                            local_pdf = p
                    except Exception:
                        local_pdf = None
                    
                    # Create metadata PDF for all books
                    pdf_bytes = create_pdf_bytes(bookmark[0], bookmark[1], link)
                    filename = make_filename(bookmark[0], bookmark[1])
                    st.download_button(
                        "📥 Download Book Info PDF",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        key=f"meta_bm_{filename}"
                    )
    
    with tab3:
        st.subheader("📖 Continue an Existing Story")
        
        existing_story = st.text_area("Paste your story so far", height=200)
        continuation_prompt = st.text_input("How should the story continue?")
        
        if st.button("Continue Story"):
            if existing_story and continuation_prompt:
                with st.spinner("Continuing your story..."):
                    continuation = story_gen.continue_story(existing_story, continuation_prompt)
                    st.markdown("### Continuation:")
                    st.write(continuation)
            else:
                st.warning("Please provide both the existing story and continuation prompt")

def show_collaborative_stories():
    """Collaborative Storytelling Page"""
    st.header("👥 Collaborative Stories")
    st.write("Write stories together with other users!")
    
    if not st.session_state.logged_in:
        st.warning("Please login to access collaborative stories")
        return
    
    collab = CollaborativeStory()
    
    tab1, tab2, tab3 = st.tabs(["📚 Browse Stories", "✍️ Create Story", "📝 My Contributions"])
    
    with tab1:
        st.subheader("Active Collaborative Stories")
        
        stories = collab.list_active_stories("public")
        
        if stories:
            for story in stories:
                st.markdown(f"""
                <div class="story-card">
                    <h3>📖 {story['title']}</h3>
                    <p><strong>Genre:</strong> {story['genre']} | <strong>Creator:</strong> {story['creator']}</p>
                    <p><strong>Contributors:</strong> {story['contributor_count']} | <strong>Total Words:</strong> {story['total_words']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("📖 Read", key=f"read_{story['story_id']}"):
                        st.session_state['viewing_story'] = story['story_id']
                with col2:
                    if st.button("✍️ Contribute", key=f"contrib_{story['story_id']}"):
                        st.session_state['contributing_to'] = story['story_id']
                
                # Show story if viewing
                if st.session_state.get('viewing_story') == story['story_id']:
                    full_story = collab.get_story(story['story_id'])
                    if full_story:
                        st.markdown("### Story Content:")
                        for chapter in full_story['chapters']:
                            st.markdown(f"**Chapter {chapter['chapter']} by {chapter['author']}:**")
                            st.write(chapter['content'])
                            st.markdown("---")
                
                # Show contribution form
                if st.session_state.get('contributing_to') == story['story_id']:
                    new_content = st.text_area("Add your contribution:", height=150, 
                                              key=f"content_{story['story_id']}")
                    if st.button("Submit Contribution", key=f"submit_{story['story_id']}"):
                        if new_content:
                            if collab.add_contribution(story['story_id'], 
                                                      st.session_state.username, 
                                                      new_content):
                                # Log gamification activity
                                gamification = GamificationSystem()
                                gamification.log_reading_activity(
                                    st.session_state.username,
                                    story['title'],
                                    "collaborative_story",
                                    story['genre']
                                )
                                st.success("Contribution added!")
                                del st.session_state['contributing_to']
                                st.rerun()
                        else:
                            st.warning("Please enter some content")
        else:
            st.info("No active stories yet. Create the first one!")
    
    with tab2:
        st.subheader("Create a New Collaborative Story")
        
        title = st.text_input("Story Title")
        genre = st.selectbox("Genre", ["Fantasy", "Sci-Fi", "Mystery", "Romance", "Horror"])
        initial_content = st.text_area("Opening Chapter (Start the story)", height=200)
        visibility = st.radio("Visibility", ["public", "private"])
        max_contrib = st.number_input("Max Contributors", min_value=2, max_value=50, value=10)
        
        if st.button("Create Story"):
            if title and initial_content:
                story_id = collab.create_story(
                    title, genre, st.session_state.username,
                    initial_content, visibility, max_contrib
                )
                st.success(f"Story created! ID: {story_id}")
                st.balloons()
            else:
                st.warning("Please fill all fields")
    
    with tab3:
        st.subheader("My Collaborative Stories")
        
        user_stories = collab.get_user_stories(st.session_state.username)
        
        if user_stories:
            for story in user_stories:
                st.write(f"**{story['title']}** - {story['genre']}")
                st.write(f"Role: {story['role']} | Contributions: {story['contributions']}")
                st.markdown("---")
        else:
            st.info("You haven't contributed to any stories yet")

def show_mood_recommendations(books_df):
    """Mood-Based Recommendations Page"""
    st.header("🎭 Mood-Based Recommendations")
    st.write("Get book recommendations based on how you're feeling!")
    
    mood_rec = MoodRecommender()
    
    tab1, tab2 = st.tabs(["😊 Select Mood", "💭 Describe Feeling"])
    
    with tab1:
        st.subheader("How are you feeling?")
        
        moods = mood_rec.get_all_moods()
        
        # Display mood buttons in a grid
        cols = st.columns(5)
        selected_mood = None
        
        for idx, mood in enumerate(moods):
            col = cols[idx % 5]
            mood_info = mood_rec.get_mood_description(mood)
            with col:
                if st.button(f"{mood_info['emoji']} {mood.title()}", key=f"mood_{mood}"):
                    selected_mood = mood
        
        if selected_mood:
            mood_info = mood_rec.get_mood_description(selected_mood)
            
            st.markdown(f"### {mood_info['emoji']} {selected_mood.title()}")
            st.write(mood_info['description'])
            st.info(f"Perfect for: {mood_info['book_types']}")
            
            # Get recommendations
            recommendations = mood_rec.get_mood_recommendations(books_df, selected_mood, 10)
            
            st.subheader("📚 Recommended Books:")
            for idx, book in recommendations.iterrows():
                st.markdown(f"""
                <div class="book-card">
                    <h4>📖 {book['Title']}</h4>
                    <p><strong>Author:</strong> {book['Author']}</p>
                    <p><strong>Category:</strong> {book['Bookshelf']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                title = book.get('Title', '')
                author = book.get('Author', '')
                html_file = (book.get('HTML_Path') or '').strip()
                link = book.get('Link', '')
                
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    # Generate PDF on-the-fly for download button
                    try:
                        # Quick metadata PDF for immediate download
                        base_name = _sanitize_filename(f"{title} - {author}" if author else title)
                        pdf_filename = f"{base_name}.pdf"
                        
                        # Create a simple PDF immediately (metadata only for speed)
                        # User can get full content from Book Catalog if needed
                        pdf_bytes = create_pdf_bytes(title, author, link, None)
                        
                        st.download_button(
                            "📥 Download PDF",
                            data=pdf_bytes,
                            file_name=pdf_filename,
                            mime="application/pdf",
                            key=f"dl_mood_{idx}",
                            use_container_width=True,
                            help="Quick download - For full book content, visit Book Catalog"
                        )
                    except Exception as e:
                        st.button("📥 Download PDF", disabled=True, key=f"btn_mood_{idx}", use_container_width=True)
                
                with col2:
                    # Read Online button
                    if html_file and html_file.strip():
                        st.link_button("📖 Read Online", html_file, use_container_width=True, type="primary")
                    elif link and link.strip():
                        html_url = get_gutenberg_html_url(link)
                        st.link_button("📖 Read Online", html_url, use_container_width=True, type="primary")
                    else:
                        st.button("📖 Read Online", disabled=True, key=f"read_mood_{idx}", help="No online link available", use_container_width=True)
                
                with col3:
                    if st.session_state.logged_in:
                        if st.button("🔖 Bookmark", key=f"bookmark_mood_{idx}", use_container_width=True):
                            save_bookmark(book)
                            st.success("Bookmarked!")
            
            # Reading activity suggestion
            activity = mood_rec.suggest_reading_activity(selected_mood)
            st.markdown("### 📖 Reading Suggestions:")
            st.write(f"**Duration:** {activity['duration']}")
            st.write(f"**Environment:** {activity['environment']}")
            st.write(f"**Tip:** {activity['suggestion']}")
    
    with tab2:
        st.subheader("Describe How You Feel")
        
        feeling_text = st.text_area("Tell me how you're feeling today...",
                                    placeholder="E.g., I'm feeling really excited and energetic today!",
                                    height=100)
        
        if st.button("Get Recommendations"):
            if feeling_text:
                detected_mood = mood_rec.detect_mood_from_text(feeling_text)
                mood_info = mood_rec.get_mood_description(detected_mood)
                
                st.success(f"Detected mood: {mood_info['emoji']} {detected_mood.title()}")
                st.write(mood_info['description'])
                
                recommendations = mood_rec.get_mood_recommendations(books_df, detected_mood, 8)
                
                st.subheader("📚 Recommended Books:")
                for idx, book in recommendations.iterrows():
                    st.markdown(f"""
                    <div class="book-card">
                        <h4>📖 {book['Title']}</h4>
                        <p><strong>Author:</strong> {book['Author']}</p>
                        <p><strong>Category:</strong> {book.get('Bookshelf', 'General')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    title = book.get('Title', '')
                    author = book.get('Author', '')
                    html_file = (book.get('HTML_Path') or '').strip()
                    link = book.get('Link', '')
                    
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        # Generate PDF on-the-fly for download button
                        try:
                            # Quick metadata PDF for immediate download
                            base_name = _sanitize_filename(f"{title} - {author}" if author else title)
                            pdf_filename = f"{base_name}.pdf"
                            
                            # Create a simple PDF immediately (metadata only for speed)
                            pdf_bytes = create_pdf_bytes(title, author, link, None)
                            
                            st.download_button(
                                "📥 Download PDF",
                                data=pdf_bytes,
                                file_name=pdf_filename,
                                mime="application/pdf",
                                key=f"dl_mood_text_{idx}",
                                use_container_width=True,
                                help="Quick download - For full book content, visit Book Catalog"
                            )
                        except Exception as e:
                            st.button("📥 Download PDF", disabled=True, key=f"btn_mood_text_{idx}", use_container_width=True)
                    
                    with col2:
                        # Read Online button
                        if html_file and html_file.strip():
                            st.link_button("📖 Read Online", html_file, use_container_width=True, type="primary")
                        elif link and link.strip():
                            html_url = get_gutenberg_html_url(link)
                            st.link_button("📖 Read Online", html_url, use_container_width=True, type="primary")
                        else:
                            st.button("📖 Read Online", disabled=True, key=f"read_mood_text_{idx}", help="No online link available", use_container_width=True)
                    
                    with col3:
                        if st.session_state.logged_in:
                            if st.button("🔖 Bookmark", key=f"bookmark_mood_text_{idx}", use_container_width=True):
                                save_bookmark(book)
                                st.success("Bookmarked!")

            else:
                st.warning("Please describe how you're feeling")

def show_achievements():
    """Gamification and Achievements Page"""
    st.header("🏆 Achievements & Gamification")
    
    if not st.session_state.logged_in:
        st.warning("Please login to view your achievements")
        return
    
    gamification = GamificationSystem()
    user_stats = gamification.get_user_stats(st.session_state.username)
    
    if not user_stats:
        st.info("Start reading to earn achievements!")
        return
    
    # User Level and XP
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-card"><h2>Level {user_stats["level"]}</h2><p>Your Level</p></div>',
                   unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><h2>{user_stats["experience_points"]}</h2><p>Experience Points</p></div>',
                   unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><h2>{user_stats["current_streak"]} 🔥</h2><p>Current Streak</p></div>',
                   unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-card"><h2>{user_stats["books_read"]}</h2><p>Books Read</p></div>',
                   unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(["🏅 Badges", "📊 Progress", "🎯 Challenges", "🏆 Leaderboard"])
    
    with tab1:
        st.subheader("Your Badges")
        
        if user_stats["badges"]:
            cols = st.columns(4)
            for idx, badge in enumerate(user_stats["badges"]):
                col = cols[idx % 4]
                with col:
                    st.markdown(f"""
                    <div class="badge-card">
                        <h2>{badge['icon']}</h2>
                        <h4>{badge['name']}</h4>
                        <p>{badge['earned_date']}</p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Start reading to earn badges!")
    
    with tab2:
        st.subheader("Achievement Progress")
        
        analytics = DataAnalytics()
        progress = analytics.get_achievement_progress(st.session_state.username)
        
        for category, milestones in progress.items():
            st.write(f"### {category}")
            for milestone in milestones:
                status = "✅" if milestone['earned'] else "🔒"
                st.write(f"{status} **{milestone['target']}** - Progress: {milestone['progress']:.1f}%")
                st.progress(milestone['progress'] / 100)
    
    with tab3:
        st.subheader("Active Challenges")
        
        challenges = gamification.get_available_challenges()
        
        if challenges:
            for challenge in challenges:
                st.markdown(f"""
                <div class="story-card">
                    <h3>🎯 {challenge['title']}</h3>
                    <p>{challenge['description']}</p>
                    <p><strong>Target:</strong> {challenge['target']} | <strong>Reward:</strong> {challenge['reward']} XP</p>
                    <p><strong>Ends:</strong> {challenge['end_date']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("Join Challenge", key=f"join_{challenge['challenge_id']}"):
                    gamification.join_challenge(st.session_state.username, challenge['challenge_id'])
                    st.success("Joined challenge!")
        else:
            st.info("No active challenges at the moment")
    
    with tab4:
        st.subheader("Top Readers Leaderboard")
        
        leaderboard = gamification.get_leaderboard(10)
        
        for leader in leaderboard:
            medal = "🥇" if leader['rank'] == 1 else "🥈" if leader['rank'] == 2 else "🥉" if leader['rank'] == 3 else f"{leader['rank']}."
            st.write(f"{medal} **{leader['username']}** - Level {leader['level']} | {leader['xp']} XP | {leader['books_read']} books | {leader['streak']} day streak")

def show_analytics_dashboard(books_df):
    """Data Analytics Dashboard"""
    st.header("📊 Analytics Dashboard")
    
    # Initialize systems that manage their own tables
    GamificationSystem()  # Creates gamification tables
    CollaborativeStory()  # Creates collaborative stories tables
    analytics = DataAnalytics()
    
    tab1, tab2, tab3 = st.tabs(["📈 Platform Stats", "👤 My Analytics", "📚 Book Trends"])
    
    with tab1:
        st.subheader("Platform Statistics")
        
        platform_stats = analytics.get_platform_statistics()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Users", platform_stats['total_users'])
            st.metric("Active Users (7d)", platform_stats['active_users_7d'])
        with col2:
            st.metric("Books Read", platform_stats['books_read'])
            st.metric("Total Activities", platform_stats['total_activities'])
        with col3:
            st.metric("Badges Earned", platform_stats['badges_earned'])
            st.metric("Collaborative Stories", platform_stats['collaborative_stories'])
        
        # Catalog insights
        st.markdown("---")
        st.subheader("Book Catalog Insights")
        catalog_insights = analytics.get_recommendations_insights(books_df)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Books in Catalog", catalog_insights['total_books'])
            st.metric("Total Authors", catalog_insights['total_authors'])
        with col2:
            st.metric("Total Categories", catalog_insights['total_categories'])
            st.metric("Most Popular Category", catalog_insights['most_popular_category'])
    
    with tab2:
        if not st.session_state.logged_in:
            st.warning("Please login to view your analytics")
        else:
            st.subheader("Your Reading Analytics")
            
            # Reading trends
            trends = analytics.get_reading_trends(st.session_state.username, 30)
            st.write(f"**Total Activities (30 days):** {trends['total_activities']}")
            st.write(f"**Average Daily Reading:** {trends['avg_daily_reading']:.1f} minutes")
            
            # Genre distribution
            st.markdown("---")
            genre_dist = analytics.get_genre_distribution(st.session_state.username)
            if genre_dist['genres']:
                st.subheader("Your Genre Preferences")
                for genre in genre_dist['genres'][:5]:
                    st.write(f"**{genre['genre']}:** {genre['count']} reads")
            
            # Comparison with platform
            st.markdown("---")
            comparison = analytics.get_user_comparison(st.session_state.username)
            if comparison:
                st.subheader("How You Compare")
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Your Stats:**")
                    st.write(f"Books Read: {comparison['user']['books_read']}")
                    st.write(f"Streak: {comparison['user']['streak']} days")
                with col2:
                    st.write("**Platform Average:**")
                    st.write(f"Books Read: {comparison['platform_average']['books_read']}")
                    st.write(f"Streak: {comparison['platform_average']['streak']} days")
                
                st.info(f"You're in the top {100 - comparison['percentile']['percentile']:.1f}% of readers!")
    
    with tab3:
        st.subheader("Popular Books")
        
        popular = analytics.get_popular_books(10, 30)
        if popular:
            for idx, book in enumerate(popular, 1):
                st.write(f"{idx}. **{book['book_title']}** ({book['genre']}) - {book['read_count']} reads by {book['unique_readers']} users")
        else:
            st.info("No data available yet")

# Import remaining functions from original app
def show_chat_assistant(books_df):
    """AI Chat Assistant"""
    st.header("💬 AI Chat Assistant")
    st.write("Ask me anything about books, literature, or get recommendations!")
    
    chat_assistant = ChatAssistant()
    
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    if prompt := st.chat_input("Ask about books..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = chat_assistant.get_response(prompt, books_df)
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

def show_summarizer(books_df):
    """Book text summarization"""
    st.header("🧾 Book Summary Generator")
    
    summarizer = BookSummarizer()
    
    option = st.radio("Choose input method:", ["Select from catalog", "Enter custom text"])
    
    if option == "Select from catalog":
        book_titles = books_df['Title'].tolist()
        selected_book = st.selectbox("Select a book:", book_titles[:100])
        
        if st.button("Generate Summary"):
            with st.spinner("Generating summary..."):
                book_info = books_df[books_df['Title'] == selected_book].iloc[0]
                text = f"{book_info['Title']} by {book_info['Author']}"
                summary = summarizer.summarize(text)
                
                st.subheader("📝 Summary")
                st.write(summary)
    else:
        text_input = st.text_area("Enter text to summarize:", height=200)
        if st.button("Summarize"):
            if text_input:
                with st.spinner("Generating summary..."):
                    summary = summarizer.summarize(text_input)
                    st.subheader("📝 Summary")
                    st.write(summary)

def show_translator(books_df):
    """Book translation feature"""
    st.header("🌍 Book Translator")
    
    translator = BookTranslator()
    
    # Input method selection
    input_method = st.radio("Choose input method:", ["📝 Text Input", "📄 Upload PDF"])
    
    text_to_translate = ""
    
    if input_method == "📝 Text Input":
        text_to_translate = st.text_area("Enter text to translate:", height=150)
    else:
        uploaded_file = st.file_uploader("Upload PDF file", type=['pdf'])
        
        # Page limit option
        extract_all = st.checkbox("📚 Extract all pages (for full book translation)", value=False)
        
        if uploaded_file is not None:
            try:
                with st.spinner("Extracting text from PDF..."):
                    # Extract text from PDF
                    import PyPDF2
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    total_pages = len(pdf_reader.pages)
                    extracted_text = []
                    
                    # Set page limit based on user choice
                    if extract_all:
                        max_pages = total_pages
                        st.info(f"📖 Extracting all {total_pages} pages. This may take a moment...")
                    else:
                        max_pages = min(10, total_pages)
                        if total_pages > 10:
                            st.warning(f"⚠️ Only extracting first 10 pages of {total_pages}. Check 'Extract all pages' for full book.")
                    
                    # Extract with progress
                    progress_bar = st.progress(0)
                    for page_num in range(max_pages):
                        page = pdf_reader.pages[page_num]
                        extracted_text.append(page.extract_text())
                        progress_bar.progress((page_num + 1) / max_pages)
                    
                    text_to_translate = "\n".join(extracted_text)
                    
                    st.success(f"✅ Extracted text from {max_pages} page(s) ({len(text_to_translate):,} characters)")
                    
                    # Show preview of extracted text
                    with st.expander("📖 Preview extracted text"):
                        preview_text = text_to_translate[:2000] + "..." if len(text_to_translate) > 2000 else text_to_translate
                        st.text_area("Extracted text:", preview_text, height=200, disabled=True)
                    
            except Exception as e:
                st.error(f"Error extracting text from PDF: {e}")
                st.info("Please make sure the PDF contains extractable text (not scanned images)")
    
    # Language selection
    col1, col2 = st.columns(2)
    
    # Get all supported languages from translator
    supported_langs = translator.get_supported_languages()
    lang_codes = list(supported_langs.keys())
    lang_names = [f"{code} - {name}" for code, name in supported_langs.items()]
    
    with col1:
        source_options = ["auto - Auto Detect"] + lang_names
        source_selection = st.selectbox("From Language", source_options)
        source_lang = source_selection.split(" - ")[0]
    
    with col2:
        target_selection = st.selectbox("To Language", lang_names, index=lang_codes.index('hi') if 'hi' in lang_codes else 0)
        target_lang = target_selection.split(" - ")[0]
    
    if st.button("🔄 Translate", type="primary"):
        if text_to_translate and text_to_translate.strip():
            # Show text length info
            char_count = len(text_to_translate)
            st.info(f"📊 Text length: {char_count:,} characters")
            
            # Calculate estimated chunks
            chunk_size = 4500
            estimated_chunks = (char_count // chunk_size) + 1 if char_count > chunk_size else 1
            
            if estimated_chunks > 1:
                st.info(f"📦 This will be translated in approximately {estimated_chunks} chunks.")
                st.warning("⏱️ Large translations may take several minutes. Each chunk has 3 retry attempts if network errors occur.")
            
            # Create progress bar for long translations
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(current, total):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"Translating chunk {current} of {total}... (with retry on errors)")
            
            try:
                # Translate with progress tracking
                if char_count > chunk_size:
                    status_text.text("Starting translation...")
                    translated = translator.translate_long_text(
                        text_to_translate, 
                        source_lang, 
                        target_lang,
                        progress_callback=update_progress
                    )
                else:
                    status_text.text("Translating...")
                    translated = translator.translate(text_to_translate, source_lang, target_lang)
                
                progress_bar.progress(1.0)
                status_text.text("✅ Translation complete!")
                
                # Check if translation contains error messages
                if "Translation failed for chunk" in translated:
                    st.warning("⚠️ Some chunks failed to translate due to network errors. Partial translation shown below.")
                else:
                    st.success(f"✨ Successfully translated {char_count:,} characters!")
                
                # Show translation
                st.subheader("✨ Translation Result")
                st.write(translated)
                
                # Download options
                col1, col2 = st.columns(2)
                
                with col1:
                    # Download as text
                    st.download_button(
                        "📥 Download as TXT",
                        data=translated,
                        file_name=f"translation_{target_lang}.txt",
                        mime="text/plain"
                    )
                
                with col2:
                    # Download as PDF
                    try:
                        # Get target language name
                        target_lang_name = translator.get_supported_languages().get(target_lang, target_lang)
                        
                        # Create PDF with translated text
                        pdf_bytes = create_pdf_bytes(
                            title=f"Translated Book ({target_lang_name})",
                            author="AI Virtual Library",
                            link="",
                            full_text=translated
                        )
                        
                        st.download_button(
                            "📥 Download as PDF",
                            data=pdf_bytes,
                            file_name=f"translation_{target_lang}.pdf",
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"PDF generation failed: {e}")
                
            except Exception as e:
                st.error(f"Translation failed: {e}")
                st.info("Try reducing the text length or translating in smaller sections.")
        else:
            st.warning("Please enter text or upload a PDF file to translate")

def show_sentiment_analysis(books_df):
    """Sentiment analysis of book reviews or text"""
    st.header("📈 Sentiment Analysis")
    
    analyzer = SentimentAnalyzer()
    
    st.write("Analyze the sentiment of book reviews or any text")
    
    text_input = st.text_area("Enter text for sentiment analysis:", height=150)
    
    if st.button("Analyze Sentiment"):
        if text_input:
            with st.spinner("Analyzing..."):
                sentiment = analyzer.analyze(text_input)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("😊 Overall Sentiment")
                    st.write(f"**{sentiment['label']}**")
                    st.write(f"Confidence: {sentiment['score']:.2%}")
                
                with col2:
                    st.subheader("📊 Sentiment Scores")
                    st.write(f"Positive: {sentiment.get('positive', 0):.2%}")
                    st.write(f"Neutral: {sentiment.get('neutral', 0):.2%}")
                    st.write(f"Negative: {sentiment.get('negative', 0):.2%}")

def show_recommendations(books_df):
    """Personalized book recommendations"""
    st.header("🎯 Book Recommendations")
    
    recommender = BookRecommender()
    
    st.write("Get personalized book recommendations based on your interests")
    
    method = st.radio("Recommendation method:", 
                      ["By Genre", "By Author", "By Book Title"])
    
    if method == "By Genre":
        genres = sorted(books_df['Bookshelf'].dropna().unique().tolist())
        selected_genre = st.selectbox("Select your favorite genre:", genres)
        
        if st.button("Get Recommendations"):
            recommendations = recommender.recommend_by_genre(books_df, selected_genre)
            display_recommendations(recommendations)
    
    elif method == "By Author":
        authors = sorted(books_df['Author'].dropna().unique().tolist())[:500]
        selected_author = st.selectbox("Select your favorite author:", authors)
        
        if st.button("Get Recommendations"):
            recommendations = recommender.recommend_by_author(books_df, selected_author)
            display_recommendations(recommendations)
    
    else:
        book_titles = books_df['Title'].tolist()[:500]
        selected_book = st.selectbox("Select a book you like:", book_titles)
        
        if st.button("Get Recommendations"):
            recommendations = recommender.recommend_by_book(books_df, selected_book)
            display_recommendations(recommendations)

def display_recommendations(recommendations):
    """Display recommended books"""
    st.subheader("📚 Recommended Books for You")
    
    for idx, book in recommendations.iterrows():
        with st.container():
            st.markdown(f"""
            <div class="book-card">
                <h4>📖 {book['Title']}</h4>
                <p><strong>Author:</strong> {book['Author']}</p>
                <p><strong>Category:</strong> {book['Bookshelf']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            title = book.get('Title', '')
            author = book.get('Author', '')
            html_file = (book.get('HTML_Path') or '').strip()
            link = book.get('Link', '')
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                # When Download PDF is clicked, fetch full content and create PDF
                if st.button("📥 Download PDF", key=f"download_rec_{idx}", use_container_width=True):
                    try:
                        with st.spinner("Fetching book content and creating PDF with full text..."):
                            html_content = None
                            book_text = None
                            pdf_bytes = None
                            
                            # Priority 1: Try to get HTML content from dataset
                            if html_file:
                                st.info(f"📄 Reading HTML file...")
                                try:
                                    content, _, mime_type = get_book_content(
                                        title=title,
                                        author=author,
                                        link=link,
                                        html_path=html_file
                                    )
                                    if content:
                                        html_content = content.decode('utf-8', errors='ignore') if isinstance(content, (bytes, bytearray)) else str(content)
                                        st.success(f"✅ Loaded HTML content ({len(html_content):,} characters)")
                                except Exception as html_error:
                                    st.warning(f"⚠️ Could not load HTML file: {str(html_error)}")
                            
                            # Priority 2: If we have HTML content, extract text and create PDF
                            if html_content:
                                st.info("📝 Extracting text from HTML...")
                                try:
                                    book_text = extract_text_from_html(html_content)
                                    
                                    if book_text and len(book_text.strip()) > 100:
                                        st.success(f"✅ Extracted {len(book_text):,} characters of text")
                                        st.info("📄 Creating PDF with full book content...")
                                        pdf_bytes = create_pdf_bytes(title, author, link, book_text)
                                    else:
                                        st.warning("⚠️ Extracted text too short, trying Gutenberg...")
                                except Exception as extract_error:
                                    st.warning(f"Text extraction failed: {str(extract_error)}")
                            
                            # Priority 3: Try Gutenberg text format if no HTML or HTML failed
                            if not pdf_bytes and link:
                                st.info("📚 Trying to fetch from Project Gutenberg...")
                                try:
                                    book_text = fetch_gutenberg_text(link)
                                    
                                    if book_text and len(book_text.strip()) > 100:
                                        st.success(f"✅ Fetched {len(book_text):,} characters from Gutenberg")
                                        pdf_bytes = create_pdf_bytes(title, author, link, book_text)
                                except Exception as gutenberg_error:
                                    st.warning(f"Gutenberg fetch failed: {str(gutenberg_error)}")
                            
                            # Last resort: Create metadata-only PDF
                            if not pdf_bytes:
                                st.warning("⚠️ Could not fetch full book content.")
                                st.info("Creating a metadata PDF with book information...")
                                pdf_bytes = create_pdf_bytes(title, author, link, None)
                            
                            # Generate filename and trigger download
                            if pdf_bytes:
                                base_name = _sanitize_filename(f"{title} - {author}" if author else title)
                                pdf_filename = f"{base_name}.pdf"
                                
                                st.download_button(
                                    "📥 Download Complete Book PDF",
                                    data=pdf_bytes,
                                    file_name=pdf_filename,
                                    mime="application/pdf",
                                    key=f"save_rec_{idx}",
                                    use_container_width=True
                                )
                                st.success("✨ PDF ready! Click above to download.")
                            else:
                                st.error("❌ Failed to create PDF")
                                
                    except Exception as e:
                        st.error(f"Error creating PDF: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
            
            with col2:
                # Read Online button
                if html_file and html_file.strip():
                    st.link_button("📖 Read Online", html_file, use_container_width=True, type="primary")
                elif link and link.strip():
                    html_url = get_gutenberg_html_url(link)
                    st.link_button("📖 Read Online", html_url, use_container_width=True, type="primary")
                else:
                    st.button("📖 Read Online", disabled=True, key=f"read_rec_{idx}", help="No online link available", use_container_width=True)
            
            with col3:
                if st.session_state.logged_in:
                    if st.button("🔖 Bookmark", key=f"bookmark_rec_{idx}", use_container_width=True):
                        save_bookmark(book)
                        st.success("Bookmarked!")

def show_user_profile():
    """User profile with reading history"""
    if not st.session_state.logged_in:
        st.warning("Please login to view your profile")
        return
    
    st.header("👤 My Profile")
    
    tab1, tab2 = st.tabs(["📚 Reading History", "🔖 Bookmarks"])
    
    with tab1:
        st.subheader("My Reading History")
        history = get_reading_history(st.session_state.username)
        if history:
            for item in history:
                st.write(f"**{item[0]}** by {item[1]} - Rating: {'⭐' * item[2]}")
        else:
            st.info("No reading history yet")
    
    with tab2:
        st.subheader("My Bookmarks")
        bookmarks = get_bookmarks(st.session_state.username)
        if bookmarks:
            for idx, bookmark in enumerate(bookmarks):
                st.write(f"📖 **{bookmark[0]}** by {bookmark[1]}")
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    pdf_bytes = create_pdf_bytes(bookmark[0], bookmark[1], bookmark[2])
                    filename = make_filename(bookmark[0], bookmark[1])
                    st.download_button(
                        "📥 Download PDF",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        key=f"download_bm_{idx}_{filename}"
                    )
                with col2:
                    # Read Online button
                    html_url = get_gutenberg_html_url(bookmark[2])
                    if html_url:
                        st.link_button("📖 Read Online", html_url, use_container_width=True)
                
                st.divider()
        else:
            st.info("No bookmarks yet")

def save_bookmark(book_row):
    """Save bookmark to database"""
    if not st.session_state.logged_in:
        return
    
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    c.execute('''INSERT INTO bookmarks VALUES (?, ?, ?, ?, ?, ?)''',
              (st.session_state.username, book_row['Title'], book_row['Author'],
               book_row['Link'], book_row['Bookshelf'], datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

def get_reading_history(username):
    """Get user reading history"""
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    c.execute('SELECT book_title, author, rating FROM reading_history WHERE user_id = ?', (username,))
    history = c.fetchall()
    conn.close()
    return history

def get_bookmarks(username):
    """Get user bookmarks"""
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    c.execute('SELECT book_title, author, link FROM bookmarks WHERE user_id = ?', (username,))
    bookmarks = c.fetchall()
    conn.close()
    return bookmarks

if __name__ == "__main__":
    main()
