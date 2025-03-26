import re
import inflect
import string

# Script to pre-process the dictionary path


def remove_punctuation(text):
    # Define the punctuation to remove
    punctuation_to_remove = r'[.,:!]'

    # Remove punctuation
    text_without_punctuation = re.sub(punctuation_to_remove, '', text)

    return text_without_punctuation


def split_text_into_words(text):
    # Split the text into words
    words = text.split()

    return words


# This is necessary as it aids in force alignment
def clean_text(text):
    """Clean text by properly separating concatenated words and handling numbers"""
    # Handle common concatenation patterns
    text = re.sub(r'([A-Z][a-z]+)([A-Z])', r'\1 \2', text)  # CamelCase
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # camelCase
    text = re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', text)  # UPPERCase

    # Handle numbers with words
    text = re.sub(r'([0-9]+)([A-Z][a-z]*)', r'\1 \2',
                  text)  # Numbers followed by words
    text = re.sub(r'([A-Z][a-z]*)([0-9]+)', r'\1 \2',
                  text)  # Words followed by numbers
    # Add spaces around standalone numbers
    text = re.sub(r'(\d+)', r' \1 ', text)

    # Split any remaining concatenated words by capital letters
    words = []
    for word in text.split():
        if word.isupper() and len(word) > 1:
            # Split uppercase words while preserving acronyms
            split_words = re.findall('[A-Z][^A-Z]*', word)
            if split_words:
                words.extend(split_words)
            else:
                words.append(word)
        else:
            words.append(word)

    # Join words and normalize spaces
    cleaned_text = ' '.join(words)
    cleaned_text = ' '.join(cleaned_text.split())

    return cleaned_text

# SECTION 1
# converting the scraped text into individual lettering + split lines


def process_text(input_filename, output_filename):
    """Process text while maintaining proper word spacing and handling special effects"""
    try:
        # Read the input text from the file
        with open(input_filename, 'r', encoding='utf-8') as input_file:
            text = input_file.read()

        # Define special effects to preserve
        effects = ['(break)', '(long-break)', '(breath)', '(laugh)', '(cough)',
                   '(lip-smacking)', '(sigh)', '(burp)']

        # Split text into words and process each word
        words = []
        for word in text.split():
            # If word is a special effect, preserve it exactly
            if word in effects:
                words.append(word)
                continue

            # Remove punctuation from non-effect words
            word = remove_punctuation(word)

            # Handle camelCase and UPPERCASE patterns
            if word.isupper() and len(word) > 1:
                # Split uppercase words while preserving acronyms
                split_words = re.findall(
                    '[A-Z][A-Z]*(?=[A-Z][a-z])|[A-Z][a-z]*', word)
                if split_words:
                    words.extend(split_words)
                else:
                    words.append(word)
            else:
                # Handle numbers attached to words
                number_splits = re.split('([0-9]+)', word)
                words.extend(part for part in number_splits if part)

        # Join words with proper spacing and convert to uppercase
        final_text = ' '.join(words).upper()

        # Write the processed text to file
        with open(output_filename, 'w', encoding='utf-8') as output_file:
            output_file.write(final_text)

        print(f"Output written to {output_filename} successfully.")

    except FileNotFoundError:
        print(f"Error: The file {input_filename} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


# SECTION 2
# Removes punctuation and ensures that the words are converted into ordinals
def process_text_section2(input_file_path, output_file_path):
    """Process text while handling numbers and maintaining word spacing"""
    p = inflect.engine()

    try:
        with open(input_file_path, 'r', encoding='utf-8') as file:
            text = file.read()
    except:
        raise TypeError

    # Define special effects to preserve
    effects = ['(break)', '(long-break)', '(breath)', '(laugh)', '(cough)',
               '(lip-smacking)', '(sigh)', '(burp)']

    # Split text into words and handle each word
    words = text.split()
    processed_words = []

    for word in words:
        # If word is a special effect, preserve it exactly
        if word in effects:
            processed_words.append(word)
            continue

        # Convert numbers and handle ordinals
        if word.isdigit() or re.match(r'^\d+(st|nd|rd|th)$', word.lower()):
            # Convert the number to words
            if re.match(r'^\d+(st|nd|rd|th)$', word.lower()):
                # Handle ordinal numbers
                cardinal = re.sub(r'(st|nd|rd|th)$', '', word.lower())
                word_form = p.number_to_words(cardinal)
                processed = p.ordinal(word_form).upper()
            else:
                # Handle cardinal numbers
                processed = p.number_to_words(word).upper()

            # Split hyphenated numbers into separate words
            processed = processed.replace('-', ' ')
            processed_words.append(processed)
        else:
            # Keep words as is, just uppercase them
            processed_words.append(word.upper())

    # Join words with proper spacing
    final_text = ' '.join(processed_words)

    # Write processed text
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write(final_text)
