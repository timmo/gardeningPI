from Device import *

class ScheduleConfig ():

   def __init__( self, device, startTime, endTime, recurrenceInDays ):
      self.device = device
      self.startTime = startTime
      self.endTime = endTime
      self.recurrenceInDays = recurrenceInDays

#   def addSchedule( self, id, device, startTime, endTime, recurrence ):
#       if( recurrence != Null ):
#          for ( element in recurrence):
#             if( isinstance( element, int ) ):
#                count.append(element)
#             else:

