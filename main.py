# robot voice sourced from: https://evolution.voxeo.com/library/audio/prompts/alphabet/index.jsp

# python3 -m pip install pydub
from pydub import AudioSegment
from pydub.silence import detect_leading_silence
from pydub.effects import speedup
import winsound
import io
import logging as log
log.basicConfig(format="[%(asctime)s] [%(filename)s/%(levelname)s]: %(message)s (Line: %(lineno)s)",
                    datefmt="%H:%M:%S",
                    level=log.DEBUG)
log.getLogger("pydub").setLevel(log.ERROR)
#DEBUG > INFO > WARNING > ERROR > CRITICAL
import os
from pathlib import Path


CURRENT_DIR = os.path.dirname(__file__)
VOICES_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "voices"))
####################

VOICE_FOLDER = 'sham_max'
#INPUT_STRING = 'Hello world! The quick brown fox jumps over the lazy dog.' # for testing regular letters
#INPUT_STRING = 'what, flock, knock, wrong, comb, debt, edge, gnaw, column, dead' # for testing silent letters
#INPUT_STRING = 'phonics, quilt, cell, cinema' # testing digraphs (that just use alphabet sounds)
#INPUT_STRING = 'a~, e~, i~, o~, u~, shoot, chill, the~, wrong, loot, looter, boil, or' # testing the digraph sounds
#INPUT_STRING = 'bumble, bouncy, cyan, suit, blue, see, boar' # testing the stuff i just added obviously
INPUT_STRING = 'a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z, a~, e~, i~, o~, u~, sh, ch, th, ng, oo, er, oi, or, ph, qu, ci, cyh, cy, ui, ue, ee, oar, wh, ck, kn, wr, gn, ea, le, mb, bt, dge, mn' # test EVERY sound & digraph and stuff possible.

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
    sound_dict['~'] = AudioSegment.silent(duration=0)
    sound_dict[' '] = AudioSegment.silent(duration=100)
    sound_dict['.'] = AudioSegment.silent(duration=200)
    sound_dict[','] = AudioSegment.silent(duration=200)
    sound_dict['!'] = AudioSegment.silent(duration=350)

    log.info("Added silences to dict.")
    
    # LOAD SOUNDS FROM FILE
    ## GRAPHEMES (ALPHABET)
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
        if audio_file is None and letter in {'q', 'x'}:
            k_audio = sound_dict['k'] # q and x are last in the loop, so we already have the sounds we need in the dict

            if letter == 'q':
                w_audio = sound_dict['w']
                audio = k_audio + w_audio
                
            elif letter == 'x':
                s_audio = sound_dict['s']
                audio = k_audio + s_audio
            
        # Fail to find sound.
        elif audio_file is None:
            log.warning(f"Failed to find grapheme's sound file for: '{letter}' ")
            continue

        # Add sound to dict
        sound_dict[letter] = audio
        log.info(f"Added grapheme from file to dict: '{letter}' ")

    
    ## DIGRAPH SOUNDS
    digraph_list = ['sh', 'ch', 'th', 'ng', 'oo', 'er', 'oi', 'or',
               'a~', 'e~', 'i~', 'o~', 'u~']
    for digraph in digraph_list:
        audio_file = next(voice_path.glob(f"{digraph}.*"), None) # grabs first item from glob search

        # Grab and clean audio if found.
        if audio_file:
            audio = AudioSegment.from_file(audio_file)
            audio = strip_silence(audio)
        
        # Add sounds for digraphs with fallback
        elif digraph == 'u~':
            if 'oo' in sound_dict.keys():
                sound_dict['u~'] = sound_dict['y'] + sound_dict['oo']
                continue
            else:
                continue
        elif digraph == 'ng':
            sound_dict['ng'] = sound_dict['n']
            continue
        
        # Don't add digraphs without fallback to the dictionary
        else:
            log.info(f"Couldn't find sound file for: '{digraph}' ")
            continue
        
        # Add sound to dict
        sound_dict[digraph] = audio
        log.info(f"Added digraph from file to dict: '{digraph}' ")
    

    # ASSIGN DI(/TRI)GRAPHS TO PRE-LOADED SOUNDS
    ## SILENTS
    ### Always
    sound_dict['wh'] = sound_dict['w']
    sound_dict['ck'] = sound_dict['k']
    sound_dict['kn'] = sound_dict['n']
    sound_dict['wr'] = sound_dict['r']
    sound_dict['gn'] = sound_dict['n']
    sound_dict['ea'] = sound_dict['e']
    ### Only at end (logic must be run live ofc)
    only_at_end = {'dge',
                   'mb', 'bt', 'mn', 'le'}
    sound_dict['dge'] = sound_dict['j']
    sound_dict['mb'] = sound_dict['m']
    sound_dict['bt'] = sound_dict['t']
    sound_dict['mn'] = sound_dict['n']
    sound_dict['le'] = sound_dict['l']
    ### Multiple sound conditions
    multi_sound_conditions = {'cy'}
    if 'i~' in sound_dict.keys():
        sound_dict['cy_typical'] = sound_dict['s'] + sound_dict['i~']
    else:
        sound_dict['cy_typical'] = sound_dict['s'] + sound_dict['i']
    if 'e~' in sound_dict.keys(): 
        sound_dict['cy_end'] = sound_dict['s'] + sound_dict['e~']
    else:
        sound_dict['cy_end'] = sound_dict['s'] + sound_dict['e']


    ## TYPICAL
    sound_dict['ph'] = sound_dict['f']
    sound_dict['qu'] = sound_dict['q']
    sound_dict['ce'] = sound_dict['s'] + sound_dict['e']
    sound_dict['ci'] = sound_dict['s'] + sound_dict['i']
    if 'oo' in sound_dict.keys():
        sound_dict['ui'] = sound_dict['oo']
        sound_dict['ue'] = sound_dict['oo']
    else:
        sound_dict['ui'] = sound_dict['o']
        sound_dict['ue'] = sound_dict['o']
    if 'e~' in sound_dict.keys():
        sound_dict['ee'] = sound_dict['e~']
    if 'or' in sound_dict.keys():
        sound_dict['oar'] = sound_dict['or']
    else:
        sound_dict['oar'] = sound_dict['o'] + sound_dict['r']
    
    log.info(f"Assigned all di(/tri)graphs to sounds.")

    


    return sound_dict, only_at_end, multi_sound_conditions
        
log.info('Generating sound dictionary.')
sound_dict, only_at_end, multi_sound_conditions = gen_sound_dict(voices_path=VOICES_PATH, voice_folder=VOICE_FOLDER)
    
#######################################################################################

# GENERATE AUDIO FILE & LIVE PLAYBACK W/ TEXT INTEGRATION
log.info('Generating audio file.')
output_audio = AudioSegment.empty()

input_chars = list(INPUT_STRING.lower())
input_words = INPUT_STRING.lower().split()


skip = 0
output_text = ''
live_playback_text = []
live_playback_sound = []
for i, char in enumerate(input_chars):  
    if skip > 0:
        skip -= 1
        continue

    try:
        # where next_ INCLUDES the current character
        next_3 = input_chars[i : i+3]
        next_3 = ''.join(next_3)
        next_2 = input_chars[i : i+2]
        next_2 = ''.join(next_2)

        # This is required for both trigraphs and digraphs
        def isalpha_ignoring_tilde(string):
            return string.replace('~', '').isalpha()


        def at_end_of_word(chunk_size: int, input_chars=input_chars, i=i):
            # Check if at end (for those which require it)
            try:
                after_chunk = input_chars[i+chunk_size]
            except IndexError:
                after_chunk = ' ' # we can set it to a space cos that signals below that its the end of a word
        
            if isalpha_ignoring_tilde(after_chunk):
                return False
            else:
                return True

        # Trigraphs
        # think of the conditional as two separate conditionals, the second one is an if which is passing essentially (except it needs to be on this line so the code below runs)
        if next_3 in sound_dict.keys() and not (next_3 in only_at_end and not at_end_of_word(chunk_size=3)):
            sound = sound_dict[next_3]
            output_text += next_3
            skip = 2

        # Digraphs
        # think of the conditional as two separate conditionals, the second one is an if which is passing essentially (except it needs to be on this line so the code below runs)
        elif next_2 in sound_dict.keys() and not (next_2 in only_at_end and not at_end_of_word(chunk_size=2)):
            sound = sound_dict[next_2]
            output_text += next_2
            skip = 1
        
        # Double letters
        elif next_2 == f'{char}{char}' and isalpha_ignoring_tilde(next_2) and char not in {'a', 'e', 'i', 'o', 'u'}:
            sound = sound_dict[char]
            output_text += next_2
            skip = 1

        # Multiple sound conditions
        elif next_2 in multi_sound_conditions:
            # End of word:
            if at_end_of_word(chunk_size=2):
                sound = sound_dict.get(f'{next_2}_end', None)    
            # Typical:
            else:
                sound = sound_dict.get(f'{next_2}_typical', None)

            if sound is not None:
                output_text += next_2
                skip = 1
            else:
                sound = sound_dict[char]
                output_text += char
                skip = 0

        # Graphemes (alphabet)
        else:
            sound = sound_dict[char]
            output_text += char

        output_audio += sound

        live_playback_sound.append(sound)
        live_playback_text.append(output_text)


    # FAIL
    except KeyError:
        log.warning(f"Couldn't find sound in dict for: {char}")
        continue


#######################################################################################

#output_audio = speedup(output_audio, playback_speed=2)  # speedup via pydub is SUPER low quality, too much data loss
log.info('Complete. EXPORTING!')
path = os.path.join(CURRENT_DIR, f"output.mp3")
output_audio.export(path, format="mp3")

#########################################################################################

print('COMMENCING LIVE PLAYBACK')

for text, sound in zip(live_playback_text, live_playback_sound):
    print(text)
    # Play Sound
    wav = io.BytesIO()
    sound.export(wav, format="wav")
    winsound.PlaySound(wav.getvalue(), winsound.SND_MEMORY)

print('------ All done now :) ------')