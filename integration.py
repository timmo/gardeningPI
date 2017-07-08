import math
import requests
from requests.exceptions import *
import json
import astral
import datetime
import hashlib

from enum import Enum, unique

from kivy.clock import Clock
from kivy.logger import Logger

# Using I2C on RasPi for reading a light sensor
import platform
if 'arm' in platform.uname().machine:
    import smbus # used for I2C connection to TSL2516 lux sensor


class ParsingException(Exception):
    pass


@unique
class WeatherCondition(Enum):
    clear = 1
    cloudy = 2
    drizzle = 3
    rain = 4
    heavy_rain = 5
    hail = 6
    snow = 7
    heavy_snow = 8
    fog = 9
    wind = 10
    thunderstorm = 11
    tornado = 12


# TODO: load credentials from external file?
class IntegrationBase:

    def __init__(self):
        super().__init__()
        self.refresh_data_time = 900  # every 15 minutes
        Clock.schedule_interval(self.refresh, self.refresh_data_time)

    def refresh(self, dt):
        pass


class NetatmoIntegration(IntegrationBase):

    _baseUrl = "https://api.netatmo.net/"

    def __init__(self, client_id, client_secret, username, password):
        super().__init__()
        # TODO: load credentials from external file?
        self.clientId = client_id
        self.clientSecret = client_secret
        self.username = username
        self.password = password
        self.access_token = None
        self.refresh_token = None
        self.refresh_access_token_time = -1
        self.retry_authentication_time = 60     # every minute

        self.wifiStatus = None
        self.calibratingCo2 = False
        self.name = "Anonymous"
        self.position = astral.Location()
        self.inside = {
            'temperature': {
                'current': "88.8"
            },
            'humidity': 100,
            'co2': 8888.8
        }
        self.outside = {
            'temperature': {
                'min': -25.0,
                'current': 38.8,
                'max': 45.0
            },
            'battery': 100,
            'connection': 100
        }
        self.rain = {
            'rain': {
                'hour': 88.8,
                'day': 88.8
            },
            'battery': 100,
            'connection': 100
        }
        self.alarm = []
        self.locale = ''

        Clock.schedule_once(self.authenticate)

    def authenticate(self, dt):
        Logger.debug('Netatmo: Starting authentication')
        try:
            params = {
                "grant_type": "password",
                "client_id": self.clientId,
                "client_secret": self.clientSecret,
                "username": self.username,
                "password": self.password,
                "scope": "read_station"
            }
            response = requests.post(NetatmoIntegration._baseUrl + "oauth2/token", data=params).json()
        # TODO: Check response
        except RequestException as rex:
            # Authentication failed
            Logger.debug('Netatmo: Failed to authenticate')
            Logger.exception(str(rex))
            Clock.schedule_once(self.authenticate, self.retry_authentication_time) # TODO only for network related errors
            return
        self.access_token = response['access_token']
        self.refresh_token = response['refresh_token']
        self.refresh_access_token_time = response['expires_in']
        Clock.schedule_once(self.refresh_access_token, self.refresh_access_token_time / 2)
        Logger.debug('Netatmo: authentication successful')

    def refresh_access_token(self, dt):
        Logger.debug('Netatmo: Starting refresh of access token')
        try:
            # Refresh access token
            params = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.clientId,
                "client_secret": self.clientSecret
            }
            response = requests.post(NetatmoIntegration._baseUrl + "oauth2/token", data=params).json()
        # TODO: Check response
        except RequestException as rex:
            Logger.debug('Netatmo: Failed to refresh access token')
            Logger.exception(str(rex))
            Clock.schedule_once(self.authenticate,
                                self.retry_authentication_time)  # TODO only for authentication related errors
            return
        self.refresh_token = response['refresh_token']
        self.refresh_access_token_time = response['expires_in']
        Clock.schedule_once(self.refresh_access_token, self.refresh_access_token_time / 2)
        Logger.debug('Netatmo: Access token refreshed successfully')

    def refresh(self, dt):
        super().refresh(dt)
        Logger.debug('Netatmo: Starting data refresh')

        # Load data from netatmo portal
        try:
            # Read weather station
            params = {
                "access_token": self.access_token
            }
            response = requests.post(NetatmoIntegration._baseUrl + "api/getstationsdata", data=params)
            #print(json.dumps(response.json(), sort_keys=True, indent=4, separators=(',', ': ')))
        except RequestException as rex:
            Logger.debug('Netatmo: Failed to refresh data')
            Logger.exception(str(rex))
            Logger.debug(str(response.content))
            return

        # Parse Response
        try:

            # TODO identify errors like
            # {
            #     "error": {
            #         "code": 500,
            #         "message": "Internal Server Error"
            #     }
            # }

            # This is the station's locale string for displaying values
            self.locale = response.json()['body']['user']['administrative']['reg_locale'].replace('-', '_')
            station = response.json()['body']['devices'][0]
            self.name = station['station_name']
            self.wifiStatus = station['wifi_status']
            self.calibratingCo2 = station['co2_calibrating']
            self.position.name = self.name
            self.position.region = station['place']['city']
            self.position.latitude = station['place']['location'][1]
            self.position.longitude = station['place']['location'][0]
            self.position.timezone = station['place']['timezone']
            self.position.elevation = 0
            Logger.debug("Netatmo: Location is {} ({}, {}); timezone: {}".format(
                str(self.position.region), str(self.position.latitude), str(self.position.longitude),
                str(self.position.timezone)))

            # Inside module
            data = station['dashboard_data']
            self.inside['temperature'] = {
                'current': data['Temperature'],
                'min': data['min_temp'],
                'max': data['max_temp'],
                'trend': data['temp_trend'] if 'temp_trend' in data else 0
            }
            self.inside['co2'] = data['CO2']
            self.inside['humidity'] = data['Humidity']
            self.inside['pressure'] = {
                'current': data['Pressure'],
                'trend': data['pressure_trend']
            }
            self.inside['noise'] = data['Noise']

            # TODO: find a better way of identifying the modules (sequence depends on configuration)

            # outside module
            data = station['modules'][1]
            self.outside['battery'] = data['battery_percent']
            self.outside['connection'] = data['rf_status']
            data = station['modules'][1]['dashboard_data']
            self.outside['temperature'] = {
                'current': data['Temperature'],
                'min': data['min_temp'],
                'max': data['max_temp'],
                'trend': data['temp_trend'] if 'temp_trend' in data else 0
            }
            self.outside['humidity'] = data['Humidity']

            # rain module
            data = station['modules'][0]
            self.rain['battery'] = data['battery_percent']
            self.rain['connection'] = data['rf_status']
            data = station['modules'][0]['dashboard_data']
            self.rain['rain'] = {
                'hour': data['sum_rain_1'],
                'day': data['sum_rain_24'] if 'sum_rain_24' in data else 0
            }

            # alarms
            if 'meteo_alarms' in station:
                for alarm in station['meteo_alarms']:
                    self.alarm.append({
                        'type': alarm['type'],
                        'level': alarm['level'],
                        'description': alarm['descr'][13:]
                    })

            Logger.debug('Netatmo: Data refresh successful')

        except (KeyError, ValueError) as err:
            Logger.debug('Netatmo: Failed to parse json')
            Logger.exception(str(err))
            Logger.debug(str(response.content))


class OpenWeatherMapIntegration(IntegrationBase):

    _baseUrl = "http://api.openweathermap.org/data/2.5/"
    _iconUrl = "http://openweathermap.org/img/w/"

    def __init__(self, position, app_id):
        super().__init__()
        self.position = position
        self.appId = app_id
        self.forecast = []

    # Converts OWM weather id to common weather condition
    def _convert_weather_id(self, weather_id):
        if 200 <= weather_id <= 299:
            return WeatherCondition.thunderstorm
        if 300 <= weather_id <= 399:
            return WeatherCondition.drizzle
        # 400 range does not exist?
        if 500 == weather_id:
            return WeatherCondition.drizzle
        if 501 == weather_id:
            return WeatherCondition.rain
        if 502 <= weather_id <= 599:
            return WeatherCondition.heavy_rain
        if 600 <= weather_id <= 601:
            return WeatherCondition.snow
        if 602 <= weather_id <= 699:
            return WeatherCondition.heavy_snow
        if 700 <= weather_id <= 780:
            return WeatherCondition.fog
        if weather_id == 781:
            return WeatherCondition.tornado
        # Clear Sky
        if weather_id == 800:
            return WeatherCondition.clear
        # Clouds
        if 801 <= weather_id <= 804:
            return WeatherCondition.cloudy
        if 900 <= weather_id <= 902:
            return WeatherCondition.tornado
        if weather_id == 905 or 957 <= weather_id <= 962:
            return WeatherCondition.wind
        if weather_id == 906:
            return WeatherCondition.hail
        return None

    def refresh(self, dt):
        super().refresh(dt)
        Logger.debug('OWM: Starting data refresh')
        Logger.debug("OWM: using location {} ({}, {}); timezone: {}".format(
            str(self.position.region), str(self.position.latitude), str(self.position.longitude),
            str(self.position.timezone)))
        try:
            # Forecast (16 days)
            params = {
                "lat": self.position.latitude,
                "lon": self.position.longitude,
                "mode": "json",
                "appid": self.appId,
                "units": "metric",
                "lang": "de",
                "cnt": 10
            }
            response = requests.get(OpenWeatherMapIntegration._baseUrl + "forecast/daily", params=params);
            # print(json.dumps(response.json(), indent=2))
        except RequestException as rex:
            Logger.debug('OWM: Failed to refresh data')
            Logger.exception(str(rex))
            return

        # Parse response
        try:
            for entry in response.json()['list']:
                timestamp = datetime.datetime.fromtimestamp(entry['dt'])
                self.forecast.append({
                    'time': timestamp,
                    'description': entry['weather'][0]['description'],
                    'icon': entry['weather'][0]['icon'],
                    'id': self._convert_weather_id(entry['weather'][0]['id']),
                    'temperature': {
                        "min": float(format(entry['temp']['min'], '.1f')),
                        "max": float(format(entry['temp']['max'], '.1f')),
                    },
                    'pressure': entry['pressure'],
                    'humidity': entry['humidity'],
                    'clouds': entry['clouds'] if 'clouds' in entry else 0,
                    'snow': entry['snow'] if 'snow' in entry else 0,
                    'rain': entry['rain'] if 'rain' in entry else 0
                })
        except KeyError as kerr:
            Logger.debug('OWM: Failed to parse json')
            Logger.exception(str(kerr))
            Logger.debug(str(response.content))
        Logger.debug('OWM: Data refresh successful')


# Only gives min/max temperature for today and next two days
class WetterComIntegration(IntegrationBase):

    _baseUrl = "http://api.wetter.com/forecast/weather/city/{}/project/{}/cs/{}"

    def __init__(self, city_code, project_name, api_key):
        super().__init__()
        self.minimumTemperature = -25;
        self.maximumTemperature = 45;
        self.id = None;
        self._city_code = city_code
        self._project_name = project_name
        self._api_key = api_key

    # Converts Wetter.com id to common weather condition
    def _convert_weather_id(self, weather_id):
        if weather_id == 0:
            return WeatherCondition.clear
        if weather_id in (1, 2, 3) or 10 <= weather_id <= 39:
            return WeatherCondition.cloudy
        if weather_id == 4 or 40 <= weather_id <= 49:
            return WeatherCondition.fog
        if weather_id in (5, 50, 51, 53, 56):
            return WeatherCondition.drizzle
        if weather_id in (6, 8, 60, 61, 63):
            return WeatherCondition.rain
        if weather_id in (55, 65, 80, 81, 82):
            return WeatherCondition.heavy_rain
        if weather_id in (57, 66, 67, 69, 83, 84):
            return WeatherCondition.hail
        if weather_id in (7, 68, 70, 71, 73, 85):
            return WeatherCondition.snow
        if weather_id in (75, 86):
            return WeatherCondition.heavy_snow
        if weather_id == 9 or 90 <= weather_id <= 99:
            return WeatherCondition.thunderstorm
        return None

    def refresh(self, dt):
        super().refresh(dt)
        Logger.debug('Wetter.com: Starting data refresh')

        # Read current weather from wetter.com
        try:
            params = {
                "output": 'json'
            }
            checksum = hashlib.md5(self._project_name.encode('utf-8') + self._api_key.encode('utf-8') +
                                   self._city_code.encode('utf-8')).hexdigest()
            response = requests.get(WetterComIntegration._baseUrl.format(self._city_code, self._project_name, checksum),
                                    params=params);
            # print(json.dumps(response.json(), sort_keys=True, indent=4, separators=(',', ': ')))
            data = response.json()
        except RequestException and ValueError and ConnectionError as ex:
            Logger.debug('Wetter.com: Failed to refresh data')
            Logger.exception(str(ex))
            if 'response' in locals():
                msg = str(response.content)
            else:
                msg = ""
            Logger.debug(msg)
            return

        # Parse response
        try:
            now = datetime.datetime.now()
            for daystring, forecast in data['city']['forecast'].items():
                day = datetime.datetime.strptime(daystring, '%Y-%m-%d')
                if day.date() == now.date():
                    self.minimumTemperature = float(forecast['tn'])
                    self.maximumTemperature = float(forecast['tx'])
                    # TODO: take values from last day for range 00:00 .. 05:59
                    if 6 <= now.hour <= 10:
                        weather_id = forecast['06:00']['w']
                    elif 11 <= now.hour <= 16:
                        weather_id = forecast['11:00']['w']
                    elif 17 <= now.hour <= 22:
                        weather_id = forecast['17:00']['w']
                    else:
                        weather_id = forecast['23:00']['w']
                    self.id = self._convert_weather_id(int(weather_id))
                    break
            else:
                Logger.warning('Wetter.com: Unable to find date {} in forecast'.format(now.strftime('%Y-%m-%d')))
        except KeyError and AttributeError as err:
            Logger.warning('Wetter.com: Unable to parse json')
            Logger.debug('Wetter.com: \n' +
                         json.dumps(response.json(), sort_keys=True, indent=4, separators=(',', ': ')))
            Logger.exception(str(err))

        Logger.debug('Wetter.com: Data refresh successful')
        Logger.debug('Wetter.com: Got id {}'.format(self.id))


# This is the new, improved version for brightness control, using a TSL2561 via I2C
class TSL2516BrightnessRegulation(IntegrationBase):

    def __init__(self):
        super().__init__()
        self.bus = 1
        self.address = 0x39

        self.ambient_light = 0
        self.infrared_light = 0

        self.lux = 2.0

        # Weight of latest lux measurement in overall brightness calculation. Used for slowing down changes in
        # brightness. A value of 1.0 completely ignores the old lux value
        self.new_lux_weight = 0.05;

        self.brightness = 120
        self.min_brightness = 15
        self.max_brightness = 255

        self.device = '/sys/class/backlight/rpi_backlight/brightness'

    def refresh(self, dt):
        super().refresh(dt)

        # Measure brightness via TSL2516 lux sensor on I2C bus 1
        # see http://www.mogalla.net/201502/lichtsensor-tsl2561-am-raspberry (german)
        # Code would benefit from a block read command. smbus-cffi 0.5.1 documentation mentions that block reads
        # currently crash with a kernel panic on RasPi. Thus, reading single bytes.
        # TODO: Try block reads
        try:
            bus = smbus.SMBus(self.bus)
            bus.write_byte_data(self.address, 0x80, 0x03)  # init measurement
            lb = bus.read_byte_data(self.address, 0x8c)
            hb = bus.read_byte_data(self.address, 0x8d)
            self.ambient_light = (hb << 8) | lb
            lb = bus.read_byte_data(self.address, 0x8e)
            hb = bus.read_byte_data(self.address, 0x8f)
            self.infrared_light = (hb << 8) + lb
        except IOError as ex:
            Logger.warning("Brightness: Problems using I2C bus ({}) ".format(str(ex)))
            # TODO: some countermeasure? bus reset?
            return

        # Calculate Lux value (see example in TSL2561 datasheet)
        if self.ambient_light == 0:
            return  # ratio would result in div by 0, avoid
        ratio = self.infrared_light / float(self.ambient_light)
        if 0 < ratio <= 0.50:
            new_lux = 0.0304 * self.ambient_light - 0.062 * self.ambient_light * (ratio ** 1.4)
        elif 0.50 < ratio <= 0.61:
            new_lux = 0.0224 * self.ambient_light - 0.031 * self.infrared_light
        elif 0.61 < ratio <= 0.80:
            new_lux = 0.0128 * self.ambient_light - 0.0153 * self.infrared_light
        elif 0.80 < ratio <= 1.3:
            new_lux = 0.00146 * self.ambient_light - 0.00112 * self.infrared_light
        else:
            new_lux = 0

        # Weighted average of old and current value
        self.lux = (1.0 - self.new_lux_weight) * self.lux + self.new_lux_weight * new_lux

        # Use a logarithmic function to map lux to brightness, clamp to min..max
        new_brightness = max(self.min_brightness, min(round(math.log10(self.lux+1.5)*300.0), self.max_brightness))

        # Write to device
        if self.brightness != new_brightness:
            Logger.debug('Brightness: Setting to {} ({} lux) - current {} lux)'.format(
                str(new_brightness), "%.2f" % self.lux, "%.2f" % new_lux))
            self.brightness = new_brightness
            with open(self.device, 'w') as d:
                d.write(str(self.brightness))
