# -*- coding: utf-8 -*-
import os
import time

# Define the folder and file name to play
VOICE_DIR = os.path.join("data", "voices")

def play_voice(FILENAME):
    path = os.path.join(VOICE_DIR, FILENAME)

    if not os.path.exists(path):
        print("Fichier introuvable:", path)
        return

    print("Lecture de:", path)
    os.system('mpg123 "{}"'.format(path))

if __name__ == "__main__":
    play_voice("Objet,_1.mp3")
    time.sleep(0.5)
    play_voice("Objet,_2.mp3")
    time.sleep(0.5)
    play_voice("Objet,_3.mp3")
    time.sleep(0.5)
    play_voice("Objet,_4.mp3")
    time.sleep(0.5)
    play_voice("Objet,_5.mp3")
    time.sleep(0.5)
    play_voice("Objet,_6.mp3")
    time.sleep(0.5)
    play_voice("Objet,_7.mp3")
    time.sleep(0.5)
    play_voice("Objet,_8.mp3")
    time.sleep(0.5)
