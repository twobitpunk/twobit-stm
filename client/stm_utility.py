import wmi
import subprocess


class STMUtilities:
    _computer = None

    def __init__(self):
        self._computer = wmi.WMI('localhost')

    def get_current_user(self):
        _current_user = None
        for process in self._computer.Win32_Process(name='explorer.exe'):
            _current_user = process.GetOwner()
        return _current_user

    @staticmethod
    def is_session_locked():
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        process_name = 'logonui.exe'
        call_all = 'TASKLIST'
        output_all = subprocess.check_output(call_all, startupinfo=si)
        if process_name in str(output_all).lower():
            return True
        return False
