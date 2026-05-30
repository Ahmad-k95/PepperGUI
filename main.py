#!/usr/bin/python2.7
# coding=utf-8

import subprocess
import Tkinter as tk # type: ignore
import time
import qi
from naoqi import ALProxy
import os
import tkMessageBox # type: ignore
import ttk # type: ignore
import tkFileDialog # type: ignore
import shutil
import re
from datetime import datetime
"""///////////////////////////////////////////////////////////////////////////////////////////"""
# import pyttsx3 # type: ignore
from gtts import gTTS
import tempfile
import urllib3
"""///////////////////////////////////////////////////////////////////////////////////////////"""
import threading
import ttk # type: ignore
from pepper_cam_reader import NaoCamera
import cv2 # type: ignore
from PIL import Image, ImageTk, ImageDraw, ImageFont
import numpy as np
import cv2.aruco as aruco # type: ignore
import cv2 as cv # type: ignore
import math
import socket
from vicon_trigger import ArduinoSerialManager

# Initialize socket client
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
HOST = '127.0.0.1'  # Localhost (same machine)
PORT = 12321  # The same port as the server

stiff_on = False
hand_opened = False
leds_on = False
choices = ["None", "Left Arm", "Right Arm", "Head", "Torso", "Knee"]
robot_ip = "169.254.223.100"
robot_port = 9559
robot_session = qi.Session()
data_folder = "data"

posture_data = []
selected_posture = ""
selected_posture_index = 0
posture_period = 2.0

motion_data = []
selected_motion = ""
motions_data = []

file_path = ""
timer_started = False
start_time = 0.0
data_recording = False
object_name="None"
experiment_names = []
Language = "English"
code = []
photo_names = []

try_posture_flag = False
try_motion_flag = False
run_code_flag = False
stop_code_flag = False


# Create an instance of NaoCamera
camera_index = 0
pepper_camera = None

snap_taken = False  # Flag to track if a photo has been taken

# Define the available dictionaries
aruco_dictionaries = [
    "DICT_4X4_50", "DICT_4X4_100", "DICT_4X4_250", "DICT_4X4_1000",
    "DICT_5X5_50", "DICT_5X5_100", "DICT_5X5_250", "DICT_5X5_1000",
    "DICT_6X6_50", "DICT_6X6_100", "DICT_6X6_250", "DICT_6X6_1000",
    "DICT_7X7_50", "DICT_7X7_100", "DICT_7X7_250", "DICT_7X7_1000"
]

# Load camera calibration data
calib_data = np.load("data/calib_data/MultiMatrix.npz")
cam_matrix = calib_data["camMatrix"]
dist_coefficients = calib_data["distCoef"]
desired_aruco_marker = -1


# Mapping between ArUco IDs and labels
id_to_label = {i: chr(ord('A') + i) for i in range(25)}

# ArUco dictionary and parameters
aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_6X6_250)
parameters = cv2.aruco.DetectorParameters_create()

# Real-world marker length in millimeters
real_marker_length_mm = 29
detected_objects = []

LLM_process = None
LLM_received_message = ""
prompts = ["STA", "STM"]
prompt_path = "data/LLM/STA.txt"

manager = ArduinoSerialManager()
ports = []


def on_enter_pressed(event):
    # Get last line
    global ports
    if not ports == []:
        lines = manip_log.get("1.0", "end-1c").split("\n")
        last_line = lines[-1].strip()

        if not last_line.startswith("port"):
            manager.log("\n> Please type like 'port1', etc.", "yellow")
            return "break"  # prevent new line

        try:
            idx = int(last_line[4:]) - 1
            if idx < 0 or idx >= len(manager.ports):
                manager.log("\n> Invalid port number.", "red")
                return "break"
            selected_port = manager.ports[idx].device
            manager.log("\n> You selected: {}".format(selected_port), "white")
            manager.connect(selected_port)
        except ValueError:
            manager.log("\n> Invalid input format.", "red")
    
        return "break"  # prevent new line


def initialize_ports():
    global ports
    ports = manager.list_ports()
    if not ports == []:
        manager.log("> Type port'n' and press Enter to connect.", "yellow")


def get_elapsed_time():
    global start_time
    elapsed_time = round(time.time() - start_time, 4)
    return elapsed_time


def connect_to_robot():
    global robot_session
    global robot_ip
    global pepper_camera
    global camera_index
    robot_ip = ip_entry.get()
    window.focus()
    if robot_session.isConnected():
        if not pepper_camera is None:
            pepper_camera.release_camera()
        manip_log.insert(tk.END, "> Robot is disconnected\n", "red")
        manip_log.yview_moveto(1.0)
        s = robot_session.service("ALTextToSpeech")
        s.setLanguage("English")
        s.say("Disconnected!")
        video_label.config(image="")
        robot_session.close()
        status_label.config(text="Connect!", fg="red")
        if not LLM_process is None:
            LLM_process.terminate()
        LLM_var.set(False)
        Aruco_var.set(False)
        recognized_speech.delete(1.0, tk.END)
    else:
        try:
            robot_session.connect(robot_ip)
        except Exception as e:
            tkMessageBox.showinfo("Warning",
                                  "Invalid Ip address!")
            return
        motion_service = robot_session.service("ALMotion")
        leds_service = robot_session.service("ALLeds")
        leds_service.setIntensity("FaceLeds", 0)

        time.sleep(2)
        s = robot_session.service("ALTextToSpeech")
        s.setLanguage("English")
        audio_device = ALProxy("ALAudioDevice", robot_ip, robot_port)
        audio_device.setOutputVolume(sound_scale.get())
        s.say("Connected!")
        stand_init()
        status_label.config(text="Connected", fg="green")
        autonomous_life_proxy = ALProxy("ALAutonomousLife", robot_ip, robot_port)
        autonomous_life_proxy.setAutonomousAbilityEnabled("All", False)
        manip_log.insert(tk.END, "> Robot is Connected\n", "green")
        manip_log.yview_moveto(1.0)

    load_data()
    if robot_session.isConnected():
        manip_log.insert(tk.END, "> Data is loaded\n", "green")
        manip_log.yview_moveto(1.0)
        battery_proxy = ALProxy("ALBattery", robot_ip, robot_port)
        battery_level = battery_proxy.getBatteryCharge()
        manip_log.insert(tk.END, "> Battery level: {}%".format(battery_level) + "\n", "yellow")


def stop_all_actions():
    global robot_session, stop_code_flag, run_code_flag
    time.sleep(1)
    stop_code_flag = True
    run_code_flag = False
    if not pepper_camera is None:
        pepper_camera.release_camera()
            
    manip_log.insert(tk.END, "> Robot is disconnected\n", "red")
    manip_log.yview_moveto(1.0)
    
    s = robot_session.service("ALTextToSpeech")
    s.setLanguage("English")
    s.say("Disconnected!")
    
    video_label.config(image="")
    robot_session.close()
    status_label.config(text="Connect!", fg="red")
    
    stand_init()    
    robot_session.close()
    
    manip_log.insert(tk.END, "> Stop!\n", "red")
    manip_log.yview_moveto(1.0)
    

def stop_robot_in_thread():
    stop_thread = threading.Thread(target=stop_all_actions)
    stop_thread.setDaemon(True)  # Manually set the daemon flag
    stop_thread.start()
    
           
def connect_to_robot_in_thread():
    connection_thread = threading.Thread(target=connect_to_robot)
    connection_thread.setDaemon(True)  # Manually set the daemon flag
    connection_thread.start()


def load_data():
    global data_folder, posture_data, motions_data, experiment_names, photo_names
    posture_data = []
    motions_data = []

    file_name = "postures_data.txt"
    file_path = os.path.join(data_folder, file_name)

    with open(file_path, "r") as file:
        for line in file:
            data = line.strip().split(';')
            posture_data.append(data)
    posture_listbox.delete(0, tk.END)
    for posture in posture_data:
        posture_listbox.insert(tk.END, posture[0])

    file_name = "motions_data.txt"
    file_path = os.path.join(data_folder, file_name)

    with open(file_path, "r") as file:
        for line in file:
            data = line.strip().split(';')
            motions_data.append(data)
    motions_listbox.delete(0, tk.END)
    for motion in motions_data:
        motions_listbox.insert(tk.END, motion[0])

    file_list = os.listdir(data_folder + "/experiments")
    files = [file for file in file_list if file.endswith(".txt")]
    experiment_names = []
    if len(files) > 0:
        for code_name in files:
            experiment_names.append(code_name.replace(".txt", ""))
            file_path = os.path.join(data_folder + "/experiments", code_name)
    else:
        pass
    experiment_names = arrange_experiment_names(experiment_names)
    experiments['values'] = experiment_names
    
    html_folder_path = "data/images/tablet/html"
    file_list = os.listdir(html_folder_path)
    image_extensions = [".jpg", ".jpeg", ".png", ".gif"]
    photo_names = [file for file in file_list if any(file.endswith(ext) for ext in image_extensions)]


def arrange_experiment_names(names):
    seq_scripts = []
    other_scripts = []

    suffix_order = {"": 0, "i": 1, "r": 2}

    for name in names:
        clean = name.strip()   # enlève espaces cachés

        if clean.lower().startswith("seq") and len(clean) >= 4 and clean[3].isalpha():
            letter = clean[3].upper()

            parts = clean.split("_", 1)
            suffix = parts[1].lower() if len(parts) == 2 else ""

            if suffix in suffix_order:
                seq_scripts.append((letter, suffix, name))
            else:
                other_scripts.append(name)
        else:
            other_scripts.append(name)

    seq_scripts.sort(key=lambda x: (x[0], suffix_order[x[1]]))

    return [x[2] for x in seq_scripts] + other_scripts


def import_code():
    file_path = tkFileDialog.askopenfilename(title="Select a code", filetypes=[("Text Files", "*.txt")])
    experiment_name_entry.delete(0, tk.END)
    experiment_name_entry.insert(0, file_path.split("/")[-1].replace(".txt", ""))
    selected_experiment.set(file_path.split("/")[-1].replace(".txt", ""))
    if file_path:
        with open(file_path, "r") as file:
            content = file.read()
            manip_code.delete("1.0", tk.END)
            manip_code.insert(tk.END, content)
    pass

    if file_path:
        destination_dir = data_folder + "/html"
        if not os.path.exists(destination_dir):
            os.makedirs(destination_dir)
        destination = os.path.join(destination_dir, os.path.basename(file_path))

        try:
            shutil.copy(file_path, destination)
            tkMessageBox.showinfo("Warning!", "You have to run \"pepper_gui_behavior\" in choregraphe to update the "
                                              "html package!")
            load_data()
        except IOError as e:
            return
    else:
        return


def import_image():
   file_path = tkFileDialog.askopenfilename(
       title="Select an Image",
       filetypes=[("Image Files", ("*.png", "*.jpg", "*.jpeg", "*.gif"))]
   )
   if file_path:
       destination_dir = data_folder + "/images/tablet/html"
       if not os.path.exists(destination_dir):
           os.makedirs(destination_dir)
       destination = os.path.join(destination_dir, os.path.basename(file_path))


       try:
           shutil.copy(file_path, destination)
           tkMessageBox.showinfo("Warning!", "You have to run \"pepper_gui_behavior\" in choregraphe to update the "
                                             "html package!")
           load_data()
       except IOError as e:
           return
   else:
       return


def import_image_in_thread():
    importing_thread = threading.Thread(target=import_image)
    importing_thread.setDaemon(True)
    importing_thread.start()
    

def list_images_in_directory():
    directory = 'data/images/tablet/html'
    # Supported image extensions
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    
    # Get list of image files
    image_files = [
        file for file in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, file)) and os.path.splitext(file)[1].lower() in image_extensions
    ]
    log_message = "> Images:\n"
    manip_log.insert(tk.END, log_message, "yellow")
    manip_log.yview_moveto(1.0)
    log_message = ""
    for file in image_files:
        log_message = "> " + file + "\n"
        manip_log.insert(tk.END, log_message, "white")
        manip_log.yview_moveto(1.0)
        log_message = ""


def show_image(image, show):
   tabletService = robot_session.service("ALTabletService")
   if show:
        # Create the thread
        image_thread = threading.Thread(target=tabletService.showImage("http://198.18.0.1/apps/pepper_gui_images-e650cd/" + image))
        image_thread.setDaemon(True)  # Manually set the daemon flag
        image_thread.start()
   else:
        # Create the thread
        image_thread = threading.Thread(target=tabletService.hideImage())
        image_thread.setDaemon(True)  # Manually set the daemon flag
        image_thread.start()


def delete_posture():
    selected_ind = posture_listbox.curselection()
    if selected_ind:
        file_name = "postures_data.txt"
        file_path = os.path.join(data_folder, file_name)
        with open(file_path, "r") as file:
            lines = file.readlines()
        del lines[selected_posture_index]
        with open(file_path, 'w') as file:
            file.writelines(lines)
        load_data()
    else:
        return


def select_posture(event):
    post_motion_listbox.delete(0, tk.END)
    global selected_posture, selected_posture_index
    selected_posture_index = posture_listbox.curselection()
    if selected_posture_index:
        selected_posture_index = selected_posture_index[0]
        selected_posture = posture_listbox.get(selected_posture_index)
        posture_entry.delete(0, tk.END)
        posture_entry.insert(0, selected_posture)
        body_part.set("None")


def wake():
    if not robot_session.isConnected():
        return
    robot_session.service("ALMotion").wakeUp()


def wake_in_thread():
    manip_log.insert(tk.END, "> Wake Up\n", "green")
    manip_log.yview_moveto(1.0)
    # Create the thread
    wake_thread = threading.Thread(target=wake)
    wake_thread.setDaemon(True)  # Manually set the daemon flag
    wake_thread.start()
    

def sleep():
    if not robot_session.isConnected():
        return
    robot_session.service("ALMotion").rest()
    

def sleep_in_thread():
    manip_log.insert(tk.END, "> Sleep mode\n", "green")
    manip_log.yview_moveto(1.0)
    # Create the thread
    sleep_thread = threading.Thread(target=sleep)
    sleep_thread.setDaemon(True)  # Manually set the daemon flag
    sleep_thread.start()


def stand_init():
    if not robot_session.isConnected():
        return
    robot_session.service("ALRobotPosture").goToPosture("StandInit", 0.2)


def stand_init_in_thread():
    manip_log.insert(tk.END, "> Stand init\n", "green")
    manip_log.yview_moveto(1.0)
    # Create the thread
    stand_init_thread = threading.Thread(target=stand_init)
    stand_init_thread.setDaemon(True)  # Manually set the daemon flag
    stand_init_thread.start()
    

def leds_control():
    if not robot_session.isConnected():
        return
    global leds_on
    if leds_on:
        leds_on = False
        leds_service = robot_session.service("ALLeds")
        leds_service.setIntensity("FaceLeds", 0)
        manip_log.insert(tk.END, "> LEDs are OFF\n", "green")
        manip_log.yview_moveto(1.0)
    else:
        leds_on = True
        leds_service = robot_session.service("ALLeds")
        leds_service.setIntensity("FaceLeds", 1)
        manip_log.insert(tk.END, "> LEDs are ON\n", "green")
        manip_log.yview_moveto(1.0)
        

def update_sound_value(value):
    if not robot_session.isConnected():
        return
    audio_device = ALProxy("ALAudioDevice", robot_ip, robot_port)
    audio_device.setOutputVolume(int(value))


def stiff_ctrl():
    if not robot_session.isConnected():
        return
    global stiff_on
    if stiff_on:

        stiffness = 1
        stiff_on = False
    else:
        stiffness = 0
        stiff_on = True

    m = robot_session.service("ALMotion")

    if body_part.get() == choices[3]:
        manip_log.insert(tk.END, "> Body part: Head\n", "yellow")
        manip_log.yview_moveto(1.0)
        manip_log.insert(tk.END, "> Stifness: {}".format(not stiff_on) + "\n", "yellow")
        manip_log.yview_moveto(1.0)
        m.stiffnessInterpolation("Head", stiffness, 0.1)
    elif body_part.get() == choices[2]:
        manip_log.insert(tk.END, "> Body part: Right Arm\n", "yellow")
        manip_log.yview_moveto(1.0)
        manip_log.insert(tk.END, "> Stifness: {}".format(not stiff_on) + "\n", "yellow")
        manip_log.yview_moveto(1.0)
        m.stiffnessInterpolation("RArm", stiffness, 0.1)
    elif body_part.get() == choices[1]:
        manip_log.insert(tk.END, "> Body part: Left Arm\n", "yellow")
        manip_log.yview_moveto(1.0)
        manip_log.insert(tk.END, "> Stifness: {}".format(not stiff_on) + "\n", "yellow")
        manip_log.yview_moveto(1.0)
        m.stiffnessInterpolation("LArm", stiffness, 0.1)


def toggle_language_fr():
    global Language
    Language = "French"
    en_language_var.set(0)


def toggle_language_en():
    global Language
    Language = "English"
    fr_language_var.set(0)


def say(text):
    global Language
    if not robot_session.isConnected():
        return
    s1 = robot_session.service("ALTextToSpeech")
    s1.setLanguage(Language)
    s1.say(text)


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def play_audio(path):
    try:
        os.system('mpg123 "{}"'.format(path))
    finally:
        os.remove(path)

def say_pc(text):
    try:
        # Générer fichier MP3 temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts = gTTS(text=text, lang='fr')
            tts.save(fp.name)
            temp_path = fp.name

        # Lire l’audio dans un thread séparé
        thread = threading.Thread(target=play_audio, args=(temp_path,))
        thread.start()

    except Exception as e:
        print("Erreur:", e)


def hand_control():
    if not robot_session.isConnected():
        return
    global hand_opened
    motion_service = robot_session.service("ALMotion")
    if body_part.get() == "Left Arm":
        if not hand_opened:
            motion_service.openHand('LHand')
            hand_opened = True
            hand_button.config(text="Close")
            manip_log.insert(tk.END, "> Left Hand is Opened\n")
            manip_log.yview_moveto(1.0)
        else:
            motion_service.closeHand('LHand')
            hand_opened = False
            hand_button.config(text="Open")
            manip_log.insert(tk.END, "> Left Hand is Closed\n")
            manip_log.yview_moveto(1.0)

    elif body_part.get() == "Right Arm":
        if not hand_opened:
            motion_service.openHand('RHand')
            hand_opened = True
            hand_button.config(text="Close")
            manip_log.insert(tk.END, "> Right Hand is Opened\n")
            manip_log.yview_moveto(1.0)
        else:
            motion_service.closeHand('RHand')
            hand_opened = False
            hand_button.config(text="Open")
            manip_log.insert(tk.END, "> Right Hand is Closed\n")
            manip_log.yview_moveto(1.0)


def hand_control_in_thread():
    # Create the thread
    hand_control_thread = threading.Thread(target=hand_control)
    hand_control_thread.setDaemon(True)  # Manually set the daemon flag
    hand_control_thread.start()
    

def get_join_angles():
    global robot_session, data_folder
    if not robot_session.isConnected():
        return
    used_name = False
    posture_name = re.sub(r'\s', '', posture_entry.get())
    if posture_name.isdigit():
        tkMessageBox.showinfo("Warning!",
                              "Posture name could not be a digit!")
        return
    if not posture_name == "":
        m = robot_session.service("ALMotion")
        Active_sensors = False
        posture_name = posture_entry.get().lower()
        # Knee and Torso
        t1 = m.getAngles("HipPitch", Active_sensors)[0]
        t2 = m.getAngles("HipRoll", Active_sensors)[0]
        t3 = m.getAngles("KneePitch", Active_sensors)[0]

        # Head
        h1 = m.getAngles("HeadPitch", Active_sensors)[0]
        h2 = m.getAngles("HeadYaw", Active_sensors)[0]

        # Right Arm
        R1 = m.getAngles("RElbowRoll", Active_sensors)[0]
        R2 = m.getAngles("RElbowYaw", Active_sensors)[0]
        R3 = m.getAngles("RHand", Active_sensors)[0]
        R4 = m.getAngles("RShoulderPitch", Active_sensors)[0]
        R5 = m.getAngles("RShoulderRoll", Active_sensors)[0]
        R6 = m.getAngles("RWristYaw", Active_sensors)[0]

        # Left Arm
        L1 = m.getAngles("LElbowRoll", Active_sensors)[0]
        L2 = m.getAngles("LElbowYaw", Active_sensors)[0]
        L3 = m.getAngles("LHand", Active_sensors)[0]
        L4 = m.getAngles("LShoulderPitch", Active_sensors)[0]
        L5 = m.getAngles("LShoulderRoll", Active_sensors)[0]
        L6 = m.getAngles("LWristYaw", Active_sensors)[0]

        posture_out = [posture_name,
                       str(R1), str(R2), str(R3), str(R4), str(R5), str(R6),
                       str(L1), str(L2), str(L3), str(L4), str(L5), str(L6),
                       str(t1), str(t2), str(t3), str(h1), str(h2)]

        posture_line = ";".join(posture_out)
        line_index = -1

        for posture in posture_data:
            line_index = line_index + 1
            if posture[0] == posture_name:
                used_name = True
                response = tkMessageBox.askokcancel("Posture Name Already Used",
                                                    "Posture name is used before! Do you want to edit the old posture?")

                if response:
                    file_name = "postures_data.txt"
                    file_path = os.path.join(data_folder, file_name)
                    with open(file_path, "r") as file:
                        lines = file.readlines()
                    lines[line_index] = posture_line + "\n"
                    with open(file_path, 'w') as file:
                        file.writelines(lines)
                    tkMessageBox.showinfo("Change Posture Name",
                                          "Posture was changed!.")
                    break
                else:
                    tkMessageBox.showinfo("Change Posture Name",
                                          "You must change the posture name because it's used before!")
                    break

        if not used_name:
            file_name = "postures_data.txt"
            file_path = os.path.join(data_folder, file_name)
            with open(file_path, "a") as file:
                file.write(posture_line + "\n")
        load_data()
    else:
        tkMessageBox.showinfo("Warning!",
                              "You must insert a name for this posture!")
        return


def select_motion(event):
    global selected_motion
    if motions_listbox.curselection():
        body_part.set("None")
        post_motion_listbox.delete(0, tk.END)
        selected_motion_index = motions_listbox.curselection()[0]
        selected_motion = motions_listbox.get(selected_motion_index)
        motion_entry.delete(0, tk.END)
        motion_entry.insert(0, selected_motion)
        for motion in motions_data:
            if motion[0] == selected_motion:
                for i in range(1, len(motion)):
                    data = motion[i]
                    if not data.replace(".", "", 1).isdigit():
                        post_motion_listbox.insert(tk.END, data)
                    else:
                        pass
                break
    else:
        body_part.set("None")
        if not post_motion_listbox.curselection():
            post_motion_listbox.delete(0, tk.END)


def select_experiment(event):
    if run_code_flag:
        return
    experiment_name_entry.delete(0, tk.END)
    experiment_name_entry.insert(0, selected_experiment.get())
    file_path = os.path.join(data_folder + "/experiments", selected_experiment.get() + ".txt")
    manip_code.delete(1.0, tk.END)
    with open(file_path, "r") as file:
        for line in file:
            manip_code.insert(tk.END, line)


def delete_experiment():
    experiment_name_entry.delete(0, tk.END)
    experiment_name_entry.insert(0, "xxxx")
    file_name = selected_experiment.get()
    selected_experiment.set("None")
    manip_code.delete(1.0, tk.END)
    file_path = os.path.join(data_folder + "/experiments", file_name + ".txt")
    if os.path.exists(file_path):
        os.remove(file_path)
        load_data()
    else:
        pass


def add_post_2_motion():
    if posture_listbox.curselection():
        global motion_data
        if (posture_period_entry.get().replace(".", "", 1).isdigit()
                and posture_period_entry.get().count(".") <= 1):
            posture_period = float(posture_period_entry.get())
        else:
            tkMessageBox.showinfo("Warning!", "Invalid time value!.")
            return
        if selected_posture == "":
            return
        motion_data.append([selected_posture, posture_period])
        motion_listbox.insert(tk.END, selected_posture)
    else:
        return


def delete_post_motion():
    global motion_data
    selected_ind = motion_listbox.curselection()
    if selected_ind:
        selected_ind = selected_ind[0]
        motion_data.pop(selected_ind)
        motion_listbox.delete(selected_ind)
    else:
        pass


def save_motion():
    post_motion_listbox.delete(0, tk.END)
    motion_name = re.sub(r'\s', '', motion_entry.get())
    if motion_name.isdigit():
        tkMessageBox.showinfo("Warning!", "Motion name could not be a digit!")
        return
    if not motion_name == "" and motion_listbox.size() > 0:
        global motion_data, data_folder
        used_name = False
        motion_out = [motion_entry.get().lower()]
        for data in motion_data:
            motion_out.append(data[0])
            motion_out.append(str(data[1]))
        motion_line = ";".join(motion_out)
        line_index = -1
        for motion in motions_data:
            line_index = line_index + 1
            if motion_name == motion[0]:
                used_name = True
                response = tkMessageBox.askokcancel("Warning!",
                                                    "Motion name is used before! Do you want to edit the old motion?")

                if response:
                    file_name = "motions_data.txt"
                    file_path = os.path.join(data_folder, file_name)
                    with open(file_path, "r") as file:
                        lines = file.readlines()
                    lines[line_index] = motion_line + "\n"
                    with open(file_path, 'w') as file:
                        file.writelines(lines)
                        motion_listbox.delete(0, tk.END)
                    tkMessageBox.showinfo("Warning!",
                                          "Motion was changed!.")
                    break
                else:
                    tkMessageBox.showinfo("Warning!", "You must change the motion name because it's used before!")
                    motion_entry.delete(0, tk.END)
                    return

        if not used_name:
            file_name = "motions_data.txt"
            file_path = os.path.join(data_folder, file_name)
            with open(file_path, "a") as file:
                file.write(motion_line + "\n")
                motion_listbox.delete(0, tk.END)
        motion_data = []
        load_data()
    else:
        tkMessageBox.showinfo("Warning!", "You must add a posture to the motion or insert its name!")
        return


def delete_motion():
    if motions_listbox.curselection():
        post_motion_listbox.delete(0, tk.END)
        file_name = "motions_data.txt"
        file_path = os.path.join(data_folder, file_name)
        with open(file_path, "r") as file:
            lines = file.readlines()
        del lines[motions_listbox.curselection()[0]]
        with open(file_path, 'w') as file:
            file.writelines(lines)
        load_data()
    else:
        pass


def save_code():
    file_name = experiment_name_entry.get()
    code = manip_code.get("1.0", tk.END)
    file_path = os.path.join(data_folder + "/experiments", file_name + ".txt")
    if os.path.isfile(file_path):
        response = tkMessageBox.askokcancel("Warning!",
                                            "Experiment name is used before! Do you want to edit the old experiment?")

        if response:
            with open(file_path, "w") as file:
                file.write(code)
            tkMessageBox.showinfo("Warning!", "Experiment was changed!.")
        else:
            tkMessageBox.showinfo("Warning!", "You must change the Experiment name because it's used before!")
            return
    else:
        with open(file_path, "w") as file:
            file.write(code)
    load_data()


def save_log():
    current_datetime = datetime.now().strftime("%Y_%m_%d_%H_%M_%S").replace(" ", "_")
    file_path = os.path.join(data_folder + "/log", experiment_name_entry.get() + "_" + current_datetime + ".txt")
    with open(file_path, "w") as file:
        file.write(manip_log.get("1.0", tk.END))


def manual_ctrl_part(event):
    if not robot_session.isConnected():
        return
    m = robot_session.service("ALMotion")
    Active_sensors = False
    if body_part.get() == "Head":
        if event.keysym == "Up":
            window.focus()
            head_pitch_angle = m.getAngles("HeadPitch", Active_sensors)[0]
            m.angleInterpolation("HeadPitch", head_pitch_angle - 0.05, 0.05, True)
        elif event.keysym == "Down":
            window.focus()
            head_pitch_angle = m.getAngles("HeadPitch", Active_sensors)[0]
            m.angleInterpolation("HeadPitch", head_pitch_angle + 0.05, 0.05, True)
        elif event.keysym == "Right":
            window.focus()
            head_yaw_angle = m.getAngles("HeadYaw", Active_sensors)[0]
            m.angleInterpolation("HeadYaw", head_yaw_angle - 0.05, 0.05, True)
        elif event.keysym == "Left":
            window.focus()
            head_yaw_angle = m.getAngles("HeadYaw", Active_sensors)[0]
            m.angleInterpolation("HeadYaw", head_yaw_angle + 0.05, 0.05, True)
        else:
            pass

    elif body_part.get() == "Torso":
        if event.keysym == "Up":
            window.focus()
            hip_pitch_angle = m.getAngles("HipPitch", Active_sensors)[0]
            m.angleInterpolation("HipPitch", hip_pitch_angle - 0.025, 0.05, True)
        elif event.keysym == "Down":
            window.focus()
            hip_pitch_angle = m.getAngles("HipPitch", Active_sensors)[0]
            m.angleInterpolation("HipPitch", hip_pitch_angle + 0.025, 0.05, True)
        elif event.keysym == "Right":
            window.focus()
            hip_Roll_angle = m.getAngles("HipRoll", Active_sensors)[0]
            m.angleInterpolation("HipRoll", hip_Roll_angle - 0.025, 0.05, True)
        elif event.keysym == "Left":
            window.focus()
            hip_Roll_angle = m.getAngles("HipRoll", Active_sensors)[0]
            m.angleInterpolation("HipRoll", hip_Roll_angle + 0.025, 0.05, True)
        else:
            pass

    elif body_part.get() == "Knee":
        if event.keysym == "Up":
            window.focus()
            Knee_pitch_angle = m.getAngles("KneePitch", Active_sensors)[0]
            m.angleInterpolation("KneePitch", Knee_pitch_angle - 0.02, 0.05, True)
        elif event.keysym == "Down":
            window.focus()
            Knee_pitch_angle = m.getAngles("KneePitch", Active_sensors)[0]
            m.angleInterpolation("KneePitch", Knee_pitch_angle + 0.02, 0.05, True)
        else:
            pass
    else:
        return


def manual_ctrl_in_thread(event):
    manual_ctrl_thread = threading.Thread(target=manual_ctrl_part, args=(event,))
    manual_ctrl_thread.setDaemon(True)
    manual_ctrl_thread.start()


def robot_motion(posture, post_time):
    if not robot_session.isConnected():
        return
    m = robot_session.service("ALMotion")
    chainName = "Arms"
    m.setExternalCollisionProtectionEnabled(chainName, False)

    names = ['RElbowRoll', 'RElbowYaw', 'RHand', 'RShoulderPitch', 'RShoulderRoll', 'RWristYaw',
             'LElbowRoll', 'LElbowYaw', 'LHand', 'LShoulderPitch', 'LShoulderRoll', 'LWristYaw',
             'HipPitch', 'HipRoll', 'KneePitch',
             'HeadPitch', 'HeadYaw']

    times = list()
    angles = list()

    for i in range(1, len(posture)):
        angles.append([float(posture[i])])
        times.append([post_time])
    m.angleInterpolation(names, angles, times, True)


def try_posture():
    if not robot_session.isConnected():
        return
    global posture_period, try_posture_flag
    if selected_posture != "" and posture_listbox.curselection():
        try_posture_flag = True
        manip_log.insert(tk.END, "> Try posture: {}".format(selected_posture) + "\n", "blue")
        manip_log.yview_moveto(1.0)

        if (posture_period_entry.get().replace(".", "", 1).isdigit()
                and posture_period_entry.get().count(".") <= 1):
            posture_period = float(posture_period_entry.get())
        else:
            tkMessageBox.showinfo("Warning!", "Invalid time value!.")
            return

        posture = posture_data[selected_posture_index]
        robot_motion(posture, posture_period)
        try_posture_flag = False
    else:
        return


def try_posture_in_thread():
    if try_posture_flag:
        manip_log.insert(tk.END, "> Trying another posture...!\n", "red")
        manip_log.yview_moveto(1.0)
        return
    try_posture_thread = threading.Thread(target=try_posture)
    try_posture_thread.setDaemon(True)  # Manually set the daemon flag
    try_posture_thread.start()


def try_unsaved_motion():
    if not robot_session.isConnected():
        return
    global motion_data
    global posture_data
    global try_motion_flag
    post_time = 0
    if not len(motion_data) == 0:
        try_motion_flag = True
        for data in motion_data:
            for posture in posture_data:
                if data[0] == posture[0]:
                    post_time = data[1]
                    manip_log.insert(tk.END, "> Try Posture: {}".format(posture[0]) + "\n", "blue")
                    manip_log.yview_moveto(1.0)
                    robot_motion(posture, post_time)
                    break
        try_motion_flag = False
    else:
        return


def try_unsaved_motion_in_thread():
    if try_motion_flag:
        manip_log.insert(tk.END, "> Testing another motion...!\n", "red")
        manip_log.yview_moveto(1.0)
        return
    try_unsaved_motion_thread = threading.Thread(target=try_unsaved_motion)
    try_unsaved_motion_thread.setDaemon(True)  # Manually set the daemon flag
    try_unsaved_motion_thread.start()
    

def try_saved_motion():
    if not robot_session.isConnected():
        return
    global motions_data
    global posture_data
    global try_motion_flag
    post_times = list()
    post_names = list()
    if motions_listbox.curselection():
        try_motion_flag = True
        selected_motion = motions_listbox.get(motions_listbox.curselection()[0])
        manip_log.insert(tk.END, "> Try motion: {}".format(selected_motion) + "\n", "blue")
        manip_log.yview_moveto(1.0)
        for motion in motions_data:
            if motion[0] == selected_motion:
                for i in range(1, len(motion)):
                    data = motion[i]
                    if not data.replace(".", "", 1).isdigit():
                        post_names.append(data)
                    else:
                        post_times.append(float(data))
                for i in range(0, len(post_names)):
                    for posture in posture_data:
                        if post_names[i] == posture[0]:
                            robot_motion(posture, post_times[i])
                            break
                        else:
                            pass
        try_motion_flag = False
    else:
        return


def try_saved_motion_in_thread():
    if try_motion_flag:
        manip_log.insert(tk.END, "> Testing another motion...!\n", "red")
        manip_log.yview_moveto(1.0)
        return
    try_saved_motion_thread = threading.Thread(target=try_saved_motion)
    try_saved_motion_thread.setDaemon(True)  # Manually set the daemon flag
    try_saved_motion_thread.start()


def clear_first_line():
    next_code = manip_code.get("1.0", "end")
    lines = next_code.split('\n')
    if len(lines) > 1:
        modified_content = '\n'.join(lines[1:])
    else:
        modified_content = ''
    modified_lines = [line for line in modified_content.split('\n') if line.strip()]
    modified_content = '\n'.join(modified_lines)
    manip_code.delete("1.0", "end")
    manip_code.insert("1.0", modified_content)


def check_code():
    global code
    checked_code = True
    code = manip_code.get("1.0", tk.END).splitlines()
    for i in range(0, len(code)):
        code[i] = code[i].encode('utf-8').lower()
    code = [item for item in code if item != '']
    for i in range(0, len(code)):
        try:
            code[i] = re.sub(r'=+', '=', code[i])
            code[i] = code[i].split("=")
            code[i][0] = code[i][0].replace(" ", "")
            if code[i][0] == "say" or code[i][0] == "say_pc":
                pass
            else:
                code[i][1] = code[i][1].replace(" ", "")
        except Exception as e:
            checked_code = False
            log_message = "> " + code[i][0] + " isn't a command\n"
            manip_log.insert(tk.END, log_message, "red")
            manip_log.yview_moveto(1.0)
            return checked_code
    if not code:
        return
    log_message = "> Checking code...\n"
    manip_log.insert(tk.END, log_message)
    manip_log.yview_moveto(1.0)
    index = 0
    while index < len(code):
        line = code[index]
        # move checking
        if line[0] == "move":
            found = False
            for motion in motions_data:
                if line[1] == motion[0]:
                    found = True
                    break
            if not found:
                checked_code = False
                log_message = "> " + line[0] + " = " + line[1] + " :: " + line[1] + " not found\n"
                manip_log.insert(tk.END, log_message, "red")
                manip_log.yview_moveto(1.0)
                
        # lookAt checking
        elif line[0] == "lookat":
            if not line[1].isdigit():
                checked_code = False
                log_message = "> " + line[0] + " = " + line[1] + " :: " + line[1] + " not an object ID\n"
                manip_log.insert(tk.END, log_message, "red")
                manip_log.yview_moveto(1.0)

        # delay checking
        elif line[0] == "delay":
            if not (line[1].replace(".", "", 1).isdigit() and line[1].count(".") <= 1):
                checked_code = False
                log_message = "> " + line[0] + " = " + line[1] + " :: " + line[1] + " not a digit\n"
                manip_log.insert(tk.END, log_message, "red")
                manip_log.yview_moveto(1.0)
        
        # trigger checking
        elif line[0] == "trigger":
            if not line[1] == "true":
                checked_code = False
                log_message = "> " + line[0] + " = " + line[1] + " :: " + line[1] + " must be \"true\"\n"
                manip_log.insert(tk.END, log_message, "red")
                manip_log.yview_moveto(1.0)
                               
        # image checking
        elif line[0] == "image":
            folder_path = data_folder + "/images/tablet/html"
            full_path = os.path.join(folder_path, line[1])
            if line[1] == "hide" or line[1] == "list":
                pass
            elif not os.path.exists(full_path):
                checked_code = False
                log_message = "> " + line[0] + " = " + line[1] + " :: " + line[1] + " doesn't exist"
                log_message = log_message + "\n"
                manip_log.insert(tk.END, log_message, "red")
                manip_log.yview_moveto(1.0)

        # break checking
        elif line[0] == "break":
            if not line[1] == "true":
                checked_code = False
                log_message = "> " + line[0] + " = " + line[1] + " :: " + line[1] + " must be \"true\"\n"
                manip_log.insert(tk.END, log_message, "red")
                manip_log.yview_moveto(1.0)


        # say checking
        elif line[0] == "say" or line[0] == "say_pc" or line[0] == "//":
            pass

        else:
            checked_code = False
            log_message = "> " + line[0] + " = " + line[1] + " :: " + line[0] + " is not a command\n"
            manip_log.insert(tk.END, log_message, "red")
            manip_log.yview_moveto(1.0)

        index += 1
    if checked_code:
        log_message = "> No errors" + "\n"
        manip_log.insert(tk.END, log_message, "green")
        manip_log.yview_moveto(1.0)
    final_code = ""
    for line in code:
        final_code = final_code + line[0] + "=" + line[1] + "\n"
    manip_code.delete(1.0, tk.END)
    manip_code.insert(1.0, final_code)
    return checked_code


def run_experiment():
    global subject_name, object_name, file_path, timer_started, data_recording, start_time, code, motions_data, posture_data, run_code_flag, stop_code_flag
    subject_name = subject_name_entry.get()
    if not robot_session.isConnected():
        return
    tracking_entry.delete(0, tk.END)
    tracking_entry.insert(0, "-1")
    if check_code():
        run_code_flag = True
        log_message = "> Running:\n"
        manip_log.insert(tk.END, log_message, "green")
        manip_log.yview_moveto(1.0)
        log_message = ""
        for line in code:
            
            if line[0] == "move":
                log_message = log_message + "> " + line[0] + "::" + line[1] + "\n"
                manip_log.insert(tk.END, log_message, "blue")
                manip_log.yview_moveto(1.0)
                for motion in motions_data:
                    if line[1] == motion[0]:
                        post_times = list()
                        post_names = list()
                        for i in range(1, len(motion)):
                            data = motion[i]
                            if not data.replace(".", "", 1).isdigit():
                                post_names.append(data)
                            else:
                                post_times.append(float(data))
                        for i in range(0, len(post_names)):
                            for posture in posture_data:
                                if post_names[i] == posture[0]:
                                    robot_motion(posture, post_times[i])
                                    break
                                else:
                                    pass
                if timer_started:
                    with open(file_path, mode='a') as file:
                        file.write("{};{};{}\n".format(line[0], line[1], get_elapsed_time()))

            elif line[0] == "say":
                log_message = log_message + "> " + line[0] + "::" + line[1] + "\n"
                manip_log.insert(tk.END, log_message, "blue")
                manip_log.yview_moveto(1.0)
                say(line[1])
                if timer_started:
                    with open(file_path, mode='a') as file:
                        file.write("{};{};{}\n".format(line[0], line[1], get_elapsed_time()))
                
            elif line[0] == "lookat":
                log_message = log_message + "> " + line[0] + ":: object" + line[1] + "\n"
                manip_log.insert(tk.END, log_message, "blue")
                manip_log.yview_moveto(1.0)
                track_object(int(line[1])-1)
                if timer_started:
                    with open(file_path, mode='a') as file:
                        file.write("{};{};{}\n".format(line[0], line[1], get_elapsed_time()))

            elif line[0] == "say_pc":
                log_message = log_message + "> " + line[0] + "::" + line[1] + "\n"
                manip_log.insert(tk.END, log_message, "blue")
                manip_log.yview_moveto(1.0)
                say_pc(line[1])
                object_name = line[1].strip()
                if timer_started:
                    with open(file_path, mode='a') as file:
                        file.write("{};{};{}\n".format(line[0], line[1], get_elapsed_time()))

            elif line[0] == "delay":
                log_message = log_message + "> " + line[0] + "::" + line[1] + "\n"
                manip_log.insert(tk.END, log_message, "blue")
                manip_log.yview_moveto(1.0)
                time.sleep(float(line[1]))
                if timer_started:
                    with open(file_path, mode='a') as file:
                        file.write("{};{};{}\n".format(line[0], line[1], get_elapsed_time()))

            elif line[0] == "//":
                log_message = log_message + "> " + line[0] + "::" + line[1] + "\n"
                manip_log.insert(tk.END, log_message, "yellow")
                manip_log.yview_moveto(1.0)

            elif line[0] == "trigger":
                data_recording = not data_recording
                if data_recording:
                    timer_started = True
                    now = datetime.now()
                    date_str = now.strftime("%Y-%m-%d")
                    time_str = now.strftime("%H-%M-%S")
                    file_name = "{}_{}_{}_{}.txt".format(subject_name, object_name, date_str, time_str)
                    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                    subject_folder = os.path.join(desktop_path, subject_name)
                    if not os.path.isdir(subject_folder):
                        try:
                            os.makedirs(subject_folder)
                        except OSError:
                            pass
                    file_path = os.path.join(subject_folder, file_name)
                    with open(file_path, 'w') as file:
                        file.write(object_name + ";;" + "\n")
                        file.write("cmd;Value;Timing\n")
                    log_message = log_message + "> " + file_name + " is Created in Desktop/" + subject_name + "\n"
                    manip_log.insert(tk.END, log_message, "blue")
                    manip_log.yview_moveto(1.0)
                    start_time = time.time()
                else:
                    timer_started = False

                if ports:
                    manager.send_message("1")
                    if timer_started:
                        with open(file_path, mode='a') as file:
                            file.write("{};{};{}\n".format(line[0], line[1], get_elapsed_time()))
            
            elif line[0] == "image":              
                log_message = log_message + "> " + line[0] + "::" + line[1] + "\n"
                manip_log.insert(tk.END, log_message, "blue")
                manip_log.yview_moveto(1.0)
                
                if line[1] == "hide":
                    show_image(line[1], False)
                elif line[1] == "list":
                    list_images_in_directory()
                else:
                    show_image(line[1], True)
                if timer_started:
                    with open(file_path, mode='a') as file:
                        file.write("{};{};{}\n".format(line[0], line[1], get_elapsed_time()))

            elif line[0] == "break":
                log_message = log_message + "> " + line[0] + "::" + line[1] + "\n"
                manip_log.insert(tk.END, log_message, "blue")
                manip_log.yview_moveto(1.0)
                battery_proxy = ALProxy("ALBattery", robot_ip, robot_port)
                battery_level = battery_proxy.getBatteryCharge()
                manip_log.insert(tk.END, "> Battery level: {}%".format(battery_level) + "\n", "yellow")
                manip_log.yview_moveto(1.0)
                manip_log.yview_moveto(1.0)
                manip_log.insert(tk.END, "\n      -------------------------\n\n", "yellow")
                clear_first_line()
                if timer_started:
                    with open(file_path, mode='a') as file:
                        file.write("{};{};{}\n".format(line[0], line[1], get_elapsed_time()))
                run_code_flag = False
                timer_started = False
                return
            log_message = ""
            if stop_code_flag:
                stop_code_flag = False
                run_code_flag = False
                return
            
            clear_first_line()

        battery_proxy = ALProxy("ALBattery", robot_ip, robot_port)
        battery_level = battery_proxy.getBatteryCharge()
        manip_log.insert(tk.END, "> Battery level: {}%".format(battery_level) + "\n", "yellow")
        manip_log.yview_moveto(1.0)
        manip_log.insert(tk.END, "\n      -------------------------\n\n", "yellow")
        manip_log.yview_moveto(1.0)
        run_code_flag = False
        timer_started = False
    else:
        return


def run_experiment_in_thread():
    # Create the thread
    if run_code_flag:
        manip_log.insert(tk.END, "> Another code is running!\n", "red")
        manip_log.yview_moveto(1.0)
        return
    run_experiment_thread = threading.Thread(target=run_experiment)
    run_experiment_thread.setDaemon(True)  # Manually set the daemon flag
    run_experiment_thread.start()


def switch_camera():
    if not robot_session.isConnected():
        return
    global camera_index, pepper_camera
    pepper_camera.release_camera()
    camera_index = 0 if camera_index == 1 else 1
    if camera_index == 0:
        manip_log.insert(tk.END, "> Top Camera Selected\n")
        manip_log.yview_moveto(1.0)
    else:
        manip_log.insert(tk.END, "> Buttom Camera Selected\n")
        manip_log.yview_moveto(1.0)
    if pepper_camera is not None:
        pepper_camera.release_camera()
    pepper_camera = NaoCamera(robot_ip, robot_port, camera_index)
    start_video_thread()


def switch_camera_in_thread():
    switch_cam_thread = threading.Thread(target=switch_camera)
    switch_cam_thread.setDaemon(True)
    switch_cam_thread.start()


def update_frame():
    if not robot_session.isConnected():
        return
    
    global pepper_camera
    global snap_taken
    
    if  Aruco_var.get():
        frame = pepper_camera.get_frame()
        if not frame is None:
            frame = process_aruco_markers(frame)
            # Draw a fixed red cross at the center of the frame
            cross_size = 20
            center_x, center_y = frame.shape[1] // 2, frame.shape[0] // 2
            cv2.line(frame, (center_x - cross_size, center_y), (center_x + cross_size, center_y), (0, 0, 255), 2)
            cv2.line(frame, (center_x, center_y - cross_size), (center_x, center_y + cross_size), (0, 0, 255), 2)
    else:
        frame = pepper_camera.get_frame()
        if snap_taken:
           snap_taken = False
           capture_image(frame)
    if not frame is None:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)
        img = img.resize((520, 376))
        img_tk = ImageTk.PhotoImage(img)
        video_label.img_tk = img_tk
        video_label.configure(image=img_tk)
        video_label.after(1, update_frame)


def start_video_thread():
    video_thread = threading.Thread(target=update_frame)
    video_thread.setDaemon(True)  # Set the thread as a daemon after creation
    video_thread.start()


def on_closing():
    global pepper_camera, robot_session
    if pepper_camera is not None and robot_session.isConnected():
        pepper_camera.release_camera()
    if LLM_process:
        LLM_process.terminate()
    window.destroy()


def process_aruco_markers(frame):
    global desired_aruco_marker, detected_objects
    cam_frame_height = frame.shape[0]
    cam_frame_width = frame.shape[1]
    m = robot_session.service("ALMotion")

    # Get the ArUco dictionary
    selected_dict = cv2.aruco.Dictionary_get(int(dictionaries.current()))
    corners, ids, _ = cv2.aruco.detectMarkers(frame, selected_dict, parameters=parameters)

    # Safely get tracking ID from the user entry
    try:
        entry_val = tracking_entry.get()
        if entry_val not in ("", "-", "-1"):
            desired_aruco_marker = int(entry_val) - 1
            log_message = "> Traking Mode\n"
            manip_log.insert(tk.END, log_message, "green")
            manip_log.yview_moveto(1.0)
    except ValueError:
        desired_aruco_marker = -1

    if ids is not None and len(ids) > 0:
        # Safely get the marker size
        try:
            marker_size = int(marker_size_entry.get())
        except (ValueError, TypeError):
            print("Invalid marker size:", marker_size_entry.get())
            return frame

        # Estimate pose of detected markers
        rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(corners, marker_size, cam_matrix, dist_coefficients)


        # Track all detected IDs
        for id in ids.flatten():
            if id not in detected_objects:
                detected_objects.append(id)

        # Draw detected markers
        frame = cv2.aruco.drawDetectedMarkers(frame, corners)

        for i in range(len(ids)):
            if ids[i][0] == desired_aruco_marker:
                # Compute center differences
                center_x, center_y = cam_frame_width // 2, cam_frame_height // 2
                marker_center_x = int(corners[i][0][:, 0].mean())
                marker_center_y = int(corners[i][0][:, 1].mean())
                dx = marker_center_x - center_x
                dy = -1 * (marker_center_y - center_y)

                # Display dx/dy
                cv2.putText(frame, "dx: {}px, dy: {}px".format(dx, dy),
                            (marker_center_x, marker_center_y + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

                # Draw marker ID and axis
                cv2.putText(frame, str(ids[i][0] + 1), tuple(corners[i][0][0]),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
                cv2.aruco.drawAxis(frame, cam_matrix, dist_coefficients, rvecs[i][0], tvecs[i][0], marker_size)

                # Reset tracking if marker is centered
                if abs(dx) < 10 and abs(dy) < 10:
                    desired_aruco_marker = -1

                # Convert pixel movement to head angles
                gain = 0.35
                Relative_head_yaw = -1 * gain * dx * (55.2 / cam_frame_width) * (math.pi / 180)
                Relative_head_pitch = -1 * gain * dy * (44.3 / cam_frame_height) * (math.pi / 180)

                # Apply head movement
                Actual_head_pitch_angle = m.getAngles("HeadPitch", False)[0]
                m.setAngles("HeadPitch", Actual_head_pitch_angle + Relative_head_pitch, 0.4)

                Actual_head_yaw_angle = m.getAngles("HeadYaw", False)[0]
                m.setAngles("HeadYaw", Actual_head_yaw_angle + Relative_head_yaw, 0.4)

    return frame


def track_object(marker_id):
    global desired_aruco_marker
    if marker_id in detected_objects:
        desired_aruco_marker = marker_id
    else:
        log_message = "> Object not found!\n"
        manip_log.insert(tk.END, log_message, "red")
        manip_log.yview_moveto(1.0)
    while desired_aruco_marker != -1:()
    return


def capture_image(frame, folder='data/images/captured'):
    """Captures and saves an image from the given frame."""

    img_path = os.path.join(folder, 'image_{}.png'.format(len(os.listdir(folder)) + 1))
    cv2.imwrite(img_path, frame)
    

def snap_photo():
    global snap_taken
    snap_taken = True


def calibrate_camera():
    
    image_dir_path="data/images/calibration"
    chess_board_dim=(9, 6)  # Tuple specifying the number of internal corners of the checkerboard (rows, columns). 
    square_size=20  # Size of a single square in the checkerboard in millimeters.

    # Check if calibration directory exists, create it if not
    CHECK_DIR = os.path.isdir("data/calib_data")
    if not CHECK_DIR:
        os.makedirs("data/calib_data")

    # Prepare object points (3D points in real world space)
    obj_3D = np.zeros((chess_board_dim[0] * chess_board_dim[1], 3), np.float32)
    obj_3D[:, :2] = np.mgrid[0:chess_board_dim[0], 0:chess_board_dim[1]].T.reshape(-1, 2)
    obj_3D *= square_size

    # Arrays to store object points and image points from all the given images
    obj_points_3D = []  # 3D points in real world space
    img_points_2D = []  # 2D points in image plane

    # List all the files in the image directory
    files = os.listdir(image_dir_path)
    for file in files:
        imagePath = os.path.join(image_dir_path, file)
        image = cv.imread(imagePath)
        grayScale = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        
        # Find chessboard corners
        ret, corners = cv.findChessboardCorners(image, chess_board_dim, None)
        if ret:
            obj_points_3D.append(obj_3D)
            corners2 = cv.cornerSubPix(grayScale, corners, (3, 3), (-1, -1), (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001))
            img_points_2D.append(corners2)
            image_with_corners = cv.drawChessboardCorners(image, chess_board_dim, corners2, ret)

    cv.destroyAllWindows()

    # Calibrate the camera using the collected points
    ret, mtx, dist, rvecs, tvecs = cv.calibrateCamera(
        obj_points_3D, img_points_2D, grayScale.shape[::-1], None, None
    )
    
    log_message = "> Calibration successful.\n> Saving calibration data...\n"
    manip_log.insert(tk.END, log_message)
    manip_log.yview_moveto(1.0)
    log_message=""

    np.savez(
        "data/calib_data/MultiMatrix",
        camMatrix=mtx,
        distCoef=dist,
        rVector=rvecs,
        tVector=tvecs,
    )

    log_message = "> Calibration data saved successfully.\n"
    manip_log.insert(tk.END, log_message, "green")
    manip_log.yview_moveto(1.0)
    log_message=""


def clear_video_frame():
    # Create white image
    blank = Image.new("RGB", (520, 376), (220, 220, 220))
    draw = ImageDraw.Draw(blank)

    # Load a bold font (default if no custom one available)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 16)
    except:
        font = ImageFont.load_default()

    text = "No camera detected!"
    text_width, text_height = draw.textsize(text, font=font)
    x = (520 - text_width) // 2
    y = (376 - text_height) // 2

    # Draw red bold text
    draw.text((x, y), text, fill="red", font=font)

    # Convert to ImageTk and update label
    blank_tk = ImageTk.PhotoImage(blank)
    video_label.configure(image=blank_tk)
    video_label.image = blank_tk


def video_activation():
    if not robot_session.isConnected():
        return
    global pepper_camera
    if enable_vision_var.get():
        pepper_camera = NaoCamera(robot_ip, robot_port, camera_index)
        start_video_thread()
    elif pepper_camera is not None:
        clear_video_frame()
        pepper_camera.release_camera()

        
def run_LLM():
    global client_socket
    os.system('clear')
    if LLM_var.get():
        global LLM_process
        LLM_process = subprocess.Popen(["python3.8", "SpeechToAction.py"])
        time.sleep(2)
        try:
            client_socket.connect((HOST, PORT))
            log_message = "> Connected to server." + "\n"
            manip_log.insert(tk.END, log_message, "green")
            manip_log.yview_moveto(1.0)
        except Exception as e:
            log_message = "> Failed to connect to server." + str(e) + "\n"
            manip_log.insert(tk.END, log_message, "red")
            manip_log.yview_moveto(1.0)
        receive_STA_messages_in_thread()
    else:
        log_message = "> LLM Module not activated.\n"
        manip_log.insert(tk.END, log_message, "red")
        manip_log.yview_moveto(1.0)
        LLM_process.terminate()
        client_socket.close()
        del client_socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        LLM_prompt.delete(1.0, tk.END)
        recognized_speech.delete(1.0, tk.END)


def run_LLM_thread():
    load_prompt()
    LLM_thread = threading.Thread(target=run_LLM)
    LLM_thread.setDaemon(True)  # Set the thread as a daemon after creation
    LLM_thread.start()


def load_prompt():
    try:
        with open(prompt_path, "r") as file:
            # Read the content of the file
            text_content = file.read()
            # Insert the content into the Text widget
            LLM_prompt.delete(1.0, tk.END)  # Clear the current content
            LLM_prompt.insert(tk.END, text_content)  # Insert new content
    except IOError:
        log_message = "> Error: The file could not be opened or found.\n"
        manip_log.insert(tk.END, log_message, "red")
        manip_log.yview_moveto(1.0)


def save_prompt():
    """Ask for confirmation before saving the text box content to the selected prompt file."""
    confirm = tkMessageBox.askyesno("Save Confirmation", "Are you sure you want to save the edited prompt?")
    
    if not confirm:
        return

    try:
        text_to_save = LLM_prompt.get(1.0, tk.END).strip()
        with open(prompt_path, "w") as file:
            file.write(text_to_save.encode("utf-8"))  # <-- Encode text before writing
    except IOError:
        log_message = "> Error: The file '{}' could not be saved.\n".format(prompt_path)
        manip_log.insert(tk.END, log_message, "red")
        manip_log.yview_moveto(1.0)
    
    load_prompt()  # Reload after saving if needed


def receive_STA_messages():
    while LLM_var.get():
        try:
            data = client_socket.recv(4096)  # Receive up to 4096 bytes
            if data:
                # In Python 2.7, you can directly print the data or decode if it's byte data
                # print("Received from STA server: {}".format(data))
                
                if data.startswith("S: "):
                    recognized_text = "> " + data[len("S: "):] + "\n"
                    recognized_speech.insert(tk.END, recognized_text)
                    recognized_speech.yview_moveto(1.0)
                    
                elif data.startswith("R: "):
                    #print(data)
                    STA_generated_code = data[len("R: "):] + "\n"
                    manip_code.delete(1.0, tk.END)
                    STA_generated_code_lines = STA_generated_code.split('/')
                    for line in STA_generated_code_lines:
                        manip_code.insert(tk.END, line + '\n')
                    manip_code.yview_moveto(1.0)
                    time.sleep(1)
                    client_socket.sendall("start")
                    log_message = "> STA code is Running...\n"
                    manip_log.insert(tk.END, log_message, "green")
                    manip_log.yview_moveto(1.0)
                    run_experiment()
                    client_socket.sendall("stop")
                    
                elif data.startswith("N: "):
                    log_message = "> " + data[len("N: "):] + "\n"
                    manip_log.insert(tk.END, log_message, "green")
                    manip_log.yview_moveto(1.0)
                
                elif data.startswith("W: "):
                    log_message = "> " + data[len("W: "):] + "\n"
                    manip_log.insert(tk.END, log_message, "yellow")
                    manip_log.yview_moveto(1.0)
                
                elif data.startswith("E: "):
                    log_message = "> " + data[len("E: "):] + "\n"
                    manip_log.insert(tk.END, log_message, "red")
                    manip_log.yview_moveto(1.0)
                else:
                     print("Message from STA: {}".format(data))
            else:
                break
        except Exception as e:
            print("Error receiving message: {}".format(e))
            break
        
        
def receive_STA_messages_in_thread():
    receive_data_thread = threading.Thread(target=receive_STA_messages)
    receive_data_thread.setDaemon(True)
    receive_data_thread.start()
  

def send_queries():
    global LLM_process
    text = recognized_speech.get("1.0", tk.END).strip()
    log_message = "> Sending recognized speech to LLM...\n"
    manip_log.insert(tk.END, log_message, "green")
    manip_log.yview_moveto(1.0)  
    client_socket.sendall(text)
    

def on_prompt_select(selection):
    global prompt_path
    prompt_path = "data/LLM/{}.txt".format(selection)
    print("Updated prompt path:", prompt_path)
    load_prompt()    


def on_option_change(value):
    if value in ["Head","Torso","Knee"]:
        window.focus_set()

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< Main window >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

window = tk.Tk()
window.title("Pepper Manager")
window.geometry("1470x900")
window.resizable(width=False, height=False)

# Define a fixed width and height for the buttons
button_width = 8
button_height = 1

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<   Connect   >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

# Create a frame named frame0 to contain the widgets
frame0 = tk.Frame(window, width=390, height=155, bd=1, relief="solid")  # Add a border with solid edges
frame0.place(x=2, y=2)

# Labels, Buttons, and other widgets inside frame0
ip_label = tk.Label(frame0, text="Enter Robot IP:", font=("Arial", 12))
ip_label.place(x=10, y=10)  # Place the label at (x=10, y=10) inside the frame

status_label = tk.Label(frame0, text="Connect!", fg="red")
status_label.place(x=160, y=40)  # Place the status label at (x=180, y=40)

connect_button = tk.Button(frame0, text="Connect", width=button_width, height=button_height, command=connect_to_robot_in_thread)
connect_button.place(x=280, y=10)  # Place the button at (x=260, y=40)

ip_entry = tk.Entry(frame0, width=13)
ip_entry.insert(0, "169.254.")
ip_entry.place(x=140, y=10)  # Place the entry at (x=120, y=10)

# Control buttons inside frame0
wake_button = tk.Button(frame0, text="Wake", width=button_width, height=button_height, command=wake_in_thread)
wake_button.place(x=10, y=70)  # Place the wake button at (x=10, y=70)

sleep_button = tk.Button(frame0, text="Sleep", width=button_width, height=button_height, command=sleep_in_thread)
sleep_button.place(x=120, y=70)  # Place the sleep button at (x=90, y=70)

stand_init_button = tk.Button(frame0, text="Pose init", width=button_width, height=button_height, command=stand_init_in_thread)
stand_init_button.place(x=10, y=110)  # Place the pose init button at (x=180, y=70)

leds_button = tk.Button(frame0, text="LEDs", width=button_width, height=button_height, command=leds_control)
leds_button.place(x=120, y=110)  # Place the LEDs button at (x=270, y=70)

sound_scale = tk.Scale(frame0, from_=0, to=100, orient="horizontal", label="       Volume", command=update_sound_value,
                       length=120, width=16, sliderlength=20, troughcolor="blue", sliderrelief="raised")
sound_scale.place(x=250, y=80)  # Place the scale at (x=120, y=40)
sound_scale.set(50)

fr_language_var = tk.IntVar()
fr_language_button = tk.Checkbutton(frame0, text="FR", variable=fr_language_var, command=toggle_language_fr)
fr_language_button.place(x=242, y=60)

en_language_var = tk.IntVar()
en_language_var.set(1)
en_language_button = tk.Checkbutton(frame0, text="EN", variable=en_language_var, command=toggle_language_en)
en_language_button.place(x=328, y=60)

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<  Postures  >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

frame1 = tk.Frame(window, width=390, height=155, bd=1, relief="solid")  # Add a border with solid edges
frame1.place(x=391, y=2)

posture_name_label = tk.Label(frame1, text="Posture name:")
posture_name_label.place(x=10, y=10)

posture_entry = tk.Entry(frame1, width=15)
posture_entry.insert(0, "pxmx")
posture_entry.place(x=130, y=10)

save_post_button = tk.Button(frame1, text="Save", command=get_join_angles, width=button_width, height=button_height)
save_post_button.place(x=285, y=7)

body_part_label = tk.Label(frame1, text="Select part:")
body_part_label.place(x=10, y=55)

body_part = tk.StringVar()
body_part.set("None")

option_menu = tk.OptionMenu(frame1, body_part, *choices,command=on_option_change)
option_menu.place(x=130, y=50)
option_menu.config(width=10)  # Adjust the width as needed

stiff_button = tk.Button(frame1, text="Stiff", command=stiff_ctrl, width=button_width, height=button_height)
stiff_button.place(x=285, y=50)

hand_button = tk.Button(frame1, text="hand", command=hand_control_in_thread, width=button_width, height=button_height)
hand_button.place(x=285, y=110)
hand_label = tk.Label(frame1, text="  Hand CTRL", fg="green")
hand_label.place(x=285, y=88)

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<   Motion   >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

frame2 = tk.Frame(window, width=779, height=287, bd=1, relief="solid")  # Add a border with solid edges
frame2.place(x=2, y=156)

posture_listbox = tk.Listbox(frame2, width=10, height = 13)
posture_listbox.place(x=10, y=35)

posture_list_label = tk.Label(frame2, text="Postures:")
posture_list_label.place(x=20, y=10)

posture_period_label = tk.Label(frame2, text="Time:")
posture_period_label.place(x=115, y=80)

posture_period_entry = tk.Entry(frame2, width=4)
posture_period_entry.insert(0, "2.0")
posture_period_entry.place(x=167, y=80)

try_post_button = tk.Button(frame2, text="Try", command=try_posture_in_thread, width=button_width, height=button_height)
try_post_button.place(x=115, y=120)

addpost2motion_button = tk.Button(frame2, text="Add", command=add_post_2_motion, width=button_width, height=button_height)
addpost2motion_button.place(x=115, y=160)

del_post_button = tk.Button(frame2, text="Delete", command=delete_posture, width=button_width, height=button_height)
del_post_button.place(x=115, y=200)

motion_label = tk.Label(frame2, text="Motion:")
motion_label.place(x=305, y=10)

motion_listbox = tk.Listbox(frame2, width=10, height=13)
motion_listbox.place(x=290, y=35)

motion_entry = tk.Entry(frame2, width=10)
motion_entry.insert(0, "mx")
motion_entry.place(x=398, y=80)

try_motion_button = tk.Button(frame2, text="Try", command=try_unsaved_motion_in_thread, width=button_width, height=button_height)
try_motion_button.place(x=395, y=120)

save_motion_button = tk.Button(frame2, text="Save", command=save_motion, width=button_width, height=button_height)
save_motion_button.place(x=395, y=160)

delete_motion_pos_button = tk.Button(frame2, text="Delete", command=delete_post_motion, width=button_width, height=button_height)
delete_motion_pos_button.place(x=395, y=200)

motions_label = tk.Label(frame2, text="Motions:")
motions_label.place(x=580, y=10)

motions_listbox = tk.Listbox(frame2, width=10, height=13)
motions_listbox.place(x=570, y=35)

post_motion_listbox = tk.Listbox(frame2, width=11, height=8)
post_motion_listbox.place(x=674, y=35)

try_motion_button2 = tk.Button(frame2, text="Try", command=try_saved_motion_in_thread, width=button_width, height=button_height)
try_motion_button2.place(x=674, y=200)

delete_motion_button = tk.Button(frame2, text="Delete", command=delete_motion, width=button_width, height=button_height)
delete_motion_button.place(x=674, y=240)

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<    Manip    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

frame3 = tk.Frame(window, width=779, height=456, bd=1, relief="solid")  # Add a border with solid edges
frame3.place(x=2, y=442)

experiment_name = tk.Label(frame3, text="Experiment Name:")
experiment_name.place(x=55, y=14)

experiment_name_entry = tk.Entry(frame3, width=10)
experiment_name_entry.insert(0, "---")
experiment_name_entry.place(x=185, y=14)

manip_code = tk.Text(frame3, width=38, height=23, background="blue", foreground="white", insertbackground="white")
manip_code.place(x=10, y=45)

subject_name = tk.Label(frame3, text="Subject:")
subject_name.place(x=362, y=68)

subject_name_entry = tk.Entry(frame3, width=10)
subject_name_entry.insert(0, "---")
subject_name_entry.place(x=344, y=90)

select_label = tk.Label(frame3, text="Select:")
select_label.place(x=362, y=115)

selected_experiment = tk.StringVar()
selected_experiment.set("None")
experiments = ttk.Combobox(frame3, textvariable=selected_experiment, width=9)
experiments.place(x=344, y=138)

check_button = tk.Button(frame3, text="Check", command=check_code, width=button_width, height=button_height)
check_button.place(x=342, y=170)

save_button = tk.Button(frame3, text="  Save ", command=save_code, width=button_width, height=button_height)
save_button.place(x=342, y=210)

run_button = tk.Button(frame3, text="  Run  ", command=run_experiment_in_thread, width=button_width, height=button_height)
run_button.place(x=342, y=250)

delete_experiment_button = tk.Button(frame3, text="Delete", command=delete_experiment, width=button_width, height=button_height)
delete_experiment_button.place(x=342, y=290)

save_log_button = tk.Button(frame3, text="Save Log", command=save_log, width=button_width, height=button_height)
save_log_button.place(x=342, y=330)

stop_button = tk.Button(frame3, text="STOP", command=stop_robot_in_thread, bg="red", fg="black", width=button_width, height=button_height)
stop_button.place(x=342, y=370)

log_label = tk.Label(frame3, text="Log terminal:")
log_label.place(x=560, y=15)

manip_log = tk.Text(frame3, width=38, height=23, background="black", foreground="white")
manip_log.place(x=457, y=45)
manip_log.bind("<Return>", on_enter_pressed)

log_message = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
log_message = log_message + "\n"
manip_log.insert(tk.END, log_message, "yellow")
manip_log.yview_moveto(1.0)
manip_log.tag_configure("yellow", foreground="yellow")
manip_log.tag_configure("red", foreground="red")
manip_log.tag_configure("green", foreground="green")
manip_log.tag_configure("blue", foreground="blue")

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<   Vision    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

frame4 = tk.Frame(window, width=688, height=399, bd=1, relief="solid")  # Add a border with solid edges
frame4.place(x=780, y=2)

cam_frame = tk.Frame(frame4, width=524, height=380, bd=1, relief="solid")  # Add a border with solid edges
cam_frame.place(x=10, y=7)

# Video frame in frame5
video_label = tk.Label(cam_frame)
video_label.place(x=0, y=0)

enable_vision_var = tk.IntVar()
enable_vision_button = tk.Checkbutton(frame4, text=" Enable", variable=enable_vision_var, command=video_activation)
enable_vision_button.place(x=570, y=10)

switch_button = tk.Button(frame4, text="Switch CAM", command=switch_camera_in_thread, width=button_width, height=button_height)
switch_button.place(x=565, y=40)

Capture_button = tk.Button(frame4, text="Snap", command=snap_photo, width=button_width, height=button_height)
Capture_button.place(x=565, y=80)

import_button = tk.Button(frame4, text="Import", command=import_image_in_thread, width=button_width, height=button_height)
import_button.place(x=565, y=120)

tracking_label = tk.Label(frame4, text="Track:")
tracking_label.place(x=570, y=165)

tracking_entry = tk.Entry(frame4, width=3)
tracking_entry.insert(0, "-1")
tracking_entry.place(x=615, y=165)

select_dictionary_label = tk.Label(frame4, text="Dictionary")
select_dictionary_label.place(x=575, y=200)

dictionaries = ttk.Combobox(frame4, values=aruco_dictionaries, width=13)
dictionaries.place(x=555, y=225)
dictionaries.current(10)

marker_size_label = tk.Label(frame4, text="Size \"mm\":")
marker_size_label.place(x=555, y=265)

marker_size_entry = tk.Entry(frame4, width=4)
marker_size_entry.insert(0, "29")
marker_size_entry.place(x=635, y=265)


Calibrate_button = tk.Button(frame4, text="Calibrate", command=calibrate_camera, width=button_width, height=button_height)
Calibrate_button.place(x=565, y=300)

Aruco_var = tk.IntVar()
Aruco_button = tk.Checkbutton(frame4, text=" ArUco", variable=Aruco_var, command=None)
Aruco_button.place(x=570, y=350)

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<    LLM     >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

frame5 = tk.Frame(window, width=688, height=498, bd=1, relief="solid")
frame5.place(x=780, y=400)

recognized_speech_label = tk.Label(frame5, text="Queries:")
recognized_speech_label.place(x=90, y=18)

recognized_speech= tk.Text(frame5, width=38, height=25, insertbackground="white", foreground="blue")
recognized_speech.place(x=10, y=51)

send_queries_button = tk.Button(frame5, text="Send", command=send_queries, width=button_width, height=button_height)
send_queries_button.place(x=153, y=13)

subFrame = tk.Frame(frame5, width=125, height=36, bd=1, relief="solid")
subFrame.place(x=280, y=-1)

LLM_var = tk.IntVar()
LLM_button = tk.Checkbutton(frame5, text="Enable LLM", font=("Arial", 12), variable=LLM_var, command=run_LLM_thread)
LLM_button.place(x=281, y=5)

Prompt_label = tk.Label(frame5, text="Prompt:")
Prompt_label.place(x=430, y=18)

LLM_prompt = tk.Text(frame5, width=38, height=25, background="black", insertbackground="yellow", foreground="yellow")
LLM_prompt.place(x=366, y=51)

prompt_var = tk.StringVar()
prompt_var.set(prompts[0])

prompt_menu = tk.OptionMenu(frame5, prompt_var, *prompts, command =on_prompt_select)
prompt_menu.place(x=500, y=13)
prompt_menu.config(width=2)  # Adjust the width as needed

save_prompt_button = tk.Button(frame5, text="Save", command=save_prompt, width=button_width-5, height=button_height)
save_prompt_button.place(x=583, y=13)

# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<    Main     >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
manager = ArduinoSerialManager(log_widget=manip_log)
window.after(100, initialize_ports)
load_data()
load_prompt()
clear_video_frame()
window.bind("<KeyPress>", manual_ctrl_in_thread)
posture_listbox.bind('<<ListboxSelect>>', select_posture)
motions_listbox.bind('<<ListboxSelect>>', select_motion)
motion_listbox.bind('<<ListboxSelect>>', select_motion)
post_motion_listbox.bind('<<ListboxSelect>>', select_motion)
experiments.bind("<<ComboboxSelected>>", select_experiment)
window.protocol("WM_DELETE_WINDOW", on_closing)
window.mainloop()

