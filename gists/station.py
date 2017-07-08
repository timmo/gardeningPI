import datetime
import locale
from pytz import timezone
import signal
import json
import platform

from integration import  NetatmoIntegration

class Station(App):

    refreshInterval = NumericProperty(600)  # 10 minutes
    symbol = Atlas('images/icons.atlas')

    def __init__(self):
        super(Station, self).__init__()

        # Read config
        with open('config.json') as config_file:
            config = json.load(config_file)

        # Netatmo
        self.netatmo = NetatmoIntegration(
            config['netatmo']['client_id'],
            config['netatmo']['client_secret'],
            config['netatmo']['username'],
            config['netatmo']['password']
        )
        self.netatmo.authenticate(None)
        Clock.schedule_once(self.netatmo.refresh)

        # Repaint everything each second
        Clock.schedule_interval(self.refresh, timeout=1)

    def refresh(self, dt):

        def get_forecast_for_day(timestamp):
            for aDay in self.owm.forecast:
                if aDay['time'].date() == timestamp.date():
                    return aDay
            else:
                raise LookupError('Unable to find date {} in forecast'.format(timestamp.strftime('%d.%m.%Y')))

        try:
            # Set time and locale
            locale.setlocale(locale.LC_ALL, self.netatmo.locale)
            station_time = timezone(self.netatmo.position.timezone)
            now = datetime.datetime.now(tz=station_time)
            self.root.ids.time.refresh(now)

            # Inside data
            w = self.root.ids.inside
            w.refresh(self.netatmo.inside['temperature']['current'], self.netatmo.inside['humidity'],
                      self.netatmo.inside['co2'])

            # Outside data
            w = self.root.ids.outside
            today = get_forecast_for_day(now)

            w.refresh(self.netatmo.position, now, self.wetter.id, today['clouds'], today['rain'],
                      self.netatmo.rain['rain']['day'])

            # Outside temperature
            w = self.root.ids.outside_temperature
            w.refresh(self.netatmo.outside['temperature']['current'], self.netatmo.outside['temperature']['min'],
                      self.netatmo.outside['temperature']['max'])
            w.refresh_forecast(self.wetter.minimumTemperature, self.wetter.maximumTemperature)

            # Forecast data
            for d in range(1, 6):
                forecast_day = now + datetime.timedelta(days=d)
                forecast = get_forecast_for_day(forecast_day)
                w = self.root.ids['day' + str(d)]
                w.refresh(forecast_day, forecast['id'], forecast['temperature']['min'], forecast['temperature']['max'],
                          forecast['rain'], forecast['snow'], forecast['clouds'])

            # Alarms
            # TODO: Take care of multiple alarms
            w = self.root.ids.alarms
            if len(self.netatmo.alarm) > 0:
                w.refresh(self.netatmo.alarm[0]['type'], self.netatmo.alarm[0]['level'],
                          self.netatmo.alarm[0]['description'])
            else:
                self.root.ids.alarms.refresh(None, None, "");

            # Status
            w = self.root.ids.status
            w.refresh({'battery': self.netatmo.outside['battery'], 'connection': self.netatmo.outside['connection']},
                      {'battery': self.netatmo.rain['battery'], 'connection': self.netatmo.rain['connection']})

        except LookupError as lerr:
            Logger.warning(str(lerr))

    def on_start(self):
        pass

    def on_signal_interrupt(self, signum, frame):
        Logger.debug('SIGINT received')

    def on_signal_terminate(self, signum, frame):
        Logger.debug('SIGTERM received')

    def on_signal_hangup(self, signum, frame):
        Logger.debug('SIGHUP received')

if __name__ == '__main__':
    station = Station()
    #signal.signal(signal.SIGINT, station.on_signal_interrupt)
    signal.signal(signal.SIGTERM, station.on_signal_terminate)
    signal.signal(signal.SIGHUP, station.on_signal_hangup)
    station.run()
