import json
import schedule
import time
import datetime
import locale

from Schedule import *
from Device import *

with open('garden-config.json') as json_data:
   d = json.load(json_data)

devices = [] 

for device in d['devices']:
   devices.append( Device( device['id'],device['name'], device['gpio'] ) ) 

print( 'devices read')
print( 'attempting: reading schedules ...' )

schedules = []

for schedule in d['schedules']:
   device = next(( x for x in devices if x.id == schedule['deviceId']),None)
   print(device.name)
   #schedules.append( Schedule(   schedule['startTime'],
   #                            schedule['endTime'], schedule['recurrence'] ) )
print( 'schedules read' )

print(len(devices))
time.sleep(2)
for device in devices:

   device.startSprinkler()
   time.sleep(2)
   device.stopSprinkler()
   time.sleep(2)


#devices[0].startSprinkler()
#time.sleep(1)
#devices[0].stopSprinkler()
#time.sleep(1)
#devices[1].startSprinkler()
#time.sleep(1)
#devices[1].stopSprinkler()
#time.sleep(1)

GPIO.cleanup()
