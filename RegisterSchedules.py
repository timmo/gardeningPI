import schedule


class RegisterSchedules():

    @staticmethod
    def registerSchedules(schedules):
        for toBeScheduled in schedules:
            RegisterSchedules.registerSchedule(toBeScheduled)

    @staticmethod
    def registerSchedule(toBeScheduled):
        schedule.every( toBeScheduled.recurrenceInDays).days.at(toBeScheduled.startTime).do(toBeScheduled.sprinkler.startSprinkler)
        schedule.every( toBeScheduled.recurrenceInDays).days.at(toBeScheduled.endTime).do(toBeScheduled.sprinkler.stopSprinkler)

        print( 'Schedule registered', toBeScheduled.sprinkler.name, toBeScheduled.startTime, '-', toBeScheduled.endTime, 'P', toBeScheduled.recurrenceInDays ,'D')

