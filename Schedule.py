from Device import *

class Schedule ():
   
   def __init__( self, deviceList, deviceId, startTime, endTime, recurrence ):
      self.deviceId = deviceId
      self.deviceList = deviceList
      self.startTime = startTime
      self.endTime = endTime
      self.recurrence = recurrence

   #def addSchedule( id, startTime, endTime ):
