# rebuilding force alignment using a wav2vec model
# Force alignment script is based off PyTorch tutorial on force alignment

import torch
import torchaudio
from dataclasses import dataclass
import IPython
import matplotlib.pyplot as plt
import os
import time
import re
import logging
import signal
import threading

# Configure module-level logger
logger = logging.getLogger(__name__)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# likely need to edit the transcript for this


def format_text(input_text):
    """Split the input text into words and format with pipe separators.
    Returns the formatted text and writes it to a temporary file."""
    # Split the input text into words
    words = input_text.split()

    # Join the words with '|' and add leading and trailing '|'
    formatted_text = '|' + '|'.join(words) + '|'

    # Create a temporary file with timestamp
    timestamp = int(time.time())
    temp_dir = 'temp'
    os.makedirs(temp_dir, exist_ok=True)
    temp_file = os.path.join(temp_dir, f'align-text-to-audio-{timestamp}.txt')

    # Write the formatted text to the temporary file
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(formatted_text)

    return formatted_text, temp_file


# Step 1: Getting class label probability (1)

def class_label_prob(SPEECH_FILE):
    bundle, model = load_model_with_timeout()
    if bundle is None or model is None:
        return None

    # Move model to the appropriate device
    model = model.to(device)

    labels = bundle.get_labels()
    with torch.inference_mode():
        waveform, sample_rate = torchaudio.load(SPEECH_FILE)
        waveform = waveform.to(device)
        if sample_rate != bundle.sample_rate:
            waveform = torchaudio.functional.resample(
                waveform, sample_rate, bundle.sample_rate)
        emission, _ = model(waveform)
        emission = emission.cpu().detach()
        emission = torch.log_softmax(emission, dim=-1)
        emission = emission.transpose(0, 1)
        emission_cpu = emission.cpu()
        return emission_cpu, labels, waveform, bundle


# Step 2: Getting the trellis: represents the probability of transcript labels
# occuring at each time frame

def trellis_algo(labels, ts, emission, blank_id=0):
    """Calculate trellis matrix for force alignment.

    Args:
        labels: Label set
        ts: Already formatted text (should already have pipe separators)
        emission: Emission matrix
        blank_id: ID for blank token
    """
    dictionary = {c: i for i, c in enumerate(labels)}

    # Use the text directly without reformatting
    tokens = []
    for c in ts:
        if c in dictionary:
            tokens.append(dictionary[c])
        else:
            tokens.append(0)

    if not tokens:
        raise ValueError(
            "Tokens list is empty. Check the input text and labels.")

    num_frame = emission.size(0)
    num_tokens = len(tokens)

    trellis = torch.zeros((num_frame, num_tokens))
    trellis[1:, 0] = torch.cumsum(emission[1:, blank_id], 0)
    trellis[0, 1:] = -float("inf")
    trellis[-num_tokens + 1:, 0] = float("inf")

    for t in range(num_frame - 1):
        trellis[t + 1, 1:] = torch.maximum(
            trellis[t, 1:] + emission[t, blank_id],
            trellis[t, :-1] + emission[t, tokens[1:]],
        )
    return trellis, emission, tokens

# Step 3: most likely path using backtracking algorithm


@dataclass
class Point:
    token_index: int
    time_index: int
    score: float


def backtrack(trellis, emission, tokens):
    # Backtrack to find the optimal path
    j = trellis.size(1) - 1
    i = torch.argmax(trellis[:, j]).item()

    # Create a list to store the path
    path = []

    # Add a safety check for the trellis size
    if trellis.size(1) <= 1:
        print("Warning: Trellis matrix is too small for backtracking")
        # Return an empty path or a default path
        return []

    # Backtrack from the last time frame
    t = j
    while t > 0:  # This is where the assertion was failing
        # Add a safety check
        if t <= 0:
            print("Warning: Backtracking reached the beginning of the trellis")
            break

        # Get the token index and its emission probability
        path.append((i, t, tokens[i]))

        # Move to the previous frame
        i = torch.argmax(trellis[:, t-1] * emission[i, t]).item()
        t = t - 1

    # Add the last token at the first time frame
    path.append((i, t, tokens[i]))

    # Reverse the path to get time-ascending order
    return path[::-1]


# Step 4: Path segmentation
@dataclass
class Segment:
    label: str
    start: int
    end: int
    score: float

    def __repr__(self):
        return f"{self.label}\t({self.score:4.2f}): [{self.start:5d}, {self.end:5d})"

    @property
    def length(self):
        return self.end - self.start


def merge_repeats(path, transcript):
    i1, i2 = 0, 0
    segments = []
    while i1 < len(path):
        while i2 < len(path) and path[i1].token_index == path[i2].token_index:
            i2 += 1
        score = sum(path[k].score for k in range(i1, i2)) / (i2 - i1)
        segments.append(
            Segment(
                transcript[path[i1].token_index],
                path[i1].time_index,
                path[i2 - 1].time_index + 1,
                score,
            )
        )
        i1 = i2
    return segments


# Merge segments into words (each part also showcases the corresponding framerate)
# Merge words
def merge_words(segments, separator="|"):
    words = []
    i1, i2 = 0, 0
    while i1 < len(segments):
        if i2 >= len(segments) or segments[i2].label == separator:
            if i1 != i2:
                segs = segments[i1:i2]
                word = "".join([seg.label for seg in segs])
                score = sum(seg.score * seg.length for seg in segs) / \
                    sum(seg.length for seg in segs)
                words.append(
                    Segment(word, segments[i1].start, segments[i2 - 1].end, score))
            i1 = i2 + 1
            i2 = i1
        else:
            i2 += 1
    return words


# Formatting portion, ensures that the time adheres to .ASS format
def format_time(seconds):
    """Format time in seconds to MM:SS.MS format"""
    minutes = int(seconds / 60)
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:06.3f}"


def format_time_ass(seconds):
    """Format time in ASS format (H:MM:SS.cc)"""
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds = seconds % 60
    centiseconds = int((seconds - int(seconds)) * 100)
    return f"{hours}:{minutes:02d}:{int(seconds):02d}.{centiseconds:02d}"


def display_segment(bundle, trellis, word_segments, waveform, i):
    ratio = waveform.size(1) / trellis.size(0)
    word = word_segments[i]
    x0 = int(ratio * word.start)
    x1 = int(ratio * word.end)
    start_time = x0 / bundle.sample_rate
    end_time = x1 / bundle.sample_rate
    formatted_start_time = format_time(start_time)
    formatted_end_time = format_time(end_time)
    segment = waveform[:, x0:x1]
    return (word.label, formatted_start_time, formatted_end_time)


# this portion converts it into ASS file format
def convert_timing_to_ass(timing_info, output_path):
    """Convert timing information to ASS subtitle format"""
    try:
        # Create ASS file header
        ass_content = """[Script Info]
Title: Generated Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,60,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,5,10,10,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        # Add dialogue events
        for word, start_time, end_time in timing_info:
            # Format times as h:mm:ss.cc
            start_str = format_time_ass(start_time)
            end_str = format_time_ass(end_time)

            # Filter out special effects markers like (break)
            if word.startswith('(') and word.endswith(')'):
                continue

            # Add dialogue line
            ass_content += f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{word}\n"

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
        return True
    except Exception as e:
        print(f"Error converting timing to ASS: {e}")
        return False

# Add a timeout handler for model downloads


class TimeoutError(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutError("Model download timed out")


def load_model_with_timeout(timeout=120):
    """Load the wav2vec2 model with a timeout"""
    original_handler = signal.getsignal(signal.SIGALRM)
    try:
        # Set the timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

        # Try to load the model
        bundle = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
        model = bundle.get_model()

        # Cancel the alarm if successful
        signal.alarm(0)
        return bundle, model
    except TimeoutError:
        logger.error(f"Model download timed out after {timeout} seconds")
        return None, None
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        return None, None
    finally:
        # Restore the original signal handler
        signal.signal(signal.SIGALRM, original_handler)
        signal.alarm(0)
