import asyncio
import websockets
import wmi
from subprocess import check_output
from win10toast import ToastNotifier
from time import sleep
import platform
import configparser
import logging

# noinspection PyBroadException
try:
    from . stm_utility import STMUtilities
    from . base_service import BaseService
except:
    from stm_utility import STMUtilities
    from base_service import BaseService


class ScreenTimeManagerClient(BaseService):
    _svc_name_ = 'ScreenTimeManagerClient'
    _svc_display_name_ = "Screen Time Manager Client"
    _svc_description_ = "This service manages screen time for kids"
    _sleep_time_seconds = 25
    _server_uri = 'ws://localhost:8765'
    _log_file = 'c:\\temp\\stm_client.log'
    _log_level = 10
    _icon_path = None
    _logger = None
    _is_running = False
    _is_logoff_issued = False
    _time_left = 0.0
    _warn_time_seconds = 600
    _computer = None
    _utility = None
    _use_ms_account = False

    def __init__(self, args):
        super().__init__(args)
        # Load configuration
        self._parser = configparser.ConfigParser()
        if platform.system() is 'Windows':
            self._parser.read('c:\\etc\\stm-client.config')
        else:
            self._parser.read('/etc/stm-client.config')
        self._log_file = self._parser.get('general', 'log-file')
        self._log_level = self._parser.getint('general', 'log-level')
        self._server_uri = self._parser.get('general', 'stm-server-uri')
        self._sleep_time_seconds = self._parser.getint('general', 'sleep-time-seconds')
        self._warn_time_seconds = self._parser.getint('general', 'warn-time-seconds')
        self._icon_path = self._parser.get('general', 'icon-path')
        self._use_ms_account = self._parser.getboolean('general', 'use-ms-account')

        # Configure logging
        self.configure_logging()

        self._computer = wmi.WMI('localhost')
        self._utility = STMUtilities()
        self._logger.info('Starting Screen Time Manager Client Service.')

    def start(self):
        self._is_running = True

    def stop(self):
        self._is_running = False

    def main(self):
        while self._is_running:
            self.check_users()
            sleep(self._sleep_time_seconds)

    def configure_logging(self):
        self._logger = logging.getLogger('stm')
        self._logger.setLevel(self._log_level)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh = logging.FileHandler(self._log_file)
        fh.setLevel(self._log_level)
        fh.setFormatter(formatter)
        ch = logging.StreamHandler()
        ch.setLevel(self._log_level)
        self._logger.addHandler(fh)
        self._logger.addHandler(ch)

    def logoff_windows(self):
        self._logger.info('Logging off Windows session')

        output = None
        try:
            self._logger.info('Issuing shutdown warning at %s minutes', self._warn_time_seconds / 60.0)
            output = check_output('shutdown /s /t {}'.format(str(self._warn_time_seconds)))
        except Exception as e:
            self._logger.error('Error while doing timed shutdown: %s, output from command was: %s', e, output)
        logging.debug('Output from logoff command was: %s', output)

    """Not really working as is. But the win10toast stuff works in simple test cases. Hmmmm."""
    def show_message(self):
        if 0.0 <= self._time_left <= 0.5 and int(self._time_left * 60.0) % 5 == 0:  # Every 5 minutes if < 30 mins left
            toaster = ToastNotifier()
            toaster.show_toast("Screen Time Manager",
                               "This machine will shut down in {} minutes".format(str(self._time_left)),
                               icon_path=self._icon_path,
                               duration=10)

    async def check_time_left(self, user_name):
        try:
            async with websockets.connect(self._server_uri) as ws:
                await ws.send(str(user_name))
                response = await ws.recv()
                self._time_left = float(response) - self._warn_time_seconds / 3600.0
                #  self.show_message()  # Not working right just now
                if self._time_left < 0.0:
                    self._logger.debug('No time left for user %s', user_name)
                    return False
                self._logger.debug('User %s has %s hours left', user_name, str(self._time_left))
                return True
        except Exception as e:
            self._logger.error('Error while querying Screen Time Manager Server - perhaps not running? Error: %s', e)
            return True  # We really don't know here, err on the side of caution.

    def check_users(self):
        _user_name=None
        if self._use_ms_account:
            _user = self._utility.get_ms_account_name()
            _user_name = _user
        else:
            _user = self._utility.get_current_user()
            _user_name = str(_user[2]).strip().lower()

        _is_locked = self._utility.is_session_locked()
        if _user_name is not None and not _is_locked:
            # Check with the service at this point and log off if it returns False
            self._logger.debug('Checking time left for user: %s', _user)
            _is_allowed = asyncio.get_event_loop().run_until_complete(self.check_time_left(_user_name))
            if not _is_allowed and not self._is_logoff_issued:
                self._logger.debug('Logging off user %s', _user_name)
                self.logoff_windows()
                self._is_logoff_issued = True  # Flagging that the logoff is initiated.
            elif _is_allowed:
                self._is_logoff_issued = False  # Reset the logoff flag if there is still time left - new day maybe.


if __name__ == '__main__':
    ScreenTimeManagerClient.parse_command_line()
