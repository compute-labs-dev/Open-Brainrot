from scraping import *
from audio import * 
from force_alignment import * 
from dict import * 
from video_generator import * 
from search import *
from brainrot_generator import transform_to_brainrot

def main(reddit_url, llm=False, scraped_url='texts/scraped_url.txt', output_pre='texts/processed_output.txt',
         final_output='texts/oof.txt', speech_final='audio/output_converted.wav', subtitle_path='texts/testing.ass',
         output_path='final/final.mp4', speaker_wav="assets/default.mp3", video_path='assets/subway.mp4', 
         language="en-us", api_key=None):
    
    print("L1: SCRAPING RIGHT NOW")
    if reddit_url:  # Only try to scrape if URL is provided
        if not llm:
            map_request = scrape(reddit_url)
        else:
            print("Using LLM to determine best thread to scrape")
            print("-------------------")
            reddit_scrape = scrape_llm(reddit_url)
            text = vader(reddit_scrape)
            if not api_key:
                api_key = input("Please input the API key\n")
            map_request = groq(text, api_key)
        print(map_request)
        save_map_to_txt(map_request, scraped_url)
    
    # Transform content to brainrot style
    print("L1.5: TRANSFORMING TO BRAINROT STYLE")
    brainrot_file = 'texts/brainrot_output.txt'
    transform_to_brainrot(scraped_url, brainrot_file, api_key)
    
    # ## AUDIO CONVERSION 
    print("L2: AUDIO CONVERSION NOW (TAKES THE LONGEST)")
    audio_wrapper(brainrot_file, speaker_wav=speaker_wav, language=language)
    convert_audio('audio/output.wav',speech_final)
    
    # IMPORTANT PRE PROCESSING STUFF 
    process_text(brainrot_file, output_pre)
    process_text_section2(output_pre, final_output)

    with open(final_output, 'r') as file: 
        text = file.read().strip()
    
    # A BUNCH OF HARDCORE FORCED ALIGNMENT FORMATTING
    print("L3: FORCE ALIGNMENT")
    transcript = format_text(text)
    bundle, waveform, labels, emission1 = class_label_prob(speech_final)
    trellis,emission,tokens = trellis_algo(labels,text,emission1)
    path = backtrack(trellis, emission, tokens)
    segments = merge_repeats(path, transcript)
    word_segments = merge_words(segments)
    timing_list = []
    for (i, word) in enumerate(word_segments):
        timing_list.append((display_segment(bundle, trellis, word_segments, waveform, i)))
    
    # FINAL VIDEO
    print("L4: VIDEO GENERATION")
    convert_timing_to_ass(timing_list, subtitle_path)

    ## Finally, we need to generate the brain rot video itself
    add_subtitles_and_overlay_audio(video_path,speech_final, subtitle_path, output_path)
    print("DONE! SAVED AT " + output_path)

if __name__ == "__main__":
    main("https://www.reddit.com/r/askSingapore/", llm = True)