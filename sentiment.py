"""
Sentiment Analysis Module
Analyzes sentiment of text using VADER and TextBlob
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob

class SentimentAnalyzer:
    """Sentiment analysis using multiple NLP methods"""
    
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
    
    def analyze(self, text):
        """
        Analyze sentiment of the given text
        Returns a dictionary with sentiment scores
        """
        try:
            # VADER sentiment analysis
            vader_scores = self.vader.polarity_scores(text)
            
            # TextBlob sentiment analysis
            blob = TextBlob(text)
            textblob_polarity = blob.sentiment.polarity
            
            # Determine overall sentiment
            compound = vader_scores['compound']
            if compound >= 0.05:
                label = "Positive"
            elif compound <= -0.05:
                label = "Negative"
            else:
                label = "Neutral"
            
            return {
                'label': label,
                'score': abs(compound),
                'positive': vader_scores['pos'],
                'neutral': vader_scores['neu'],
                'negative': vader_scores['neg'],
                'textblob_polarity': textblob_polarity
            }
            
        except Exception as e:
            return {
                'label': 'Error',
                'score': 0.0,
                'positive': 0.0,
                'neutral': 1.0,
                'negative': 0.0,
                'error': str(e)
            }
    
    def analyze_review(self, review_text):
        """
        Specialized method for analyzing book reviews
        """
        return self.analyze(review_text)
    
    def get_emotion(self, text):
        """
        Get the dominant emotion from text
        """
        result = self.analyze(text)
        
        if result['label'] == 'Positive':
            if result['score'] > 0.7:
                return "Very Happy 😄"
            else:
                return "Happy 🙂"
        elif result['label'] == 'Negative':
            if result['score'] > 0.7:
                return "Very Sad 😢"
            else:
                return "Sad 😟"
        else:
            return "Neutral 😐"
