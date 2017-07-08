import datetime
import locale
from pytz import timezone
import signal
import json
import platform

import kivy
from kivy.app import App
from kivy.atlas import Atlas
from kivy.clock import Clock
from kivy.uix.image import Image
from kivy.uix.widget import Widget, ObjectProperty, StringProperty, NumericProperty
from kivy.logger import Logger

from integration import WeatherCondition, NetatmoIntegration, OpenWeatherMapIntegration, WetterComIntegration, \
    TSL2516BrightnessRegulation

kivy.require('1.9.1')  # replace with your current kivy version !

# TODO use weather symbol from wetter.com? better quality forecast?
# TODO FEATURE adapt to Fahrenheit...


# Determines weather symbol based on weather id from service, daytime and clouds
def symbol_for_weather(condition, is_day, clouds_percentage):

    # Determine base symbol through given code
    if condition == WeatherCondition.clear:
        return 'sun' if is_day else 'moon'  # no clouds
    elif condition == WeatherCondition.cloudy:
        symbol_name = 'cloud'
    elif condition == WeatherCondition.drizzle:
        symbol_name = 'drizzle_2'
    elif condition == WeatherCondition.rain:
        symbol_name = 'rain_2'
    elif condition == WeatherCondition.heavy_rain:
        symbol_name = 'rain'
    elif condition == WeatherCondition.hail:
        symbol_name = 'hail_2'
    elif condition == WeatherCondition.snow:
        symbol_name = 'snow'
    elif condition == WeatherCondition.heavy_snow:
        symbol_name = 'snow_2'
    elif condition == WeatherCondition.fog:
        symbol_name = 'fog'
    elif condition == WeatherCondition.wind:
        if clouds_percentage < 10:
            return 'wind_plain'  # clear skies, no day/night indication
        else:
            symbol_name = 'wind'
    elif condition == WeatherCondition.thunderstorm:
        symbol_name = 'lightning'
    elif condition == WeatherCondition.tornado:
        return 'tornado'
    else:
        return 'blank'  # give up

    # Adapt to day/night?
    if clouds_percentage < 75:
        return symbol_name + ('_d' if is_day else '_n')
    else:
        return symbol_name


# Display status information
class Status(Widget):

    outside_signal_symbol = StringProperty('signal_1')
    outside_battery_symbol = StringProperty('battery_0')
    rain_signal_symbol = StringProperty('signal_1')
    rain_battery_symbol = StringProperty('battery_0')

    @staticmethod
    def symbol_for_battery(amount):
        if amount <= 19:
            return 'battery_0'
        if 20 <= amount <= 39:
            return 'battery_1'
        if 40 <= amount <= 59:
            return 'battery_2'
        if 60 <= amount <= 79:
            return 'battery_3'
        else:
            return 'battery_4'

    @staticmethod
    def symbol_for_connection(amount):
        if amount <= 62:
            return 'signal_5'
        if 63 <= amount <= 70:
            return 'signal_4'
        if 71 <= amount <= 78:
            return 'signal_3'
        if 79 <= amount <= 86:
            return 'signal_2'
        else:
            return 'signal_1'

    def refresh(self, outside, rain):
        self.outside_battery_symbol = Status.symbol_for_battery(outside['battery'])
        self.outside_signal_symbol = Status.symbol_for_connection(outside['connection'])
        self.rain_battery_symbol = Status.symbol_for_battery(rain['battery'])
        self.rain_signal_symbol = Status.symbol_for_connection(rain['connection'])


# Displays a forecast for a single day
class Forecast(Widget):

    date = StringProperty('Missing\nData')
    symbol = StringProperty('blank')
    min_temperature = NumericProperty(0)
    max_temperature = NumericProperty(0)
    precipitation = NumericProperty(0)

    def refresh(self, time, weather_id, temp_min, temp_max, rain, snow, clouds):
        self.date = time.strftime('%A\n%d. %B')
        self.symbol = symbol_for_weather(weather_id, True, clouds)
        self.min_temperature = temp_min
        self.max_temperature = temp_max
        self.precipitation = rain + snow


# Displays Date and Time
class DateTime(Widget):

    formatstring = '%A, %d. %B %Y — %H:%M'

    # Example: 'Donnerstag, 25. November 2016 - 13:45'
    text = StringProperty(datetime.datetime.now().strftime(formatstring))

    def refresh(self, time):
        self.text = time.strftime(self.formatstring)


# Shows outside temperature as a thermometer
class OutsideTemperature(Widget):

    gradient = ObjectProperty(Image(source='images/gradient.png'))
    size_thermometer = NumericProperty(340)
    temperature = NumericProperty(21.5)
    min_temperature = NumericProperty(17.8)
    max_temperature = NumericProperty(24.3)

    min_temperature_measured = NumericProperty(17.8)
    max_temperature_measured = NumericProperty(24.3)
    min_temperature_forecast = NumericProperty(17.8)
    max_temperature_forecast = NumericProperty(24.3)

    def map_offset(self, temperature):
        if temperature < -25:  # Clip at bottom of thermometer
            return 0
        elif temperature > 45:  # Clip at top of thermometer
            return self.size_thermometer - 1
        else:
            return (self.size_thermometer / 70.0) * (temperature + 25)

    # Ensures that current temperature is within bounds of minimum/maximum temperature range
    def _set_temperature_range(self):
        self.min_temperature = min([self.temperature, self.min_temperature_measured, self.min_temperature_forecast])
        self.max_temperature = max([self.temperature, self.max_temperature_measured, self.max_temperature_forecast])

    def refresh(self, temperature, temp_min, temp_max):
        self.temperature = temperature
        self.min_temperature_measured = temp_min
        self.max_temperature_measured = temp_max
        self._set_temperature_range()

    def refresh_forecast(self, temp_min, temp_max):
        self.min_temperature_forecast = temp_min
        self.max_temperature_forecast = temp_max
        self._set_temperature_range()


# Shows outside information
class OutsideInformation(Widget):

    weather_symbol = StringProperty('blank')
    moon_phase_symbol = StringProperty('moon')
    sunrise = StringProperty('00:00')
    sunset = StringProperty('00:00')
    precipitation_forecast = NumericProperty(88.8)
    precipitation_day = NumericProperty(88.8)

    @staticmethod
    def symbol_for_moon(phase):
        if phase == 0:
            return 'new_moon'
        if 1 <= phase <= 5:
            return 'moon_waxing_crescent'
        if 6 <= phase <= 8:
            return 'moon_first_quarter'
        if 9 <= phase <= 13:
            return 'moon_waxing_gibbous'
        if phase == 14:
            return 'full_moon'
        if 15 <= phase <= 19:
            return 'moon_waning_gibbous'
        if 20 <= phase <= 22:
            return 'moon_last_quarter'
        if 23 <= phase <= 27:
            return 'moon_waning_crescent'
        else:
            return 'blank'  # Error

    def refresh(self, position, time, weather_id, clouds_percentage, precipitation_forecast, precipitation_day):
        sunrise = position.sunrise(time)
        sunset = position.sunset(time)
        is_day = sunrise <= time <= sunset
        self.sunrise = sunrise.strftime('%H:%M')
        self.sunset = sunset.strftime('%H:%M')
        self.weather_symbol = symbol_for_weather(weather_id, is_day, clouds_percentage)
        self.moon_phase_symbol = self.symbol_for_moon(position.moon_phase(time))
        self.precipitation_forecast = precipitation_forecast
        self.precipitation_day = precipitation_day


# Shows inside information
class InsideInformation(Widget):

    temperature = NumericProperty(0)
    humidity = NumericProperty(100)
    co2_symbol = StringProperty('blank')

    @staticmethod
    def symbol_for_co2(amount):
        if amount <= 500:
            return 'grin'
        if 501 <= amount <= 1000:
            return 'smile'
        if 1001 <= amount <= 1500:
            return 'mhm'
        if 1401 <= amount <= 2000:
            return 'nope'
        else:
            return 'ohgod'

    def refresh(self, temperature, humidity, co2):
        self.temperature = temperature
        self.humidity = humidity
        self.co2_symbol = InsideInformation.symbol_for_co2(co2)


# Shows Alarms
class Alarms(Widget):

    alarm_symbol = StringProperty('blank')
    message = StringProperty("")

    def refresh(self, type, level, description):
        # TODO: Process type and level
        if len(description) > 0:
            self.alarm_symbol = 'danger_sign'
            self.message = 'description'
        else:
            self.alarm_symbol = 'blank'
            self.message = ""


# General layout
class MainWidget(Widget):

    def refresh(self):
        pass


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

        # Open Weather Map
        self.owm = OpenWeatherMapIntegration(
            self.netatmo.position,
            config['open_weather_map']['app_id']
        )
        Clock.schedule_once(self.owm.refresh, timeout=5)

        # Wetter.com
        self.wetter = WetterComIntegration(
            config['wetter.com']['city_code'],  # Berlin, Lichterfelde hard-coded :-(
            config['wetter.com']['project_name'],
            config['wetter.com']['api_key']
        )
        Clock.schedule_once(self.wetter.refresh)

        # Screen brightness regulation on RasPi
        if 'arm' in platform.uname().machine:
            self.screen_brightness = TSL2516BrightnessRegulation()
            Clock.schedule_interval(self.screen_brightness.refresh, timeout=1)

        # Repaint everything each second
        Clock.schedule_interval(self.refresh, timeout=1)

    def build(self):
        return MainWidget()

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
