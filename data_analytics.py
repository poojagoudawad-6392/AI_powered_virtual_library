"""
Data Analytics Module
Analyze book data, user trends, and generate insights
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import Counter

class DataAnalytics:
    """Analyze library data and user behavior"""
    
    def __init__(self, db_path: str = 'library.db'):
        """Initialize data analytics"""
        self.db_path = db_path
    
    def get_reading_trends(self, username: Optional[str] = None, 
                          days: int = 30) -> Dict:
        """
        Analyze reading trends over time
        
        Args:
            username: Specific user (None for all users)
            days: Number of days to analyze
        
        Returns:
            Dictionary with trend data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get reading activities
            if username:
                query = '''SELECT DATE(timestamp) as date, COUNT(*) as count, 
                                 AVG(duration_minutes) as avg_duration
                          FROM reading_activities 
                          WHERE username = ? AND timestamp >= ?
                          GROUP BY DATE(timestamp)
                          ORDER BY date'''
                params = (username, (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"))
            else:
                query = '''SELECT DATE(timestamp) as date, COUNT(*) as count,
                                 AVG(duration_minutes) as avg_duration
                          FROM reading_activities 
                          WHERE timestamp >= ?
                          GROUP BY DATE(timestamp)
                          ORDER BY date'''
                params = ((datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),)
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            return {
                "daily_activity": df.to_dict('records'),
                "total_activities": int(df['count'].sum()) if not df.empty else 0,
                "avg_daily_reading": float(df['avg_duration'].mean()) if not df.empty else 0
            }
        except sqlite3.OperationalError:
            return {
                "daily_activity": [],
                "total_activities": 0,
                "avg_daily_reading": 0
            }
    
    def get_genre_distribution(self, username: Optional[str] = None) -> Dict:
        """
        Analyze genre distribution
        
        Args:
            username: Specific user (None for all users)
        
        Returns:
            Dictionary with genre distribution
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            if username:
                query = '''SELECT genre, COUNT(*) as count 
                          FROM reading_activities 
                          WHERE username = ?
                          GROUP BY genre
                          ORDER BY count DESC'''
                params = (username,)
            else:
                query = '''SELECT genre, COUNT(*) as count 
                          FROM reading_activities 
                          GROUP BY genre
                          ORDER BY count DESC'''
                params = ()
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            return {
                "genres": df.to_dict('records'),
                "total_genres": len(df),
                "most_popular": df.iloc[0]['genre'] if not df.empty else "None"
            }
        except sqlite3.OperationalError:
            return {
                "genres": [],
                "total_genres": 0,
                "most_popular": "None"
            }
    
    def get_user_comparison(self, username: str) -> Dict:
        """
        Compare user stats with platform average
        
        Args:
            username: Username to analyze
        
        Returns:
            Comparison metrics
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # User stats
        c.execute('''SELECT total_books_read, current_streak, experience_points
                    FROM user_stats WHERE username = ?''', (username,))
        user = c.fetchone()
        
        if not user:
            conn.close()
            return {}
        
        # Platform averages
        c.execute('''SELECT AVG(total_books_read), AVG(current_streak), 
                           AVG(experience_points)
                    FROM user_stats''')
        averages = c.fetchone()
        
        conn.close()
        
        return {
            "user": {
                "books_read": user[0],
                "streak": user[1],
                "xp": user[2]
            },
            "platform_average": {
                "books_read": round(averages[0], 1) if averages[0] else 0,
                "streak": round(averages[1], 1) if averages[1] else 0,
                "xp": round(averages[2], 1) if averages[2] else 0
            },
            "percentile": self._calculate_percentile(username)
        }
    
    def _calculate_percentile(self, username: str) -> Dict:
        """Calculate user's percentile ranking"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get user's XP
        c.execute('SELECT experience_points FROM user_stats WHERE username = ?', 
                 (username,))
        user_xp = c.fetchone()
        
        if not user_xp:
            conn.close()
            return {}
        
        user_xp = user_xp[0]
        
        # Count users with lower XP
        c.execute('SELECT COUNT(*) FROM user_stats WHERE experience_points < ?',
                 (user_xp,))
        lower_count = c.fetchone()[0]
        
        # Total users
        c.execute('SELECT COUNT(*) FROM user_stats')
        total_users = c.fetchone()[0]
        
        conn.close()
        
        percentile = (lower_count / total_users * 100) if total_users > 0 else 0
        
        return {
            "percentile": round(percentile, 1),
            "total_users": total_users
        }
    
    def get_popular_books(self, limit: int = 10, days: int = 30) -> List[Dict]:
        """
        Get most popular books based on reading activity
        
        Args:
            limit: Number of books to return
            days: Time period to analyze
        
        Returns:
            List of popular books
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            query = '''SELECT book_title, genre, COUNT(*) as read_count,
                             COUNT(DISTINCT username) as unique_readers
                      FROM reading_activities
                      WHERE timestamp >= ?
                      GROUP BY book_title
                      ORDER BY read_count DESC
                      LIMIT ?'''
            
            df = pd.read_sql_query(
                query, 
                conn, 
                params=((datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"), limit)
            )
            conn.close()
            
            return df.to_dict('records')
        except sqlite3.OperationalError:
            return []
    
    def get_reading_heatmap(self, username: str) -> Dict:
        """
        Generate reading activity heatmap data
        
        Args:
            username: Username to analyze
        
        Returns:
            Heatmap data by day and hour
        """
        conn = sqlite3.connect(self.db_path)
        
        query = '''SELECT strftime('%w', timestamp) as day_of_week,
                         strftime('%H', timestamp) as hour_of_day,
                         COUNT(*) as activity_count
                  FROM reading_activities
                  WHERE username = ?
                  GROUP BY day_of_week, hour_of_day'''
        
        df = pd.read_sql_query(query, conn, params=(username,))
        conn.close()
        
        # Convert to more readable format
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        
        heatmap = {}
        for _, row in df.iterrows():
            day = days[int(row['day_of_week'])]
            hour = int(row['hour_of_day'])
            count = int(row['activity_count'])
            
            if day not in heatmap:
                heatmap[day] = {}
            heatmap[day][hour] = count
        
        return heatmap
    
    def get_achievement_progress(self, username: str) -> Dict:
        """
        Get progress towards various achievements
        
        Args:
            username: Username to analyze
        
        Returns:
            Achievement progress data
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get user stats
        c.execute('''SELECT total_books_read, current_streak, longest_streak
                    FROM user_stats WHERE username = ?''', (username,))
        stats = c.fetchone()
        
        if not stats:
            conn.close()
            return {}
        
        books_read, current_streak, longest_streak = stats
        
        # Get earned badges
        c.execute('SELECT badge_id FROM user_badges WHERE username = ?', (username,))
        earned_badges = {row[0] for row in c.fetchall()}
        
        conn.close()
        
        # Calculate progress
        milestones = {
            "Books Read": [
                {"target": 10, "current": books_read, "badge": "bookworm"},
                {"target": 25, "current": books_read, "badge": "scholar"},
                {"target": 50, "current": books_read, "badge": "librarian"},
                {"target": 100, "current": books_read, "badge": "master_reader"}
            ],
            "Reading Streak": [
                {"target": 7, "current": current_streak, "badge": "streak_7"},
                {"target": 30, "current": current_streak, "badge": "streak_30"},
                {"target": 100, "current": current_streak, "badge": "streak_100"}
            ]
        }
        
        # Add earned status
        for category in milestones:
            for milestone in milestones[category]:
                milestone['earned'] = milestone['badge'] in earned_badges
                milestone['progress'] = min(100, (milestone['current'] / milestone['target']) * 100)
        
        return milestones
    
    def get_platform_statistics(self) -> Dict:
        """Get overall platform statistics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Helper function to safely query tables
        def safe_query(query, params=None, default=0):
            try:
                if params:
                    c.execute(query, params)
                else:
                    c.execute(query)
                result = c.fetchone()
                return result[0] if result else default
            except sqlite3.OperationalError:
                return default
        
        # Total users
        total_users = safe_query('SELECT COUNT(*) FROM users')
        
        # Total books in catalog
        books_in_use = safe_query('SELECT COUNT(DISTINCT book_title) FROM reading_activities')
        
        # Total reading activities
        total_activities = safe_query('SELECT COUNT(*) FROM reading_activities')
        
        # Active users (last 7 days)
        active_users = safe_query(
            '''SELECT COUNT(DISTINCT username) FROM reading_activities
               WHERE timestamp >= ?''',
            ((datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),)
        )
        
        # Total badges earned
        total_badges = safe_query('SELECT COUNT(*) FROM user_badges')
        
        # Collaborative stories
        total_stories = safe_query('SELECT COUNT(*) FROM collaborative_stories')
        
        conn.close()
        
        return {
            "total_users": total_users,
            "active_users_7d": active_users,
            "books_read": books_in_use,
            "total_activities": total_activities,
            "badges_earned": total_badges,
            "collaborative_stories": total_stories
        }
    
    def get_recommendations_insights(self, books_df: pd.DataFrame) -> Dict:
        """
        Analyze book catalog for insights
        
        Args:
            books_df: DataFrame with book catalog
        
        Returns:
            Catalog insights
        """
        return {
            "total_books": len(books_df),
            "total_authors": books_df['Author'].nunique(),
            "total_categories": books_df['Bookshelf'].nunique(),
            "most_popular_category": books_df['Bookshelf'].mode()[0] if not books_df.empty else "N/A",
            "books_per_category": books_df.groupby('Bookshelf').size().to_dict()
        }
