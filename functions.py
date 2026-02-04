# python3 -m pip install pydub
from pydub import AudioSegment
from pydub.silence import detect_leading_silence
from pydub.effects import speedup
# python3 -m pip install pygame
import pygame
import logging as log
log.basicConfig(format="[%(asctime)s] [%(filename)s/%(levelname)s]: %(message)s (Line: %(lineno)s)",
                    datefmt="%H:%M:%S",
                    level=log.DEBUG)
log.getLogger("pydub").setLevel(log.ERROR)
#DEBUG > INFO > WARNING > ERROR > CRITICAL
import os
from pathlib import Path
import json
import pickle
import time
####################################################################################

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

####################################################################################

class VoiceSynthesiser:
    # Initialiser
    def __init__(self, settings_json_path=None, voice_path=None, sfx_path=None):
        if settings_json_path is not None:
            self.load_settings_json(file_path=settings_json_path)
        if voice_path:
            self.define_voice_and_sfx_file_paths(voice_path=voice_path, sfx_path=sfx_path)

    # DEFINE VOICE AND SFX PATHS
    def define_voice_and_sfx_file_paths(self, voice_path, sfx_path=None):
        self.VOICE_NAME = os.path.basename(voice_path)
        log.debug(self.VOICE_NAME)
        self.VOICE_PATH = Path(voice_path)
        if sfx_path:
            self.SFX_PATH = Path(sfx_path)

    # Settings JSON is not for defining file paths. That is done in the function above. (pkl_path is provided for load_sound_dictionary() as an arg)
    def load_settings_json(self, file_path):
        with open(file_path, 'r') as f:
            settings = json.load(f)
        self.INPUT_STRING_FROM_JSON = settings.get('TEXT_TO_SPEAK', None)
        self.VOICE_NAME_FROM_JSON = settings.get('voice_folder_name', None)

        self.PLAYBACK_SPEED = settings['playback_speed']
        if self.PLAYBACK_SPEED < 1:
            self.PLAYBACK_SPEED = 1

        self.USE_PKL = not settings['regenerate_sound_dictionary']

        self.SFX_ENABLED = settings['sfx_enabled']
        self.SFX_DICT = dict(zip(settings['characters_that_play_sfx'], settings['sfx_file_for_characters_to_use']))

        self.HIDE_VOWEL_TILDES = settings['hide_tildes_denoting_long_vowels_in_text_output']
    
    # LOAD SOUND DICT
    def load_sound_dictionary(self, pkl_path=None):
        USE_PKL = self.USE_PKL
        SFX_ENABLED = self.SFX_ENABLED
        SFX_DICT = self.SFX_DICT

        # LOAD FROM PKL
        if USE_PKL:
            if pkl_path is None:
                raise Exception('USE_PKL=True but pkl_path was not provided.')

            log.info(f'Loading sound dictionary from: {pkl_path}')
            try:
                with open(pkl_path, 'rb') as f:
                    sound_dict = pickle.load(f)
                failed_to_find_pkl = False
            except FileNotFoundError:
                failed_to_find_pkl = True

        # GENERATE FROM SCRATCH
        if (not USE_PKL) or (failed_to_find_pkl is True):
            log.info('Generating sound dictionary.')
            sound_dict = {}

            if not hasattr(self, 'VOICE_PATH'):
                raise Exception('Must set up a voice path')
            VOICE_PATH = self.VOICE_PATH

            if ( SFX_ENABLED is True ) and ( not hasattr(self, 'SFX_PATH') ):
                raise Exception('SFX_ENABLED=True so a SFX_PATH must be provided.')
            SFX_PATH = self.SFX_PATH

            # Function for later.
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
                    audio_file = next(VOICE_PATH.glob(f"k.*"), None)

                # Everything but c.
                else:
                    audio_file = next(VOICE_PATH.glob(f"{letter}.*"), None) # grabs first item from glob search

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
                audio_file = next(VOICE_PATH.glob(f"{digraph}.*"), None) # grabs first item from glob search

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
            sound_dict['dge'] = sound_dict['j']
            sound_dict['mb'] = sound_dict['m']
            sound_dict['bt'] = sound_dict['t']
            sound_dict['mn'] = sound_dict['n']
            sound_dict['le'] = sound_dict['l']
            ### Multiple sound conditions
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
                    audio_file = next(SFX_PATH.glob(f"{file_name}.*"), None) # grabs first item from glob search

                    # Grab and clean audio if found.
                    if audio_file:
                        audio = AudioSegment.from_file(audio_file)
                    
                    # Fail
                    else:
                        log.warning(f'Failed to find SFX file "{file_name}" for {char}')
                        continue

                    sound_dict[char] = audio
                    log.info(f"Added SFX '{file_name}' from file to dict for: {char}")
            
            # Save to PKL
            if pkl_path is not None:
                with open(pkl_path, 'wb') as f:
                    pickle.dump(sound_dict, f)
            else:
                log.info('pkl_path not provided. sound_dict was unable to be saved to pickle.')
        
        # Save sound dict as attribute no matter which option was chosen.
        self.sound_dict = sound_dict

    # GENERATE AUDIO  
    def generate_audio(self, input_string, output_path_folder, output_name='output'):
        if not hasattr(self, 'sound_dict'):
            raise Exception('Cannot generate audio without first loading the sound dictionary via load_sound_dictionary()')
        
        PLAYBACK_SPEED = self.PLAYBACK_SPEED
        USE_PKL = self.USE_PKL
        SFX_ENABLED = self.SFX_ENABLED
        SFX_DICT = self.SFX_DICT
        HIDE_VOWEL_TILDES = self.HIDE_VOWEL_TILDES

        log.info('Generating audio file.')

        ONLY_AT_END = {'dge',
            'mb', 'bt', 'mn', 'le'}
        MULTI_SOUND_CONDITIONS = {'cy'}
        
        sound_dict = self.sound_dict
        output_audio = AudioSegment.empty()

        input_chars = list(input_string)
        input_chars_lowercase = list(input_string.lower())

        # Build
        skip = 0
        output_text = ''
        live_playback_text_concatenated = []
        live_playback_text_individual = []
        live_playback_sound_lengths = []
        for i, char_lowercase in enumerate(input_chars_lowercase):  
            if skip > 0:
                skip -= 1
                continue

            try:
                # where next_ INCLUDES the current character
                next_3_lowercase = ''.join( input_chars_lowercase[i : i+3] )
                next_3_output = ''.join( input_chars[i : i+3] )

                next_2_lowercase = ''.join( input_chars_lowercase[i : i+2] )
                next_2_output = ''.join( input_chars[i : i+2] )

                char_output = input_chars[i]

                # This is required for both trigraphs and digraphs
                def isalpha_ignoring_tilde(string):
                    return string.replace('~', '').isalpha()


                def at_end_of_word(chunk_size: int, input_chars_lowercase=input_chars_lowercase, i=i):
                    # Check if at end (for those which require it)
                    try:
                        after_chunk = input_chars_lowercase[i+chunk_size]
                    except IndexError:
                        after_chunk = ' ' # we can set it to a space cos that signals below that its the end of a word
                
                    if isalpha_ignoring_tilde(after_chunk):
                        return False
                    else:
                        return True

                # Trigraphs
                # think of the conditional as two separate conditionals, the second one is an if which is passing essentially (except it needs to be on this line so the code below runs)
                if next_3_lowercase in sound_dict.keys() and not (next_3_lowercase in ONLY_AT_END and not at_end_of_word(chunk_size=3)):
                    output_text += next_3_output
                    sound = sound_dict[next_3_lowercase]
                    skip = 2

                # Digraphs
                # think of the conditional as two separate conditionals, the second one is an if which is passing essentially (except it needs to be on this line so the code below runs)
                elif next_2_lowercase in sound_dict.keys() and not (next_2_lowercase in ONLY_AT_END and not at_end_of_word(chunk_size=2)):
                    output_text += next_2_output
                    sound = sound_dict[next_2_lowercase]
                    skip = 1
                
                # Double letters
                elif next_2_lowercase == f'{char_lowercase}{char_lowercase}' and isalpha_ignoring_tilde(next_2_lowercase) and char_lowercase not in {'a', 'e', 'i', 'o', 'u'}:
                    output_text += next_2_output
                    sound = sound_dict[char_lowercase]
                    skip = 1

                # Multiple sound conditions
                elif next_2_lowercase in MULTI_SOUND_CONDITIONS:
                    # End of word:
                    if at_end_of_word(chunk_size=2):
                        sound = sound_dict.get(f'{next_2_lowercase}_end', None)    
                    # Typical:
                    else:
                        sound = sound_dict.get(f'{next_2_lowercase}_typical', None)

                    if sound is not None:
                        output_text += next_2_output
                        skip = 1
                    else:
                        output_text += char_output
                        sound = sound_dict[char_lowercase]
                        skip = 0

                # Graphemes (alphabet)
                else:
                    output_text += char_output
                    sound = sound_dict[char_lowercase]

            # FAILED TO FIND SOUND
            except KeyError:
                log.warning(f"Couldn't find sound in dict for: {char_lowercase}")
                sound = AudioSegment.silent(duration=0)
            
            # OUTPUT
            output_audio += sound
            live_playback_sound_lengths.append(sound.duration_seconds)

            if HIDE_VOWEL_TILDES:
                output_text = output_text.replace('a~', 'a').replace('e~', 'e').replace('i~', 'i').replace('o~', 'o').replace('u~', 'u')
            
            # Live playback text
            if live_playback_text_concatenated != []:
                current_chunk = output_text.removeprefix( live_playback_text_concatenated[-1] ) # by removing prev output_text from beginning of current output_text we get the change
            else:
                current_chunk = output_text
            live_playback_text_individual.append(current_chunk)

            live_playback_text_concatenated.append(output_text)
        
        # Export
        if PLAYBACK_SPEED != 1:
            output_audio = speedup(output_audio, playback_speed=PLAYBACK_SPEED)
        log.info('Complete. EXPORTING!')
        output_path_file = os.path.join(output_path_folder, f"{output_name}.wav")
        output_audio.export(output_path_file, format="wav")

        self.output_path_file = output_path_file
        self.live_playback_text_concatenated = live_playback_text_concatenated
        self.live_playback_text_individual = live_playback_text_individual
        self.live_playback_sound_lengths = live_playback_sound_lengths

    # LIVE PLAYBACK (GENERATOR)
    def live_playback(self, pre_concatenated_chunks=False):
        if not hasattr(self, 'PLAYBACK_SPEED'):
            log.warning('Playback speed not defined, defaulting to 1.')
            playback_speed = 1
        else:
            playback_speed = self.PLAYBACK_SPEED
        
        # Missing necessary attributes:
        if (not hasattr(self, 'output_path_file')) or (not hasattr(self, 'live_playback_text_concatenated')) or (not hasattr(self, 'live_playback_sound_lengths')):
            errorText = 'live_playback requires the class to have the following attributes which were not found:'
            if not hasattr(self, 'output_path_file'):
                errorText += ' output_path_file'
            if not hasattr(self, 'live_playback_text_concatenated'):
                errorText += ' live_playback_text_concatenated'
            if not hasattr(self, 'live_playback_sound_lengths'):
                errorText += ' live_playback_sound_lengths'
            raise Exception(errorText)

        # PLAY EXPORTED SOUND
        pygame.mixer.init()
        pygame.mixer.music.load(self.output_path_file)
        pygame.mixer.music.play()

        if pre_concatenated_chunks:
            text_list = self.live_playback_text_concatenated
        else:
            text_list = self.live_playback_text_individual

        for text, length in zip(text_list, self.live_playback_sound_lengths):
            yield text
            time.sleep(length/playback_speed)