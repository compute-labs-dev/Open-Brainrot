# Open Brain Rot

![Logo](images/logo.jpg)
<Created with Imagen 3>

## Updates:

Thank you everyone for the support so far albeit the r/learnmachinelearning && r/machinelearning community! In short here are some future updates I would be doing overtime

1. Readjusting the text and font :white_check_mark:
2. Adding k-ranking sentiments using VADER :white_check_mark:
3. Adding parallel compute (Very much in the future)
4. Add support for generative image and video in the future
5. Create CLI interface or fully functional website :white_check_mark:
6. Update readme for LLM scraping feature! :white_check_mark:

## New Updates!!:

### UI Interface has finally been created!

![UI Interface](images/ui.png)

To facilitate and make things easier to create videos, I have created a web interface to make things easier.

### So i got extremely bored over the holidays and decided to just make a fun project to see if its possible to automate the kind of content i was seeing on TikTok

## A simple brain rot generator just by inserting your reddit url

## Example

[![Watch the video](images/thumbnail.png)](https://youtube.com/shorts/CRhbay8YvBg)

## How it works

### High Level Diagram

![Diagram](images/diagram.png)

### Switch

Deciding if its a thread or an actual link based on the link provided, if it is a thread it will go through a filter via VADER and llama 3.3 70b via sentiment analysis to see which thread to select, else it would enter directly into scraping.

### Scraping

Simple webscraping using Reddit's open source API, to collect the title and story based off the reddit website

### Voice Translation:

Using Coqui's xTTSv2 (which is super lightweight , portable and accurate), I converted the text into audio. Coqui's TTS audio also allows you to use sample audios, so I used the common-man's TikTok audio.

### Pre-processing:

Removal of certain punctuations, special characters via RegEx before we carry out force alignment.

### On Force Alignment:

The most important step to generate the video was the alignment between audio and text in order to get the subtitle. This was achieved using forced alignment. In this, we used wav2vec2 and base it all on Motu Hira's tutorial on Forced alignment with Wav2Vec2. It uses a frame-wise label probality from the audio (that is the voice that we generated), creates a trellis matrix representing the probability of labels aligned per time step before using the most likely path from the trellis matrix.

### ffpmeg Magic:

Once we got the audio, video sample as well as the timestamp text (which is in .ass format btw), we can then generate the video using some simple ffmpeg magic. This subprocess can be viewed under

`video_generator.py`

## How to run it

There are mainly 6 important scripts within this, each deliberately separated so that it can be easier to include any upgrades in the future (and what not)

### Pre-requisites:

1. PyTorch (with CUDA 12.4)
2. Coqui TTS ([Link](https://github.com/coqui-ai/TTS))
3. FFMpeg ([Link](https://www.ffmpeg.org/))

Afterwards, just run the script

` python server.py`

and you are good to go!

Take note, when turning on the reddit link thread,

![Terminal](images/terminal.png)

it will prompt for Groq API Key which can be acquired when you sign up as a Groq member. I will look into integrated other LLMs or creating your own heuristics too in the future :).

## Others:

### Why is there no requirements.txt?

I installed the script on my personal venv so if i were to make a pip it would be very messy (and I am too lazy to do that) ~ in general just follow the instructs on how to run it above and it should be good

### Are there any future updates?

So far , yes there are but it is to hopefully create website or gradio to make this more user friendly, and to hopefully create more brain rot videos in the future (i am looking at OpenSora but no plans as of now)

## Thanks:

I would like to thank Motu Hira for creating this tutorial on Forced Alignment using Wav2Vec2. Without this, the subtitles would not be able to work (the original plan was to use CMUSphinx but the lack of community support made it difficult for me to work with)

Here is the original Tutorial if anyone is interested:

[Link](https://pytorch.org/audio/main/tutorials/forced_alignment_tutorial.html)

## Database Schema Tests

The project includes a suite of tests to verify the database schema changes and interactions with the updated schema. These tests are located in the `tests` directory.

To run all the tests at once, use:

```bash
./tests/run_all_tests.sh
```

Or run individual tests:

```bash
# Test basic database interactions
./tests/test_db_schema.py

# Test voice field handling in database operations
./tests/test_db_voice.py
./tests/test_db_voice_insert.py
./tests/test_db_update_status.py

# Test process_voice function
./tests/test_process_voice.py
```

For detailed information about the database schema changes, see [tests/README_DB_SCHEMA_CHANGES.md](tests/README_DB_SCHEMA_CHANGES.md).
