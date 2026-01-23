# robot voice sourced from: https://evolution.voxeo.com/library/audio/prompts/alphabet/index.jsp

# pip install pydub
from pydub import AudioSegment
from pydub.silence import detect_leading_silence
from pydub.effects import speedup
import logging as log
log.basicConfig(format="[%(asctime)s] [%(filename)s/%(levelname)s]: %(message)s (Line: %(lineno)s)",
                    datefmt="%H:%M:%S",
                    level=log.DEBUG)
log.getLogger("pydub").setLevel(log.ERROR)
import os

CURRENT_DIR = os.path.dirname(__file__)
VOICES_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "voices"))
####################
'''
TO DO
- generate the silence threshold magic number automatically so its NOT a magic number (and works more consistently)
- find a good module for audio speed up that works with pydub, cos pydub's one is far too low quality
- make a mode where it can speak each character LIVE so you can run text integration
'''




VOICE_FOLDER = 'sham'
INPUT_STRING = 'Hello world.'

# TRIM LEADING AND TRAILING SILENCE
def trim_leading_silence(audio: AudioSegment) -> AudioSegment:
    average_loudness = audio.dBFS
    silence_threshold = average_loudness - 2.5 # magic number was 16, but was lowered to deal with louder bg noise

    silence_ms = detect_leading_silence(audio, silence_threshold=silence_threshold)
    return audio[silence_ms:]


def trim_trailing_silence(audio: AudioSegment) -> AudioSegment:
    return trim_leading_silence(audio.reverse()).reverse()


def strip_silence(audio: AudioSegment) -> AudioSegment:
    audio = trim_leading_silence(audio)
    audio = trim_trailing_silence(audio)
    return audio


# GENERATE SOUNDS DICTIONARY
def gen_dict(voices_path, voice_folder):
    sound_dict = {}

    voice_path = os.path.join(voices_path, voice_folder)
    for file in os.listdir(voice_path):
        # Get sound name (eg letter) and file type (eg mp3)
        path = os.path.join(voice_path, file)
        if os.path.isfile(path):
            sound_name, file_extension = os.path.splitext(file)
            file_type = file_extension[1:]

        try:
            loader = getattr(AudioSegment, f"from_{file_type}")
        except AttributeError:
            raise ValueError(f"Unsupported audio format: {file_type}")
        audio = loader(path) # where loader is something like AudioSegment.from_mp3, from_wav, etc

        audio = strip_silence(audio)
        sound_dict[sound_name] = audio
    
    return sound_dict
        
log.info('Generating sound dictionary.')
sound_dict = gen_dict(voices_path=VOICES_PATH, voice_folder=VOICE_FOLDER)
    


# GENERATE AUDIO FILE
log.info('Generating audio file.')
output_audio = AudioSegment.empty()
input_list = list(INPUT_STRING.upper())
for char in input_list:
    try:
        output_audio += sound_dict[char]
    except KeyError:
        # AudioSegment.silent's duration field is in milliseconds (1s = 1000ms)
        if char == ' ':
            output_audio += AudioSegment.silent(duration=100)
        if char == '.' or char == ',':
            output_audio += AudioSegment.silent(duration=200)
        if char == '!':
            output_audio += AudioSegment.silent(duration=350)
        else:
            continue


#output_audio = speedup(output_audio, playback_speed=2)  # speedup via pydub is SUPER low quality, too much data loss
log.info('Complete. EXPORTING!')
path = os.path.join(CURRENT_DIR, f"output.mp3")
output_audio.export(path, format="mp3")
