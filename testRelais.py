import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)  # GPIO Nummern statt Board Nummern

RELAIS_1_GPIO = 17
GPIO.setup(RELAIS_1_GPIO, GPIO.OUT)  # GPIO Modus zuweisen

while True:

    GPIO.output(RELAIS_1_GPIO, GPIO.LOW)  # aus
    print("off")

    time.sleep(1)

    GPIO.output(RELAIS_1_GPIO, GPIO.HIGH)  # an
    print ("on")

    time.sleep(1)
