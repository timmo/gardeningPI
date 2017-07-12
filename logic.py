import json
import schedule
import time
import datetime
import locale
import sys

from ScheduleConfig import *
from Device import *
from RegisterSchedules import *

with open('garden-config.json') as json_data:
   d = json.load(json_data)

devices = [] 

for device in d['devices']:
   devices.append( Device( device['id'],device['name'], device['gpio'] ) ) 

print( 'devices read')
print( 'attempting: reading schedules ...' )

schedules = []

for toBeScheduled in d['schedules']:
   device = next(( x for x in devices if x.id == toBeScheduled['deviceId']),None)
   print(device.name)
   schedules.append( ScheduleConfig( device, toBeScheduled['startTime'],
                                     toBeScheduled['endTime'], toBeScheduled['recurrenceInDays'] ) )
print( 'schedules read' )

RegisterSchedules.registerSchedules(schedules)

try:
   while ( True ):
      schedule.run_pending()
      time.sleep(1)
except KeyboardInterrupt:
   print ' Bye'
   sys.exit()
finally:
   GPIO.cleanup()
#time.sleep(2)
#for device in devices:
#
#   device.startSprinkler()
#   time.sleep(2)
#   device.stopSprinkler()
#   time.sleep(2)


#devices[0].startSprinkler()
#time.sleep(1)
#devices[0].stopSprinkler()
#time.sleep(1)
#devices[1].startSprinkler()
#time.sleep(1)
#devices[1].stopSprinkler()
#time.sleep(1)


