# robot voice sourced from: https://evolution.voxeo.com/library/audio/prompts/alphabet/index.jsp

# python3 -m pip install pydub
from pydub import AudioSegment
from pydub.silence import detect_leading_silence
from pydub.effects import speedup
import logging as log
log.basicConfig(format="[%(asctime)s] [%(filename)s/%(levelname)s]: %(message)s (Line: %(lineno)s)",
                    datefmt="%H:%M:%S",
                    level=log.DEBUG)
log.getLogger("pydub").setLevel(log.ERROR)
#DEBUG > INFO > WARNING > ERROR > CRITICAL
import os
from pathlib import Path
import string

CURRENT_DIR = os.path.dirname(__file__)
VOICES_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "voices"))
####################

VOICE_FOLDER = 'sham_all'
INPUT_STRING = 'Hello world! The quick brown fox jumps over the lazy dog.'


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
def gen_sound_dict(voices_path, voice_folder):
    sound_dict = {}

    ##voice_path = os.path.join(voices_path, voice_folder)
    voice_path = Path(voices_path) / voice_folder
    # GRAPHEMES (alphabet)
    for letter in string.ascii_lowercase:
        # c uses the k sound.
        if letter == 'c':
            audio_file = next(voice_path.glob(f"k.*"), None)

        # Everything but c.
        else:
            audio_file = next(voice_path.glob(f"{letter}.*"), None) # grabs first item from glob search

        # Grab and clean audio if found.
        if audio_file:
            audio = AudioSegment.from_file(audio_file)
            audio = strip_silence(audio)

        # Handle the optional q and x sounds (if sound not found).
        if audio_file is None and letter == 'q' or letter == 'x':
            k_audio_file = next(voice_path.glob(f"k.*"), None)
            k_audio = AudioSegment.from_file(k_audio_file)
            k_audio = strip_silence(k_audio)

            if letter == 'q':
                w_audio_file = next(voice_path.glob(f"w.*"), None)
                w_audio = AudioSegment.from_file(w_audio_file)
                w_audio = strip_silence(w_audio)

                audio = k_audio + w_audio
                
            elif letter == 'x':
                s_audio_file = next(voice_path.glob(f"s.*"), None)
                s_audio = AudioSegment.from_file(s_audio_file)
                s_audio = strip_silence(s_audio)

                audio = k_audio + s_audio
            
        # Fail to find sound.
        elif audio_file is None:
            log.warning(f"Failed to find grapheme's sound file for: '{letter}' ")
            continue

        # Add sound to dict
        log.info(f"Added grapheme to dict: '{letter}' ")
        sound_dict[letter] = audio
  
    return sound_dict
        
log.info('Generating sound dictionary.')
sound_dict = gen_sound_dict(voices_path=VOICES_PATH, voice_folder=VOICE_FOLDER)
    


# GENERATE AUDIO FILE
log.info('Generating audio file.')
output_audio = AudioSegment.empty()
input_list = list(INPUT_STRING.lower())
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
