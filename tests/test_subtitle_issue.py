#!/usr/bin/env python3
"""
Diagnostic script to troubleshoot missing subtitles in videos.
This script checks each step of the subtitle generation and application process.
"""

import os
import sys
import json
import subprocess
import re
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_ffmpeg_subtitle_support():
    """Check if ffmpeg has subtitle support enabled."""
    try:
        result = subprocess.run(
            ['ffmpeg', '-filters'],
            capture_output=True,
            text=True
        )
        
        # Check for subtitle filters
        subtitle_filters = ['subtitles', 'ass']
        found_filters = []
        
        for subtitle_filter in subtitle_filters:
            if f" {subtitle_filter}" in result.stdout:
                found_filters.append(subtitle_filter)
        
        if found_filters:
            print(f"✅ ffmpeg has subtitle filters: {', '.join(found_filters)}")
        else:
            print("❌ ffmpeg doesn't appear to have subtitle filters")
            print("This could be the root cause of missing subtitles")
        
        # Check for subtitle encoders
        encoder_result = subprocess.run(
            ['ffmpeg', '-encoders'],
            capture_output=True,
            text=True
        )
        
        subtitle_encoders = ['ass', 'ssa', 'srt', 'webvtt']
        found_encoders = []
        
        for encoder in subtitle_encoders:
            if f" {encoder}" in encoder_result.stdout:
                found_encoders.append(encoder)
        
        if found_encoders:
            print(f"✅ ffmpeg has subtitle encoders: {', '.join(found_encoders)}")
        else:
            print("❌ ffmpeg doesn't appear to have subtitle encoders")
            
    except subprocess.SubprocessError as e:
        print(f"❌ Error checking ffmpeg: {str(e)}")


def check_subtitle_file(subtitle_path):
    """Check if the subtitle file exists and has valid content."""
    if not os.path.exists(subtitle_path):
        print(f"❌ Subtitle file not found: {subtitle_path}")
        return False
    
    if os.path.getsize(subtitle_path) == 0:
        print(f"❌ Subtitle file is empty: {subtitle_path}")
        return False
    
    try:
        with open(subtitle_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for essential ASS file sections
        has_script_info = "[Script Info]" in content
        has_styles = "[V4+ Styles]" in content or "[Styles]" in content
        has_events = "[Events]" in content
        has_dialogue = "Dialogue:" in content
        
        print(f"\nSubtitle file check ({os.path.basename(subtitle_path)}):")
        print(f"  - Size: {os.path.getsize(subtitle_path)} bytes")
        print(f"  - Script Info section: {'✅' if has_script_info else '❌'}")
        print(f"  - Styles section: {'✅' if has_styles else '❌'}")
        print(f"  - Events section: {'✅' if has_events else '❌'}")
        print(f"  - Contains dialogue lines: {'✅' if has_dialogue else '❌'}")
        
        # Count dialogue lines
        dialogue_count = content.count("Dialogue:")
        print(f"  - Number of dialogue lines: {dialogue_count}")
        
        if dialogue_count == 0:
            print("❌ No dialogue lines found in subtitle file")
            return False
            
        # Print sample dialogue lines
        if has_dialogue:
            print("\nSample dialogue lines:")
            dialogue_lines = re.findall(r"Dialogue:.*", content)
            for i in range(min(3, len(dialogue_lines))):
                print(f"  {dialogue_lines[i]}")
        
        return has_script_info and has_styles and has_events and has_dialogue
        
    except Exception as e:
        print(f"❌ Error reading subtitle file: {str(e)}")
        return False


def analyze_video_file(video_path):
    """Analyze a video file for subtitle streams."""
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return
    
    try:
        # Check video streams
        probe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_streams',
            '-of', 'json',
            video_path
        ]
        
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Error probing video file: {result.stderr}")
            return
        
        data = json.loads(result.stdout)
        
        # Count stream types
        stream_types = {}
        subtitle_streams = []
        
        for stream in data.get('streams', []):
            stream_type = stream.get('codec_type')
            if stream_type:
                stream_types[stream_type] = stream_types.get(stream_type, 0) + 1
                
                if stream_type == 'subtitle':
                    subtitle_streams.append(stream)
        
        print(f"\nVideo file analysis ({os.path.basename(video_path)}):")
        print(f"  - Stream types: {stream_types}")
        
        if 'subtitle' in stream_types:
            print(f"✅ Video contains {stream_types['subtitle']} subtitle stream(s)")
            for i, stream in enumerate(subtitle_streams):
                print(f"  - Subtitle stream {i}: codec={stream.get('codec_name')}")
        else:
            print("❌ Video does not contain any subtitle streams")
            print("This confirms subtitles are not being embedded in the video")
    
    except Exception as e:
        print(f"❌ Error analyzing video file: {str(e)}")


def check_ffmpeg_commands_in_codebase():
    """Check ffmpeg commands in the codebase that deal with subtitles."""
    print("\nAnalyzing ffmpeg commands in video_generator.py:")
    
    try:
        # Get the absolute path to video_generator.py
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video_generator.py")
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Look for ffmpeg commands with subtitle filters
        subtitle_filter_pattern = r"subtitle_filter\s*=\s*f\"([^\"]+)\""
        matches = re.findall(subtitle_filter_pattern, content)
        
        if matches:
            print("✅ Found subtitle filter definition:")
            for match in matches:
                print(f"  {match}")
                
            # Look for where this filter is used
            for match in matches:
                # Escape special regex characters in the match
                escaped_match = re.escape(match)
                # Find where this filter string is used in an ffmpeg command
                usage_pattern = r"subprocess\.run\(\s*\[\s*'ffmpeg'[^]]*?{0}[^]]*?\]".format(escaped_match.replace("'", "['\"]").replace('"', "['\"]"))
                usage_matches = re.findall(usage_pattern, content, re.DOTALL)
                
                if usage_matches:
                    print("✅ Subtitle filter is used in ffmpeg commands")
                else:
                    print("❌ Subtitle filter is defined but not used in ffmpeg commands")
        else:
            print("❌ No subtitle filter definitions found")
            
        # Check for the add_subtitles_and_overlay_audio function
        function_pattern = r"def add_subtitles_and_overlay_audio\([^)]*\):[^}]*?ffmpeg[^}]*?subtitle"
        function_match = re.search(function_pattern, content, re.DOTALL)
        
        if function_match:
            print("✅ Found add_subtitles_and_overlay_audio function with subtitle handling")
            
            # Check if subtitle_path is validated
            validation_pattern = r"subtitle_valid\s*=\s*os\.path\.exists\([^)]+\)\s*and\s*os\.path\.getsize\([^)]+\)\s*>\s*0"
            validation_match = re.search(validation_pattern, content)
            
            if validation_match:
                print("✅ Subtitle path is properly validated before use")
            else:
                print("❌ Subtitle path validation might be insufficient")
                
            # Check debug logging for subtitle issues
            debug_pattern = r"print\(f[\"'].*subtitle.*[\"']\)"
            debug_matches = re.findall(debug_pattern, content)
            
            if debug_matches:
                print("✅ Found subtitle debug logging:")
                for match in debug_matches[:3]:  # Show first 3 matches
                    print(f"  {match}")
            else:
                print("❌ No subtitle debug logging found")
        else:
            print("❌ Could not find add_subtitles_and_overlay_audio function with subtitle handling")
    
    except Exception as e:
        print(f"❌ Error analyzing ffmpeg commands: {str(e)}")


def main():
    print("=== Subtitle Issue Diagnostic ===\n")
    
    # Check ffmpeg subtitle support
    print("Checking ffmpeg subtitle support:")
    check_ffmpeg_subtitle_support()
    
    # Check for arguments
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
        if os.path.exists(output_dir) and os.path.isdir(output_dir):
            print(f"\nChecking output directory: {output_dir}")
            
            # Check for subtitle files
            subtitle_files = list(Path(output_dir).glob("*.ass"))
            if subtitle_files:
                print(f"✅ Found {len(subtitle_files)} subtitle file(s)")
                for subtitle_file in subtitle_files:
                    check_subtitle_file(str(subtitle_file))
            else:
                print("❌ No subtitle files found in output directory")
                
            # Check video files
            video_files = list(Path(output_dir).glob("*.mp4")) + list(Path(output_dir).glob("*.mkv"))
            if video_files:
                print(f"✅ Found {len(video_files)} video file(s)")
                for video_file in video_files[:1]:  # Analyze just the first video to avoid too much output
                    analyze_video_file(str(video_file))
            else:
                print("❌ No video files found in output directory")
        else:
            print(f"❌ Invalid output directory: {output_dir}")
    
    # Check ffmpeg commands in codebase
    check_ffmpeg_commands_in_codebase()
    
    print("\n=== Diagnostic Complete ===")
    print("Possible issues to check:")
    print("1. Make sure subtitle files are being generated with dialogue lines")
    print("2. Verify the subtitle filter in ffmpeg commands is correctly formatted")
    print("3. Check if ffmpeg has subtitle support enabled")
    print("4. Ensure video encoding is compatible with subtitle embedding")


if __name__ == "__main__":
    main() 