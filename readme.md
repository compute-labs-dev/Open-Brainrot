# Open Brain Rot 
![Logo](images/logo.jpg)

### So i got extremely bored over the holidays and decided to just make a fun project to see if its possible to automate the kind of content i was seeing on TikTok

## A simple brain rot generator just by inserting your reddit url

## Example
[![Watch the video](images/thumbnail.png)](https://youtube.com/shorts/CRhbay8YvBg)


## How it works 
Insert Short & Sweet Diagram 

## How to run it
There are mainly 6 important scripts within this, each deliberately separated so that it can be easier to include any upgrades in the future (and what not)

### Pre-requisites:
1. PyTorch (with CUDA 12.4)
2. Conqui TTS ([Link](https://github.com/coqui-ai/TTS))
3. FFMpeg ([Link](https://www.ffmpeg.org/))

Afterwards, just run the script 

``` python main.py```

and you are good to go!

## Others:
### Why is there no requirements.txt? 
I installed the script on my personal venv so if i were to make a pip it would be very messy (and I am too lazy to do that)  ~ in general just follow the instructs on how to run it above and it should be good

### Are there any future updates?
So far , yes there are but it is to hopefully create website or gradio to make this more user friendly, furthermore to hopefully create more brain rot videos in the future (i am looking at OpenSora but no plans as of now)


## Thanks:
I would like to thank Motu Hira for creatig this tutorial on Forced Alignment using Wav2Vec2. Without this, the subtitles would not be able to work (the original plan was to use CMUSphinx but the lack of community support made it difficult for me to work with)

Here is the original Tutorial if anyone is interested: 

[Link](https://pytorch.org/audio/main/tutorials/forced_alignment_tutorial.html)