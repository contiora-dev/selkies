import ctypes
import ctypes.wintypes as wintypes
import logging

logger = logging.getLogger("win_display")

user32 = ctypes.windll.user32

class DEVMODE(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", wintypes.WCHAR * 32),
        ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD),
        ("dmOrientation", wintypes.SHORT),
        ("dmPaperSize", wintypes.SHORT),
        ("dmPaperLength", wintypes.SHORT),
        ("dmPaperWidth", wintypes.SHORT),
        ("dmScale", wintypes.SHORT),
        ("dmCopies", wintypes.SHORT),
        ("dmDefaultSource", wintypes.SHORT),
        ("dmPrintQuality", wintypes.SHORT),
        ("dmColor", wintypes.SHORT),
        ("dmDuplex", wintypes.SHORT),
        ("dmYResolution", wintypes.SHORT),
        ("dmTTOption", wintypes.SHORT),
        ("dmCollate", wintypes.SHORT),
        ("dmFormName", wintypes.WCHAR * 32),
        ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD),
        ("dmICMMethod", wintypes.DWORD),
        ("dmICMIntent", wintypes.DWORD),
        ("dmMediaType", wintypes.DWORD),
        ("dmDitherType", wintypes.DWORD),
        ("dmReserved1", wintypes.DWORD),
        ("dmReserved2", wintypes.DWORD),
        ("dmPanningWidth", wintypes.DWORD),
        ("dmPanningHeight", wintypes.DWORD),
    ]

DM_PELSWIDTH = 0x00080000
DM_PELSHEIGHT = 0x00100000
DM_BITSPERPEL = 0x00040000
DM_DISPLAYFREQUENCY = 0x00400000

CDS_FULLSCREEN = 0x00000004
CDS_UPDATEREGISTRY = 0x00000001
CDS_TEST = 0x00000002
CDS_RESET = 0x40000000
DISP_CHANGE_SUCCESSFUL = 0
DISP_CHANGE_RESTART = 1
DISP_CHANGE_FAILED = -1
DISP_CHANGE_BADMODE = -2
DISP_CHANGE_NOTUPDATED = -3
DISP_CHANGE_BADFLAGS = -4
DISP_CHANGE_BADPARAM = -5

SPI_SETLOGICALDPIOX = 0x009F
SPIF_UPDATEINIFILE = 0x0001
SPIF_SENDCHANGE = 0x0002

def resize_display(width, height):
    devmode = DEVMODE()
    devmode.dmSize = ctypes.sizeof(DEVMODE)
    devmode.dmPelsWidth = width
    devmode.dmPelsHeight = height
    devmode.dmFields = DM_PELSWIDTH | DM_PELSHEIGHT

    result = user32.ChangeDisplaySettingsExW(
        None,
        ctypes.byref(devmode),
        None,
        CDS_FULLSCREEN,
        None,
    )

    if result == DISP_CHANGE_SUCCESSFUL:
        logger.info(f"Display resized to {width}x{height}")
        return True
    else:
        error_names = {
            DISP_CHANGE_RESTART: "restart required",
            DISP_CHANGE_FAILED: "failed",
            DISP_CHANGE_BADMODE: "bad mode",
            DISP_CHANGE_NOTUPDATED: "not updated",
            DISP_CHANGE_BADFLAGS: "bad flags",
            DISP_CHANGE_BADPARAM: "bad param",
        }
        err_name = error_names.get(result, f"unknown error {result}")
        logger.error(f"Failed to resize display to {width}x{height}: {err_name}")
        return False

def set_dpi(dpi_value):
    try:
        result = user32.SystemParametersInfoW(
            SPI_SETLOGICALDPIOX,
            0,
            ctypes.byref(ctypes.c_uint(dpi_value)),
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
        )
        if result:
            logger.info(f"Set DPI to {dpi_value}")
            return True
        else:
            logger.error(f"Failed to set DPI to {dpi_value}")
            return False
    except Exception as e:
        logger.error(f"Error setting DPI: {e}")
        return False

def get_current_resolution():
    width = user32.GetSystemMetrics(0)
    height = user32.GetSystemMetrics(1)
    return width, height


def set_cursor_size(size):
    """Set Windows cursor size via registry (Windows 10/11 accessibility setting).

    :param size: Cursor size in pixels (valid range is typically 16-512).
    :returns: True on success, False on failure.
    """
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Control Panel\Cursors",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, "CursorBaseSize", 0, winreg.REG_DWORD, int(size))

        # Refresh cursor to apply change immediately
        result = user32.SystemParametersInfoW(
            0x0057,  # SPI_SETCURSORS
            0,
            None,
            SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
        )
        if result:
            logger.info(f"Set cursor size to {size}px")
            return True
        else:
            logger.warning(f"Set cursor registry key to {size}px but SPI_SETCURSORS failed")
            return True  # Registry change persists after reboot anyway
    except Exception as e:
        logger.error(f"Error setting cursor size: {e}")
        return False
