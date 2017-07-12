import RPi.GPIO as GPIO
import time

class Device():

   def __init__( self, id, name, gpio ):
      self.id = id
      self.name = name
      self.gpio = gpio
      GPIO.setmode(GPIO.BCM)
      GPIO.setup( self.gpio, GPIO.OUT )
      self.stopSprinkler()

   def startSprinkler(self):
      GPIO.output( self.gpio, GPIO.LOW )
      print( self.id, self.gpio, self.name,' ', 'start' )

   def stopSprinkler(self):
      GPIO.output( self.gpio, GPIO.HIGH )
      print( self.id, self.gpio, self.name,' ', 'stop' )

