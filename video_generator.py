import subprocess
import os

# Use this if you need to trim longer videos from sample video
def trim_video(input_path, output_path, duration=120):
    command = [
        'ffmpeg',
        '-i', input_path,  # Input file
        '-t', str(duration),  # Duration to trim (in seconds)
        '-c', 'copy',  # Copy codec (no re-encoding)
        output_path  # Output file
    ]
    subprocess.run(command, check=True)

# Crop video to 9:16 aspect ratio
def crop_to_vertical(input_path, output_path):
    # Get video dimensions
    dimension_cmd = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'csv=s=x:p=0',
        input_path
    ]
    dimensions = subprocess.check_output(dimension_cmd).decode('utf-8').strip().split('x')
    width = int(dimensions[0])
    height = int(dimensions[1])
    
    # Calculate crop dimensions for 9:16 ratio
    if width/height > 9/16:  # If video is wider than 9:16
        new_width = int(height * 9/16)
        crop_x = int((width - new_width) / 2)
        crop_command = f"crop={new_width}:{height}:{crop_x}:0"
    else:  # If video is taller than 9:16
        new_height = int(width * 16/9)
        crop_y = int((height - new_height) / 2)
        crop_command = f"crop={width}:{new_height}:0:{crop_y}"
    
    # Apply crop
    command = [
        'ffmpeg',
        '-i', input_path,
        '-vf', crop_command,
        '-c:a', 'copy',
        '-y',
        output_path
    ]
    subprocess.run(command, check=True)
    return output_path

# Use this to overlay subtitles and video
def add_subtitles_and_overlay_audio(video_path, audio_path, subtitle_path, output_path):
    # Create the output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Get audio duration
    audio_duration_cmd = [
        'ffprobe', 
        '-v', 'error', 
        '-show_entries', 'format=duration', 
        '-of', 'default=noprint_wrappers=1:nokey=1', 
        audio_path
    ]
    audio_duration = float(subprocess.check_output(audio_duration_cmd).decode('utf-8').strip())
    
    # Get video duration
    video_duration_cmd = [
        'ffprobe', 
        '-v', 'error', 
        '-show_entries', 'format=duration', 
        '-of', 'default=noprint_wrappers=1:nokey=1', 
        video_path
    ]
    video_duration = float(subprocess.check_output(video_duration_cmd).decode('utf-8').strip())
    
    # If audio is longer than video, loop the video
    if audio_duration > video_duration:
        # Create a temporary file with looped video
        temp_video = "temp_looped_video.mp4"
        loop_cmd = [
            'ffmpeg',
            '-stream_loop', str(int(audio_duration / video_duration) + 1),  # Loop enough times
            '-i', video_path,
            '-c', 'copy',
            '-t', str(audio_duration + 5),  # Add 5 seconds buffer
            '-y',
            temp_video
        ]
        subprocess.run(loop_cmd, check=True)
        video_path = temp_video
    
    # Crop to 9:16 aspect ratio
    cropped_video = "temp_cropped_video.mp4"
    crop_to_vertical(video_path, cropped_video)
    video_path = cropped_video
    
    # Add subtitles to the video and overlay audio
    # Use ASS subtitles with custom styling for better positioning in 9:16 format
    command = [
        'ffmpeg',
        '-i', video_path,  # Input video file
        '-i', audio_path,  # Input audio file
        '-vf', f"subtitles={subtitle_path}:force_style='Fontsize=30,Alignment=2,MarginV=30'",  # Add subtitles with custom styling
        '-c:v', 'libx264',  # Video codec
        "-map", "0:v",
        "-map", "1:a",
        '-c:a', 'aac',  # Audio codec
        '-strict', 'experimental',  # Allow experimental codecs
        '-shortest',  # Match the shortest input duration
        output_path  # Output file
    ]
    subprocess.run(command, check=True)
    
    # Clean up temporary files
    if os.path.exists("temp_looped_video.mp4"):
        os.remove("temp_looped_video.mp4")
    if os.path.exists("temp_cropped_video.mp4"):
        os.remove("temp_cropped_video.mp4")

# Process the initial video
trim_video('assets/subway.mp4','assets/trimed.mp4', duration = 120)