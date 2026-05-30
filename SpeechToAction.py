#!/usr/bin/python3.10
import time
import speech_recognition as sr  # type: ignore
import sys
import threading
import os
from mistralai import Mistral  # type: ignore
import sounddevice   # type: ignore
import socket

# Initialize recognizer
recognizer = sr.Recognizer()

# Initialize Mistral API
api_key = "xR5qX4SwQABW4yb1fS42UCh7XpWRZmAL"
model = "mistral-large-latest"
SpeechToActionClient = Mistral(api_key=api_key)

running = False
STM_text = "We remind you that:\n"

# Initialize socket server
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Host and Port for socket server
HOST = '127.0.0.1'
PORT = 12321

# Bind and listen
server_socket.bind((HOST, PORT))
server_socket.listen(1)

# Accept connection
client_socket, client_address = server_socket.accept()

def send_message(message):
    """Send message to client and print it."""
    try:
        if client_socket:
            client_socket.sendall(message.encode('utf-8'))
    except Exception as e:
        print(f"Error sending message: {e}")

def read_SpeechToActionInitialPrompt():
    try:
        with open("data/LLM/STA.txt", "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        send_message("E: Prompt file not found. Using default prompt.")
        return "You are an assistant helping with speech-based robot interaction."

def read_STM_prompt():
    try:
        with open("data/LLM/STM.txt", "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        send_message("E: STM prompt file not found. Using default STM prompt.")
        return "You are keeping track of the robot's recent actions."

STM_prompt = read_STM_prompt()
SpeechToActionInitialPrompt = read_SpeechToActionInitialPrompt()

send_message("N: Program started.")
time.sleep(1)

def send_to_llm(user_request):
    global STM_text
    try:
        text = user_request + ". " + STM_text

        SpeechToActionInput = f"{SpeechToActionInitialPrompt}\nUser: {text}\nAssistant:"
        response1 = SpeechToActionClient.chat.complete(
            model=model,
            messages=[{"role": "user", "content": SpeechToActionInput}]
        )
        llm_output = response1.choices[0].message.content.strip()
        send_message(f"R: {llm_output}")
        time.sleep(1)  # Slow down to respect rate limits

        STM_Input = f"{STM_prompt}\nUser request: {text}\nRobot's command output: {llm_output}\nAssistant:"
        response2 = SpeechToActionClient.chat.complete(
            model=model,
            messages=[{"role": "user", "content": STM_Input}]
        )
        STM_output = response2.choices[0].message.content.strip()
        STM_text += STM_output + "\n"        

    except Exception as e:
        error_message = str(e)
        if "429" in error_message:
            send_message("E: Rate limit hit. Waiting 5 seconds before retry.")
            time.sleep(5)
        else:
            send_message(f"E: Error in LLM communication: {e}")

def listen_for_client_data():
    global running
    while True:
        try:
            data = client_socket.recv(4096)
            if not data:
                send_message("E: Client disconnected.")
                break
            message = data.decode('utf-8')
            if message == "start":
                running = True
            elif message == "stop":
                running = False
            else:
                send_to_llm(message)
        except Exception as e:
            send_message(f"E: Error receiving from client: {e}")
            break

client_data_thread = threading.Thread(target=listen_for_client_data)
client_data_thread.daemon = True
client_data_thread.start()

def listen_for_speech():
    global running
    while True:
        # Wait until running becomes False
        while running:
            time.sleep(0.1)

        try:
            with sr.Microphone() as source:
                send_message("N: Listening for speech...")
                recognizer.adjust_for_ambient_noise(source, duration=0.5)

                if running:
                    send_message("N: Cancelled listening because running became True.")
                    continue  # Skip if running becomes True during setup

                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)

                if not running:
                    try:
                        text = recognizer.recognize_google(audio)
                        send_message(f"S: {text}")
                        send_to_llm(text)
                    except sr.UnknownValueError:
                        send_message("W: Could not understand the speech.")
                    except sr.RequestError as e:
                        send_message(f"E: Speech recognition API error: {e}")

        except sr.WaitTimeoutError:
            send_message("W: Timeout waiting for speech input.")
        except Exception as e:
            send_message(f"E: Speech recognition error: {e}")

# Start speech listening in the main thread
listen_for_speech()
