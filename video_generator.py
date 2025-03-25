import subprocess
import os
import math
import gentle
import re
import json
import random
from pathlib import Path
from brainrot_generator import transform_to_brainrot, clean_text_for_tts
from pydub import AudioSegment


def get_duration(file_path):
    """Get duration of a media file using ffprobe"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        file_path
    ]
    return float(subprocess.check_output(cmd).decode('utf-8').strip())

# Use this if you need to trim longer videos from sample video


def trim_video(input_path, output_path, duration=120):
    """Trim video to specified duration"""
    # Only trim if output doesn't exist or is older than input
    if not os.path.exists(output_path) or \
       os.path.getmtime(input_path) > os.path.getmtime(output_path):
        command = [
            'ffmpeg',
            '-i', input_path,
            '-t', str(duration),
            '-c', 'copy',
            '-y',  # Overwrite without asking
            output_path
        ]
        subprocess.run(command, check=True)

# Crop video to 9:16 aspect ratio


def crop_to_vertical(input_path, output_path):
    """Crop video to 9:16 aspect ratio (vertical video)"""
    subprocess.run([
        'ffmpeg',
        '-i', input_path,
        '-vf', 'crop=iw*9/16:ih:iw/2-iw*9/32:0',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-profile:v', 'high',
        '-c:a', 'copy',
        '-y',
        output_path
    ], check=True)
    return output_path


# ===== SUBTITLE PROCESSING FUNCTIONS =====

class SubtitleEntry:
    """A class representing a single subtitle entry with timing and text"""

    def __init__(self, text, start_time, end_time):
        self.text = text
        self.start_time = start_time
        self.end_time = end_time

    def __repr__(self):
        return f"SubtitleEntry({self.start_time:.2f}-{self.end_time:.2f}: '{self.text}')"


def format_time_ass(seconds):
    """Format time in ASS format (H:MM:SS.cc)"""
    if isinstance(seconds, str):
        return seconds

    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds = seconds % 60
    centiseconds = int((seconds - int(seconds)) * 100)
    return f"{hours}:{minutes:02d}:{int(seconds):02d}.{centiseconds:02d}"


def parse_ass_subtitles(subtitle_path):
    """Parse an ASS subtitle file and return a list of SubtitleEntry objects"""
    if not os.path.exists(subtitle_path) or os.path.getsize(subtitle_path) == 0:
        print(
            f"Warning: Subtitle file {subtitle_path} does not exist or is empty")
        return []

    dialogue_entries = []

    try:
        with open(subtitle_path, 'r', encoding='utf-8') as f:
            subtitle_content = f.read()

        # Extract dialogue lines
        for line in subtitle_content.splitlines():
            if line.startswith('Dialogue:'):
                # Split only first 9 commas to keep text intact
                parts = line.split(',', 9)
                if len(parts) >= 10:
                    layer, start_time, end_time = parts[0:3]
                    text = parts[9]

                    # Convert ASS time format (H:MM:SS.cc) to seconds
                    def time_to_seconds(time_str):
                        h, m, s = time_str.split(':')
                        return float(h) * 3600 + float(m) * 60 + float(s)

                    start_sec = time_to_seconds(start_time)
                    end_sec = time_to_seconds(end_time)

                    dialogue_entries.append(
                        SubtitleEntry(text, start_sec, end_sec))

                print(
                    f"Successfully parsed {len(dialogue_entries)} subtitle entries from ASS file")
    except Exception as e:
        print(f"Error parsing subtitle file: {str(e)}")

    return dialogue_entries


def create_fallback_subtitles():
    """Create fallback subtitles for testing"""
    test_texts = [
        "This is subtitle 1 - Testing visibility",
        "This is subtitle 2 - Should appear after subtitle 1",
        "This is subtitle 3 - One subtitle at a time",
        "This is subtitle 4 - Final test subtitle"
    ]

    dialogue_entries = []
    for i, text in enumerate(test_texts):
        # Each subtitle appears for 5 seconds with 1 second gap
        start_time = i * 6
        end_time = start_time + 5
        dialogue_entries.append(SubtitleEntry(text, start_time, end_time))

    return dialogue_entries


def create_non_overlapping_subtitles(entries):
    """Ensure subtitles don't overlap by adjusting end times"""
    if not entries:
        return []

    # Sort entries by start time to ensure proper ordering
    sorted_entries = sorted(entries.copy(), key=lambda e: e.start_time)

    # Adjust end times to prevent overlap
    for i in range(len(sorted_entries) - 1):
        if sorted_entries[i].end_time > sorted_entries[i+1].start_time:
            # If current entry overlaps with next, cut off at start of next
            sorted_entries[i].end_time = sorted_entries[i+1].start_time

            # Add a small gap between subtitles for better readability (0.2 seconds)
            if sorted_entries[i].end_time > 0.2:
                sorted_entries[i].end_time -= 0.2

    return sorted_entries


def generate_ffmpeg_filters(subtitle_entries, font_size=80, font_path="/System/Library/Fonts/Helvetica.ttc"):
    """Generate FFmpeg drawtext filters for subtitle entries"""
    filter_complex = []

    for i, entry in enumerate(subtitle_entries):
        # Clean text for FFmpeg drawtext filter
        clean_text = entry.text.replace("'", "'\\''").replace(
            ":", "\\:").replace(",", "\\,")

        # Create a complex condition that ensures only one subtitle shows at a time
        # Position subtitle in center of screen both horizontally and vertically
        filter_text = (
            f"drawtext=fontfile={font_path}:fontsize={font_size}:"
            f"fontcolor=white:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:text='{clean_text}':"
            f"enable='between(t,{entry.start_time},{entry.end_time})'"
        )

        filter_complex.append(filter_text)

    # Join all filters with commas
    filter_string = ','.join(filter_complex)

    return filter_string


def add_subtitles_and_overlay_audio(video_path, audio_path, subtitle_path, output_path):
    """Add subtitles to a video and overlay the audio, all in one step using FFmpeg."""
    print(f"\n=== PROCESSING VIDEO WITH SUBTITLES ===")

    # Create temporary directory for processing
    temp_dir = os.path.dirname(output_path)
    os.makedirs(temp_dir, exist_ok=True)

    # Get the duration of the audio and video files
    audio_duration = get_duration(audio_path)
    video_duration = get_duration(video_path)

    print(f"Audio duration: {audio_duration:.2f} seconds")
    print(f"Video duration: {video_duration:.2f} seconds")

    # Analyze audio for speech patterns using silencedetect filter
    # This helps identify natural pauses in speech for better subtitle timing
    silence_analysis_file = os.path.join(temp_dir, "silence_analysis.txt")
    silence_cmd = [
        'ffmpeg', '-y',
        '-i', audio_path,
        '-af', 'silencedetect=noise=-30dB:d=0.5',
        '-f', 'null',
        '-'
    ]

    try:
        print("Analyzing audio for natural speech patterns...")
        with open(silence_analysis_file, 'w') as f:
            process = subprocess.run(
                silence_cmd, stderr=subprocess.PIPE, text=True, check=False)
            f.write(process.stderr)

        # Parse silence detection results (will be used later for subtitle adjustment)
        silence_periods = []
        if os.path.exists(silence_analysis_file):
            with open(silence_analysis_file, 'r') as f:
                content = f.read()
                # Extract silence start times
                start_matches = re.findall(
                    r'silence_start: (\d+\.\d+)', content)
                # Extract silence end times
                end_matches = re.findall(r'silence_end: (\d+\.\d+)', content)

                # Pair start and end times
                for i in range(min(len(start_matches), len(end_matches))):
                    start = float(start_matches[i])
                    end = float(end_matches[i])
                    silence_periods.append((start, end))

            print(f"Detected {len(silence_periods)} natural pauses in speech")
    except Exception as e:
        print(
            f"Silence detection failed: {str(e)}. Continuing without speech pattern analysis.")
        silence_periods = []

    # Extend video if needed
    if audio_duration > video_duration:
        print(f"Audio is longer than video. Extending video to match audio duration.")
        video_path = extend_video(
            video_path, temp_dir, audio_duration, video_duration)

    # Crop the video to vertical format
    print("Cropping video to vertical format...")
    temp_cropped_video = os.path.join(temp_dir, "temp_cropped_video.mp4")
    crop_cmd = [
        'ffmpeg', '-y', '-i', video_path,
        '-vf', 'crop=ih*9/16:ih',  # 9:16 aspect ratio (vertical video)
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k',
        temp_cropped_video
    ]
    subprocess.run(crop_cmd, check=True)

    # Parse subtitle file
    subtitle_entries = parse_ass_subtitles(subtitle_path)

    # Fall back to test subtitles if needed
    if not subtitle_entries:
        print("Using fallback subtitles")
        subtitle_entries = create_fallback_subtitles()

    # If we have silence periods, use them to refine subtitle timings
    if silence_periods:
        subtitle_entries = adjust_subtitles_with_silence_data(
            subtitle_entries, silence_periods, audio_duration)
        print("Applied speech pattern analysis to subtitle timing")

    # Make subtitles sequential by forcing them not to overlap
    non_overlapping_entries = ensure_strictly_sequential_subtitles(
        subtitle_entries)
    print(f"Processing {len(non_overlapping_entries)} subtitle entries")

    # --- NEW APPROACH: Create SRT subtitle file instead of using drawtext filters ---
    temp_srt_path = os.path.join(temp_dir, "temp_subtitles.srt")
    create_srt_subtitle_file(non_overlapping_entries, temp_srt_path)
    print(f"Created temporary SRT subtitle file at: {temp_srt_path}")

    # Temporary file for video with subtitles
    temp_with_subs = os.path.join(temp_dir, "temp_with_subs.mp4")

    # Add subtitles to video using subtitles filter instead of drawtext
    print("Adding subtitles to video...")

    # Alignment
    # 1 = left bottom
    # 2 = bottom center
    # 3 = right bottom
    # 4 = left top
    # 5 =
    # 6 = top center
    # 7 = right top
    # 8 = left center
    # 9 = left center
    # 10 = center center

    subtitle_cmd = [
        'ffmpeg', '-y',
        '-i', temp_cropped_video,
        '-vf', f"subtitles={temp_srt_path}:force_style='FontName=Arial,FontSize=22,PrimaryColour=&HFFFFFF,SecondaryColour=&H000000,BackColour=&H00000000,Bold=1,BorderStyle=1,Outline=2,Shadow=0,Alignment=10'",
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-profile:v', 'high',
        '-c:a', 'copy',
        temp_with_subs
    ]

    subprocess.run(subtitle_cmd, check=True)
    print(f"✓ Successfully burned subtitles into video")

    # Add audio to video
    print("Adding audio to video...")
    final_cmd = [
        'ffmpeg', '-y',
        '-i', temp_with_subs,
        '-i', audio_path,
        '-map', '0:v', '-map', '1:a',  # Use video from first input, audio from second
        '-c:v', 'copy', '-c:a', 'aac',
        output_path
    ]
    subprocess.run(final_cmd, check=True)
    print(f"✓ Successfully added audio to video")

    # Ensure video duration matches audio duration
    ensure_matching_duration(output_path, audio_duration, temp_dir)

    return output_path


def extend_video(video_path, temp_dir, target_duration, video_duration):
    """Extend a video by looping to reach target duration"""
    temp_extended_video = os.path.join(temp_dir, "temp_extended_video.mp4")

    # Calculate the number of loops needed (round up)
    loops_needed = math.ceil(target_duration / video_duration)

    # Create a temporary file list for concat
    concat_file = os.path.join(temp_dir, "concat_list.txt")
    with open(concat_file, 'w') as f:
        for _ in range(loops_needed):
            f.write(f"file '{os.path.abspath(video_path)}'\n")

    # Concatenate the video with itself multiple times
    concat_cmd = [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', concat_file,
        '-c', 'copy',
        temp_extended_video
    ]
    subprocess.run(concat_cmd, check=True)
    print(f"Extended video created with duration for {loops_needed} loops")

    return temp_extended_video


def ensure_matching_duration(video_path, target_duration, temp_dir):
    """Ensure video duration matches the target duration"""
    video_duration = get_duration(video_path)

    if abs(video_duration - target_duration) > 0.5:  # Allow half second tolerance
        print(
            f"Video duration ({video_duration:.2f}s) doesn't match target duration ({target_duration:.2f}s)")
        print(f"Trimming video to match target duration...")

        # Create temp file for the trimmed video
        temp_trimmed = os.path.join(temp_dir, "temp_trimmed.mp4")

        # Use ffmpeg to trim the video to match audio duration
        trim_cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-t', str(target_duration),  # Duration in seconds
            '-c:v', 'copy', '-c:a', 'copy',
            temp_trimmed
        ]
        subprocess.run(trim_cmd, check=True)

        # Replace the output file with the trimmed version
        os.replace(temp_trimmed, video_path)
        print(f"✓ Successfully trimmed video to match target duration")
    else:
        print(f"✓ Video duration already matches target duration")


def generate_subtitles(audio_path, text, output_path, voice="donald_trump", model="claude", api_key=None):
    """Generate subtitles for a video based on audio and text."""
    print(f"\n=== GENERATING SUBTITLES ===")

    # Process the input text
    transformed_text = process_input_text(
        text, output_path, voice, model, api_key)

    # Create a temporary directory for gentle's output
    temp_dir = os.path.dirname(output_path)
    os.makedirs(temp_dir, exist_ok=True)

    # Get audio duration
    audio_duration = get_duration(audio_path)
    print(f"Audio duration: {audio_duration:.2f} seconds")

    # Try different methods to generate subtitle timing
    try:
        # First attempt: Gentle forced alignment
        subtitle_entries = generate_subtitles_with_gentle(
            audio_path, transformed_text, temp_dir)

        if not subtitle_entries:
            # Second attempt: Simple timing based on word count
            subtitle_entries = generate_subtitles_with_simple_timing(
                transformed_text, audio_duration)
    except Exception as e:
        print(f"Error in subtitle generation: {str(e)}")
        subtitle_entries = generate_subtitles_with_simple_timing(
            transformed_text, audio_duration)

    # Create ASS subtitle file with improved styling
    create_ass_subtitle_file(subtitle_entries, output_path, audio_duration)

    return output_path


def process_input_text(text, output_path, voice, model, api_key):
    """Process input text for subtitle generation"""
    if model == "bypass_transform":
        print("Bypassing text transformation, using provided text directly")
        return text

    print(f"Using {model} to transform text for {voice}")
    text_path = os.path.join(os.path.dirname(output_path), f"{voice}_text.txt")
    with open(text_path, 'w') as f:
        f.write(text)

    # Transform text if not already in the right format for the voice
    try:
        transformed_text, _ = transform_to_brainrot(
            text_path, api_key=api_key, voice=voice, model=model)
    except Exception as e:
        print(f"Error transforming text: {str(e)}")
        print("Using original text for subtitles")
        transformed_text = text

    # Clean text for TTS compatibility
    return clean_text_for_tts(transformed_text)


def generate_subtitles_with_gentle(audio_path, text, temp_dir):
    """Generate subtitles using Gentle forced alignment"""
    print("Attempting to generate subtitles with Gentle forced alignment...")
    json_output = os.path.join(temp_dir, "alignment.json")

    # Use Gentle for forced alignment
    resources = gentle.Resources()
    with gentle.resampled(audio_path) as wavfile:
        aligner = gentle.ForcedAligner(resources, text)
        result = aligner.transcribe(wavfile)

        # Save alignment to JSON
        with open(json_output, 'w') as f:
            f.write(result.to_json())

        # Process the alignment data
        with open(json_output, 'r') as f:
            alignment_data = json.load(f)

        # Build word timings
        entries = []
        for word in alignment_data.get('words', []):
            if word.get('case') == 'success':
                start = word.get('start', 0)
                end = word.get('end', 0)
                word_text = word.get('word', '')

                # Advance subtitles by 0.3 seconds for better synchronization
                start_advanced = max(0, start - 0.3)
                end_advanced = max(0, end - 0.3)

                entries.append(SubtitleEntry(
                    word_text, start_advanced, end_advanced))

        # Group words into phrases
        return group_words_into_phrases(entries)


def group_words_into_phrases(word_entries, max_duration=2.5, max_words=4):
    """Group words into phrases for better subtitle display"""
    phrases = []
    current_phrase = []
    current_start = None
    current_end = None

    for entry in word_entries:
        if not current_phrase:
            current_start = entry.start_time
            current_phrase.append(entry.text)
            current_end = entry.end_time
        # Maximum duration per subtitle and max words
        elif entry.end_time - current_start <= max_duration and len(current_phrase) < max_words:
            current_phrase.append(entry.text)
            current_end = entry.end_time
        else:
            phrases.append(SubtitleEntry(
                ' '.join(current_phrase), current_start, current_end))
            current_phrase = [entry.text]
            current_start = entry.start_time
            current_end = entry.end_time

    if current_phrase:
        phrases.append(SubtitleEntry(
            ' '.join(current_phrase), current_start, current_end))

    return phrases


def generate_subtitles_with_simple_timing(text, audio_duration):
    """Generate subtitles with simple timing based on word count"""
    print("Using simple timing method for subtitle generation...")
    words = text.split()
    total_words = len(words)
    words_per_second = total_words / max(audio_duration, 1)

    # Analyze word lengths to better time subtitles
    avg_word_length = sum(len(word) for word in words) / max(1, total_words)

    entries = []

    # Create evenly spaced subtitles
    words_per_subtitle = 3  # Reduced for better readability
    current_word = 0

    while current_word < total_words:
        end_word = min(current_word + words_per_subtitle, total_words)
        subtitle_text = ' '.join(words[current_word:end_word])

        # Calculate timing more precisely based on word length
        subtitle_words = words[current_word:end_word]
        subtitle_word_length_ratio = sum(
            len(word) for word in subtitle_words) / (avg_word_length * len(subtitle_words))

        # Adjust timing based on relative word length and position in audio
        position_factor = current_word / \
            max(1, total_words)  # 0-1 position in text
        start_time = (current_word / words_per_second) * \
            (0.95 + 0.1 * position_factor)
        word_duration_factor = 1.0 + 0.2 * \
            subtitle_word_length_ratio  # Longer words get more time
        end_word_time = (end_word / words_per_second) * word_duration_factor

        # Apply subtitle preview buffer (show slightly earlier)
        # Increase buffer slightly as we progress
        preview_buffer = 0.2 + (0.1 * position_factor)
        start_time = max(0, start_time - preview_buffer)
        # Ensure minimum duration, end slightly earlier
        end_time = max(start_time + 0.3, end_word_time - 0.1)

        # Ensure minimum duration
        if end_time - start_time < 0.5:
            end_time = start_time + 0.5

        entries.append(SubtitleEntry(subtitle_text, start_time, end_time))
        current_word = end_word

    return entries


def create_ass_subtitle_file(subtitle_entries, output_path, audio_duration):
    """Create an ASS subtitle file from subtitle entries"""
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write header
        f.write('[Script Info]\n')
        f.write('Title: Generated Subtitles\n')
        f.write('ScriptType: v4.00+\n')
        f.write('WrapStyle: 0\n')
        f.write('ScaledBorderAndShadow: yes\n')
        f.write('YCbCr Matrix: None\n')
        f.write('PlayResX: 720\n')
        f.write('PlayResY: 1280\n\n')

        # Write styles with white text and black border, no background
        f.write('[V4+ Styles]\n')
        f.write('Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n')
        f.write('Style: Default,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,5,10,10,10,1\n\n')

        # Write events
        f.write('[Events]\n')
        f.write(
            'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')

        # Write dialogue lines
        for entry in subtitle_entries:
            start_time = format_time_ass(entry.start_time)
            end_time = format_time_ass(entry.end_time)
            f.write(
                f'Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{entry.text}\n')

        # Add a final empty subtitle if needed to match audio duration
        if subtitle_entries:
            last_subtitle_end = subtitle_entries[-1].end_time
            if last_subtitle_end < audio_duration - 0.5:  # If gap is more than 0.5 seconds
                final_start = format_time_ass(last_subtitle_end)
                final_end = format_time_ass(audio_duration)
                f.write(
                    f'Dialogue: 0,{final_start},{final_end},Default,,0,0,0,,\n')
                print(
                    f"Added final empty subtitle from {last_subtitle_end:.2f} to {audio_duration:.2f} seconds")

    print(f"Created subtitle file at: {output_path}")
    return output_path


def ensure_strictly_sequential_subtitles(entries):
    """
    Ensure subtitles appear one after another with no overlap
    This is different from create_non_overlapping_subtitles because it enforces
    strict sequencing regardless of original timing

    Also breaks up longer subtitles into smaller chunks for faster-paced style
    """
    if not entries:
        return []

    # Voice-specific timing adjustments - different TTS engines have slightly different timing characteristics
    VOICE_SYNC_ADJUSTMENTS = {
        "donald_trump": -0.15,  # Trump voice tends to start slightly late
        "andrew_tate": -0.3,    # Tate voice needs more lead time
        "mario": -0.25,         # Mario voice needs more lead time
        "default": -0.2         # Default adjustment
    }

    # Try to detect voice from the first entry's text if possible
    voice_hint = None
    if entries and hasattr(entries[0], 'voice'):
        voice_hint = entries[0].voice

    # Apply voice-specific offset or use default
    voice_offset = VOICE_SYNC_ADJUSTMENTS.get(
        voice_hint, VOICE_SYNC_ADJUSTMENTS['default'])

    # Sort entries by start time to ensure proper ordering
    sorted_entries = sorted(entries.copy(), key=lambda e: e.start_time)

    # Break up longer entries into smaller chunks (for faster pace)
    chunked_entries = []
    for entry in sorted_entries:
        # If text is long enough to split
        text = entry.text.strip()

        # Detect if entry contains a question - questions need more time
        is_question = '?' in text

        # Look for natural breaking points (punctuation marks)
        punctuation_breaks = [
            i for i, char in enumerate(text) if char in '.,:;-']

        words = text.split()
        if len(words) > 4:
            # Calculate duration per chunk
            total_duration = entry.end_time - entry.start_time

            # Determine optimal chunk size based on content
            if is_question:
                # Smaller chunks for questions (need more time to process)
                chunk_size = 2
            elif any(len(word) > 8 for word in words):
                chunk_size = 2  # Smaller chunks for content with long words
            else:
                chunk_size = 3  # Default chunk size

            num_chunks = (len(words) + chunk_size -
                          1) // chunk_size  # Ceiling division
            chunk_duration = total_duration / num_chunks

            # Create chunks
            for i in range(0, len(words), chunk_size):
                chunk_words = words[i:i+chunk_size]
                chunk_text = ' '.join(chunk_words)

                # Calculate smart preview buffer based on content
                content_complexity = sum(
                    len(word) for word in chunk_words) / (5 * len(chunk_words))
                preview_buffer = 0.2 + (0.1 * min(1.0, content_complexity))

                # Calculate start time with voice-specific adjustment
                chunk_start = max(0, entry.start_time + (i //
                                  chunk_size) * chunk_duration + voice_offset)

                # Dynamic duration based on content
                duration_factor = 1.0
                if is_question:
                    duration_factor = 1.2  # Questions need more time
                elif any(len(word) > 8 for word in chunk_words):
                    duration_factor = 1.15  # Long words need more time

                # Apply dynamic duration
                adjusted_duration = chunk_duration * duration_factor
                chunk_end = chunk_start + adjusted_duration + 0.15

                chunked_entries.append(SubtitleEntry(
                    chunk_text, chunk_start, chunk_end))
        else:
            # Keep short entries as they are, but add smart preview buffer
            complexity = sum(len(word)
                             for word in words) / (5 * max(1, len(words)))
            preview_buffer = 0.2 + (0.1 * min(1.0, complexity))

            # Apply voice-specific adjustment
            adjusted_start = max(0, entry.start_time + voice_offset)

            # Determine optimal duration based on content
            duration_factor = 1.0
            if is_question:
                duration_factor = 1.2
            elif any(len(word) > 8 for word in words):
                duration_factor = 1.15

            adjusted_duration = (
                entry.end_time - entry.start_time) * duration_factor

            modified_entry = SubtitleEntry(
                entry.text,
                adjusted_start,
                adjusted_start + adjusted_duration + 0.1
            )
            chunked_entries.append(modified_entry)

    # Use the chunked entries instead
    sorted_entries = sorted(chunked_entries, key=lambda e: e.start_time)

    # Dynamic gap calculation helper
    def calculate_optimal_gap(current_entry, next_entry):
        """Calculate optimal gap between subtitles based on content"""
        current_words = current_entry.text.split()
        next_words = next_entry.text.split()

        # Calculate complexity of transition
        current_complexity = sum(
            len(word) for word in current_words) / max(1, len(current_words))
        next_complexity = sum(len(word)
                              for word in next_words) / max(1, len(next_words))

        # More complex transitions need slightly bigger gaps
        complexity_factor = (current_complexity + next_complexity) / 10

        # If current entry ends with sentence-ending punctuation, slightly larger gap
        ends_sentence = any(current_entry.text.rstrip().endswith(p)
                            for p in '.!?')
        sentence_factor = 0.05 if ends_sentence else 0.0

        # Base gap plus adjustments
        return min(0.15, max(0.05, 0.08 + complexity_factor + sentence_factor))

    # Adjust all timing to ensure sequential display
    for i in range(len(sorted_entries) - 1):
        # Force end of current subtitle to be start of next
        if sorted_entries[i].end_time >= sorted_entries[i+1].start_time:
            # Calculate optimal gap based on content
            gap = calculate_optimal_gap(sorted_entries[i], sorted_entries[i+1])

            # If we're pushing the next subtitle's start time, adjust it
            if sorted_entries[i].end_time > sorted_entries[i+1].start_time:
                sorted_entries[i +
                               1].start_time = sorted_entries[i].end_time + gap

                # Ensure minimum duration for each subtitle (based on content complexity)
                word_count = len(sorted_entries[i+1].text.split())
                word_complexity = sum(
                    len(word) for word in sorted_entries[i+1].text.split()) / max(1, word_count)
                min_duration = max(0.3, word_count * 0.15 *
                                   (1 + word_complexity/10))

                sorted_entries[i+1].end_time = max(
                    sorted_entries[i+1].end_time,
                    sorted_entries[i+1].start_time + min_duration
                )
            else:
                # Just add a gap after the current subtitle
                sorted_entries[i].end_time = sorted_entries[i +
                                                            1].start_time - gap

    # Verify no overlaps and print timing for debugging
    print("Subtitle timing (sequential order):")
    for i, entry in enumerate(sorted_entries):
        print(
            f"  {i+1}: {format_time_ass(entry.start_time)} - {format_time_ass(entry.end_time)} : {entry.text[:30]}...")

        # Ensure minimum duration (adaptive based on content)
        words = entry.text.split()
        word_count = len(words)
        word_complexity = sum(len(word) for word in words) / max(1, word_count)
        has_punctuation = any(p in entry.text for p in '.,:;?!')

        # Adjust minimum duration based on content characteristics
        min_duration = max(0.3, word_count * 0.15 *
                           (1 + 0.1 * word_complexity))
        if has_punctuation:
            min_duration *= 1.1  # Allow more time for sentences with punctuation

        if entry.end_time - entry.start_time < min_duration:
            entry.end_time = entry.start_time + min_duration
            print(
                f"    Fixed short duration for subtitle {i+1} (word count: {word_count}, complexity: {word_complexity:.2f})")

    return sorted_entries


def create_srt_subtitle_file(subtitle_entries, output_path):
    """Create an SRT subtitle file from subtitle entries"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, entry in enumerate(subtitle_entries):
            # Convert seconds to SRT time format (HH:MM:SS,mmm)
            start_time_str = seconds_to_srt_time(entry.start_time)
            end_time_str = seconds_to_srt_time(entry.end_time)

            # All text is white now
            styled_text = entry.text

            # Write subtitle entry
            f.write(f"{i+1}\n")
            f.write(f"{start_time_str} --> {end_time_str}\n")
            f.write(f"{styled_text}\n\n")

    print(f"Created SRT subtitle file with {len(subtitle_entries)} entries")
    return output_path


def seconds_to_srt_time(seconds):
    """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_remainder = seconds % 60
    milliseconds = int((seconds_remainder % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds_remainder):02d},{milliseconds:03d}"


def adjust_subtitles_with_silence_data(subtitle_entries, silence_periods, audio_duration):
    """Adjust subtitle timing based on detected silence periods in audio"""
    if not subtitle_entries or not silence_periods:
        return subtitle_entries

    adjusted_entries = subtitle_entries.copy()

    # Find significant pauses (longer than 0.3 seconds)
    significant_pauses = [(start, end)
                          for start, end in silence_periods if end - start > 0.3]

    if not significant_pauses:
        return subtitle_entries

    # Sort entries by start time
    adjusted_entries = sorted(adjusted_entries, key=lambda e: e.start_time)

    # For each subtitle, check if there's a silence period nearby
    for i, entry in enumerate(adjusted_entries):
        # Look for silence periods that overlap with this subtitle timing
        for silence_start, silence_end in significant_pauses:
            # If a silence period starts during this subtitle, try to end the subtitle there
            if entry.start_time < silence_start < entry.end_time:
                # End subtitle at silence start (with small buffer)
                adjusted_entries[i].end_time = silence_start - 0.1
                print(
                    f"Adjusted subtitle {i+1} to end at natural pause: {silence_start:.2f}s")

            # If next subtitle exists and a silence period ends just before it
            if i < len(adjusted_entries) - 1:
                next_subtitle = adjusted_entries[i+1]
                # If silence ends shortly before next subtitle, delay next subtitle to align with speech
                if abs(silence_end - next_subtitle.start_time) < 0.5:
                    time_diff = silence_end - next_subtitle.start_time
                    if time_diff > 0:
                        # Add a small buffer after silence ends
                        adjusted_entries[i+1].start_time = silence_end + 0.1
                        print(
                            f"Delayed subtitle {i+2} to align with speech after pause")

    return adjusted_entries


# Only trim video if this file is run directly
if __name__ == "__main__":
    trim_video('assets/minecraft.mp4', 'assets/trimed.mp4', duration=120)
