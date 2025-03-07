from scraping import *
from audio import *
from force_alignment import *
from dict import *
from video_generator import *
from search import *
from brainrot_generator import transform_to_brainrot
import time
from datetime import timedelta
import os
import shutil
import boto3
from botocore.exceptions import ClientError
import logging


def upload_to_s3(file_path, bucket, object_name=None):
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


def main(input_source, llm=False, scraped_url='texts/scraped_url.txt', output_pre='texts/processed_output.txt',
         final_output='texts/oof.txt', speech_final='audio/output_converted.wav', subtitle_path='texts/testing.ass',
         output_path='final/final.mp4', speaker_wav="assets/default.mp3", video_path='assets/minecraft.mp4',
         language="en-us", api_key=None, voice="donald_trump", model="claude", s3_bucket=None):

    total_start_time = time.time()
    step_times = {}

    # SCRAPING (only if input is a URL)
    print("\n=== STEP 1: SCRAPING ===")
    start_time = time.time()
    if input_source.startswith(('http://', 'https://')):  # It's a URL
        if not llm:
            map_request = scrape(input_source)
        else:
            print("Using LLM to determine best thread to scrape")
            print("-------------------")
            reddit_scrape = scrape_llm(input_source)
            text = vader(reddit_scrape)
            if not api_key:
                api_key = input("Please input the API key\n")
            map_request = groq(text, api_key)
        print(map_request)
        save_map_to_txt(map_request, scraped_url)
        input_file = scraped_url
    else:  # It's a file path with direct text
        input_file = input_source
    step_times['scraping'] = time.time() - start_time
    print(
        f"Input processing completed in {format_time(step_times['scraping'])}")

    # BRAINROT TRANSFORMATION
    print("\n=== STEP 2: TRANSFORMING TO BRAINROT STYLE ===")
    start_time = time.time()
    brainrot_text, output_paths = transform_to_brainrot(
        input_file, api_key, voice, model)
    step_times['brainrot_transform'] = time.time() - start_time
    print(
        f"Brainrot transformation completed in {format_time(step_times['brainrot_transform'])}")

    # AUDIO CONVERSION
    print("\n=== STEP 3: AUDIO CONVERSION ===")
    start_time = time.time()
    audio_wrapper(output_paths['brainrot_text'],
                  file_path=output_paths['audio'], voice=voice)
    convert_audio(output_paths['audio'], output_paths['audio_converted'])
    step_times['audio_conversion'] = time.time() - start_time
    print(
        f"Audio conversion completed in {format_time(step_times['audio_conversion'])}")

    # TEXT PROCESSING
    print("\n=== STEP 4: TEXT PROCESSING ===")
    start_time = time.time()
    process_text(output_paths['brainrot_text'], output_pre)
    process_text_section2(output_pre, final_output)
    with open(final_output, 'r') as file:
        text = file.read().strip()
    step_times['text_processing'] = time.time() - start_time
    print(
        f"Text processing completed in {format_time(step_times['text_processing'])}")

    # FORCE ALIGNMENT
    print("\n=== STEP 5: ALIGNING TEXT TO AUDIO ===")
    start_time = time.time()
    formatted_text, temp_file = format_text(text)
    bundle, waveform, labels, emission1 = class_label_prob(
        output_paths['audio_converted'])
    trellis, emission, tokens = trellis_algo(labels, formatted_text, emission1)
    path = backtrack(trellis, emission, tokens)
    segments = merge_repeats(path, formatted_text)
    word_segments = merge_words(segments)
    timing_list = []
    for (i, word) in enumerate(word_segments):
        timing_list.append(
            (display_segment(bundle, trellis, word_segments, waveform, i)))

    # Pass voice, model, and api_key to generate_subtitles
    generate_subtitles(output_paths['audio_converted'], text, output_paths['subtitle'],
                       voice=voice, model=model, api_key=api_key)

    # Clean up temporary file
    if os.path.exists(temp_file):
        os.remove(temp_file)

    step_times['force_alignment'] = time.time() - start_time
    print(
        f"Force alignment completed in {format_time(step_times['force_alignment'])}")

    # VIDEO GENERATION
    print("\n=== STEP 6: VIDEO GENERATION ===")
    start_time = time.time()
    convert_timing_to_ass(timing_list, output_paths['subtitle'])

    # Generate video in outputs directory using specified video_path
    add_subtitles_and_overlay_audio(video_path, output_paths['audio_converted'],
                                    output_paths['subtitle'], output_paths['video'])

    step_times['video_generation'] = time.time() - start_time
    print(
        f"Video generation completed in {format_time(step_times['video_generation'])}")

    # After video generation is complete and successful
    if s3_bucket and os.path.exists(output_paths['video']):
        print("\n=== STEP 7: UPLOADING TO S3 ===")
        start_time = time.time()

        # Upload to S3
        s3_object_name = f"videos/{os.path.basename(output_paths['video'])}"
        s3_url = upload_to_s3(output_paths['video'], s3_bucket, s3_object_name)

        if s3_url:
            print(f"Video uploaded successfully to S3: {s3_url}")
            step_times['s3_upload'] = time.time() - start_time
            print(
                f"S3 upload completed in {format_time(step_times['s3_upload'])}")
        else:
            print("Failed to upload video to S3")

    # Print final summary
    total_time = time.time() - total_start_time
    print("\n=== EXECUTION SUMMARY ===")
    print(f"Total execution time: {format_time(total_time)}")
    print("\nBreakdown by step:")
    for step, duration in step_times.items():
        percentage = (duration / total_time) * 100
        print(
            f"- {step.replace('_', ' ').title()}: {format_time(duration)} ({percentage:.1f}%)")

    print(f"\nDONE! Video saved at {output_paths['video']}")
    if s3_bucket and s3_url:
        print(f"S3 URL: {s3_url}")

    return output_paths['video'], s3_url if s3_bucket else None


if __name__ == "__main__":
    main("https://www.reddit.com/r/askSingapore/", llm=True)
