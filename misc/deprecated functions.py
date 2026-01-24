from pydub import AudioSegment
from pydub.silence import detect_leading_silence
from pydub.effects import speedup
import logging as log
log.basicConfig(format="[%(asctime)s] [%(filename)s/%(levelname)s]: %(message)s (Line: %(lineno)s)",
                    datefmt="%H:%M:%S",
                    level=log.DEBUG)
log.getLogger("pydub").setLevel(log.ERROR)
import os

#######################################################################################################
#   this segment here is NOT deprecated (maybe outdated when ur reading this idk) but its needed for the deprecated gen_dict to work
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
#######################################################################################################


# This adds anything in the folder to the dict, rather than being specific to the sounds we need, and doing stuff like assign c the k sound (which is what the new one does)
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