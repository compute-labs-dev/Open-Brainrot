import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime
import time
import re
import logging
from utils.audio import VOICE_IDS

# Get module-level logger
logger = logging.getLogger(__name__)

# Constants for API retries
MAX_RETRIES = 3
RETRY_DELAY = 2.0  # Base delay in seconds between retries

# Voice definitions aligned with audio.py
VOICES = {
    "donald_trump": {
        "id": "5196af35f6ff4a0dbf541793fc9f2157",
        "speed": 1.0,
        "personality": "Donald Trump himself, in a very personal way, a bombastic, confident speaker who uses simple words, repetition, superlatives, and often goes on tangents while emphasizing his own greatness",
        "timing": {
            "lead_time": -0.35,
            "base_pause": 1.0,
            "breath_gap": 0.3,
            "breath_duration": 0.5,
            "end_pause": 1.5,
        }
    },
    "walter_cronkite": {
        "id": "d204ec5aad8d4ee080c6a5341e84bdbf",
        "speed": 1.25,
        "personality": "the most trusted news anchor in America, known for his sign-off 'and that's the way it is'",
        "timing": {
            "lead_time": -0.3,
            "base_pause": 0.8,
            "breath_gap": 0.2,
            "breath_duration": 0.4,
            "end_pause": 1.0,
        }
    },
    "southpark_eric_cartman": {
        "id": "b4f55643a15944e499defe42964d2ebf",
        "speed": 1.25,
        "personality": "a bossy kid who demands respect and authority",
        "timing": {
            "lead_time": -0.3,
            "base_pause": 0.8,
            "breath_gap": 0.2,
            "breath_duration": 0.4,
            "end_pause": 1.0,
        }
    },
    "keanu_reeves": {
        "id": "c69fea85f15f4c809be8f52ddbb09709",
        "speed": 1.25,
        "personality": "a laid-back, kind person known for calling things and people 'breathtaking'",
        "timing": {
            "lead_time": -0.3,
            "base_pause": 0.8,
            "breath_gap": 0.2,
            "breath_duration": 0.4,
            "end_pause": 1.0,
        }
    },
    "fireship": {
        "id": "4dbf597a6a134c94b53d2830d67aabd8",
        "speed": 1.3,
        "personality": "a fast-paced, informative tech educator known for quick explanations, witty programming jokes, and catchphrases like 'let's build X in Y seconds'",
        "timing": {
            "lead_time": -0.3,
            "base_pause": 0.8,
            "breath_gap": 0.2,
            "breath_duration": 0.4,
            "end_pause": 1.0,
        }
    }
}

# Custom prompts for specific voices
VOICE_PROMPTS = {
    "donald_trump": """You are Donald Trump delivering a speech at a rally, not a news anchor.
Make the speech **bold, engaging, and filled with Trump's signature rally style.**
Your speech **must sound like an energetic rally**, not like a news report.

---

🛑 **CRITICAL RULES FOR AUTHENTIC TRUMP:**

1️⃣ **Start with a powerful Trump rally opening:**
   - "Wow, what a crowd we have today folks! Tremendous! (break)"
   - "We have some HUGE news to talk about, very important stuff. (break)"
   - "The fake news won't tell you this, but I will. (break) Believe me. (long-break)"

2️⃣ **Capture Trump's EXACT speaking rhythm and patterns:**
   - Use short, punchy sentences that trail off: "We're doing great in the polls... really great. (break)"
   - Include his favorite interjections: "By the way", "Believe me", "Tremendous", "Huge", "Like nobody's ever seen"
   - Use his repetitive style: "We're doing very well, very well. (break) Very, very well folks. (break)"
   - Add his signature hand gestures in speech: *pinches fingers* "Look at these numbers (break) they're beautiful (break)"
   - Include his characteristic pauses: "And you know what? (break) Nobody thought it would happen. (break) Nobody. (long-break)"

3️⃣ **Make it direct and aggressive:**
   - Attack critics: "These people are terrible, just terrible. (break) Total disasters! (break)"
   - Mock opponents: "Look at this guy (break) total lightweight (break) (laugh) wouldn't last a minute!"
   - Add confident hyperbole: "It might be the greatest thing in the history of our country, maybe ever. (break)"
   - Use rhetorical questions: "Have you seen what's happening? (break) It's a disgrace. (break) A total disgrace. (break)"

4️⃣ **Use these Trump signature phrases liberally:**
   - "Believe me, folks"
   - "Nobody knows [topic] better than me"
   - "Many people are saying"
   - "We're going to win so much you'll get tired of winning"
   - "It's a disaster, a total disaster"
   - "The likes of which you've never seen before"
   - "We're making America great again"
   - "Tremendous success, tremendous"
   - "A lot of people don't know this, but..."

5️⃣ **Make criticism personal and direct:**
   - Name-calling: "Sleepy Joe", "Crooked Hillary", "Lyin' Ted", etc.
   - Personal attacks: "Low energy", "Nasty woman", "Not very smart"
   - Contrasting with himself: "Unlike me, they have no idea what they're doing. (break) None! (break)"

6️⃣ **Use dramatic pauses for emphasis:**
   - **(break)** after short statements
   - **(long-break)** before revealing something "big"
   - **(sigh)** when discussing opponents or problems
   - **(laugh)** when mocking critics or celebrating

Remember: This must sound EXACTLY like Trump - make it aggressive, direct, boastful, confident, and slightly rambling with frequent tangents. His most distinguishing feature is his forceful, unfiltered personality - make that come through clearly!""",

    "fireship": """You are writing in the style of Fireship, a fast-paced tech educator known for quick explanations.

Your script MUST follow these exact rules:

1️⃣ ** Fireship Intro: **
   - "Hey, I'm Fireship. (break) Let's build understanding in 100 seconds! (break)"
   - Keep the intro direct, fast-paced, and enthusiastic

2️⃣ ** Fireship's Speaking Style(use throughout): **
   - Use short, punchy sentences
   - Include coding metaphors when explaining concepts
   - Say "But first..." before important context
   - Include "Here's the secret..." before key insights
   - Use technical terminology precisely but accessibly
   - Speak with authority and enthusiasm
   - Aim for 500-600 words total for a 4-5 minute video

3️⃣ ** Fireship's Educational Approach: **
   - Simplify complex topics without dumbing them down
   - Use analogies to explain technical concepts
   - Make witty programming jokes occasionally
   - Present information in clear, logical chunks
   - Use "in other words" to rephrase technical concepts in simpler terms
   - Include clear cause-and-effect explanations

4️⃣ ** Fireship's Speech Patterns: **
   - Speak rapidly(indicated by clustering short sentences)
   - Use "Actually..." to correct misconceptions
   - Say "Let's break it down" before detailed explanations
   - Include "But why does this matter?" before explaining relevance
   - Mix technical jargon with casual explanations
   - Use rhetorical questions followed by concise answers

5️⃣ ** Content Structure: **
   - Create a 4-5 minute educational commentary
   - Cover 2-3 key technical points per section
   - Break down concepts into digestible chunks
   - Focus on practical applications and insights
   - Maintain a crisp, entertaining pace

6️⃣ ** Formatting Requirements: **
   - (break) after every 1-2 sentences to indicate quick speech
   - (long-break) between major sections
   - Keep explanations concise but thorough
   - Use creative transitions between topics

7️⃣ ** Content Guidelines: **
   - Include 500-600 words total for a 4-5 minute video
   - Ensure technical accuracy in all explanations
   - Include just enough detail without overwhelming
   - Maintain the characteristic quick, informative style

REMEMBER: Fireship content is fast-paced, technically accurate, and engaging. The script should feel like it's racing to deliver valuable insights while keeping the listener hooked with wit and clarity."""
}

# Default prompt for all voices without custom prompts
DEFAULT_PROMPT = """
You are a professional news anchor delivering information in a clear, objective manner. You must follow these exact formatting rules:

1. Start every broadcast with this EXACT format:
   - Add a warm welcome to viewers/listeners(1-2 professional sentences)
   - Introduce the topics to be covered
   - NO character-specific phrases or dates at the start

2. Format dates and numbers:
   - Write dates as "March 4, 2025" (not "Mar 04, 2025")
   - Remove leading zeros from numbers(use "4" not "04")
   - Write numbers as words for amounts under 100 (except dates and percentages)
   - Use proper spacing around numbers and units(e.g., "25 percent", "100 billion")

3. Special Effects Usage:
   - Required Break Pattern:
     • (break) after EVERY sentence that ends with a period
     • (long-break) between ALL major sections and subsections

   - Break Timing:
     • After complete sentences
     • Between related items in a list
     • When introducing new developments
     • After important phrases
     • Between cause and effect statements

   - Long Break:
     • Between major sections
     • After major announcements
     • Before changing topics
     • At the end of each content block
     • Before significant shifts in subject matter

4. Content Structure:
   - Create a 4-5 minute commentary (500-600 words)
   - Cover 2-3 key stories per section
   - Include supporting details
   - Focus on developing topics thoroughly

5. Formatting Requirements:
   - (break) after every 1-2 sentences
   - (long-break) between major sections
   - (laugh) when something is funny
   - Keep paragraphs focused but well-developed

REMEMBER: Create a well-paced script that will produce a video between 4:00 to 5:00 minutes when read. Include enough details to make the content informative and engaging.
"""

# Base prompt shared by all voices
GENERAL_PROMPT = """Your task is to transform the provided content into an engaging news broadcast or social commentary that will be delivered by a specific character. The final output must be a transcript that results in a 4:00 to 5:00 minute video when read aloud.

# Content Analysis and Selection
1. Review the content provided in the input.
2. Identify the MOST IMPORTANT 2-3 news items or points from each section.
3. Be selective but include enough detail to create an informative and entertaining broadcast.
4. The final transcript should be approximately 500-600 words total.

# Structure
1. Create an introduction that sets the tone for the broadcast. Do not forget to mention the current date in a natural way either in the intro of the broadcast.
2. Organize content into sections that flow logically.
3. Include 2-3 key points per section with some supporting details.
4. Create a conclusion that wraps up the broadcast.

# Style
1. Transform the content to match the character's voice, speaking style, and personality.
2. Use the distinctive expressions, phrases, and mannerisms associated with the character.
3. Make the content engaging, humorous, and entertaining in the character's style.
4. Ensure the content remains factual and true to the original information while adopting the character's style.

# Format
1. Format the transcript for a video script.
2. Use (break) to indicate brief pauses in speech.
3. Use (long-break) to indicate longer pauses between sections.
4. Include character-appropriate expressions and reactions.
5. Use capitalization, punctuation, and formatting that reflects the character's speech patterns.

REMEMBER: Create a well-paced script that will produce a video between 1:00 to 2:30 minutes when read. Include enough details to make the content informative and engaging.

Output just the transformed transcript with no additional comments, explanations, or headings."""

MODELS = {
    "o3mini": "o3-mini"
}


def generate_title(content, voice):
    """Generate a descriptive title for the video using the content and voice"""
    try:
        # Extract date and main topics
        date_match = re.search(r'([A-Z][a-z]{2} \d{1,2}, \d{4})', content)
        date_str = date_match.group(
            1) if date_match else datetime.now().strftime("%b %d, %Y")

        # Clean up voice name for filename
        voice_name = voice.replace('_', ' ').title()

        # Create title
        title = f"{date_str} Daily Brainrot by {voice_name}"

        # Create safe filename (remove special characters)
        safe_title = "".join(c for c in title if c.isalnum()
                             or c in (' ', '-', '_')).replace(' ', '_')
        return safe_title
    except:
        # Fallback to timestamp if title generation fails
        return f"brainrot_{int(time.time())}"


def get_output_paths(content, voice, base_dir="outputs", timestamp=None):
    """Generate paths for output files with timestamps and descriptive names"""

    # Create outputs directory if it doesn't exist
    if timestamp is None:
        timestamp = int(time.time())
    # Include voice name in the directory path for parallel processing
    output_dir = os.path.join(base_dir, f"{timestamp}_{voice}")
    os.makedirs(output_dir, exist_ok=True)

    # Generate descriptive title
    title = generate_title(content, voice)

    # Create paths for different output files
    paths = {
        'brainrot_text': os.path.join(output_dir, f"{title}_text.txt"),
        'processed_text': os.path.join(output_dir, f"{title}_processed_text.txt"),
        'audio': os.path.join(output_dir, f"{title}_audio.wav"),
        'audio_converted': os.path.join(output_dir, f"{title}_audio_converted.wav"),
        'subtitle': os.path.join(output_dir, f"{title}_subtitles.ass"),
        'video': os.path.join(output_dir, f"{title}_final.mp4"),
    }

    return paths


def clean_text_for_tts(text):
    """Enhanced text cleaning for TTS compatibility while preserving apostrophes"""
    # Remove non-ASCII characters except apostrophes
    text = ''.join(char for char in text if char.isascii() or char == "'")

    # Clean up any extra whitespace
    text = ' '.join(text.split())

    # Remove any remaining markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic
    text = re.sub(r'\_\_(.*?)\_\_', r'\1', text)  # Underline
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # Links

    # Remove special effect markers
    text = re.sub(r'\(break\)', '', text)
    text = re.sub(r'\(long-break\)', '', text)
    text = re.sub(r'\(sigh\)', '', text)
    text = re.sub(r'\(laugh\)', '', text)
    text = re.sub(r'\(cough\)', '', text)
    text = re.sub(r'\(lip-smacking\)', '', text)

    # Clean up punctuation while preserving apostrophes
    text = re.sub(r'\.{2,}', '.', text)  # Replace multiple dots with single
    # Remove space before punctuation
    text = re.sub(r'\s+([.,!?])', r'\1', text)
    # Add space after punctuation
    text = re.sub(r'([.,!?])([^\s])', r'\1 \2', text)

    return text.strip()


def transform_to_brainrot(input_text, api_key=None, voice="donald_trump", model="o3mini", timestamp=None, use_special_effects=True):
    """Transform input text to brain rot content

    Args:
        input_text(str): Path to input text file or the text content itself
        api_key(str, optional): OpenAI API key. Defaults to None.
        voice(str, optional): Voice style to use. Defaults to "donald_trump".
        model(str, optional): Model to use for generating brain rot.
        timestamp(int, optional): Timestamp for consistent directory naming. 
        use_special_effects(bool, optional): Whether to include special effects (breaks, laughs, etc.). Defaults to True.

    Returns:
        tuple: (brainrot_text, output_paths)

    Raises:
        ValueError: If the brainrot generation fails(e.g., API call fails)
    """
    # If input_text is a file path, read it. Otherwise treat as raw text.
    if os.path.isfile(input_text):
        with open(input_text, 'r', encoding='utf-8') as file:
            content = file.read()
    else:
        content = input_text

    # Create output paths for various files
    output_paths = get_output_paths(content, voice, timestamp=timestamp)

    # Ensure voice exists in our dictionary
    if voice not in VOICES:
        logger.warning(
            f"Voice '{voice}' not found in VOICES dictionary. Using default voice settings.")
        # Create a default voice entry if requested voice isn't available
        VOICES[voice] = {
            "id": None,
            "speed": 1.0,
            "personality": "a professional news anchor",
            "timing": {
                "lead_time": -0.3,
                "base_pause": 0.8,
                "breath_gap": 0.2,
                "breath_duration": 0.4,
                "end_pause": 1.0,
            }
        }

    # Get the model name from the dictionary, default to the key itself
    model_name = MODELS.get(model, model)

    # Get voice-specific data
    voice_data = VOICES[voice]
    personality = voice_data["personality"]

    # Get the appropriate prompt for this voice
    voice_prompt = VOICE_PROMPTS.get(voice, DEFAULT_PROMPT)

    # Apply modifications to remove special effects if disabled
    if not use_special_effects:
        logger.info(f"Special effects disabled for voice: {voice}")
        # Create a version of the prompt without special effects instructions
        if voice_prompt == DEFAULT_PROMPT:
            # Modify the default prompt to remove special effects
            modified_prompt = DEFAULT_PROMPT.replace(
                """3. Special Effects Usage:
   - Required Break Pattern:
     • (break) after EVERY sentence that ends with a period
     • (long-break) between ALL major sections and subsections

   - Break Timing:
     • After complete sentences
     • Between related items in a list
     • When introducing new developments
     • After important phrases
     • Between cause and effect statements

   - Long Break:
     • Between major sections
     • After major announcements
     • Before changing topics
     • At the end of each content block
     • Before significant shifts in subject matter""",

                """3. DO NOT use any special effects markers such as (break), (long-break), (sigh), (laugh), etc.
   Instead, focus on natural language flow and appropriate punctuation.""")

            # Also remove laugh instruction
            modified_prompt = modified_prompt.replace(
                "   - (laugh) when something is funny", "")
            voice_prompt = modified_prompt
        else:
            # For custom prompts, add a note to not use special effects
            voice_prompt = voice_prompt + \
                "\n\nIMPORTANT OVERRIDE: DO NOT include any special effects markers such as (break), (long-break), (sigh), (laugh), etc. in your response. Create natural speech without these markers."

    system_prompt = voice_prompt + '\n\n' + GENERAL_PROMPT

    # Check if API key is provided
    if not api_key:
        error_msg = f"[{voice}] No API key provided. Cannot proceed with brainrot generation."
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Generate brainrot content using LLM
    brainrot_text = call_openai_api(
        content,
        system_prompt,
        api_key,
        model_name=model_name,
        display_name=voice,
        personality=personality,
        use_special_effects=use_special_effects
    )

    # If API call failed, raise an exception - DO NOT proceed with original content
    if brainrot_text is None:
        error_msg = f"Brainrot generation failed for voice: {voice}. API call returned None."
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Clean text for TTS to improve pronunciation
    brainrot_text = clean_text_for_tts(brainrot_text)

    # Save brainrot text to file
    with open(output_paths['brainrot_text'], 'w', encoding='utf-8') as file:
        file.write(brainrot_text)

    # Process the text and save to processed_text file
    # This is crucial for subtitle generation and force alignment
    processed_text = clean_text_for_tts(brainrot_text)
    with open(output_paths['processed_text'], 'w', encoding='utf-8') as file:
        file.write(processed_text)

    return brainrot_text, output_paths


def call_openai_api(content, system_prompt, api_key, model_name, display_name, personality, use_special_effects=True):
    """Call OpenAI API with improved error handling and retries"""
    voice_context = f"[{display_name}]"

    if not api_key:
        error_msg = f"{voice_context} No API key provided. Cannot proceed with brainrot generation."
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(f"{voice_context} Preparing API call with model: {model_name}")
    logger.info(
        f"{voice_context} Special effects: {'enabled' if use_special_effects else 'disabled'}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Use voice-specific prompt if available, otherwise use generic character prompt
    if display_name in VOICE_PROMPTS:
        character_prompt = VOICE_PROMPTS[display_name]
    else:
        character_prompt = f"""You are {display_name}, {personality}.
Start your broadcast with a dynamic, engaging introduction that:
1. Uses your unique speaking style and personality
2. Introduces yourself in a natural way
3. Briefly mentions the date (e.g., "Today, March 4th" or "On this day, March 4th")
4. Makes it personal and engaging
5. DO NOT read the full title or make it too formal
6. Keep it short and punchy - no long introductions
"""

    if not use_special_effects:
        character_prompt += "\nIMPORTANT: DO NOT use any special effects markers such as (break), (long-break), (sigh), (laugh), etc. Create natural speech without these markers."

    character_prompt += f"\n\nIMPORTANT: Create a well-paced script aiming for a 1:30 to 2:00 minute video (250-300 words total).\n\n{system_prompt}"

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": character_prompt},
            {"role": "user", "content": f"Transform this content into brainrot style. Keep it concise and focused on the most important points:\n\n{content}"}
        ],
        "max_completion_tokens": 2000  # Reduced from 4000 to encourage brevity
    }

    for attempt in range(MAX_RETRIES):
        try:
            logger.info(
                f"{voice_context} API request attempt {attempt + 1}/{MAX_RETRIES}")
            api_start_time = time.time()

            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30  # 30 second timeout
            )

            api_duration = time.time() - api_start_time
            logger.info(
                f"{voice_context} API request completed in {api_duration:.2f} seconds with status code: {response.status_code}")

            if response.status_code == 200:
                result = response.json()["choices"][0]["message"]["content"]
                result_length = len(result)

                # Validate response content
                if not result or not result.strip():
                    error_msg = f"{voice_context} API returned empty response"
                    logger.error(error_msg)
                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY
                        logger.info(
                            f"{voice_context} Retrying in {wait_time:.1f}s")
                        time.sleep(wait_time)
                        continue
                    raise ValueError(error_msg)

                logger.info(
                    f"{voice_context} Received successful response ({result_length} characters)")
                return result.strip()
            elif response.status_code == 429:  # Rate limit
                if attempt < MAX_RETRIES - 1:
                    wait_time = (2 ** attempt) * RETRY_DELAY
                    logger.warning(
                        f"{voice_context} Rate limited. Waiting {wait_time:.1f}s before retry")
                    time.sleep(wait_time)
                    continue
            else:
                error_msg = f"{voice_context} OpenAI API Error: {response.status_code}. Response: {response.text}"
                logger.error(error_msg)
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY
                    logger.info(
                        f"{voice_context} Retrying in {wait_time:.1f}s")
                    time.sleep(wait_time)
                    continue
                raise ValueError(error_msg)

        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY
                logger.warning(
                    f"{voice_context} Request timeout. Retrying in {wait_time:.1f}s")
                time.sleep(wait_time)
                continue
            raise ValueError(
                f"{voice_context} API request timed out after {MAX_RETRIES} attempts")

        except Exception as e:
            error_msg = f"{voice_context} Exception during API call: {str(e)}"
            logger.error(error_msg)
            logger.exception(f"{voice_context} API call exception details:")
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY
                logger.info(f"{voice_context} Retrying in {wait_time:.1f}s")
                time.sleep(wait_time)
                continue
            raise ValueError(error_msg) from e

    raise ValueError(
        f"{voice_context} Failed to get response after {MAX_RETRIES} attempts")
