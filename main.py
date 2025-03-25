from scraping import *
from audio import *
from force_alignment import *
from dict import *
from video_generator import *
from search import *
from brainrot_generator import transform_to_brainrot, MODELS, VOICE_STYLES
import time
from datetime import timedelta
import os
import shutil
import boto3
from botocore.exceptions import ClientError
import logging
import threading
import traceback
import re
import math
from pydub import AudioSegment
import asyncio
from tqdm import tqdm
from botocore.exceptions import NoCredentialsError

# Configure module-level logger to match the server format
logger = logging.getLogger(__name__)

# Configure logging
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def upload_to_s3(file_path, bucket, object_name=None):
    return ""
    """Upload a file to an S3 bucket

    Args:
        file_path: File to upload
        bucket: Bucket to upload to
        object_name: S3 object name. If not specified then file_path is used

    Returns:
        True if file was uploaded, else False
    """
    # If S3 object_name was not specified, use file_path
    if object_name is None:
        object_name = os.path.basename(file_path)

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        s3_client.upload_file(file_path, bucket, object_name)
        return f"https://{bucket}.s3.amazonaws.com/{object_name}"
    except ClientError as e:
        logging.error(e)
        return None


def format_time(seconds):
    """Convert seconds to a human-readable format"""
    return str(timedelta(seconds=round(seconds)))


def get_audio_duration(audio_path):
    """Get the duration of an audio file in seconds"""
    try:
        import wave
        with wave.open(audio_path, 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            duration = frames / float(rate)
            return duration
    except Exception:
        # Fallback method using ffprobe if available
        try:
            import subprocess
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                   '-of', 'default=noprint_wrappers=1:nokey=1', audio_path]
            output = subprocess.check_output(cmd).decode('utf-8').strip()
            return float(output)
        except Exception:
            # If all else fails, return a default duration
            return 60.0  # Default to 1 minute


def main(input_source, llm=False, scraped_url='texts/scraped_url.txt', output_pre='texts/processed_output.txt',
         final_output='texts/oof.txt', speech_final='audio/output_converted.wav', subtitle_path='texts/testing.ass',
         output_path='final/final.mp4', speaker_wav="assets/default.mp3", video_path='assets/minecraft.mp4',
         language="en-us", api_key=None, voice="donald_trump", model="claude", s3_bucket=None, timestamp=None):
    """
    Main function to generate a video from text

    Parameters:
    - input_source: Path to input text file or text content
    - llm: Whether to use LLM for text processing
    - scraped_url: Path to save scraped URL
    - output_pre: Path to save preprocessed output
    - final_output: Path to save final output
    - speech_final: Path to save final speech audio
    - subtitle_path: Path to save subtitles
    - output_path: Path to save output video
    - speaker_wav: Path to speaker audio file
    - video_path: Path to video file
    - language: Language code
    - api_key: API key for OpenAI
    - voice: Voice to use
    - model: Model to use
    - s3_bucket: S3 bucket to upload to
    - timestamp: Timestamp for consistent directory naming
    """
    # Start timing the entire process
    total_start_time = time.time()

    # Initialize variables that might be used later
    s3_url = None  # Initialize s3_url to avoid undefined variable issues
    timing_list = []  # Initialize timing_list to avoid undefined variable issues

    # Get the current thread name for logging context
    thread_name = threading.current_thread().name
    voice_context = f"[{voice}]"

    # Helper function to log with voice context
    def log_info(message):
        logger.info(f"{voice_context} {message}")

    def log_error(message):
        logger.error(f"{voice_context} {message}")

    log_info("Starting video generation pipeline")

    # Create timestamped output directory with voice name
    if timestamp is None:
        timestamp = int(time.time())
    # Include voice name in the directory path for parallel processing
    output_dir = f'outputs/{timestamp}_{voice}'
    os.makedirs(output_dir, exist_ok=True)
    log_info(f"Created output directory: {output_dir}")

    # Define output paths
    output_paths = {
        'audio': os.path.join(output_dir, f'Mar_4_2025_Daily_Brainrot_by_{voice}_audio.mp3'),
        'audio_converted': os.path.join(output_dir, f'Mar_4_2025_Daily_Brainrot_by_{voice}_audio_converted.wav'),
        'subtitle': os.path.join(output_dir, f'Mar_4_2025_Daily_Brainrot_by_{voice}_subtitles.ass'),
        'processed_text': os.path.join(output_dir, f'Mar_4_2025_Daily_Brainrot_by_{voice}_processed_text.txt'),
        'video': os.path.join(output_dir, f'Mar_4_2025_Daily_Brainrot_by_{voice}_final.mp4')
    }

    # Store timing information
    step_times = {}

    try:
        # SCRAPING (only if input is a URL)
        log_info("\n=== STEP 1: SCRAPING ===")
        start_time = time.time()
        if input_source.startswith(('http://', 'https://')):  # It's a URL
            if not llm:
                map_request = scrape(input_source)
            else:
                log_info("Using LLM to determine best thread to scrape")
                log_info("-------------------")
                reddit_scrape = scrape_llm(input_source)
                text = vader(reddit_scrape)
                if not api_key:
                    api_key = input("Please input the API key\n")
                map_request = groq(text, api_key)
            log_info(map_request)
            save_map_to_txt(map_request, scraped_url)
            input_file = scraped_url
        else:  # It's a file path with direct text
            input_file = input_source
        step_times['scraping'] = time.time() - start_time
        log_info(
            f"Input processing completed in {format_time(step_times['scraping'])}")

        # BRAINROT TRANSFORMATION
        log_info("\n=== STEP 2: TRANSFORMING TO BRAINROT STYLE ===")
        start_time = time.time()
        brainrot_text, output_paths = transform_to_brainrot(
            input_file, api_key, voice, model, timestamp=timestamp)
        step_times['brainrot_transform'] = time.time() - start_time
        log_info(
            f"Brainrot transformation completed in {format_time(step_times['brainrot_transform'])}")

        # AUDIO CONVERSION
        log_info("\n=== STEP 3: AUDIO CONVERSION ===")
        start_time = time.time()
        audio_wrapper(output_paths['brainrot_text'],
                      file_path=output_paths['audio'], voice=voice)
        convert_audio(output_paths['audio'], output_paths['audio_converted'])

        # Add a small silence at the beginning of the audio to help with subtitle synchronization
        log_info(
            "Adding initial silence to audio for better subtitle synchronization")
        add_initial_silence(
            output_paths['audio_converted'], silence_duration=300)

        step_times['audio_conversion'] = time.time() - start_time
        log_info(
            f"Audio conversion completed in {format_time(step_times['audio_conversion'])}")

        # TEXT PROCESSING
        log_info("\n=== STEP 4: TEXT PROCESSING ===")
        start_time = time.time()
        process_text(output_paths['brainrot_text'], output_pre)
        process_text_section2(output_pre, final_output)
        with open(final_output, 'r') as file:
            text = file.read().strip()

        # Also write the processed text to the output_paths['processed_text'] file
        # This is crucial for subtitle generation and force alignment
        processed_text = clean_text(text)
        with open(output_paths['processed_text'], 'w', encoding='utf-8') as file:
            file.write(processed_text)
        log_info(f"Wrote processed text to: {output_paths['processed_text']}")

        step_times['text_processing'] = time.time() - start_time
        log_info(
            f"Text processing completed in {format_time(step_times['text_processing'])}")

        # FORCE ALIGNMENT
        log_info("\n=== STEP 5: ALIGNING TEXT TO AUDIO ===")
        start_time = time.time()

        try:
            # Check if the model file is already downloaded
            model_path = os.path.expanduser(
                "~/.cache/torch/hub/checkpoints/wav2vec2_fairseq_base_ls960_asr_ls960.pth")
            if not os.path.exists(model_path):
                log_info(
                    "Force alignment model not found locally. Skipping force alignment to avoid download.")
                log_info("Using simple timing-based subtitles instead.")

                # Skip directly to simple timing-based subtitles
                audio_duration = get_audio_duration(
                    output_paths['audio_converted'])
                text = open(output_paths['processed_text'], 'r').read()
                words = text.split()
                word_count = len(words)
                avg_word_duration = audio_duration / max(word_count, 1)

                # Create simple timing list
                timing_list = []
                current_time = 0

                for word in words:
                    # Adjust based on word length
                    word_duration = len(word) * avg_word_duration / 5
                    start_time_str = format_time_ass(current_time)
                    end_time_str = format_time_ass(
                        current_time + word_duration)
                    timing_list.append((word, start_time_str, end_time_str))
                    current_time += word_duration
            else:
                # Model is already downloaded, proceed with force alignment
                log_info(
                    "Force alignment model found locally. Proceeding with force alignment.")

                # Initialize timing_list as empty
                timing_list = []

                # Set a timeout for the entire force alignment process
                force_alignment_timeout = 180  # 3 minutes max

                def force_alignment_task():
                    nonlocal timing_list
                    try:
                        from force_alignment import format_text

                        # Try different text sources in order of preference
                        text = ""
                        if os.path.exists(output_paths.get('processed_text', '')) and os.path.getsize(output_paths.get('processed_text', '')) > 0:
                            # First try the processed text file
                            try:
                                with open(output_paths['processed_text'], 'r', encoding='utf-8') as f:
                                    text = f.read().strip()
                                log_info(
                                    f"Using processed text for force alignment: {len(text)} chars")
                            except Exception as e:
                                log_error(
                                    f"Error reading processed text: {str(e)}")
                                text = ""

                        if not text and os.path.exists(output_paths.get('brainrot_text', '')) and os.path.getsize(output_paths.get('brainrot_text', '')) > 0:
                            # Then try the brainrot text file
                            try:
                                with open(output_paths['brainrot_text'], 'r', encoding='utf-8') as f:
                                    text = f.read().strip()
                                log_info(
                                    f"Using brainrot text for force alignment: {len(text)} chars")
                            except Exception as e:
                                log_error(
                                    f"Error reading brainrot text: {str(e)}")
                                text = ""

                        if not text and input_source and os.path.exists(input_source):
                            # Finally try the original input file
                            try:
                                with open(input_source, 'r', encoding='utf-8') as f:
                                    text = f.read().strip()
                                log_info(
                                    f"Using original input text for force alignment: {len(text)} chars")
                            except Exception as e:
                                log_error(
                                    f"Error reading input source: {str(e)}")
                                text = ""

                        if not text:
                            log_error(
                                "No valid text source found for force alignment")
                            raise Exception(
                                "No valid text for force alignment")

                        formatted_text = format_text(text)

                        # Import here to avoid circular imports
                        from force_alignment import class_label_prob
                        result = class_label_prob(
                            output_paths['audio_converted'])

                        # If model loading failed, raise exception to fall back to simple timing
                        if result is None:
                            raise Exception(
                                "Force alignment model could not be loaded")

                        # Continue with force alignment
                        emission_cpu, labels, waveform, bundle = result

                        # Import necessary functions
                        from force_alignment import trellis_algo, backtrack, merge_repeats, merge_words, display_segment

                        # Perform force alignment
                        trellis, emission, tokens = trellis_algo(
                            labels, formatted_text, emission_cpu)

                        # Check if trellis is valid
                        if trellis.size(1) <= 1:
                            raise ValueError(
                                "Trellis matrix is too small for backtracking")

                        path = backtrack(trellis, emission, tokens)

                        # Check if path is valid
                        if not path:
                            raise ValueError(
                                "Backtracking failed to produce a valid path")

                        segments = merge_repeats(path, formatted_text)
                        word_segments = merge_words(segments)

                        # Create timing list with consistent format
                        local_timing_list = []
                        for i, word in enumerate(word_segments):
                            word_text, start_time_str, end_time_str = display_segment(
                                bundle, trellis, word_segments, waveform, i)
                            local_timing_list.append(
                                (word_text, start_time_str, end_time_str))

                        # Update the outer timing_list
                        timing_list = local_timing_list
                        return True
                    except Exception as e:
                        log_error(f"Force alignment error: {str(e)}")
                        log_error(
                            "Falling back to simple timing-based subtitles")
                        return False

            # Create a thread for force alignment with timeout
            alignment_thread = threading.Thread(target=force_alignment_task)
            alignment_thread.daemon = True
            alignment_thread.start()

            # Wait for the thread to complete with timeout
            alignment_thread.join(timeout=force_alignment_timeout)

            # If thread is still alive after timeout, it's stuck
            if alignment_thread.is_alive():
                log_error(
                    f"Force alignment timed out after {force_alignment_timeout} seconds")
                log_error("Falling back to simple timing-based subtitles")

                # Generate simple timing-based subtitles as fallback
                audio_duration = get_audio_duration(
                    output_paths['audio_converted'])

                # Try different text sources in order of preference
                text = ""
                if os.path.exists(output_paths.get('processed_text', '')) and os.path.getsize(output_paths.get('processed_text', '')) > 0:
                    # First try the processed text file
                    try:
                        with open(output_paths['processed_text'], 'r', encoding='utf-8') as f:
                            text = f.read().strip()
                        log_info(
                            f"Using processed text for subtitle generation: {len(text)} chars")
                    except Exception as e:
                        log_error(f"Error reading processed text: {str(e)}")
                        text = ""

                if not text and os.path.exists(output_paths.get('brainrot_text', '')) and os.path.getsize(output_paths.get('brainrot_text', '')) > 0:
                    # Then try the brainrot text file
                    try:
                        with open(output_paths['brainrot_text'], 'r', encoding='utf-8') as f:
                            text = f.read().strip()
                        log_info(
                            f"Using brainrot text for subtitle generation: {len(text)} chars")
                    except Exception as e:
                        log_error(f"Error reading brainrot text: {str(e)}")
                        text = ""

                if not text and input_source and os.path.exists(input_source):
                    # Finally try the original input file
                    try:
                        with open(input_source, 'r', encoding='utf-8') as f:
                            text = f.read().strip()
                        log_info(
                            f"Using original input text for subtitle generation: {len(text)} chars")
                    except Exception as e:
                        log_error(f"Error reading input source: {str(e)}")
                        text = ""

                if not text:
                    log_error(
                        "No valid text source found for subtitle generation")
                    text = "No subtitles available"

                # Split into words for timing
                words = text.split()
                word_count = len(words)
                log_info(
                    f"Using {word_count} words for simple subtitle timing")

                # If no words (empty text), create a default subtitle file
                if word_count == 0:
                    create_empty_subtitle_file(output_paths['subtitle'])
                    log_info("Created empty subtitle file due to lack of content")
                    step_times['force_alignment'] = time.time() - start_time
                    log_info(
                        f"Force alignment completed in {format_time(step_times['force_alignment'])}")
                    return output_paths

                # Calculate average word duration
                avg_word_duration = audio_duration / max(word_count, 1)

                # Create simple timing list
                timing_list = []
                current_time = 0

                for word in words:
                    if not word:  # Skip empty words
                        continue
                    # Adjust based on word length with reasonable limits
                    word_duration = max(
                        min(len(word) * avg_word_duration / 5, 1.5), 0.3)
                    start_time_str = format_time_ass(current_time)
                    end_time_str = format_time_ass(
                        current_time + word_duration)
                    timing_list.append({
                        'word': word,
                        'start': current_time,
                        'end': current_time + word_duration
                    })
                    current_time += word_duration

            # Convert to ASS subtitles
            convert_simple_timing_to_ass(timing_list, output_paths['subtitle'])

        except Exception as e:
            log_error(f"Force alignment error: {str(e)}")
            log_error("Falling back to simple timing-based subtitles")

            # Create an empty subtitle file to avoid errors
            with open(output_paths['subtitle'], 'w', encoding='utf-8') as f:
                f.write('''[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
Timer: 100.0000

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,60,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,1,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
''')

        step_times['force_alignment'] = time.time() - start_time
        log_info(
            f"Force alignment completed in {format_time(step_times['force_alignment'])}")

        # VIDEO GENERATION
        log_info("\n=== STEP 6: VIDEO GENERATION ===")
        start_time = time.time()

        # Ensure we have a valid subtitle file
        try:
            # Check if we have a valid timing_list and need to generate subtitles
            if timing_list and (not os.path.exists(output_paths['subtitle']) or
                                os.path.getsize(output_paths['subtitle']) == 0):
                log_info(
                    f"Converting timing list to ASS subtitles (length: {len(timing_list)})")

                # Ensure timing format is consistent
                formatted_timing_list = []
                for item in timing_list:
                    if len(item) == 3:  # Already in the right format (word, start_time, end_time)
                        word, start_time, end_time = item
                        # Ensure start_time and end_time are strings in the right format
                        if not isinstance(start_time, str):
                            start_time = format_time_ass(start_time)
                        if not isinstance(end_time, str):
                            end_time = format_time_ass(end_time)
                        formatted_timing_list.append(
                            (word, start_time, end_time))
                    else:
                        log_error(f"Invalid timing item format: {item}")

                # Use convert_simple_timing_to_ass for all subtitle generation
                convert_simple_timing_to_ass(
                    formatted_timing_list, output_paths['subtitle'])
                log_info(
                    f"Successfully generated subtitle file at {output_paths['subtitle']}")
            else:
                log_info(
                    "Using existing subtitle file or skipping timing conversion")
        except Exception as timing_error:
            log_error(f"Error in subtitle generation: {str(timing_error)}")
            # Create a fallback subtitle file
            log_info("Creating fallback subtitle file")
            try:
                # Generate simple timing-based subtitles as fallback
                audio_duration = get_audio_duration(
                    output_paths['audio_converted'])
                text = open(output_paths['processed_text'], 'r').read()
                words = text.split()
                word_count = len(words)
                avg_word_duration = audio_duration / max(word_count, 1)

                # Create simple timing list
                simple_timing_list = []
                current_time = 0
                for word in words:
                    # Adjust based on word length
                    word_duration = len(word) * avg_word_duration / 5
                    start_time_str = format_time_ass(current_time)
                    end_time_str = format_time_ass(
                        current_time + word_duration)
                    simple_timing_list.append(
                        (word, start_time_str, end_time_str))
                    current_time += word_duration

                # Generate subtitle file
                convert_simple_timing_to_ass(
                    simple_timing_list, output_paths['subtitle'])
                log_info("Successfully created fallback subtitle file")
            except Exception as fallback_error:
                log_error(
                    f"Fallback subtitle generation failed: {str(fallback_error)}")
                # Create an empty subtitle file with proper formatting
                with open(output_paths['subtitle'], 'w', encoding='utf-8') as f:
                    f.write('''[Script Info]
; Script generated by Python script
Title: Default ASS file
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
ScaledBorderAndShadow: yes
YCbCr Matrix: None

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,60,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,1,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
''')
                log_info("Created empty subtitle file with proper formatting")

        # Generate video in outputs directory using specified video_path
        add_subtitles_and_overlay_audio(video_path, output_paths['audio_converted'],
                                        output_paths['subtitle'], output_paths['video'])

        step_times['video_generation'] = time.time() - start_time
        log_info(
            f"Video generation completed in {format_time(step_times['video_generation'])}")

        # After video generation is complete and successful
        if s3_bucket and os.path.exists(output_paths['video']):
            log_info("\n=== STEP 7: UPLOADING TO S3 ===")
            start_time = time.time()

            # Upload to S3
            s3_object_name = f"videos/{os.path.basename(output_paths['video'])}"
            s3_url = upload_to_s3(
                output_paths['video'], s3_bucket, s3_object_name)

            if s3_url:
                log_info(f"Video uploaded successfully to S3: {s3_url}")
                step_times['s3_upload'] = time.time() - start_time
                log_info(
                    f"S3 upload completed in {format_time(step_times['s3_upload'])}")
            else:
                log_error("Failed to upload video to S3")
        elif s3_bucket:
            log_error(
                f"Video file not found at {output_paths['video']}, cannot upload to S3")
            s3_url = None

        # VALIDATION: Check that video duration matches audio duration
        log_info("\n=== STEP 7: FINAL VALIDATION ===")
        start_time = time.time()

        audio_duration = get_audio_duration(output_paths['audio_converted'])
        video_duration = get_duration(output_paths['video'])

        log_info(f"Audio duration: {format_time(audio_duration)}")
        log_info(f"Video duration: {format_time(video_duration)}")

        # Check if durations are significantly different (allow 3 second margin)
        if abs(audio_duration - video_duration) > 3:
            log_error(
                f"WARNING: Video duration ({format_time(video_duration)}) does not match audio duration ({format_time(audio_duration)})")
            log_error(
                f"This may indicate the video was truncated. Check the video_generator.py implementation.")
        else:
            log_info(f"✓ Validation passed: Video includes the entire audio track")

        step_times['validation'] = time.time() - start_time

        # FINAL SUMMARY
        total_time = time.time() - total_start_time
        log_info("\n=== GENERATION SUMMARY ===")
        log_info(f"Total processing time: {format_time(total_time)}")
        for step, duration in step_times.items():
            log_info(
                f"  - {step}: {format_time(duration)} ({duration / total_time * 100:.1f}%)")

        result = {
            "success": True,
            "message": f"Generated video for {voice}",
            "output_paths": output_paths,
            "s3_url": s3_url if s3_bucket else None,
            "processing_time": total_time,
            "step_times": {k: v for k, v in step_times.items()}
        }

        return output_paths['video'], s3_url if s3_bucket else None

    except Exception as e:
        log_error(f"Error in video generation pipeline: {str(e)}")
        log_error(traceback.format_exc())
        raise


def convert_simple_timing_to_ass(timing_list, output_file):
    """
    Convert a timing list to ASS subtitle format for better visibility
    """
    if not timing_list:
        print("Warning: Empty timing list, creating default subtitle file")
        create_empty_subtitle_file(output_file)
        return

    # Set up ASS file header with improved styling
    header = """[Script Info]
Title: Generated Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,3,2,10,10,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # Group words into phrases for better readability
    max_words_per_phrase = 5  # Increased from 3 to 5 for better flow
    print(f"Max words per phrase: {max_words_per_phrase}")

    phrases = []
    current_phrase = []
    current_start = 0

    for item in timing_list:
        if len(current_phrase) == 0:
            current_start = item['start']

        current_phrase.append(item)

        if len(current_phrase) >= max_words_per_phrase:
            phrases.append({
                'start': current_start,
                'end': current_phrase[-1]['end'],
                'words': [w['word'] for w in current_phrase]
            })
            current_phrase = []

    # Add any remaining words
    if current_phrase:
        phrases.append({
            'start': current_start,
            'end': current_phrase[-1]['end'],
            'words': [w['word'] for w in current_phrase]
        })

    print(f"Estimated phrases: {len(phrases)}")

    # Convert to ASS dialogue lines
    dialogue_lines = []

    for phrase in phrases:
        start_time = convert_seconds_to_ass_time(phrase['start'])
        end_time = convert_seconds_to_ass_time(phrase['end'])

        # Join the words with spaces, and add the dialogue line
        text = ' '.join(phrase['words'])

        # Simple sentence capitalization
        if text and len(text) > 0:
            text = text[0].upper() + text[1:]

        dialogue_line = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}"
        dialogue_lines.append(dialogue_line)

    # Write to the output file
    with open(output_file, 'w') as f:
        f.write(header)
        for line in dialogue_lines:
            f.write(line + '\n')

    print(
        f"Created subtitle file at {output_file} with {len(phrases)} phrases")


def create_empty_subtitle_file(output_file):
    """Create an empty subtitle file with a placeholder message"""
    header = """[Script Info]
Title: Default Subtitles
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,3,2,10,10,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:05.00,Default,,0,0,0,,No subtitle data available
"""
    with open(output_file, 'w') as f:
        f.write(header)
    print(f"Created empty subtitle file at {output_file}")


def format_time_ass(seconds):
    """Format time in ASS format (H:MM:SS.cc)"""
    if isinstance(seconds, str):
        return seconds

    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds = seconds % 60
    centiseconds = int((seconds - int(seconds)) * 100)
    return f"{hours}:{minutes:02d}:{int(seconds):02d}.{centiseconds:02d}"


def add_initial_silence(audio_path, output_path=None, silence_duration=300):
    """Add a short silence at the beginning of an audio file.

    Args:
        audio_path: Path to the input audio file
        output_path: Path to save the modified audio. If None, modifies in place.
        silence_duration: Duration of silence to add in milliseconds (default: 300ms)

    Returns:
        Path to the modified audio file
    """
    if output_path is None:
        output_path = audio_path

    # Load the audio file
    audio = AudioSegment.from_file(audio_path)

    # Create silence segment
    silence = AudioSegment.silent(duration=silence_duration)

    # Add silence to the beginning
    modified_audio = silence + audio

    # Export the modified audio
    modified_audio.export(
        output_path, format=os.path.splitext(output_path)[1][1:])

    return output_path


def convert_seconds_to_ass_time(seconds):
    """Convert seconds to ASS time format (H:MM:SS.cc)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    centiseconds = int((seconds % 1) * 100)
    seconds = int(seconds)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


if __name__ == "__main__":
    main("https://www.reddit.com/r/askSingapore/", llm=True)
