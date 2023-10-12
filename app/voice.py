import sounddevice, json

from scipy.io.wavfile import write

import main

#sample_rate
fs=44100
#Ask to enter the recording time
second = int (input("Enter the Recording Time in second: "))
print("Recording.... In")
record_voice = sounddevice.rec(int(second * fs), samplerate=fs, channels=1)
sounddevice.wait()
write("MyRecording.wav",fs,record_voice)

# save the recording to variable text
text = record_voice
print("Recording is done Please check you folder to listen recording")

import os
import openai


openai.api_key = main.openai_api_key
audio_file = open("MyRecording.wav", "rb")
transcript = openai.Audio.transcribe("whisper-1", audio_file)

print(transcript['text'])

