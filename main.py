import os

from functions import VoiceSynthesiser

CURRENT_DIR = os.path.dirname(__file__)
VOICES_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "voices"))
SFX_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "sfx"))
PKL_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "pickles"))
SOUND_DICT_PKL_PATH = os.path.abspath(os.path.join(PKL_PATH, 'sound_dict'))

# SETUP
settings_json_path = os.path.join(CURRENT_DIR, '.SETTINGS.json')
vs = VoiceSynthesiser(settings_json_path = settings_json_path)

voice_path = os.path.join(VOICES_PATH, vs.VOICE_NAME_FROM_JSON) # if you only want one voice you'd replace vs.VOICE_NAME_FROM_JSON with the specific name, otherwise do from JSON or from your own variable
vs.define_voice_and_sfx_file_paths(voice_path=voice_path, sfx_path=SFX_PATH)

# LOAD SOUND DICT
pkl_path = os.path.join(SOUND_DICT_PKL_PATH, f'{vs.VOICE_NAME}.pkl') # vs.VOICE_NAME is an attribute fetched from the voice_path provided through vs.define_voice_sfx_file_paths()
vs.load_sound_dictionary(pkl_path=pkl_path)

# GENERATE AUDIO
vs.generate_audio(input_string = vs.INPUT_STRING_FROM_JSON, output_path_folder = CURRENT_DIR, output_name = 'output')
# input_string defaults to INPUT_STRING_FROM_JSON but this is how to set one not from JSON. If nothing from JSON or from here is provided an error is raised.
# output_name defaults to 'output', but I've manually set it as an example.

    
# LIVE PLAYBACK
print('COMMENCING LIVE PLAYBACK')

for text in vs.live_playback(pre_concatenated_chunks=False): # pre_concatenated_chunks defaults to False. False: outputs individual newest chunk each time. True: outputs chunk concatenated to all previous chunks each time.
    print(text, end='', flush=True) # You can replace print() with whatever text display you want. vs.live_playback() handles the timings on it's own.

print('\n------ All done now :) ------')