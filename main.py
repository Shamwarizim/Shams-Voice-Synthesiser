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
import json


CURRENT_DIR = os.path.dirname(__file__)
VOICES_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "voices"))
SFX_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "sfx"))

####################

# Load settings.
with open('.INPUT.json', 'r') as f:
    settings = json.load(f)
INPUT_STRING = settings['TEXT_TO_SPEAK']
VOICE_FOLDER = settings['voice_folder_name']

SFX_ENABLED = settings['sfx_enabled']
SFX_DICT = dict(zip(settings['characters_that_play_sfx'], settings['sfx_file_for_characters_to_use']))

HIDE_TILDE = settings['hide_tildes_in_text_output']



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
    sfx_path = Path(SFX_PATH)

    def assign_existing_sounds(sound_names: list):
        new_sound = AudioSegment.empty()
        for sound_name in sound_names:
            new_sound += sound_dict[sound_name]
        return new_sound

    # SILENCES
    # AudioSegment.silent's duration field is in milliseconds (1s = 1000ms)
    #0
    sound_dict['~'] = AudioSegment.silent(duration=0)
    #50
    for char in ['(', ')', '[', ']', '{', '}', ':', ';', '"', "'"]: sound_dict[char] = AudioSegment.silent(duration=50)
    #100
    for char in [' ', '-']: sound_dict[char] = AudioSegment.silent(duration=100)
    #200
    for char in ['.', ',', '/', '\\']: sound_dict[char] = AudioSegment.silent(duration=200)
    #350
    for char in ['!', '?', '...', '…']: sound_dict[char] = AudioSegment.silent(duration=350)

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
                sound_dict['u~'] = assign_existing_sounds(['y', 'oo'])
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
        sound_dict['cy_typical'] = assign_existing_sounds(['s', 'i~'])
    else:
        sound_dict['cy_typical'] = assign_existing_sounds(['s', 'i'])
    if 'e~' in sound_dict.keys(): 
        sound_dict['cy_end'] = assign_existing_sounds(['s', 'e~'])
    else:
        sound_dict['cy_end'] = assign_existing_sounds(['s', 'e'])


    ## TYPICAL
    sound_dict['ph'] = sound_dict['f']
    sound_dict['qu'] = sound_dict['q']
    sound_dict['ce'] = assign_existing_sounds(['s', 'e'])
    sound_dict['ci'] = assign_existing_sounds(['s', 'i'])
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
        sound_dict['oar'] = assign_existing_sounds(['o', 'r'])
    
    log.info(f"Assigned all di(/tri)graphs to sounds.")


    # SPECIAL CHARACTERS TO READ OUT
    ## Numbers
    sound_dict['1'] = assign_existing_sounds(['w', 'u', 'n'])

    if 'oo' in sound_dict.keys():
        sound_dict['2'] = assign_existing_sounds(['t', 'oo'])
    else:
        sound_dict['2'] = assign_existing_sounds(['t', 'w', 'o'])

    if 'th' in sound_dict.keys() and 'ee' in sound_dict.keys():
        sound_dict['3'] = assign_existing_sounds(['th', 'r', 'ee'])
    else:
        sound_dict['3'] = assign_existing_sounds(['t', 'h', 'r', 'e', 'e'])
    
    if 'or' in sound_dict.keys():
        sound_dict['4'] = assign_existing_sounds(['f', 'or'])
    else:
        sound_dict['4'] = assign_existing_sounds(['f', 'o', 'r'])
    
    if 'i~' in sound_dict.keys():
        sound_dict['5'] = assign_existing_sounds(['f', 'i~', 'v'])
    else:
        sound_dict['5'] = assign_existing_sounds(['f', 'i', 'v'])
    
    sound_dict['6'] = assign_existing_sounds(['s', 'i', 'x'])

    sound_dict['7'] = assign_existing_sounds(['s', 'e', 'v', 'i', 'n'])

    if 'a~' in sound_dict.keys():
        sound_dict['8'] = assign_existing_sounds(['a~', 't'])
    else:
        sound_dict['8'] = assign_existing_sounds(['e', 't'])
    
    if 'i~' in sound_dict.keys():
        sound_dict['9'] = assign_existing_sounds(['n', 'i~', 'n'])
    else:
        sound_dict['9'] = assign_existing_sounds(['n', 'i', 'n'])
    
    if 'e~' in sound_dict.keys() and 'o~' in sound_dict.keys():
        sound_dict['0'] = assign_existing_sounds(['z', 'e~', 'r', 'o~'])
    elif 'e~' in sound_dict.keys():
        sound_dict['0'] = assign_existing_sounds(['z', 'e~', 'r', 'o'])
    elif 'o~' in sound_dict.keys():
        sound_dict['0'] = assign_existing_sounds(['z', 'e', 'r', 'o~'])
    else:
        sound_dict['0'] = assign_existing_sounds(['z', 'e', 'r', 'o'])

    ## NOT NUMBERS
    sound_dict['@'] = assign_existing_sounds(['a', 't'])

    if 'sh' in sound_dict.keys():
        sound_dict['#'] = assign_existing_sounds(['h', 'a', 'sh', 't', 'a', 'g'])
    else:
        sound_dict['#'] = assign_existing_sounds(['h', 'a', 's', 'h', 't', 'a', 'g'])
    
    if 'er' in sound_dict.keys():
        sound_dict['$'] = assign_existing_sounds(['d', 'o', 'l', 'er'])
    else:
        sound_dict['$'] = assign_existing_sounds(['d', 'o', 'l', 'u'])
    
    if 'er' in sound_dict.keys():
        sound_dict['%'] = assign_existing_sounds(['p', 'er', 's', 'e', 'n', 't'])
    else:
        sound_dict['%'] = assign_existing_sounds(['p', 'e', 'r', 's', 'e', 'n', 't'])
    
    sound_dict['^'] = assign_existing_sounds(['c', 'a', 'r', 'i', 't'])

    sound_dict['&'] = assign_existing_sounds(['a', 'n', 'd'])

    if 'er' in sound_dict.keys():
        sound_dict['*'] = assign_existing_sounds(['a', 's', 't', 'er', 'i', 's', 'k'])
    else:
        sound_dict['*'] = assign_existing_sounds(['a', 's', 't', 'e', 'r', 'i', 's', 'k'])
    
    if 'er' in sound_dict.keys() and 'or' in sound_dict.keys():
        sound_dict['_'] = assign_existing_sounds(['u', 'n', 'd', 'er', 's', 'k', 'or'])
    elif 'er' in sound_dict.keys():
        sound_dict['_'] = assign_existing_sounds(['u', 'n', 'd', 'er', 's', 'k', 'o'])
    elif 'or' in sound_dict.keys():
        sound_dict['_'] = assign_existing_sounds(['u', 'n', 'd', 'or', 's', 'k', 'or'])
    else:
        sound_dict['_'] = assign_existing_sounds(['u', 'n', 'd', 'o', 's', 'k', 'o'])
    
    sound_dict['+'] = assign_existing_sounds(['p', 'l', 'u', 's'])

    if 'e~' in sound_dict.keys():
        sound_dict['='] = assign_existing_sounds(['e~', 'q', 'l', 's'])
    else:
        sound_dict['='] = assign_existing_sounds(['e', 'q', 'l', 's'])
    
    if 'i~' in sound_dict.keys():
        sound_dict['|'] = assign_existing_sounds(['p', 'i~', 'p'])
    else:
        sound_dict['|'] = assign_existing_sounds(['p', 'i', 'p'])
    
    if 'th' in sound_dict.keys():
        sound_dict['<'] = assign_existing_sounds(['l', 'e', 's', ' ', 'th', 'a', 'n'])
    else:
        sound_dict['<'] = assign_existing_sounds(['l', 'e', 's', ' ', 't', 'h', 'a', 'n'])
    
    # >
    if 'a~' in sound_dict.keys():
        a = 'a~'
    else:
        a = 'e'
    if 'er' in sound_dict.keys():
        er = 'er'
    else:
        er = 'u'
    if 'th' in sound_dict.keys():
        th = 'th'
    else:
        th = 't'
    sound_dict['>'] = assign_existing_sounds(['g', 'r', a, 't', er, th, 'a', 'n'])

    sound_dict['~'] = assign_existing_sounds(['t', 'i', 'l', 'd', 'u'])
    
    log.info(f"Assigned read out special characters to sounds.")

    
    # SFX
    if SFX_ENABLED:
        for char, file_name in SFX_DICT.items():
            audio_file = next(sfx_path.glob(f"{file_name}.*"), None) # grabs first item from glob search

            # Grab and clean audio if found.
            if audio_file:
                audio = AudioSegment.from_file(audio_file)
            
            # Fail
            else:
                log.warning(f'Failed to find SFX file "{file_name}" for {char}')
                continue

            sound_dict[char] = audio
            log.info(f"Added SFX '{file_name}' from file to dict for: {char}")

    


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
            output_text += next_3
            sound = sound_dict[next_3]
            skip = 2

        # Digraphs
        # think of the conditional as two separate conditionals, the second one is an if which is passing essentially (except it needs to be on this line so the code below runs)
        elif next_2 in sound_dict.keys() and not (next_2 in only_at_end and not at_end_of_word(chunk_size=2)):
            output_text += next_2
            sound = sound_dict[next_2]
            skip = 1
        
        # Double letters
        elif next_2 == f'{char}{char}' and isalpha_ignoring_tilde(next_2) and char not in {'a', 'e', 'i', 'o', 'u'}:
            output_text += next_2
            sound = sound_dict[char]
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
                output_text += char
                sound = sound_dict[char]
                skip = 0

        # Graphemes (alphabet)
        else:
            output_text += char
            sound = sound_dict[char]

    # FAILED TO FIND SOUND
    except KeyError:
        log.warning(f"Couldn't find sound in dict for: {char}")
        sound = AudioSegment.silent(duration=0)
    
    # OUTPUT
    output_audio += sound
    live_playback_sound.append(sound)

    if HIDE_TILDE:
        output_text = output_text.replace('~', '')
    live_playback_text.append(output_text)

    


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