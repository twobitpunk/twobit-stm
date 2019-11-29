import wmi
import subprocess
import winreg
import win32security


class STMUtilities:
    _computer = None

    def __init__(self):
        self._computer = wmi.WMI('localhost')

    def get_current_user(self):
        _current_user = None
        for process in self._computer.Win32_Process(name='explorer.exe'):
            _current_user = process.GetOwner()
        return _current_user

    def get_ms_account_name(self):
        ms_account_name = None
        try:
            sid, domain, _type = win32security.LookupAccountName('localhost', self.get_current_user()[2])
            sid_str = win32security.ConvertSidToStringSid(sid)
            sub_key = r'\Software\Microsoft\IdentityCRL\UserExtendedProperties'
            key = winreg.OpenKey(winreg.HKEY_USERS, sid_str + sub_key)
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
