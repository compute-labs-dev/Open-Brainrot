#!/usr/bin/env python3
"""
Script to generate a test video with subtitles using the fixed code.
This script creates a simple video with subtitles to verify the fixes.
"""

import os
import sys
import uuid
import argparse
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our modules
try:
    from video_generator import generate_subtitles, add_subtitles_and_overlay_audio, get_duration
    from brainrot_generator import transform_to_brainrot, clean_text_for_tts
    from audio import audio_wrapper, convert_audio
    from main import add_initial_silence
except ImportError as e:
    print(f"Error importing modules: {str(e)}")
    sys.exit(1)


def generate_test_video(text=None, voice="donald_trump", model="claude", use_brainrot=False):
    """Generate a test video with subtitles."""
    print("\n=== Generating Test Video with Subtitles ===")

    # Create a timestamp for the output directory
    timestamp = int(datetime.now().timestamp())
    output_dir = os.path.join("outputs", f"{timestamp}_{voice}")
    os.makedirs(output_dir, exist_ok=True)

    # Use default text if none provided
    if not text:
        text = """This is a test video with subtitles.
The subtitles should be visible in the final video.
This test verifies that the subtitle generation and application fixes work correctly.
The text should be displayed at the bottom of the video with good visibility."""

    # Transform text if requested
    if use_brainrot:
        print("Transforming text using brainrot generator...")
        # Save the original text to file first
        input_text_path = os.path.join(output_dir, f"input_text_{voice}.txt")
        with open(input_text_path, "w", encoding="utf-8") as f:
            f.write(text)

        # Transform the text
        transformed_text, _ = transform_to_brainrot(
            input_text_path, voice=voice, model=model)
        text = transformed_text
        print(f"Text transformed. Word count: {len(text.split())}")

    # Save the final text to file
    text_path = os.path.join(output_dir, f"test_text_{voice}.txt")
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"✅ Saved text to: {text_path}")

    # Define paths for the test
    audio_path = os.path.join(output_dir, f"test_audio_{voice}.wav")
    audio_converted_path = os.path.join(
        output_dir, f"test_audio_converted_{voice}.wav")

    # Generate audio from the text
    try:
        print(f"Generating audio to: {audio_path}")
        audio_wrapper(text_path, file_path=audio_path, voice=voice)

        # Convert audio to the format needed for video
        convert_audio(audio_path, audio_converted_path)
        print(f"✅ Audio generated and converted: {audio_converted_path}")

        # Add a small silence at the beginning of the audio to help with subtitle synchronization
        print(f"Adding initial silence to audio for better subtitle synchronization")
        add_initial_silence(audio_converted_path, silence_duration=500)

        # Use the converted audio
        audio_path = audio_converted_path
    except Exception as e:
        print(f"❌ Error generating audio: {str(e)}")
        print("Using default audio file instead")
        # Fall back to default audio if available
        default_audio = "assets/default.mp3"
        if os.path.exists(default_audio):
            audio_path = default_audio
        else:
            # Try to find a system audio file
            for path in ["/System/Library/Sounds/Ping.aiff", "/usr/share/sounds/alsa/Front_Center.wav"]:
                if os.path.exists(path):
                    audio_path = path
                    break

    video_path = "assets/minecraft.mp4"  # Use a default video file
    if not os.path.exists(video_path):
        print(f"❌ Default video file not found: {video_path}")
        print("Please specify a valid video file path")
        return False

    # Define output paths
    subtitle_path = os.path.join(output_dir, f"test_subtitles_{voice}.ass")
    output_path = os.path.join(output_dir, f"test_video_{voice}.mp4")

    # Generate subtitles using the SAME TEXT as the audio
    print(f"Generating subtitles to: {subtitle_path}")
    if use_brainrot:
        print("Using transformed text for subtitles")
    else:
        print("Bypassing text transformation as requested - using original text directly")

    generate_subtitles(audio_path, text, subtitle_path,
                       voice=voice, model="bypass_transform")

    # Check if subtitle file was created
    if os.path.exists(subtitle_path) and os.path.getsize(subtitle_path) > 0:
        print(f"✅ Subtitle file created: {subtitle_path}")

        # Check if subtitle file contains dialogue lines
        with open(subtitle_path, "r") as f:
            subtitle_content = f.read()
            dialogue_count = subtitle_content.count("Dialogue:")
            if dialogue_count > 0:
                print(
                    f"✅ Subtitle file contains {dialogue_count} dialogue lines")
            else:
                print("❌ Subtitle file does not contain any dialogue lines")
                return False
    else:
        print(f"❌ Failed to create subtitle file: {subtitle_path}")
        return False

    # Generate video with subtitles
    print(f"Generating video with subtitles to: {output_path}")
    result_path = add_subtitles_and_overlay_audio(
        video_path, audio_path, subtitle_path, output_path)

    # Check if video was created
    if os.path.exists(result_path) and os.path.getsize(result_path) > 0:
        print(f"✅ Video with subtitles created: {result_path}")
        print(f"Video duration: {get_duration(result_path):.2f} seconds")
        print(f"Please check the video to confirm subtitles are visible")
        return result_path
    else:
        print(f"❌ Failed to create video with subtitles: {result_path}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a test video with subtitles")
    parser.add_argument("--text", help="Text to use for the subtitles")
    parser.add_argument("--voice", default="donald_trump",
                        help="Voice to use for the subtitles")
    parser.add_argument("--model", default="claude",
                        help="Model to use for text transformation")
    parser.add_argument("--use_brainrot", action="store_true",
                        help="Use brainrot transformation on the input text")
    args = parser.parse_args()

    result = generate_test_video(
        text=args.text, voice=args.voice, model=args.model, use_brainrot=args.use_brainrot)
    if result:
        print(f"\n✅ Test video generation completed successfully")
        print(f"Video saved at: {result}")
        sys.exit(0)
    else:
        print(f"\n❌ Test video generation failed")
        sys.exit(1)
