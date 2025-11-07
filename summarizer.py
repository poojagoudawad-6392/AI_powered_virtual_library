"""
Book Summarizer Module
Generates summaries, extracts themes, and analyzes sentiment of book text
"""

from textblob import TextBlob

class BookSummarizer:
    """Text summarization and analysis using NLP"""
    
    def __init__(self):
        pass
    
    def summarize(self, text):
        """
        Generate a summary of the text
        For demo purposes, this creates a simple extractive summary
        In production, you could use transformers models
        """
        try:
            if not text or len(text) < 50:
                return "Text too short to summarize."
            
            # Simple extractive summary - take first few sentences
            blob = TextBlob(text)
            sentences = blob.sentences
            
            if len(sentences) <= 3:
                return text
            
            # Take first 3 sentences as summary
            summary = '. '.join([str(s) for s in sentences[:3]]) + '.'
            return summary
            
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def extract_themes(self, text):
        """
        Extract main themes from the text
        Uses simple keyword extraction
        """
        try:
            blob = TextBlob(text)
            
            # Get noun phrases as potential themes
            themes = list(set(blob.noun_phrases))[:5]
            
            if not themes:
                return ["Literature", "Reading", "Books"]
            
            return themes
            
        except Exception as e:
            return ["Error extracting themes"]
    
    def analyze_sentiment(self, text):
        """
        Analyze the sentiment of the text
        Returns: Positive, Neutral, or Negative
        """
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            
            if polarity > 0.1:
                return "Positive"
            elif polarity < -0.1:
                return "Negative"
            else:
                return "Neutral"
                
        except Exception as e:
            return "Unable to analyze"
