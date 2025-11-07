"""
AI Chat Assistant Module
Conversational AI for book-related queries
"""

import os

class ChatAssistant:
    """AI-powered chat assistant for book discussions"""
    
    def __init__(self):
        """
        Initialize the chat assistant
        You can optionally use OpenAI API by setting OPENAI_API_KEY environment variable
        """
        self.use_openai = False
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        
        # Try to import OpenAI if API key is available
        if self.api_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
                self.use_openai = True
            except ImportError:
                self.use_openai = False
    
    def get_response(self, user_message, books_df=None):
        """
        Get AI response to user message
        
        Args:
            user_message: The user's question or message
            books_df: Optional DataFrame of books for context
        
        Returns:
            AI-generated response
        """
        if self.use_openai:
            return self._get_openai_response(user_message, books_df)
        else:
            return self._get_fallback_response(user_message, books_df)
    
    def _get_openai_response(self, user_message, books_df):
        """Get response using OpenAI API"""
        try:
            # Create context from books database
            context = "You are a helpful AI assistant for a virtual library. "
            context += "You help users discover books, answer questions about literature, "
            context += "and provide reading recommendations. "
            
            if books_df is not None and len(books_df) > 0:
                num_books = len(books_df)
                context += f"The library has {num_books} books available. "
            
            # Create chat completion
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": context},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}. Let me try to help you anyway!"
    
    def _get_fallback_response(self, user_message, books_df):
        """Fallback response when OpenAI is not available"""
        
        message_lower = user_message.lower()
        
        # Book recommendations
        if any(word in message_lower for word in ['recommend', 'suggestion', 'suggest', 'book']):
            if books_df is not None and len(books_df) > 0:
                sample_books = books_df.sample(min(3, len(books_df)))
                response = "I'd be happy to recommend some books! Here are a few from our collection:\n\n"
                for idx, row in sample_books.iterrows():
                    response += f"📖 **{row['Title']}** by {row['Author']}\n"
                return response
            else:
                return "I'd love to recommend books, but I don't have access to the catalog right now."
        
        # Search queries
        elif any(word in message_lower for word in ['find', 'search', 'looking for']):
            return "You can use the Book Catalog page to search for books by title, author, or category. Use the search bar and filters to find exactly what you're looking for!"
        
        # Genre questions
        elif any(word in message_lower for word in ['genre', 'category', 'type']):
            if books_df is not None and 'Bookshelf' in books_df.columns:
                genres = books_df['Bookshelf'].dropna().unique()[:5]
                return f"Our library has books in various genres including: {', '.join(genres)}. What genre interests you?"
            return "We have books across many genres! You can browse by category in the Book Catalog."
        
        # Author questions
        elif 'author' in message_lower:
            if books_df is not None and 'Author' in books_df.columns:
                authors = books_df['Author'].dropna().unique()[:5]
                return f"We have works by many authors including: {', '.join(authors)}. Who is your favorite author?"
            return "We have books from many renowned authors. Use the search feature to find books by your favorite author!"
        
        # Features
        elif any(word in message_lower for word in ['feature', 'can you', 'help', 'what']):
            return """I can help you with:
            
📚 **Book Discovery**: Find books by title, author, or genre
🤖 **Recommendations**: Get personalized book suggestions
📝 **Summaries**: Read AI-generated book summaries
🌍 **Translation**: Translate book excerpts to different languages
📊 **Analysis**: View sentiment analysis of reviews
🔖 **Bookmarks**: Save your favorite books

What would you like to do today?"""
        
        # Greetings
        elif any(word in message_lower for word in ['hello', 'hi', 'hey', 'greetings']):
            return "Hello! 👋 Welcome to the AI Virtual Library. I'm here to help you discover amazing books! Ask me for recommendations, search for specific titles, or explore our catalog. What are you interested in reading today?"
        
        # Thanks
        elif any(word in message_lower for word in ['thank', 'thanks']):
            return "You're welcome! Happy reading! 📚 Feel free to ask me anything else about books."
        
        # Default response
        else:
            return """I'm here to help you explore our virtual library! You can ask me to:

• Recommend books based on your interests
• Find books by a specific author or genre
• Learn about library features
• Get reading suggestions

What would you like to know about?"""
    
    def set_api_key(self, api_key):
        """Set OpenAI API key"""
        self.api_key = api_key
        if api_key:
            try:
                import openai
                self.client = openai.OpenAI(api_key=api_key)
                self.use_openai = True
            except ImportError:
                self.use_openai = False
