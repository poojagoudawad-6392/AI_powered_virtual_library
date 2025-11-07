"""
Gamification Module
Reading challenges, badges, and streaks to boost user engagement
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

class GamificationSystem:
    """Manage gamification features: badges, challenges, streaks"""
    
    # Badge definitions
    BADGES = {
        "first_book": {
            "name": "First Steps",
            "description": "Read your first book",
            "icon": "📖",
            "requirement": 1
        },
        "bookworm": {
            "name": "Bookworm",
            "description": "Read 10 books",
            "icon": "🐛",
            "requirement": 10
        },
        "scholar": {
            "name": "Scholar",
            "description": "Read 25 books",
            "icon": "🎓",
            "requirement": 25
        },
        "librarian": {
            "name": "Librarian",
            "description": "Read 50 books",
            "icon": "👓",
            "requirement": 50
        },
        "master_reader": {
            "name": "Master Reader",
            "description": "Read 100 books",
            "icon": "👑",
            "requirement": 100
        },
        "streak_7": {
            "name": "Week Warrior",
            "description": "7-day reading streak",
            "icon": "🔥",
            "requirement": 7
        },
        "streak_30": {
            "name": "Monthly Master",
            "description": "30-day reading streak",
            "icon": "⭐",
            "requirement": 30
        },
        "streak_100": {
            "name": "Century Streak",
            "description": "100-day reading streak",
            "icon": "💯",
            "requirement": 100
        },
        "genre_explorer": {
            "name": "Genre Explorer",
            "description": "Read from 5 different genres",
            "icon": "🌍",
            "requirement": 5
        },
        "night_owl": {
            "name": "Night Owl",
            "description": "Read 10 books after 10 PM",
            "icon": "🦉",
            "requirement": 10
        },
        "early_bird": {
            "name": "Early Bird",
            "description": "Read 10 books before 8 AM",
            "icon": "🐦",
            "requirement": 10
        },
        "speed_reader": {
            "name": "Speed Reader",
            "description": "Complete 5 books in one week",
            "icon": "⚡",
            "requirement": 5
        },
        "review_master": {
            "name": "Review Master",
            "description": "Write 20 book reviews",
            "icon": "✍️",
            "requirement": 20
        },
        "social_reader": {
            "name": "Social Reader",
            "description": "Contribute to 5 collaborative stories",
            "icon": "👥",
            "requirement": 5
        }
    }
    
    def __init__(self, db_path: str = 'library.db'):
        """Initialize gamification system"""
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables for gamification"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # User stats table
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
        
        # User badges table
        c.execute('''CREATE TABLE IF NOT EXISTS user_badges
                     (username TEXT,
                      badge_id TEXT,
                      earned_date TEXT,
                      PRIMARY KEY (username, badge_id))''')
        
        # Reading activities table
        c.execute('''CREATE TABLE IF NOT EXISTS reading_activities
                     (activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT,
                      book_title TEXT,
                      activity_type TEXT,
                      timestamp TEXT,
                      genre TEXT,
                      duration_minutes INTEGER)''')
        
        # Challenges table
        c.execute('''CREATE TABLE IF NOT EXISTS challenges
                     (challenge_id TEXT PRIMARY KEY,
                      title TEXT,
                      description TEXT,
                      challenge_type TEXT,
                      target_value INTEGER,
                      start_date TEXT,
                      end_date TEXT,
                      reward_points INTEGER,
                      status TEXT)''')
        
        # User challenges table
        c.execute('''CREATE TABLE IF NOT EXISTS user_challenges
                     (username TEXT,
                      challenge_id TEXT,
                      progress INTEGER DEFAULT 0,
                      status TEXT DEFAULT 'active',
                      completed_date TEXT,
                      PRIMARY KEY (username, challenge_id))''')
        
        conn.commit()
        conn.close()
    
    def log_reading_activity(self, username: str, book_title: str, 
                           activity_type: str = "read", genre: str = "General",
                           duration_minutes: int = 30):
        """
        Log a reading activity
        
        Args:
            username: User's username
            book_title: Book title
            activity_type: Type of activity (read, review, bookmark, etc.)
            genre: Book genre
            duration_minutes: Reading duration
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Log activity
        c.execute('''INSERT INTO reading_activities 
                     (username, book_title, activity_type, timestamp, genre, duration_minutes)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (username, book_title, activity_type,
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   genre, duration_minutes))
        
        # Update user stats
        self._update_user_stats(username, c)
        
        # Check and award badges
        self._check_badges(username, c)
        
        conn.commit()
        conn.close()
    
    def _update_user_stats(self, username: str, cursor):
        """Update user statistics"""
        # Ensure user stats exist
        cursor.execute('SELECT username FROM user_stats WHERE username = ?', (username,))
        if not cursor.fetchone():
            cursor.execute('''INSERT INTO user_stats (username) VALUES (?)''', (username,))
        
        # Update streak
        cursor.execute('SELECT last_activity_date, current_streak FROM user_stats WHERE username = ?',
                      (username,))
        result = cursor.fetchone()
        
        if result and result[0]:
            last_date = datetime.strptime(result[0], "%Y-%m-%d").date()
            today = datetime.now().date()
            days_diff = (today - last_date).days
            
            if days_diff == 0:
                # Same day, no streak change
                pass
            elif days_diff == 1:
                # Consecutive day, increment streak
                new_streak = result[1] + 1
                cursor.execute('''UPDATE user_stats 
                                SET current_streak = ?,
                                    longest_streak = MAX(longest_streak, ?),
                                    last_activity_date = ?
                                WHERE username = ?''',
                             (new_streak, new_streak, today.strftime("%Y-%m-%d"), username))
            else:
                # Streak broken, reset to 1
                cursor.execute('''UPDATE user_stats 
                                SET current_streak = 1,
                                    last_activity_date = ?
                                WHERE username = ?''',
                             (today.strftime("%Y-%m-%d"), username))
        else:
            # First activity
            cursor.execute('''UPDATE user_stats 
                            SET current_streak = 1,
                                longest_streak = 1,
                                last_activity_date = ?
                            WHERE username = ?''',
                         (datetime.now().strftime("%Y-%m-%d"), username))
        
        # Update XP and level
        cursor.execute('''UPDATE user_stats 
                        SET experience_points = experience_points + 10
                        WHERE username = ?''', (username,))
        
        cursor.execute('SELECT experience_points FROM user_stats WHERE username = ?',
                      (username,))
        xp = cursor.fetchone()[0]
        new_level = (xp // 100) + 1
        
        cursor.execute('UPDATE user_stats SET level = ? WHERE username = ?',
                      (new_level, username))
    
    def _check_badges(self, username: str, cursor):
        """Check and award eligible badges"""
        # Get user stats
        cursor.execute('''SELECT total_books_read, current_streak, longest_streak 
                         FROM user_stats WHERE username = ?''', (username,))
        stats = cursor.fetchone()
        
        if not stats:
            return
        
        books_read, current_streak, longest_streak = stats
        
        # Check book count badges
        book_badges = [
            ("first_book", 1),
            ("bookworm", 10),
            ("scholar", 25),
            ("librarian", 50),
            ("master_reader", 100)
        ]
        
        for badge_id, requirement in book_badges:
            if books_read >= requirement:
                self._award_badge(username, badge_id, cursor)
        
        # Check streak badges
        streak_badges = [
            ("streak_7", 7),
            ("streak_30", 30),
            ("streak_100", 100)
        ]
        
        for badge_id, requirement in streak_badges:
            if longest_streak >= requirement:
                self._award_badge(username, badge_id, cursor)
        
        # Check genre diversity
        cursor.execute('''SELECT COUNT(DISTINCT genre) FROM reading_activities 
                         WHERE username = ?''', (username,))
        genre_count = cursor.fetchone()[0]
        if genre_count >= 5:
            self._award_badge(username, "genre_explorer", cursor)
    
    def _award_badge(self, username: str, badge_id: str, cursor):
        """Award a badge to user if not already earned"""
        cursor.execute('''SELECT badge_id FROM user_badges 
                         WHERE username = ? AND badge_id = ?''',
                      (username, badge_id))
        
        if not cursor.fetchone():
            cursor.execute('''INSERT INTO user_badges VALUES (?, ?, ?)''',
                         (username, badge_id,
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            # Award bonus XP
            cursor.execute('''UPDATE user_stats 
                            SET experience_points = experience_points + 50
                            WHERE username = ?''', (username,))
    
    def get_user_stats(self, username: str) -> Dict:
        """Get user statistics and progress"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get stats
        c.execute('SELECT * FROM user_stats WHERE username = ?', (username,))
        stats = c.fetchone()
        
        if not stats:
            conn.close()
            return {}
        
        # Get badges
        c.execute('''SELECT badge_id, earned_date FROM user_badges 
                    WHERE username = ? ORDER BY earned_date DESC''', (username,))
        badges = c.fetchall()
        
        # Get recent activities
        c.execute('''SELECT book_title, activity_type, timestamp FROM reading_activities
                    WHERE username = ? ORDER BY timestamp DESC LIMIT 10''', (username,))
        activities = c.fetchall()
        
        conn.close()
        
        return {
            "username": stats[0],
            "books_read": stats[1],
            "pages_read": stats[2],
            "reading_time": stats[3],
            "current_streak": stats[4],
            "longest_streak": stats[5],
            "last_activity": stats[6],
            "level": stats[7],
            "experience_points": stats[8],
            "badges": [
                {
                    "id": b[0],
                    "name": self.BADGES[b[0]]["name"],
                    "icon": self.BADGES[b[0]]["icon"],
                    "earned_date": b[1]
                } for b in badges if b[0] in self.BADGES
            ],
            "recent_activities": [
                {
                    "book": a[0],
                    "type": a[1],
                    "timestamp": a[2]
                } for a in activities
            ]
        }
    
    def create_challenge(self, challenge_id: str, title: str, description: str,
                        challenge_type: str, target_value: int, 
                        duration_days: int, reward_points: int = 100):
        """Create a new reading challenge"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        start_date = datetime.now()
        end_date = start_date + timedelta(days=duration_days)
        
        c.execute('''INSERT OR IGNORE INTO challenges VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (challenge_id, title, description, challenge_type, target_value,
                   start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"),
                   reward_points, "active"))
        
        conn.commit()
        conn.close()
    
    def get_available_challenges(self) -> List[Dict]:
        """Get all active challenges"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''SELECT * FROM challenges WHERE status = 'active' 
                    AND end_date >= ?''', (datetime.now().strftime("%Y-%m-%d"),))
        challenges = c.fetchall()
        conn.close()
        
        return [
            {
                "challenge_id": ch[0],
                "title": ch[1],
                "description": ch[2],
                "type": ch[3],
                "target": ch[4],
                "end_date": ch[6],
                "reward": ch[7]
            } for ch in challenges
        ]
    
    def join_challenge(self, username: str, challenge_id: str):
        """User joins a challenge"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''INSERT OR IGNORE INTO user_challenges 
                    (username, challenge_id) VALUES (?, ?)''',
                  (username, challenge_id))
        
        conn.commit()
        conn.close()
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top readers leaderboard"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''SELECT username, level, experience_points, total_books_read, 
                           current_streak FROM user_stats 
                    ORDER BY experience_points DESC LIMIT ?''', (limit,))
        
        leaders = c.fetchall()
        conn.close()
        
        return [
            {
                "rank": idx + 1,
                "username": leader[0],
                "level": leader[1],
                "xp": leader[2],
                "books_read": leader[3],
                "streak": leader[4]
            } for idx, leader in enumerate(leaders)
        ]
