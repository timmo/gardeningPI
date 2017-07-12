import json
import time
import sys
import schedule

from ScheduleConfig import *
from Device import *
from RegisterSchedules import *


with open('garden-config.json') as json_data:
    d = json.load(json_data)

devices = []

for device in d['devices']:
    devices.append(Device(device['id'], device['name'], device['gpio']))

print('Devices read')

schedules = []

for toBeScheduled in d['schedules']:
    device = next((x for x in devices if x.id == toBeScheduled['deviceId']), None)
    schedules.append(ScheduleConfig(device, toBeScheduled['startTime'], toBeScheduled['endTime'], toBeScheduled['recurrenceInDays']))

RegisterSchedules.registerSchedules(schedules)

print('Schedules read')

print('now looping to run pending schedules ...')

try:
    while (True):

        schedule.run_pending()
        time.sleep(1)
except KeyboardInterrupt:
    print(' Bye')
    sys.exit()
finally:
    GPIO.cleanup()
    print('GPIO channels cleaned up')
