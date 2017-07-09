from Device import *

class Schedule ():

   def __init__( self, device, startTime, endTime, recurrence ):
      self.device = device
      self.startTime = startTime
      self.endTime = endTime
      self.recurrence = recurrence

#   def addSchedule( self, id, device, startTime, endTime, recurrence ):
#       if( recurrence != Null ):
#          for ( element in recurrence):
#             if( isinstance( element, int ) ):
#                count.append(element)
#             else:

