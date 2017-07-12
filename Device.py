import RPi.GPIO as GPIO


class Device():
    def __init__(self, id, name, gpio):
        GPIO.setmode(GPIO.BCM)
        self.id = id
        self.name = name
        self.gpio = gpio
        GPIO.setup(gpio, GPIO.OUT)
        print(self.id, self.gpio, self.name)
        self.stopSprinkler()

    def startSprinkler(self):
        GPIO.output(self.gpio, GPIO.LOW)
        print(self.id, self.gpio, self.name, ' ', 'start')

    def stopSprinkler(self):
        GPIO.output(self.gpio, GPIO.HIGH)
        print(self.id, self.gpio, self.name, ' ', 'stop')
