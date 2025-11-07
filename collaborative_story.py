"""
Collaborative Storytelling Module
Enables multiple users to co-author interactive stories with AI assistance
"""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import json

class CollaborativeStory:
    """Manage collaborative story writing sessions"""
    
    def __init__(self, db_path: str = 'library.db'):
        """Initialize collaborative story manager"""
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables for collaborative stories"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Stories table
        c.execute('''CREATE TABLE IF NOT EXISTS collaborative_stories
                     (story_id TEXT PRIMARY KEY,
                      title TEXT,
                      genre TEXT,
                      creator TEXT,
                      created_date TEXT,
                      status TEXT,
                      visibility TEXT,
                      max_contributors INTEGER)''')
        
        # Story content/chapters table
        c.execute('''CREATE TABLE IF NOT EXISTS story_content
                     (content_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      story_id TEXT,
                      chapter_number INTEGER,
                      content TEXT,
                      author TEXT,
                      added_date TEXT,
                      word_count INTEGER,
                      FOREIGN KEY (story_id) REFERENCES collaborative_stories(story_id))''')
        
        # Contributors table
        c.execute('''CREATE TABLE IF NOT EXISTS story_contributors
                     (story_id TEXT,
                      username TEXT,
                      role TEXT,
                      joined_date TEXT,
                      contribution_count INTEGER,
                      PRIMARY KEY (story_id, username))''')
        
        # Story comments/feedback table
        c.execute('''CREATE TABLE IF NOT EXISTS story_comments
                     (comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      story_id TEXT,
                      username TEXT,
                      comment TEXT,
                      timestamp TEXT)''')
        
        conn.commit()
        conn.close()
    
    def create_story(self, title: str, genre: str, creator: str, 
                    initial_content: str, visibility: str = "public",
                    max_contributors: int = 10) -> str:
        """
        Create a new collaborative story
        
        Args:
            title: Story title
            genre: Story genre
            creator: Username of creator
            initial_content: Initial story content
            visibility: 'public' or 'private'
            max_contributors: Maximum number of contributors
        
        Returns:
            story_id
        """
        story_id = f"{creator}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Create story
        c.execute('''INSERT INTO collaborative_stories VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (story_id, title, genre, creator, 
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   "active", visibility, max_contributors))
        
        # Add initial content
        c.execute('''INSERT INTO story_content 
                     (story_id, chapter_number, content, author, added_date, word_count)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (story_id, 1, initial_content, creator,
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   len(initial_content.split())))
        
        # Add creator as contributor
        c.execute('''INSERT INTO story_contributors VALUES (?, ?, ?, ?, ?)''',
                  (story_id, creator, "creator", 
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1))
        
        conn.commit()
        conn.close()
        
        return story_id
    
    def add_contribution(self, story_id: str, username: str, content: str,
                        chapter_number: Optional[int] = None) -> bool:
        """
        Add a contribution to a collaborative story
        
        Args:
            story_id: Story ID
            username: Contributor username
            content: Story content to add
            chapter_number: Chapter number (auto-increments if None)
        
        Returns:
            Success status
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Check if user is a contributor
            c.execute('''SELECT username FROM story_contributors 
                        WHERE story_id = ? AND username = ?''',
                     (story_id, username))
            
            if not c.fetchone():
                # Add as new contributor
                c.execute('''INSERT INTO story_contributors VALUES (?, ?, ?, ?, ?)''',
                         (story_id, username, "contributor",
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 0))
            
            # Get next chapter number if not provided
            if chapter_number is None:
                c.execute('''SELECT MAX(chapter_number) FROM story_content 
                            WHERE story_id = ?''', (story_id,))
                result = c.fetchone()
                chapter_number = (result[0] or 0) + 1
            
            # Add content
            c.execute('''INSERT INTO story_content 
                        (story_id, chapter_number, content, author, added_date, word_count)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (story_id, chapter_number, content, username,
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                      len(content.split())))
            
            # Update contribution count
            c.execute('''UPDATE story_contributors 
                        SET contribution_count = contribution_count + 1
                        WHERE story_id = ? AND username = ?''',
                     (story_id, username))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error adding contribution: {e}")
            return False
        finally:
            conn.close()
    
    def get_story(self, story_id: str) -> Optional[Dict]:
        """
        Get full story with all contributions
        
        Args:
            story_id: Story ID
        
        Returns:
            Dictionary with story data
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get story metadata
        c.execute('''SELECT * FROM collaborative_stories WHERE story_id = ?''',
                 (story_id,))
        story = c.fetchone()
        
        if not story:
            conn.close()
            return None
        
        # Get all content
        c.execute('''SELECT chapter_number, content, author, added_date, word_count
                    FROM story_content WHERE story_id = ? ORDER BY chapter_number''',
                 (story_id,))
        chapters = c.fetchall()
        
        # Get contributors
        c.execute('''SELECT username, role, contribution_count
                    FROM story_contributors WHERE story_id = ?
                    ORDER BY contribution_count DESC''',
                 (story_id,))
        contributors = c.fetchall()
        
        conn.close()
        
        return {
            "story_id": story[0],
            "title": story[1],
            "genre": story[2],
            "creator": story[3],
            "created_date": story[4],
            "status": story[5],
            "visibility": story[6],
            "max_contributors": story[7],
            "chapters": [
                {
                    "chapter": ch[0],
                    "content": ch[1],
                    "author": ch[2],
                    "date": ch[3],
                    "word_count": ch[4]
                } for ch in chapters
            ],
            "contributors": [
                {
                    "username": c[0],
                    "role": c[1],
                    "contributions": c[2]
                } for c in contributors
            ]
        }
    
    def list_active_stories(self, visibility: str = "public") -> List[Dict]:
        """
        List all active collaborative stories
        
        Args:
            visibility: Filter by visibility (public/private/all)
        
        Returns:
            List of story summaries
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        if visibility == "all":
            c.execute('''SELECT story_id, title, genre, creator, created_date, status
                        FROM collaborative_stories WHERE status = 'active'
                        ORDER BY created_date DESC''')
        else:
            c.execute('''SELECT story_id, title, genre, creator, created_date, status
                        FROM collaborative_stories 
                        WHERE status = 'active' AND visibility = ?
                        ORDER BY created_date DESC''', (visibility,))
        
        stories = c.fetchall()
        
        result = []
        for story in stories:
            # Get contributor count
            c.execute('''SELECT COUNT(*) FROM story_contributors 
                        WHERE story_id = ?''', (story[0],))
            contributor_count = c.fetchone()[0]
            
            # Get total word count
            c.execute('''SELECT SUM(word_count) FROM story_content 
                        WHERE story_id = ?''', (story[0],))
            total_words = c.fetchone()[0] or 0
            
            result.append({
                "story_id": story[0],
                "title": story[1],
                "genre": story[2],
                "creator": story[3],
                "created_date": story[4],
                "contributor_count": contributor_count,
                "total_words": total_words
            })
        
        conn.close()
        return result
    
    def add_comment(self, story_id: str, username: str, comment: str) -> bool:
        """
        Add a comment/feedback to a story
        
        Args:
            story_id: Story ID
            username: Commenter username
            comment: Comment text
        
        Returns:
            Success status
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('''INSERT INTO story_comments 
                        (story_id, username, comment, timestamp)
                        VALUES (?, ?, ?, ?)''',
                     (story_id, username, comment,
                      datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding comment: {e}")
            return False
        finally:
            conn.close()
    
    def get_comments(self, story_id: str) -> List[Dict]:
        """Get all comments for a story"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''SELECT username, comment, timestamp FROM story_comments
                    WHERE story_id = ? ORDER BY timestamp DESC''',
                 (story_id,))
        comments = c.fetchall()
        conn.close()
        
        return [
            {
                "username": c[0],
                "comment": c[1],
                "timestamp": c[2]
            } for c in comments
        ]
    
    def get_user_stories(self, username: str) -> List[Dict]:
        """Get all stories a user has contributed to"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''SELECT cs.story_id, cs.title, cs.genre, sc.role, sc.contribution_count
                    FROM collaborative_stories cs
                    JOIN story_contributors sc ON cs.story_id = sc.story_id
                    WHERE sc.username = ?
                    ORDER BY sc.joined_date DESC''',
                 (username,))
        
        stories = c.fetchall()
        conn.close()
        
        return [
            {
                "story_id": s[0],
                "title": s[1],
                "genre": s[2],
                "role": s[3],
                "contributions": s[4]
            } for s in stories
        ]
