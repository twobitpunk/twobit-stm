import os
import sys
import websockets
import asyncio
import logging
import configparser
import platform
from datetime import datetime

sys.path.append('..')


class TimeTracker:
    _user = None
    _day = None
    _last_update = None
    _time_spent = 0.0
    _pause_threshold = None

    def __init__(self, pause_threshold=None):
        self._last_update = datetime.now()
        self._day = self._last_update.strftime("%A").lower()
        self._pause_threshold = pause_threshold

    def update(self):
        _now = datetime.now()
        if self._pause_threshold is not None and (_now - self._last_update).total_seconds() > self._pause_threshold:
            self._last_update = _now  # There was a pause. Do not add that to the time spent.
            return self._time_spent
        self._time_spent += (_now - self._last_update).total_seconds() / 3600.0  # Time spent in hours
        self._last_update = _now
        return self._time_spent

    def get_time_spent(self):
        return self._time_spent

    def get_day(self):
        return self._day


class ScreenTimeManagerServer:
    _screen_times = dict()
    _time_trackers = dict()
    _hostname = 'localhost'
    _port = 8765
    _logger = None
    _log_file = '/tmp/stm_server.log'
    _log_level = 20
    _parser = None
    _config_file = None
    _config_m_time = None
    _pause_threshold = None

    def __init__(self):
        # Load configuration
        self._parser = configparser.ConfigParser()
        if platform.system() is 'Windows':
            self._config_file = 'c:\\etc\\stm-server.config'
        else:
            self._config_file = '/etc/stm-server.config'
        self._check_config()
        self._log_file = self._parser.get('general', 'log-file')
        self._log_level = self._parser.getint('general', 'log-level')
        self._hostname = self._parser.get('general', 'hostname')
        self._port = self._parser.getint('general', 'port')
        self._pause_threshold = self._parser.getint('general', 'pause-threshold')
        # Configure logging
        self.configure_logging()
        self._logger.info('Starting Screen Time Manager Server')

    def _check_config(self):
        m_time = os.path.getmtime(self._config_file)
        if self._config_m_time is None or m_time > self._config_m_time:
            self._parser.read(self._config_file)
            self._load_screen_times()
            self._config_m_time = m_time

    def configure_logging(self):
        self._logger = logging.getLogger()
        self._logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh = logging.FileHandler(self._log_file)
        fh.setLevel(self._log_level)
        fh.setFormatter(formatter)
        ch = logging.StreamHandler()
        ch.setLevel(self._log_level)
        self._logger.addHandler(fh)
        self._logger.addHandler(ch)

    def _load_screen_times(self):
        _sections = self._parser.sections()
        for _section in _sections:
            if _section.lower() != 'general':
                _user = _section  # This section is a user section
                self._screen_times[_user.lower()] = dict(self._parser.items(_user))
        for _user in self._screen_times.keys():
            if _user not in _sections:  # This user was removed, so delete the ScreenTime object
                del self._screen_times[_user]

    def get_screen_time_limit_for_user(self, user=None):
        self._logger.debug('Getting screen time for user %s', user)
        if user is None:
            return 24.0
        now = datetime.now()
        this_day = now.strftime("%A").lower()
        if self._screen_times.get(user) is None or len(self._screen_times[user]) == 0:
            return 24.0
        else:
            return float(self._screen_times[user][this_day])

    def get_screen_time_spent_for_user(self, user, update=False):
        _today = datetime.now().strftime("%A").lower()
        _time_tracker = self._time_trackers.get(user)
        _time_spent = 0.0
        if _time_tracker is None:  # First connect
            self._logger.debug('Creating time tracker for user %s', user)
            self._time_trackers[user] = TimeTracker(pause_threshold=self._pause_threshold)
        elif _time_tracker.get_day() != _today:  # New day
            self._logger.debug('New day for user %s - resetting time tracker', user)
            self._time_trackers[user] = TimeTracker(pause_threshold=self._pause_threshold)
        else:
            if update:
                _time_spent = self._time_trackers[user].update()
            else:
                _time_spent = self._time_trackers[user].get_time_spent()
            self._logger.debug('User %s has spent %s hours of screen time', user, _time_spent)
        return _time_spent

    # noinspection PyUnusedLocal
    async def ws_serve(self, websocket, path):
        try:
            request = await websocket.recv()
            query = eval(request)  # Rebuild the dictionary sent by the client
            user_name = query.get('user_name')
            command = query.get('command')
            screen_time_remaining = 24.0  # Maybe configurable so you can send 0.0 or some other default?
            self._logger.debug('Received command %s for user %s', command, user_name)

            if user_name is None or command is None or len(user_name) == 0 or len(command) == 0:
                self._logger.warning('Invalid user_name or command received: %s, %s', user_name, command)
                await websocket.send(str(screen_time_remaining))  # Send time remaining
            else:
                self._check_config()  # Reload config if changed

                screen_time_spent = 0.0
                if command == 'query_time_left':
                    screen_time_spent = self.get_screen_time_spent_for_user(user_name)
                elif command == 'update_time_left':
                    screen_time_spent = self.get_screen_time_spent_for_user(user_name, update=True)
                else:
                    self._logger.warning('Received invalid command %s from client %s', command, websocket.remote_address()[0])

                screen_time_limit = self.get_screen_time_limit_for_user(user_name)
                screen_time_remaining = screen_time_limit - screen_time_spent
                self._logger.debug('User %s has spent %s out of %s hours allowed. Sending %s remaining hours.',
                                   user_name, screen_time_spent, screen_time_limit, screen_time_remaining)
                await websocket.send(str(screen_time_remaining))  # Send time remaining
        except Exception as e:
            self._logger.warning('Unable to send session info to client. %s', e)

    def run(self):
        start_server = websockets.serve(self.ws_serve, self._hostname, self._port)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    _server = ScreenTimeManagerServer()
    _server.run()
