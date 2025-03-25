#!/usr/bin/env python3
"""
Test script to verify the subtitle fixes.
This script generates a test video with subtitles to confirm the fixes work.
"""

import os
import sys
import uuid
import tempfile
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our modules
try:
    from video_generator import generate_subtitles, add_subtitles_and_overlay_audio, get_duration
    from main import add_initial_silence
except ImportError as e:
    print(f"Error importing modules: {str(e)}")
    sys.exit(1)


def test_subtitle_generation():
    """Test the subtitle generation and application process."""
    print("\n=== Testing Subtitle Generation and Application ===")

    try:
        # Create a temporary directory for the test
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test text file
            test_text = """This is a test text for subtitle generation.
It should create subtitles with multiple lines.
Let's see if the fixes work properly.
The subtitles should be visible in the final video."""

            text_file_path = os.path.join(temp_dir, "test_text.txt")
            with open(text_file_path, "w") as f:
                f.write(test_text)

            # Define paths for the test
            test_id = str(uuid.uuid4())[:8]
            output_dir = os.path.join(
                "outputs", f"test_subtitle_fix_{test_id}")
            os.makedirs(output_dir, exist_ok=True)

            audio_path = "assets/default.mp3"  # Use a default audio file
            if not os.path.exists(audio_path):
                print(f"❌ Default audio file not found: {audio_path}")
                print("Using a system audio file instead")
                # Try to find a system audio file
                for path in ["/System/Library/Sounds/Ping.aiff", "/usr/share/sounds/alsa/Front_Center.wav"]:
                    if os.path.exists(path):
                        audio_path = path
                        break

            # Add a small silence at the beginning of the audio to help with subtitle synchronization
            print(f"Adding initial silence to audio for better subtitle synchronization")
            temp_audio_path = os.path.join(
                output_dir, "audio_with_silence.mp3")
            add_initial_silence(
                audio_path, output_path=temp_audio_path, silence_duration=500)
            audio_path = temp_audio_path

            video_path = "assets/minecraft.mp4"  # Use a default video file
            if not os.path.exists(video_path):
                print(f"❌ Default video file not found: {video_path}")
                print("Please specify a valid video file path")
                return False

            subtitle_path = os.path.join(output_dir, "test_subtitles.ass")
            output_path = os.path.join(
                output_dir, "test_video_with_subtitles.mp4")

            # Generate subtitles
            print(f"Generating subtitles to: {subtitle_path}")
            generate_subtitles(audio_path, test_text, subtitle_path,
                               voice="test_voice", model="test_model")

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
                print(
                    f"Video duration: {get_duration(result_path):.2f} seconds")
                print(f"Please check the video to confirm subtitles are visible")
                return True
            else:
                print(
                    f"❌ Failed to create video with subtitles: {result_path}")
                return False

    except Exception as e:
        print(f"❌ Error in test_subtitle_generation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_subtitle_generation()
    if success:
        print("\n✅ Subtitle generation and application test completed successfully")
        sys.exit(0)
    else:
        print("\n❌ Subtitle generation and application test failed")
        sys.exit(1)
