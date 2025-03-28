"""
Constants for the Brainrot Generator application.
This file contains styling and configuration constants used throughout the application.
"""

# Video configuration
VIDEO_CONFIG = {
    "width": 1080,      # 9:16 ratio width
    "height": 1920,    # Standard height
    "fps": 60,         # Standard high fps
}

# Subtitle styling
SUBTITLE_STYLE = {
    # Font properties
    "font_name": "Arial",
    "font_size": 72,

    # Colors (in ASS format: &HAABBGGRR)
    "primary_color": "&HFFFFFF",   # White text
    "secondary_color": "&H000000",  # Black secondary
    "outline_color": "&H000000",    # Black outline
    "back_color": "&H00000000",  # Transparent background (00 alpha)

    # Formatting
    "bold": 1,               # 1 for bold, 0 for normal
    "italic": 0,             # 0 for no italic
    "underline": 0,          # 0 for no underline
    "strike_out": 0,         # 0 for no strikeout
    "scale_x": 100,          # 100% horizontal scaling
    "scale_y": 100,          # 100% vertical scaling
    "spacing": 0,            # Letter spacing
    "angle": 0,              # Text rotation angle
    "border_style": 1,       # 1 for outline only, 3 for opaque box
    "outline": 2.5,          # Outline thickness
    "shadow": 0,             # Shadow distance

    # Positioning
    # 7 8 9
    # 4 5 6
    # 1 2 3
    "alignment": 2,          # Changed to bottom-center (2) from center (5)
    "margin_l": 20,          # Left margin
    "margin_r": 20,          # Right margin
    "margin_v": 50,          # Vertical margin from bottom

    # Other
    "bg_opacity": 0.0,       # Background opacity (0.0 = transparent)
}

# Speaking rates for different voices (words per second)
VOICE_SPEAKING_RATES = {
    "donald_trump": 1.8,              # Adjusted from 1.2 to 1.8 for better timing
    "walter_cronkite": 2.2,           # Standard news anchor rate
    "southpark_eric_cartman": 2.5,    # Fast and excited
    "keanu_reeves": 1.7,              # Slow and deliberate
    "fireship": 3.0                   # Very fast tech explanations
}

# Default speaking rate if voice not in the dictionary
DEFAULT_SPEAKING_RATE = 2.0

# Timing parameters for subtitle generation
SUBTITLE_TIMING = {
    # Initial silence before first subtitle (seconds)
    "initial_silence": 0.7,
    # Standard padding between subtitles (seconds)
    "standard_padding": 0.25,
    # Extra pause at the start of sentences (seconds)
    "sentence_start_pause": 0.5,
    "minimum_subtitle_duration": 1.0,  # Minimum subtitle duration (seconds)
    # Maximum words per subtitle chunk (reduced from 4 to 3)
    "max_words_per_chunk": 3,
    # Additional padding for long words (>6 chars)
    "long_word_factor": 0.18,
    # Time multiplier for question marks
    "question_time_factor": 1.25,
    # Time multiplier for end-of-sentence
    "end_sentence_factor": 1.2,
    # Minimum duration per word in seconds (increased)
    "min_duration_per_word": 0.35,
}

# FFmpeg parameters for video generation
FFMPEG_PARAMS = {
    "preset": "fast",                 # Encoding preset (fast, medium, slow)
    # Constant Rate Factor (quality, lower is better)
    "crf": "23",
    "audio_codec": "aac",             # Audio codec
    "video_codec": "libx264",         # Video codec
    "audio_bitrate": "192k",          # Audio bitrate
}

# ASS subtitle format parameters
ASS_FORMAT = {
    "script_type": "v4.00+",
    "wrap_style": "0",
    "scaled_border_shadow": "yes",
    "ycbcr_matrix": "None",
    "bold": 1,
    "italic": 0,
    "underline": 0,
    "strikeout": 0,
    "scale_x": 100,
    "scale_y": 100,
    "spacing": 0,
    "angle": 0,
    "encoding": 1,
}
