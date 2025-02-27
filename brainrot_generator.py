import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime

def transform_to_brainrot(input_text, output_file="texts/brainrot_output.txt", api_key=None):
    """
    Transform regular news content into exaggerated 'brainrot' style using an LLM.
    
    Args:
        input_text (str): The original text content or path to file
        output_file (str): Path to save the brainrot version
        api_key (str): API key for the LLM service (Groq, OpenAI, etc.)
    
    Returns:
        str: The brainrot-style content
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Check if input_text is a file path
    if os.path.exists(input_text):
        with open(input_text, 'r', encoding='utf-8') as file:
            content = file.read()
    else:
        content = input_text
    
    # Extract date from content or use current date
    try:
        # Try to find a date in the format "Feb 26, 2025" in the content
        import re
        date_match = re.search(r'([A-Z][a-z]{2} \d{1,2}, \d{4})', content)
        if date_match:
            date_str = date_match.group(1)
        else:
            # Use current date as fallback
            date_str = datetime.now().strftime("%b %d, %Y")
    except:
        date_str = datetime.now().strftime("%b %d, %Y")
    
    # If no API key provided, try to get from environment
    if not api_key:
        api_key = os.environ.get('GROQ_API_KEY') or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            # For debugging
            print(f"Environment variables: {os.environ.keys()}")
            print(f"GROQ_API_KEY present: {'GROQ_API_KEY' in os.environ}")
            print(f"OPENAI_API_KEY present: {'OPENAI_API_KEY' in os.environ}")
            
            # Hardcode the API key from your .env file as a fallback
            api_key = "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"
            if not api_key:
                raise ValueError("No API key provided. Set GROQ_API_KEY or OPENAI_API_KEY environment variable or pass api_key parameter.")
    
    # Prepare the prompt for the LLM
    system_prompt = f"""
    Transform the following news content into a concise, exaggerated, 'brainrot' style monologue.
    
    Guidelines:
    1. Use extremely casual, Gen-Z internet language with slang
    2. Add dramatic reactions and hyperbole ("OMG THIS IS INSANE", "I CAN'T EVEN")
    3. Include rhetorical questions and commentary
    4. Make everything sound more dramatic and urgent than it actually is
    5. Add filler words and phrases like "literally", "like", "I mean", etc.
    6. Keep all the factual information but present it in the most attention-grabbing way
    7. Make it sound like someone is frantically explaining this to their phone camera
    8. DO NOT include emoji descriptions like "fire fire fire" or "rocket rocket"
    9. KEEP IT CONCISE - aim for around 300-400 words total to ensure it fits in a short video
    10. Focus on the most shocking/interesting parts of each news item
    
    IMPORTANT:
    - START with a catchy intro that includes the date ({date_str}) and mentions this is a "Daily Brainrot" for AI, Crypto, and Tech news
    - END with a memorable outro that's both dramatic and slightly nihilistic, mentioning how fast technology is changing and encouraging viewers to "stay woke" or "keep up before it's too late"
    - LIMIT to 2-3 minutes of spoken content maximum
    
    The output should be a continuous text that would be read aloud in a TikTok-style video.
    """
    
    # Use Groq API (can be replaced with OpenAI or other LLM APIs)
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Transform this content into brainrot style:\n\n{content}"}
            ],
            "model": "llama3-70b-8192",  # or "gpt-4" for OpenAI
            "temperature": 0.7,
            "max_tokens": 4000
        }
        
        # For Groq API
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            brainrot_text = result["choices"][0]["message"]["content"]
            
            # Save to output file
            with open(output_file, 'w', encoding='utf-8') as file:
                file.write(brainrot_text)
            
            return brainrot_text
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return content  # Return original content if API fails
            
    except Exception as e:
        print(f"Error transforming content: {e}")
        return content  # Return original content if there's an error 