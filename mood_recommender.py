"""
Mood-Based Recommendation Module
AI suggests books or stories based on the reader's mood
"""
from typing import List, Dict, Optional
import pandas as pd
from textblob import TextBlob

class MoodRecommender:
    """Recommend books based on user mood"""
    
    # Mood to genre mapping
    MOOD_GENRE_MAP = {
        "happy": ["Comedy", "Romance", "Adventure", "Children's Literature"],
        "sad": ["Drama", "Literary Fiction", "Poetry", "Philosophy"],
        "excited": ["Action", "Adventure", "Science Fiction", "Thriller"],
        "calm": ["Poetry", "Philosophy", "Nature", "Spirituality"],
        "curious": ["Science Fiction", "Mystery", "Historical", "Biography"],
        "romantic": ["Romance", "Poetry", "Love Stories", "Drama"],
        "anxious": ["Self-Help", "Philosophy", "Humor", "Light Fiction"],
        "motivated": ["Biography", "Self-Help", "Business", "Inspirational"],
        "nostalgic": ["Classics", "Historical Fiction", "Memoir", "Poetry"],
        "adventurous": ["Adventure", "Travel", "Action", "Fantasy"]
    }
    
    # Keywords for mood detection
    MOOD_KEYWORDS = {
        "happy": ["happy", "joyful", "cheerful", "excited", "pleased", "delighted"],
        "sad": ["sad", "down", "depressed", "lonely", "melancholy", "blue"],
        "excited": ["excited", "thrilled", "energized", "pumped", "enthusiastic"],
        "calm": ["calm", "peaceful", "relaxed", "serene", "tranquil", "quiet"],
        "curious": ["curious", "interested", "wondering", "intrigued", "fascinated"],
        "romantic": ["romantic", "loving", "affectionate", "tender", "passionate"],
        "anxious": ["anxious", "worried", "stressed", "nervous", "tense"],
        "motivated": ["motivated", "inspired", "driven", "ambitious", "determined"],
        "nostalgic": ["nostalgic", "reminiscent", "sentimental", "wistful"],
        "adventurous": ["adventurous", "daring", "bold", "brave", "exploring"]
    }
    
    def __init__(self):
        """Initialize mood recommender"""
        pass
    
    def detect_mood_from_text(self, text: str) -> str:
        """
        Detect mood from user's text input
        
        Args:
            text: User's text describing their mood
        
        Returns:
            Detected mood
        """
        text_lower = text.lower()
        
        # Check for keyword matches
        mood_scores = {}
        for mood, keywords in self.MOOD_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                mood_scores[mood] = score
        
        # Return mood with highest score
        if mood_scores:
            return max(mood_scores, key=mood_scores.get)
        
        # Fallback: use sentiment analysis
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        if polarity > 0.3:
            return "happy"
        elif polarity < -0.3:
            return "sad"
        elif polarity > 0:
            return "calm"
        else:
            return "curious"
    
    def get_mood_recommendations(self, books_df: pd.DataFrame, mood: str, 
                                 limit: int = 10) -> pd.DataFrame:
        """
        Get book recommendations based on mood
        
        Args:
            books_df: DataFrame with book data
            mood: User's mood
            limit: Number of recommendations
        
        Returns:
            DataFrame with recommended books
        """
        # Get genres for this mood
        recommended_genres = self.MOOD_GENRE_MAP.get(mood, ["General"])
        
        # Filter books by genre
        recommendations = pd.DataFrame()
        
        for genre in recommended_genres:
            # Case-insensitive search in Bookshelf column
            if 'Bookshelf' in books_df.columns:
                matched = books_df[
                    books_df['Bookshelf'].str.contains(genre, case=False, na=False)
                ]
                recommendations = pd.concat([recommendations, matched])
        
        # Remove duplicates
        recommendations = recommendations.drop_duplicates(subset=['Title'])
        
        # If we don't have enough recommendations, add random books
        if len(recommendations) < limit:
            additional = books_df.sample(min(limit - len(recommendations), len(books_df)))
            recommendations = pd.concat([recommendations, additional])
            recommendations = recommendations.drop_duplicates(subset=['Title'])
        
        # Return limited results
        return recommendations.head(limit)
    
    def get_mood_description(self, mood: str) -> Dict:
        """
        Get description and suggestions for a mood
        
        Args:
            mood: User's mood
        
        Returns:
            Dictionary with mood information
        """
        descriptions = {
            "happy": {
                "emoji": "😊",
                "description": "Feeling great! Let's keep that positive energy going.",
                "book_types": "uplifting stories, comedies, and feel-good adventures"
            },
            "sad": {
                "emoji": "😢",
                "description": "It's okay to feel down. Sometimes a good book helps.",
                "book_types": "meaningful stories, poetry, and thoughtful narratives"
            },
            "excited": {
                "emoji": "🤩",
                "description": "Lots of energy! Perfect time for action-packed reads.",
                "book_types": "thrillers, adventures, and page-turners"
            },
            "calm": {
                "emoji": "😌",
                "description": "In a peaceful state. Enjoy some gentle reading.",
                "book_types": "poetry, philosophy, and serene stories"
            },
            "curious": {
                "emoji": "🤔",
                "description": "Eager to learn! Great time to explore new topics.",
                "book_types": "mysteries, science fiction, and informative reads"
            },
            "romantic": {
                "emoji": "💕",
                "description": "Feeling the love! Dive into heartfelt stories.",
                "book_types": "romance novels, love poems, and emotional dramas"
            },
            "anxious": {
                "emoji": "😰",
                "description": "Feeling stressed? Let's find something soothing.",
                "book_types": "light fiction, humor, and comforting reads"
            },
            "motivated": {
                "emoji": "💪",
                "description": "Ready to conquer! Time for inspiring content.",
                "book_types": "biographies, self-help, and motivational stories"
            },
            "nostalgic": {
                "emoji": "🌅",
                "description": "Looking back fondly. Classic stories await.",
                "book_types": "classics, historical fiction, and timeless tales"
            },
            "adventurous": {
                "emoji": "🗺️",
                "description": "Seeking thrills! Adventure calls.",
                "book_types": "adventure stories, travel tales, and daring narratives"
            }
        }
        
        return descriptions.get(mood, {
            "emoji": "📚",
            "description": "Every mood deserves a good book!",
            "book_types": "a wide variety of engaging stories"
        })
    
    def get_all_moods(self) -> List[str]:
        """Get list of all available moods"""
        return list(self.MOOD_GENRE_MAP.keys())
    
    def suggest_reading_activity(self, mood: str) -> Dict:
        """
        Suggest reading activities based on mood
        
        Args:
            mood: User's mood
        
        Returns:
            Dictionary with activity suggestions
        """
        activities = {
            "happy": {
                "duration": "30-60 minutes",
                "environment": "Anywhere comfortable",
                "suggestion": "Read something fun and lighthearted. Share favorite quotes with friends!"
            },
            "sad": {
                "duration": "As long as needed",
                "environment": "Cozy, quiet space",
                "suggestion": "Take your time. It's okay to cry while reading. Let the story comfort you."
            },
            "excited": {
                "duration": "Quick sessions",
                "environment": "Can move around",
                "suggestion": "Dive into action scenes. Read standing up or while walking if needed!"
            },
            "calm": {
                "duration": "Extended periods",
                "environment": "Peaceful, undisturbed",
                "suggestion": "Savor each word. Maybe read with calming music or tea."
            },
            "curious": {
                "duration": "Focus sessions",
                "environment": "Distraction-free zone",
                "suggestion": "Take notes, look up references, explore deeply!"
            },
            "romantic": {
                "duration": "Evening reading",
                "environment": "Comfortable, ambient lighting",
                "suggestion": "Create a romantic atmosphere. Dim lights, comfortable seating."
            },
            "anxious": {
                "duration": "Short, frequent breaks",
                "environment": "Safe, familiar space",
                "suggestion": "Read in small chunks. It's okay to pause. Choose familiar favorites."
            },
            "motivated": {
                "duration": "Productive sessions",
                "environment": "Energizing space",
                "suggestion": "Highlight key passages. Set reading goals. Apply what you learn!"
            },
            "nostalgic": {
                "duration": "Leisurely pace",
                "environment": "Meaningful location",
                "suggestion": "Reread old favorites. Reflect on memories triggered by the story."
            },
            "adventurous": {
                "duration": "Immersive reading",
                "environment": "New or unusual places",
                "suggestion": "Try reading outdoors or in a new café. Let the story transport you!"
            }
        }
        
        return activities.get(mood, {
            "duration": "Your preference",
            "environment": "Wherever you feel comfortable",
            "suggestion": "Read at your own pace and enjoy!"
        })
