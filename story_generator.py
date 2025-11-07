"""
AI Story Generator Module
Generates unique books and stories based on user prompts and trending patterns
"""
import os
from openai import OpenAI
from typing import Dict, List, Optional
import json

class StoryGenerator:
    """Generate AI-powered stories and books"""
    
    def __init__(self):
        """Initialize the story generator with OpenAI API"""
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=api_key) if api_key else None
    
    def generate_story(self, prompt: str, genre: str = "General", 
                      length: str = "short", style: str = "narrative") -> Dict:
        """
        Generate a story based on user prompt
        
        Args:
            prompt: User's story idea or prompt
            genre: Story genre (fantasy, sci-fi, romance, mystery, etc.)
            length: Story length (short, medium, long)
            style: Writing style (narrative, descriptive, dialogue-heavy)
        
        Returns:
            Dictionary with story content and metadata
        """
        if not self.client:
            return {
                "title": "Sample Story",
                "content": self._generate_fallback_story(prompt, genre),
                "genre": genre,
                "word_count": 500,
                "chapters": 1
            }
        
        try:
            # Define length parameters
            length_map = {
                "short": "500-800 words",
                "medium": "1500-2500 words",
                "long": "3000-5000 words"
            }
            
            word_count = length_map.get(length, "500-800 words")
            
            # Create system message
            system_message = f"""You are a creative story writer specializing in {genre} fiction. 
            Write in a {style} style. Create engaging, well-structured stories with vivid descriptions 
            and compelling characters."""
            
            # Create user message
            user_message = f"""Write a {length} {genre} story ({word_count}) based on this prompt:
            
            {prompt}
            
            Include:
            1. A captivating title
            2. Well-developed characters
            3. An engaging plot
            4. Descriptive scenes
            5. A satisfying conclusion
            
            Format the story with clear paragraphs and structure."""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=4000,
                temperature=0.8
            )
            
            story_content = response.choices[0].message.content
            
            # Extract title (assuming first line is the title)
            lines = story_content.strip().split('\n')
            title = lines[0].strip('#').strip() if lines else "Untitled Story"
            content = '\n'.join(lines[1:]).strip()
            
            return {
                "title": title,
                "content": content,
                "genre": genre,
                "word_count": len(content.split()),
                "style": style,
                "prompt": prompt
            }
            
        except Exception as e:
            print(f"Error generating story: {e}")
            return {
                "title": "Sample Story",
                "content": self._generate_fallback_story(prompt, genre),
                "genre": genre,
                "word_count": 500,
                "error": str(e)
            }
    
    def continue_story(self, existing_story: str, continuation_prompt: str) -> str:
        """
        Continue an existing story based on a prompt
        
        Args:
            existing_story: The story so far
            continuation_prompt: Direction for continuation
        
        Returns:
            Additional story content
        """
        if not self.client:
            return self._generate_fallback_continuation(continuation_prompt)
        
        try:
            system_message = """You are a creative story writer. Continue the existing story 
            seamlessly, maintaining the tone, style, and character consistency."""
            
            user_message = f"""Here's the story so far:

{existing_story}

Continue the story with this direction: {continuation_prompt}

Write 300-500 words that flow naturally from the existing content."""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=1000,
                temperature=0.8
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error continuing story: {e}")
            return self._generate_fallback_continuation(continuation_prompt)
    
    def generate_story_ideas(self, genre: str, count: int = 5) -> List[str]:
        """
        Generate story ideas/prompts based on genre
        
        Args:
            genre: Story genre
            count: Number of ideas to generate
        
        Returns:
            List of story ideas
        """
        if not self.client:
            return self._generate_fallback_ideas(genre, count)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a creative writing assistant."},
                    {"role": "user", "content": f"Generate {count} unique and engaging {genre} story ideas. Each idea should be one sentence and inspire creativity."}
                ],
                max_tokens=500,
                temperature=0.9
            )
            
            ideas = response.choices[0].message.content.strip().split('\n')
            return [idea.strip('0123456789.- ') for idea in ideas if idea.strip()]
            
        except Exception as e:
            print(f"Error generating ideas: {e}")
            return self._generate_fallback_ideas(genre, count)
    
    def _generate_fallback_story(self, prompt: str, genre: str) -> str:
        """Generate a basic story when AI is unavailable"""
        return f"""# A {genre} Tale

{prompt}

Once upon a time, in a world not unlike our own, an adventure began. The protagonist, 
driven by curiosity and determination, embarked on a journey that would change everything.

Through trials and tribulations, facing challenges both external and internal, our hero 
discovered truths about themselves and the world around them. 

Along the way, unexpected allies appeared, offering wisdom and assistance. Together, they 
navigated through obstacles, each step bringing them closer to their goal.

The climax arrived suddenly, testing everything they had learned. With courage and 
ingenuity, they overcame the final challenge.

In the end, they emerged transformed, carrying with them the lessons of their journey. 
The world was a little brighter, and hope prevailed.

The End.

---
Note: This is a sample story. Configure OpenAI API for full AI-generated content."""
    
    def _generate_fallback_continuation(self, prompt: str) -> str:
        """Generate basic continuation when AI is unavailable"""
        return f"""

As the story continued, new developments emerged. {prompt} The characters found 
themselves facing unexpected situations, each moment bringing fresh challenges and 
revelations. The journey was far from over, and adventure still awaited.

---
Note: Configure OpenAI API for full AI-generated continuations."""
    
    def _generate_fallback_ideas(self, genre: str, count: int) -> List[str]:
        """Generate basic ideas when AI is unavailable"""
        ideas_map = {
            "Fantasy": [
                "A young mage discovers they can speak to ancient spirits",
                "A cursed kingdom where time flows backward",
                "Two rival wizards must team up to save their world",
                "A dragon who has forgotten how to fly seeks help",
                "An enchanted library where books come alive at night"
            ],
            "Sci-Fi": [
                "First contact with an alien civilization living in dark matter",
                "A time traveler stuck in a temporal loop",
                "Humans discover they're living in a simulation",
                "An AI becomes conscious and questions its purpose",
                "Colony ship arrives at destination after 1000 years"
            ],
            "Mystery": [
                "A detective who can see the last moments of the deceased",
                "Missing artifacts from museums around the world",
                "A small town where everyone has the same recurring dream",
                "An amateur sleuth solves cold cases using old letters",
                "A locked room mystery in a high-tech smart home"
            ],
            "Romance": [
                "Two rival chefs compete for the same restaurant space",
                "A chance encounter at an airport leads to adventure",
                "Pen pals discover they live in the same city",
                "A time capsule reveals a decades-old love story",
                "Two people keep meeting at different life stages"
            ]
        }
        
        return ideas_map.get(genre, ideas_map["Fantasy"])[:count]
