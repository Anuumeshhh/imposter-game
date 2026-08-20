import os
import random
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def get_random_word_pair():
    themes = [
        "anime and manga powers, concepts, or rival characters", 
        "video game legends, factions, or iconic characters", 
        "mythology figures, deities, or legendary founders", 
        "historical epochs, iconic artifacts, or pop culture counterparts"
    ]
    chosen_theme = random.choice(themes)
    
    prompt = f"""
    Generate a pair of conceptually linked words, characters, or terms from the theme: {chosen_theme}.
    They should not be identical, but they must share a strong underlying thematic connection or category.
    
    Format your response strictly on separate lines like this:
    Word1: [concept A]
    Word2: [concept B]
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        
        text = response.text
        word1, word2 = "Pizza", "Burger"
        
        for line in text.split("\n"):
            if line.startswith("Word1:"):
                word1 = line.replace("Word1:", "").strip()
            elif line.startswith("Word2:"):
                word2 = line.replace("Word2:", "").strip()
                
        if random.choice([True, False]):
            return word1, word2
        return word2, word1

    except Exception as e:
        print(f"API Error: {e}")
        fallback_pairs = [("Arthur Morgan", "John Marston"), ("Cursed Technique", "Imaginary Technique"), ("Zeus", "Odin")]
        common, imposter = random.choice(fallback_pairs)
        return (common, imposter) if random.choice([True, False]) else (imposter, common)
