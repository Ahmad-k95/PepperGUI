# -*- coding: utf-8 -*-
import time
import sys
import qi

############################
# ROBOT CONFIGURATION
############################
ROBOT_IP = "169.254.128.87"   # <-- change this
ROBOT_PORT = 9559

Language = "French"

############################
# CONNECT TO PEPPER
############################
robot_session = qi.Session()

try:
    robot_session.connect("tcp://{}:{}".format(ROBOT_IP, ROBOT_PORT))
    print("Connected to Pepper at {}:{}".format(ROBOT_IP, ROBOT_PORT))
except RuntimeError:
    print("Failed to connect to Pepper")
    sys.exit(1)

############################
# TEXT TO SPEECH FUNCTION
############################
def say(text):
    global Language
    if not robot_session.isConnected():
        return
    tts = robot_session.service("ALTextToSpeech")
    tts.setLanguage(Language)
    tts.say(text)

############################
# TEXT LIST
############################
texts = [
    "C’est à moi",
    "Tu gères !",
    "Je m’en charge.",
    "C'est pour toi!",
    "Voici!",
    "bravo!",
    "Prépare-toi",
    "tien!",
    "Prends ca!",
    "Parfait, continue !",
    "impeccable!",
    "Au top !",
    "Magnifique !",
    "Super !",
    "C’est parti.",
    "Pour toi !",
    "Je m’en occupe.",
    "Voilà pour toi !",
    "Attrape!",
    "Attends un instant",
    "Le voici !",
    "Je me depeche",
    "Tiens, prends !",
    "C’est à mon tour!",
    "Tiens bon !",
    "je gère ne t'en fais pas",
    "Formidables!",
    "Je me lance!",
    "Parfaitement exécuté !",
    "Je prends la main!",
    "Prend le !",
    "Je viens t’aider!",
    "Hop, pour toi !",
    "Excellent !",
    "C’est tout bon !",
    "À ton tour!",
    "C’est bien ça !",
    "Je vais t’aider!",
    "À toi maintenant !",
    "C’est mon tour !",
    "Attrape ça !",
    "Très bien !",
    "Je gère cette partie!",
    "Tu peux le prendre!",
    "Oui, comme ça !",
    "À moi!",
    "Je gère la suite!",
    "Voilà!",
    "Et voila!",
    "Parfait!",
    "Je te donne ça !",
    "Top!",
    "Je vais le chercher!",
    "Je te le donne !",
    "Je t'aide!",
    "Il est a toi!",
    "Je m’y mets!",
    "Reçois ça !",
    "Je m’occupe de la suite!",
    "Nickel!",
    "À moi d’agir!",
    "bien vu!",
    "Laisse-moi faire ça!",
    "Je me charge de ça!",
    "J'y travaille!",
    "c’est pour moi!",
    "Je te le donne!",
    "Je vais le faire!",
    "Tiens, c’est prêt !",
    "Je prends la suite!",
    "Je te l’amène!",
    "Voilà, prends le!",
    "Ne fais rien!",
    "Attends, j'y vais!",
    "Felicitations!",
    "Tu peux y aller!",
    "J’arrive",
    "Attrape !",
    "Je gére.",
    "Je me lance.",
    "J’attrape.",
    "Je prends.",
    "je t'aide.",
    "Attends.",
    "J'y vais.",
    "c'est ca!",
    "Je suis là.",
    "Je le prend.",
    "Je récupère l'objet.",
    "On y va.",
    "C’est parti.",
    "Je récupère.",
    "A moi.",
    "Je vais te donner un coup de main.",
    "Felicitations! C'etait super.",
    "laisse-moi faire.",
    "Formidable! Continue comme ca.",
    "je vais m'en occuper.",
    "bon! je vais t'aider",
    "bravo! trai bien",
    "Bien jouer!",
    "Laisse, je m’en occupe.",
    "je vais m’en charger.",
    "Je vais m’occuper de ça.",
    "Pas de souci, je gère.",
    "Attends, je peux t'aider.",
    "Laisse-moi m’en charger.",
    "C’est un peu loin, Je m’en charge !",
    "C’est bon, je m’en occupe.",
    "C’est bon, je m'en charge.",
    "c’est un peu loin, je m’en occupe !",
    "Prends le!",
    "Je prends les choses en main !",
    "Je prends ça pour toi.",
    "Laisse-moi t’aider un peu.",
    "Je vais m’en occuper.",
    "Je m'en charge pour toi.",
    "Je prends ça en main !",
    "Allez, je te file un coup de main !",
    "Je m’en occupe à ta place.",
    "Je m’en charge, c’est plus simple"
]


############################
# SAY + MEASURE FUNCTION
############################
def say_and_measure(text_list, output_file="file.txt"):
    results = []

    for text in text_list:
        print("Text:", text)

        start_time = time.time()
        say(text)
        end_time = time.time()

        duration_ms = int((end_time - start_time) * 1000)

        print("Duration:", duration_ms, "ms")
        print("-----------------------------")

        results.append(
            "text: {} / duration:{}\n".format(text, duration_ms)
        )

    with open(output_file, "w") as f:
        for line in results:
            f.write(line)

    print("Results written to", output_file)

############################
# MAIN
############################
if __name__ == "__main__":
    say_and_measure(texts)
