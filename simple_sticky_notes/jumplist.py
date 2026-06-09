"""Windows taskbar Jump List (right-click the taskbar/pinned icon).

Mirrors the tray menu's top-level actions as Jump List "Tasks", plus a "Recent"
category of recent notes. Each entry relaunches the app with a CLI flag, which the
single-instance layer forwards to the running app. Best-effort: every function is a
no-op (returns False) if pywin32/COM is unavailable, so it never breaks the app.
"""
from __future__ import annotations

import os
import sys

# Stable identity shared by the running process and the installed shortcut, so the
# Jump List shows on the pinned taskbar icon. Must match the shortcut's AppUserModelID.
APP_USER_MODEL_ID = "Whitkin.SimpleStickyNotes"


def set_app_user_model_id() -> None:
    """Group the app's windows under APP_USER_MODEL_ID so the Jump List attaches."""
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def set_shortcut_app_id(lnk_path: str, app_id: str = APP_USER_MODEL_ID) -> bool:
    """Stamp a .lnk with System.AppUserModel.ID so its Jump List matches the app."""
    try:
        import pythoncom
        from win32com.propsys import propsys, pscon
        from win32com.shell import shell
    except Exception:
        return False
    pythoncom.CoInitialize()
    try:
        link = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink
        )
        persist = link.QueryInterface(pythoncom.IID_IPersistFile)
        persist.Load(lnk_path, 0x00000002)  # STGM_READWRITE so the property store is writable
        store = link.QueryInterface(propsys.IID_IPropertyStore)
        store.SetValue(pscon.PKEY_AppUserModel_ID, propsys.PROPVARIANTType(app_id, pythoncom.VT_LPWSTR))
        store.Commit()
        persist.Save(lnk_path, True)
        return True
    except Exception:
        return False
    finally:
        pythoncom.CoUninitialize()


def _launch_command() -> tuple[str, str]:
    """(executable, args-prefix) used to relaunch the app with a flag appended."""
    if getattr(sys, "frozen", False):
        return sys.executable, ""
    main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
    return sys.executable, f'"{main_py}"'


def _make_link(exe: str, arguments: str, title: str):
    import pythoncom
    from win32com.propsys import propsys, pscon
    from win32com.shell import shell

    link = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink
    )
    link.SetPath(exe)
    link.SetArguments(arguments)
    link.SetIconLocation(exe, 0)
    store = link.QueryInterface(propsys.IID_IPropertyStore)
    store.SetValue(pscon.PKEY_Title, propsys.PROPVARIANTType(title, pythoncom.VT_LPWSTR))
    store.Commit()
    return link


def build_jumplist(recent: list[tuple[str, str]] | None = None) -> bool:
    """(Re)build the Jump List. `recent` is a list of (title, note_id)."""
    try:
        import pythoncom
        from win32com.shell import shell
    except Exception:
        return False

    pythoncom.CoInitialize()
    try:
        exe, prefix = _launch_command()

        def args(flag: str) -> str:
            return (prefix + " " + flag).strip()

        cdl = pythoncom.CoCreateInstance(
            shell.CLSID_DestinationList,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_ICustomDestinationList,
        )
        cdl.SetAppID(APP_USER_MODEL_ID)
        cdl.BeginList()

        tasks = pythoncom.CoCreateInstance(
            shell.CLSID_EnumerableObjectCollection,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IObjectCollection,
        )
        tasks.AddObject(_make_link(exe, args("--new-note"), "New Sticky"))
        tasks.AddObject(_make_link(exe, args("--show-phone-notes"), "Show phone sticky notes"))
        tasks.AddObject(_make_link(exe, args("--exit"), "Exit"))
        cdl.AddUserTasks(tasks)

        if recent:
            collection = pythoncom.CoCreateInstance(
                shell.CLSID_EnumerableObjectCollection,
                None,
                pythoncom.CLSCTX_INPROC_SERVER,
                shell.IID_IObjectCollection,
            )
            for title, note_id in recent[:10]:
                collection.AddObject(
                    _make_link(exe, args(f'--show-note "{note_id}"'), title or note_id)
                )
            cdl.AppendCategory("Recent", collection)

        cdl.CommitList()
        return True
    except Exception:
        return False
    finally:
        pythoncom.CoUninitialize()
