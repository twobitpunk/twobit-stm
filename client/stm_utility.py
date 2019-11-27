import wmi
import subprocess
import winreg


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
    def get_ms_account_name():
        ms_account_name = None
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\IdentityCRL\UserExtendedProperties", 0,
                                 winreg.KEY_READ | winreg.KEY_WOW64_32KEY)
            ms_account_name = winreg.EnumKey(key, 0)
        finally:
            return ms_account_name

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
