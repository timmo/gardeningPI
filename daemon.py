import json
import time
import sys
import schedule

from datetime import datetime
from ScheduleConfig import *
from Sprinkler import *
from RegisterSchedules import *

try:

    with open('garden-config.json') as json_data:
        config = json.load(json_data)

    sprinklerList = []
    for sprinkler in config['sprinklers']:
        sprinklerList.append(Sprinkler(sprinkler['id'], sprinkler['name'], sprinkler['gpio']))
    print('Sprinklers read')

    schedules = []
    for toBeScheduled in config['schedules']:
        sprinkler = next((x for x in sprinklerList if x.id == toBeScheduled['sprinklerId']), None)
        schedules.append(ScheduleConfig(sprinkler, toBeScheduled['startTime'], toBeScheduled['endTime'], toBeScheduled['recurrenceInDays']))
    RegisterSchedules.registerSchedules(schedules)
    print('Schedules read')

    print('now looping to run pending schedules ...')
    while (True):
        print(datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
        schedule.run_pending()
        time.sleep(1)

except KeyboardInterrupt:
    print(' exit by keyboard interrupt')
    sys.exit()

finally:
    GPIO.cleanup()
    print('GPIO channels cleaned up')
