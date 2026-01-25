# robot voice sourced from: https://evolution.voxeo.com/library/audio/prompts/alphabet/index.jsp

# python3 -m pip install pydub
from pydub import AudioSegment
from pydub.silence import detect_leading_silence
from pydub.playback import play
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
#INPUT_STRING = 'Hello world! The quick brown fox jumps over the lazy dog.' # for testing regular letters
INPUT_STRING = 'what, flock, knock, wrong, comb, debt, edge, gnaw, column, dead' # for testing silent letters


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
    voice_path = Path(voices_path) / voice_folder

    # SILENCES
    # AudioSegment.silent's duration field is in milliseconds (1s = 1000ms)
    sound_dict[' '] = AudioSegment.silent(duration=100)
    sound_dict['.'] = AudioSegment.silent(duration=200)
    sound_dict[','] = AudioSegment.silent(duration=200)
    sound_dict['!'] = AudioSegment.silent(duration=350)

    log.info("Added silences to dict.")
    
    # GRAPHEMES (ALPHABET)
    for letter in 'abcdefghijklmnoprstuvwyzqx':
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
            k_audio = sound_dict['k'] # q and x are last in the loop, so we already have the sounds we need in the dict

            if letter == 'q':
                w_audio = sound_dict['w']
                audio = k_audio + w_audio
                
            elif letter == 'x':
                s_audio = sound_dict['w']
                audio = k_audio + s_audio
            
        # Fail to find sound.
        elif audio_file is None:
            log.warning(f"Failed to find grapheme's sound file for: '{letter}' ")
            continue

        # Add sound to dict
        log.info(f"Added grapheme to dict: '{letter}' ")
        sound_dict[letter] = audio
  
    # DIGRAPHS
    ## SILENTS
    ### Always
    sound_dict['wh'] = sound_dict['w']
    sound_dict['ck'] = sound_dict['k']
    sound_dict['kn'] = sound_dict['n']
    sound_dict['wr'] = sound_dict['r']
    sound_dict['gn'] = sound_dict['n']
    sound_dict['ea'] = sound_dict['e']
    ### Only at end (logic must be run live ofc)
    sound_dict['mb'] = sound_dict['m']
    sound_dict['bt'] = sound_dict['t']
    sound_dict['dge'] = sound_dict['j']
    sound_dict['mn'] = sound_dict['n']
    log.info(f"Added silent di(/tri)graphs: '{letter}' ")


    return sound_dict
        
log.info('Generating sound dictionary.')
sound_dict = gen_sound_dict(voices_path=VOICES_PATH, voice_folder=VOICE_FOLDER)
    
#######################################################################################

# GENERATE AUDIO FILE
log.info('Generating audio file.')
output_audio = AudioSegment.empty()

input_chars = list(INPUT_STRING.lower())
input_words = INPUT_STRING.lower().split()

skip = 0
for i, char in enumerate(input_chars):
    if skip > 0:
        log.debug(f'SKIPPED {char}')
        skip -= 1
        continue

    try:
        # where next_ INCLUDES the current character
        next_3 = input_chars[i : i+3]
        next_3 = ''.join(next_3)
        next_2 = input_chars[i : i+2]
        next_2 = ''.join(next_2)

        # Trigraphs
        if next_3 in sound_dict.keys():
            sound = sound_dict[next_3]
            skip = 2

        # Digraphs
        elif next_2 in sound_dict.keys():
            sound = sound_dict[next_2]
            skip = 1

        # Graphemes (alphabet)
        else:
            sound = sound_dict[char]

        output_audio += sound
        play(sound)

    # FAIL
    except KeyError:
        log.warning(f"Couldn't find sound in dict for: {char}")
        continue


#######################################################################################

#output_audio = speedup(output_audio, playback_speed=2)  # speedup via pydub is SUPER low quality, too much data loss
log.info('Complete. EXPORTING!')
path = os.path.join(CURRENT_DIR, f"output.mp3")
output_audio.export(path, format="mp3")
