#!/usr/bin/env python3
"""
Test script to verify subtitle generation and application to video.
This script tests the subtitle creation process and checks if subtitles are being correctly applied.
"""

import os
import sys
import subprocess
import tempfile
import json
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def extract_subtitles_from_video(video_path, output_path=None):
    """Extract subtitles from a video file."""
    if output_path is None:
        # Create a temporary file for the subtitles
        temp_file = tempfile.NamedTemporaryFile(suffix='.ass', delete=False)
        output_path = temp_file.name
        temp_file.close()

    try:
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-map', '0:s:0',  # Select the first subtitle stream
            '-c', 'copy',
            output_path,
            '-y'  # Overwrite output file if it exists
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Warning: Could not extract subtitles: {result.stderr}")
            return None

        return output_path
    except Exception as e:
        print(f"Error extracting subtitles: {str(e)}")
        return None


def check_subtitle_file_exists(subtitle_path):
    """Check if a subtitle file exists and has content."""
    if not os.path.exists(subtitle_path):
        print(f"❌ Subtitle file does not exist: {subtitle_path}")
        return False

    file_size = os.path.getsize(subtitle_path)
    if file_size == 0:
        print(f"❌ Subtitle file is empty: {subtitle_path}")
        return False

    print(
        f"✅ Subtitle file exists and has content ({file_size} bytes): {subtitle_path}")
    return True


def check_subtitles_in_video(video_path):
    """Check if a video file has embedded subtitles."""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 's',
            '-show_entries', 'stream=index,codec_name,codec_type',
            '-of', 'json',
            video_path
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        subtitle_streams = data.get('streams', [])

        if subtitle_streams:
            print(f"✅ Video has {len(subtitle_streams)} subtitle stream(s):")
            for stream in subtitle_streams:
                print(
                    f"  - Stream #{stream['index']}: {stream.get('codec_name', 'unknown')}")
            return True
        else:
            print(f"❌ No subtitle streams found in video")
            return False
    except subprocess.CalledProcessError as e:
        print(f"Error checking subtitles in video: {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return False


def verify_subtitles_in_output_directory(output_dir, expected_subtitles_name=None):
    """
    Check if subtitle files exist in the output directory.
    If expected_subtitles_name is provided, look for a specific file, otherwise check for any .ass files.
    """
    if not os.path.exists(output_dir) or not os.path.isdir(output_dir):
        print(f"❌ Output directory does not exist: {output_dir}")
        return False

    if expected_subtitles_name:
        subtitle_path = os.path.join(output_dir, expected_subtitles_name)
        return check_subtitle_file_exists(subtitle_path)
    else:
        # Look for any .ass subtitle files
        subtitle_files = list(Path(output_dir).glob("*.ass"))

        if not subtitle_files:
            print(f"❌ No subtitle files found in directory: {output_dir}")
            return False

        print(f"Found {len(subtitle_files)} subtitle file(s) in directory:")
        all_valid = True
        for subtitle_file in subtitle_files:
            valid = check_subtitle_file_exists(str(subtitle_file))
            if not valid:
                all_valid = False

        return all_valid


def inspect_subtitle_content(subtitle_path):
    """Inspect the content of a subtitle file to verify it has valid formatting."""
    if not os.path.exists(subtitle_path):
        print(f"❌ Subtitle file does not exist: {subtitle_path}")
        return False

    try:
        with open(subtitle_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for basic ASS subtitle format sections
        has_script_info = "[Script Info]" in content
        has_styles = "[V4+ Styles]" or "[Styles]" in content
        has_events = "[Events]" in content
        has_dialogue = "Dialogue:" in content

        print(f"Subtitle format check:")
        print(f"  - Script Info section: {'✅' if has_script_info else '❌'}")
        print(f"  - Styles section: {'✅' if has_styles else '❌'}")
        print(f"  - Events section: {'✅' if has_events else '❌'}")
        print(f"  - Contains dialogue lines: {'✅' if has_dialogue else '❌'}")

        # Print a preview of the content
        preview_length = min(500, len(content))
        print(f"\nSubtitle content preview (first {preview_length} chars):")
        print("-" * 40)
        print(content[:preview_length])
        print("-" * 40)

        return has_script_info and has_styles and has_events and has_dialogue
    except Exception as e:
        print(f"Error inspecting subtitle content: {str(e)}")
        return False


def analyze_subtitle_mapping_in_ffmpeg_command(file_path):
    """Analyze the ffmpeg command in the given file to check subtitle mapping."""
    if not os.path.exists(file_path):
        print(f"❌ File does not exist: {file_path}")
        return False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Look for ffmpeg commands related to subtitle mapping
        import re

        # Check for subtitle file inclusion
        subtitle_file_pattern = r'-i\s+([^\s]+\.ass)'
        subtitle_files = re.findall(subtitle_file_pattern, content)

        # Check for subtitle mapping
        subtitle_map_pattern = r'-map\s+\d+:s(?::\d+)?'
        subtitle_maps = re.findall(subtitle_map_pattern, content)

        # Check for subtitle filter complexes
        subtitle_filter_pattern = r'subtitles=([^\s,]+)'
        subtitle_filters = re.findall(subtitle_filter_pattern, content)

        # Check for ASS subtitle filter
        ass_filter_pattern = r'ass=([^\s,]+)'
        ass_filters = re.findall(ass_filter_pattern, content)

        print("\nAnalysis of ffmpeg subtitle mapping:")

        if subtitle_files:
            print(f"✅ Found subtitle input file(s): {subtitle_files}")
        else:
            print(f"❌ No subtitle input files found")

        if subtitle_maps:
            print(f"✅ Found subtitle mapping(s): {subtitle_maps}")
        else:
            print(f"❌ No subtitle mappings found")

        if subtitle_filters:
            print(f"✅ Found subtitles filter(s): {subtitle_filters}")
        else:
            print(f"❌ No subtitles filters found")

        if ass_filters:
            print(f"✅ Found ASS subtitle filter(s): {ass_filters}")
        else:
            print(f"❌ No ASS subtitle filters found")

        # Check for -c:s codec settings
        subtitle_codec_pattern = r'-c:s\s+(\w+)'
        subtitle_codecs = re.findall(subtitle_codec_pattern, content)

        if subtitle_codecs:
            print(f"✅ Found subtitle codec setting(s): {subtitle_codecs}")
        else:
            print(f"❌ No subtitle codec settings found")

        return bool(subtitle_files or subtitle_maps or subtitle_filters or ass_filters)
    except Exception as e:
        print(f"Error analyzing ffmpeg command: {str(e)}")
        return False


def test_subtitle_generation_in_video_generator():
    """Test the subtitle generation logic in video_generator.py."""
    print("\n=== Testing Subtitle Generation in video_generator.py ===")

    try:
        # Import video_generator module
        from video_generator import add_subtitles_and_overlay_audio, generate_subtitles
        import inspect

        # Analyze the add_subtitles_and_overlay_audio function
        add_subtitles_source = inspect.getsource(
            add_subtitles_and_overlay_audio)
        print("\nAnalyzing add_subtitles_and_overlay_audio function:")

        # Look for subtitle-related operations
        if "subtitles" in add_subtitles_source.lower():
            print("✅ Function contains references to subtitles")

            # Check for the proper ffmpeg subtitle mapping
            subtitle_mapping_pattern = r'-vf\s+.*?subtitles=|ass=|-map\s+\d+:s'
            if re.search(subtitle_mapping_pattern, add_subtitles_source, re.IGNORECASE):
                print(
                    "✅ Function appears to have proper subtitle mapping in ffmpeg command")
            else:
                print(
                    "❌ Function may be missing proper subtitle mapping in ffmpeg command")

                # Suggest a potential fix
                print("\nPotential fix:")
                print(
                    "Make sure the ffmpeg command includes proper subtitle mapping, for example:")
                print("  -vf \"subtitles='{subtitle_path}'\" or")
                print("  -vf \"ass='{subtitle_path}'\"")
        else:
            print("❌ Function does not contain references to subtitles")

        # Analyze the generate_subtitles function
        generate_subtitles_source = inspect.getsource(generate_subtitles)
        print("\nAnalyzing generate_subtitles function:")

        if "convert_timing_to_ass" in generate_subtitles_source:
            print("✅ Function calls convert_timing_to_ass to create ASS subtitle file")
        else:
            print(
                "❌ Function may be missing call to convert subtitle timing to ASS format")

        return True
    except ImportError:
        print("❌ Could not import video_generator module")
        return False
    except Exception as e:
        print(f"Error analyzing subtitle generation: {str(e)}")
        return False


if __name__ == "__main__":
    # Test subtitle generation logic
    test_subtitle_generation_in_video_generator()

    # Analyze ffmpeg commands in video_generator.py
    print("\n=== Analyzing ffmpeg commands in video_generator.py ===")
    video_generator_path = os.path.join(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))), "video_generator.py")
    analyze_subtitle_mapping_in_ffmpeg_command(video_generator_path)

    # If a video file path is provided as an argument, check if it has subtitles
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        if os.path.exists(video_path):
            print(
                f"\n=== Checking for subtitles in video: {os.path.basename(video_path)} ===")
            check_subtitles_in_video(video_path)

            # Extract subtitles if possible
            output_dir = os.path.dirname(video_path)
            subtitle_path = os.path.join(
                output_dir, f"{os.path.splitext(os.path.basename(video_path))[0]}_extracted.ass")
            extracted_subtitle_path = extract_subtitles_from_video(
                video_path, subtitle_path)

            if extracted_subtitle_path:
                inspect_subtitle_content(extracted_subtitle_path)
        else:
            print(f"❌ Video file not found: {video_path}")

    # If an output directory is provided as the second argument, check for subtitle files
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
        if os.path.exists(output_dir) and os.path.isdir(output_dir):
            print(
                f"\n=== Checking for subtitle files in directory: {output_dir} ===")
            verify_subtitles_in_output_directory(output_dir)
