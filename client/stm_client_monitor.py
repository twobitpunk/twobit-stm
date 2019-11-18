from tkinter import Label, StringVar, Tk, Frame
import asyncio
import wmi
import websockets
import threading
import configparser
import platform
import signal
try:
    from . stm_utility import STMUtilities
except:
    from stm_utility import STMUtilities


# noinspection PyBroadException
class ScreenTimeClientMonitor:
    _computer = None
    _server_uri = 'ws://192.168.10.10:8765'
    _time_left = 24.0
    _user = None
    _label_text = 'Time remaining (mins): '
    _top_window = None
    _time_var = None
    _time_label = None
    _run = True
    _event = threading.Event()
    _utility = None

    def __init__(self):
        self._computer = wmi.WMI('localhost')
        self._parser = configparser.ConfigParser()
        if platform.system() is 'Windows':
            self._parser.read('c:\\etc\\stm-client.config')
        else:
            self._parser.read('/etc/stm-client.config')
        self._server_uri = self._parser.get('general', 'stm-server-uri')
        self._utility = STMUtilities()
        self._user = self._utility.get_current_user()

    async def get_time_remaining(self):
        is_locked = self._utility.is_session_locked()  # Only query when session is unlocked
        if self._user is not None and not is_locked :
            user_name = str(self._user[2]).strip().lower()
            try:
                async with websockets.connect(self._server_uri) as ws:
                    await ws.send(str(user_name))
                    response = await ws.recv()
                    self._time_left = float(response)
            except:
                self._time_left = 24.0  # No response so we don't really know

    def show_gui(self):
        self._top_window = Tk(className='Screen time remaining')

        frame = Frame(self._top_window)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        text_var = StringVar()
        text_var.set(self._label_text)
        Label(frame, textvariable=text_var).grid(row=0, column=0, sticky='w')

        self._time_var = StringVar()
        self._time_label = Label(frame, textvariable=self._time_var).grid(row=0, column=1, sticky='e')
        self._update_time_label()

        frame.pack()
        self._top_window.protocol('WM_DELETE_WINDOW', self.on_closing)
        self._top_window.mainloop()

    def _update_time_label(self):
        # _time = '%.2f' % self._time_left
        _time = int(self._time_left * 60.0)
        self._time_var.set(_time)

    def update_remaining_time(self):
        loop = asyncio.new_event_loop()
        while self._run:
            if self._top_window is not None and self._time_var is not None:
                loop.run_until_complete(self.get_time_remaining())
                self._update_time_label()
                self._top_window.update()
            self._event.wait(5.0)

    def main(self):
        update_thread = threading.Thread(target=self.update_remaining_time)
        update_thread.start()
        self.show_gui()

    def on_closing(self):
        self.exit()
        self._top_window.destroy()

    def exit(self):
        self._run = False
        self._event.set()


monitor = ScreenTimeClientMonitor()


# noinspection PyUnusedLocal
def handler(signum, frame):
    monitor.exit()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, handler=handler)
    monitor.main()
