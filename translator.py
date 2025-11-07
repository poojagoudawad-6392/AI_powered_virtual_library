"""
Book Translator Module
Translates book text between multiple languages
"""

from deep_translator import GoogleTranslator

class BookTranslator:
    """Language translation using Google Translate API"""
    
    def __init__(self):
        self.supported_languages = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh-cn': 'Chinese (Simplified)',
            'hi': 'Hindi',
            'kn': 'Kannada',
            'ar': 'Arabic'
        }
    
    def translate(self, text, source_lang='auto', target_lang='en', chunk_size=4500):
        """
        Translate text from source language to target language
        Handles long texts by splitting into chunks
        
        Args:
            text: Text to translate
            source_lang: Source language code (default: 'auto' for auto-detect)
            target_lang: Target language code (default: 'en')
            chunk_size: Maximum characters per chunk (default: 4500)
        
        Returns:
            Translated text
        """
        try:
            if not text or len(text.strip()) == 0:
                return "No text to translate"
            
            # If text is short, translate directly
            if len(text) <= chunk_size:
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                return translator.translate(text)
            
            # For long texts, split and translate in chunks
            return self.translate_long_text(text, source_lang, target_lang, chunk_size)
            
        except Exception as e:
            return f"Translation error: {str(e)}"
    
    def get_supported_languages(self):
        """Return list of supported languages"""
        return self.supported_languages
    
    def detect_language(self, text):
        """
        Detect the language of the given text
        """
        try:
            from deep_translator import single_detection
            detected = single_detection(text, api_key=None)
            return detected
        except:
            return "unknown"
    
    def translate_long_text(self, text, source_lang='auto', target_lang='en', chunk_size=4500, progress_callback=None):
        """
        Translate long text by splitting into chunks
        
        Args:
            text: Long text to translate
            source_lang: Source language code
            target_lang: Target language code
            chunk_size: Maximum characters per chunk
            progress_callback: Optional callback function(current, total) for progress updates
        
        Returns:
            Translated text
        """
        try:
            # Split text into sentences to avoid breaking mid-sentence
            import re
            import time
            sentences = re.split(r'(?<=[.!?])\s+', text)
            
            chunks = []
            current_chunk = ""
            
            for sentence in sentences:
                # If adding this sentence exceeds chunk size, save current chunk
                if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = sentence
                else:
                    current_chunk += (" " if current_chunk else "") + sentence
            
            # Add the last chunk
            if current_chunk:
                chunks.append(current_chunk)
            
            # Translate each chunk with retry logic
            translated_chunks = []
            
            for i, chunk in enumerate(chunks):
                if progress_callback:
                    progress_callback(i + 1, len(chunks))
                
                # Retry logic for network errors
                max_retries = 3
                retry_delay = 2
                
                for attempt in range(max_retries):
                    try:
                        # Create new translator instance for each chunk to avoid connection issues
                        translator = GoogleTranslator(source=source_lang, target=target_lang)
                        translated = translator.translate(chunk)
                        translated_chunks.append(translated)
                        break  # Success, exit retry loop
                        
                    except Exception as e:
                        if attempt < max_retries - 1:
                            # Wait before retrying
                            time.sleep(retry_delay * (attempt + 1))
                        else:
                            # Last attempt failed, append error message
                            translated_chunks.append(f"[Translation failed for chunk {i+1}: {str(e)}]")
                
                # Delay between chunks to avoid rate limiting
                time.sleep(1)
            
            return " ".join(translated_chunks)
            
        except Exception as e:
            return f"Translation error: {str(e)}"
    
    def translate_book_excerpt(self, excerpt, target_lang='en'):
        """
        Translate a book excerpt to the target language
        """
        return self.translate(excerpt, source_lang='auto', target_lang=target_lang)
