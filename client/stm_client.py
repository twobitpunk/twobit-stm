import sys
import asyncio
import websockets
import wmi
from subprocess import check_output
import platform
import configparser
import logging
import win32api
import win32con
import win32gui
import win32ts
from threading import Thread, Event

# noinspection PyBroadException
try:
    from .stm_utility import STMUtilities
    from .base_service import BaseService
except:
    # noinspection PyUnresolvedReferences
    from stm_utility import STMUtilities
    # noinspection PyUnresolvedReferences
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
    _stop_event = Event()
    _is_shutdown_issued = False
    _time_left = 0.0
    _warn_time_seconds = 600
    _computer = None
    _utility = None
    _use_ms_account = False
    _event_listener = None
    _is_session_locked = False

    WM_WTSSESSION_CHANGE = 0x2B1
    WTS_SESSION_LOCK = 0x7
    WTS_SESSION_UNLOCK = 0x8

    def __init__(self, args):
        super().__init__(args)
        # Load configuration
        self._parser = configparser.ConfigParser()
        if platform.system() == 'Windows':
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
        if sys.platform == "win32" and sys.version_info >= (3, 8, 0):
            #  There seems to be a problem in Python 3.8.x preventing event loops from working as before on Windows
            # noinspection PyUnresolvedReferences
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # noinspection PyUnusedLocal
    def msg_handler(self, hwnd, msg, wparam, lparam):
        if msg == self.WM_WTSSESSION_CHANGE:
            self._logger.debug('Caught a session change message: %s, event: %s', msg, wparam)
            if wparam == self.WTS_SESSION_LOCK:
                self._logger.debug('Session is locked')
                self._is_session_locked = True
            elif wparam == self.WTS_SESSION_UNLOCK:
                self._logger.debug('Session is unlocked')
                self._is_session_locked = False
            else:
                self._logger.debug('Strange session change event: %s', wparam)

    def message_receiver(self):  # Hidden window that can listen for messages
        self._logger.debug('Starting the message receiver')
        event_window = None
        try:
            hinst = win32api.GetModuleHandle(None)
            wndclass = win32gui.WNDCLASS()
            wndclass.hInstance = hinst
            wndclass.lpszClassName = "ListenerWindowClass"
            wndclass.lpfnWndProc = self.msg_handler
            event_window = None

            event_window_class = win32gui.RegisterClass(wndclass)
            event_window = win32gui.CreateWindowEx(0, event_window_class,
                                                   "ListenerWindow",
                                                   0,
                                                   0,
                                                   0,
                                                   0,
                                                   0,
                                                   win32con.HWND_MESSAGE,
                                                   None,
                                                   None,
                                                   None)
            win32ts.WTSRegisterSessionNotification(event_window, win32ts.NOTIFY_FOR_ALL_SESSIONS)
            while not self._stop_event.is_set():
                win32gui.PumpWaitingMessages()
                self._stop_event.wait(5)
        except Exception as e:
            self._logger.error("Exception while making message handler: %s", e)
        finally:
            win32ts.WTSUnRegisterSessionNotification(event_window)
            self._logger.debug('Exiting the message receiver')

    def start(self):
        self._logger.debug('Entering start')

    def stop(self):
        self._logger.debug('Entering stop')
        self._stop_event.set()
        self._event_listener.join()

    def main(self):
        self._logger.debug('Entering main')
        self._event_listener = Thread(target=self.message_receiver)
        self._event_listener.start()

        while not self._stop_event.is_set():
            self.check_users()
            self._stop_event.wait(self._sleep_time_seconds)

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

    def shutdown(self):
        self._logger.info('Shutting down Windows')
        output = None
        try:
            self._logger.info('Issuing shutdown warning at %s minutes', self._warn_time_seconds / 60.0)
            output = check_output('shutdown /s /t {}'.format(str(self._warn_time_seconds)))
        except Exception as e:
            self._logger.error('Error while doing timed shutdown: %s, output from command was: %s', e, output)
        self._logger.debug('Output from logoff command was: %s', output)

    def cancel_shutdown(self):
        try:
            output = check_output('shutdown /a')
            self._logger.info('Cancelling shutdown - new lease acquired: %s', str(output))
        except Exception as e:
            self._logger.error('Error while cancelling issued shutdown: %s', e)

    async def check_time_left(self, user_name):
        request = {'user_name': user_name, 'command': 'update_time_left'}
        try:
            async with websockets.connect(self._server_uri, timeout=5) as ws:
                await ws.send(str(request))
                response = await ws.recv()
                self._time_left = float(response) - self._warn_time_seconds / 3600.0
                if self._time_left < 0.0:
                    self._logger.debug('No time left for user %s', user_name)
                    return False
                self._logger.debug('User %s has %s hours left', user_name, str(self._time_left))
                return True
        except Exception as e:
            self._logger.error('Error while querying Screen Time Manager Server - perhaps not running? Error: %s', e)
            return True  # We really don't know here, err on the side of caution.

    def check_users(self):
        _user_name = None
        if self._use_ms_account:
            _user = self._utility.get_ms_account_name()
            _user_name = _user
        else:
            _user = self._utility.get_current_user()
            _user_name = str(_user[2]).strip().lower()

        self._logger.debug('Current active user is: %s', _user_name)

        if _user_name is not None:
            if not self._is_session_locked:
                # Check with the service at this point and log off if it returns False
                self._logger.debug('Checking time left for user: %s', _user)
                _is_allowed = False
                try:
                    _is_allowed = asyncio.get_event_loop().run_until_complete(self.check_time_left(_user_name))
                except Exception as e:
                    self._logger.error('Oopsie while querying service: %s', e)
                if not _is_allowed and not self._is_shutdown_issued:
                    self.shutdown()
                    self._is_shutdown_issued = True  # Flagging that the logoff is initiated.
                elif _is_allowed and self._is_shutdown_issued:
                    self._is_shutdown_issued = False  # Reset logoff flag. New day or new user maybe.
                    self.cancel_shutdown()
            else:
                self._logger.debug('Session for user %s is locked', _user_name)
        else:
            self._logger.debug('User is None - perhaps noone is logged on?')


if __name__ == '__main__':
    ScreenTimeManagerClient.parse_command_line()
