#!/usr/bin/env python3
"""
Test script to measure video duration and ensure it's within the desired range (1:30-3:30 minutes).
This script also tests text length to estimate video duration before generation.
"""

import os
import sys
import subprocess
import json
from datetime import datetime, timedelta
import re
import math

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MIN_DURATION_SECONDS = 90  # 1:30 minutes
MAX_DURATION_SECONDS = 210  # 3:30 minutes

# Estimated speaking rate (words per minute)
# This is an approximation and may need adjustment
AVERAGE_SPEAKING_RATE = 150


def get_video_duration(video_path):
    """Get the duration of a video file in seconds using ffprobe."""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json',
            video_path
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        duration = float(data['format']['duration'])

        return duration
    except subprocess.CalledProcessError as e:
        print(f"Error getting video duration: {e.stderr}")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None


def estimate_duration_from_text(text, voice="donald_trump"):
    """
    Estimate the duration of speech in seconds based on text length and speaking rate.
    Different voices may have different speaking rates.
    """
    # Count words
    words = re.findall(r'\w+', text)
    word_count = len(words)

    # Get voice-specific speed multiplier
    from audio import VOICE_SPEEDS
    speed_multiplier = VOICE_SPEEDS.get(voice, VOICE_SPEEDS["default"])

    # Calculate duration in minutes, then convert to seconds
    # Adjust for the speed multiplier (higher speed = shorter duration)
    estimated_duration_minutes = word_count / \
        (AVERAGE_SPEAKING_RATE * speed_multiplier)
    estimated_duration_seconds = estimated_duration_minutes * 60

    return estimated_duration_seconds, word_count


def truncate_text_to_target_duration(text, target_duration_seconds, voice="donald_trump"):
    """
    Truncate text to approximately match the target duration.
    Returns the truncated text and estimated duration.
    """
    # If text is already short enough, return it as is
    estimated_duration, word_count = estimate_duration_from_text(text, voice)
    if estimated_duration <= target_duration_seconds:
        return text, estimated_duration, word_count

    # Calculate target word count
    from audio import VOICE_SPEEDS
    speed_multiplier = VOICE_SPEEDS.get(voice, VOICE_SPEEDS["default"])
    target_word_count = int((target_duration_seconds / 60)
                            * AVERAGE_SPEAKING_RATE * speed_multiplier)

    # Split text into words and take only the number needed
    words = re.findall(r'\w+', text)
    truncated_words = words[:target_word_count]

    # Find the last complete sentence
    joined_text = ' '.join(truncated_words)
    sentences = re.split(r'(?<=[.!?])\s+', joined_text)

    if len(sentences) > 1:
        # Remove the last incomplete sentence
        truncated_text = ' '.join(sentences[:-1])
        # Add trailing punctuation if missing
        if not truncated_text[-1] in '.!?':
            truncated_text += '.'
    else:
        # If there's only one sentence, use it and add a period
        truncated_text = sentences[0]
        if not truncated_text[-1] in '.!?':
            truncated_text += '.'

    # Recalculate the estimated duration
    new_estimated_duration, new_word_count = estimate_duration_from_text(
        truncated_text, voice)

    return truncated_text, new_estimated_duration, new_word_count


def test_text_truncation():
    """Test the text truncation function."""
    print("\n=== Testing Text Truncation for Video Duration Control ===")

    # Sample long text that would produce a video longer than the maximum duration
    long_text = """
    Agent Daily Digest Bot
    APP  Today at 2:36 AM
    Daily Digest (Mar 4, 2025) – AI, Compute, & Web3
    :earth_americas: Macro:
    • :us: Trump's 25% tariffs on Canada and Mexico, 20% on China took effect; all three countries announced retaliatory measures.
    • :us: Treasury Secretary Bessent confirms administration is "set on bringing interest rates down."
    • :us: IRS drafting plans to cut up to half of its 90,000-person workforce through layoffs and buyouts.
    :computer: Technology & Infrastructure:
    • BlackRock consortium acquires Hutchison Port Holdings for $23 billion, gaining control of 43 ports in 23 countries.
    • T-Mobile's parent Deutsche Telekom announced sub-$1K AI phone with Perplexity Assistant launching later this year.
    • Reddit co-founder Alexis Ohanian joins bid to acquire TikTok US and "bring it on-chain."
    :robot_face: AI & Research:
    • OpenAI launching NextGenAI consortium with 15 leading institutions to advance AI research and education.
    • Microsoft debuts Dragon Copilot for healthcare, automating clinical documentation with ambient listening and voice dictation.
    • Google's Project Astra video capabilities coming to Android this month for Gemini Advanced subscribers.
    :coin: Crypto/Web3:
    • :us: White House crypto summit scheduled for Friday; Coinbase CEO and MicroStrategy's Michael Saylor among confirmed attendees.
    • :flag-mx: Mexican billionaire Ricardo Salinas allocates 70% of his $5.8 billion portfolio to Bitcoin.
    • :flag-sv: El Salvador President Bukele affirms country will continue Bitcoin purchases despite IMF's request to stop.
    • :us: White House announces support for rescinding the DeFi broker rule, calling it "an 11th hour attack on crypto."
    • Bybit hackers successfully launder 100% of stolen $1.4 billion in crypto within 10 days.
    """

    # Test different voice types
    voices = ["donald_trump", "keanu_reeves", "kermit_the_frog"]

    for voice in voices:
        print(f"\nTesting voice: {voice}")

        # Measure original text
        original_duration, original_word_count = estimate_duration_from_text(
            long_text, voice)
        print(
            f"Original text: {original_word_count} words, estimated duration: {original_duration:.2f} seconds ({original_duration/60:.2f} minutes)")

        # Truncate to maximum duration
        truncated_text, truncated_duration, truncated_word_count = truncate_text_to_target_duration(
            long_text, MAX_DURATION_SECONDS, voice
        )

        print(
            f"Truncated text: {truncated_word_count} words, estimated duration: {truncated_duration:.2f} seconds ({truncated_duration/60:.2f} minutes)")
        print(
            f"Target maximum duration: {MAX_DURATION_SECONDS} seconds ({MAX_DURATION_SECONDS/60:.2f} minutes)")

        # Check if within range
        if MIN_DURATION_SECONDS <= truncated_duration <= MAX_DURATION_SECONDS:
            print(
                f"✅ Duration within target range: {MIN_DURATION_SECONDS/60:.2f}-{MAX_DURATION_SECONDS/60:.2f} minutes")
        else:
            print(
                f"❌ Duration outside target range: {MIN_DURATION_SECONDS/60:.2f}-{MAX_DURATION_SECONDS/60:.2f} minutes")

        # Print truncated text preview
        preview_length = min(200, len(truncated_text))
        print(
            f"\nTruncated text preview:\n{truncated_text[:preview_length]}...")


def test_video_duration(video_path):
    """Test if a video file's duration is within the desired range."""
    print(f"\n=== Testing Video Duration: {os.path.basename(video_path)} ===")

    duration = get_video_duration(video_path)

    if duration is None:
        print("❌ Could not determine video duration")
        return False

    print(
        f"Video duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
    print(f"Target range: {MIN_DURATION_SECONDS/60:.2f}-{MAX_DURATION_SECONDS/60:.2f} minutes ({MIN_DURATION_SECONDS}-{MAX_DURATION_SECONDS} seconds)")

    if MIN_DURATION_SECONDS <= duration <= MAX_DURATION_SECONDS:
        print(f"✅ Duration within target range")
        return True
    else:
        print(f"❌ Duration outside target range")
        return False


if __name__ == "__main__":
    # Test text truncation logic
    test_text_truncation()

    # If a video file path is provided as an argument, test its duration
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        if os.path.exists(video_path):
            test_video_duration(video_path)
        else:
            print(f"❌ Video file not found: {video_path}")
