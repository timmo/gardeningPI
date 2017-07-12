from Sprinkler import *

class ScheduleConfig ():

   def __init__(self, sprinkler, startTime, endTime, recurrenceInDays):
      self.sprinkler = sprinkler
      self.startTime = startTime
      self.endTime = endTime
      self.recurrenceInDays = recurrenceInDays

