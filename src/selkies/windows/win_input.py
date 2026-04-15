import ctypes
import ctypes.wintypes as wintypes
import logging

logger = logging.getLogger("win_input")

user32 = ctypes.windll.user32

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000
MOUSEEVENTF_ABSOLUTE = 0x8000

KEYEVENTF_KEYDOWN = 0x0000
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_CAPITAL = 0x14
VK_NUMLOCK = 0x90
VK_SCROLL = 0x91

try:
    import pynput
    _pynput_mouse = pynput.mouse.Controller()
    _pynput_mouse_button_map = {
        "left": pynput.mouse.Button.left,
        "middle": pynput.mouse.Button.middle,
        "right": pynput.mouse.Button.right,
    }
    _USE_PYNPUT_MOUSE = True
    logger.info("pynput mouse controller initialized")
except Exception as e:
    _USE_PYNPUT_MOUSE = False
    logger.warning("pynput mouse not available (%s), falling back to SendInput", e)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]

KEYSYM_TO_VK = {
    0xFF08: 0x08,
    0xFF09: 0x09,
    0xFF0A: 0x0A,
    0xFF0B: 0x0B,
    0xFF0D: 0x0D,
    0xFF1B: 0x1B,
    0xFF50: 0x24,
    0xFF51: 0x25,
    0xFF52: 0x26,
    0xFF53: 0x27,
    0xFF54: 0x28,
    0xFF55: 0x2D,
    0xFF56: 0x2E,
    0xFF57: 0x2F,
    0xFF58: 0x30,
    0xFF59: 0x31,
    0xFF5A: 0x32,
    0xFF5B: 0x33,
    0xFF5C: 0x34,
    0xFF5D: 0x35,
    0xFF5E: 0x36,
    0xFF5F: 0x37,
    0xFF60: 0x38,
    0xFF61: 0x39,
    0xFF62: 0x30,
    0xFF63: 0xBD,
    0xFF64: 0xBB,
    0xFF65: 0xBC,
    0xFF66: 0xBE,
    0xFF67: 0xBF,
    0xFF68: 0xC0,
    0xFF69: 0xDB,
    0xFF6A: 0xDD,
    0xFF6B: 0xDC,
    0xFF7F: 0x2F,
    0xFF80: 0x2A,
    0xFFAA: 0xBA,
    0xFFAE: 0xDE,
    0xFFE1: VK_SHIFT,
    0xFFE2: VK_SHIFT,
    0xFFE3: VK_CONTROL,
    0xFFE4: VK_CONTROL,
    0xFFE5: 0x00,
    0xFFE7: 0x12,
    0xFFE8: 0x12,
    0xFFE9: VK_MENU,
    0xFFEA: VK_MENU,
    0xFFEB: VK_LWIN,
    0xFFEC: VK_RWIN,
    0xFFED: 0x5D,
    0xFFEE: 0x5D,
    0xFFFF: 0x2E,
    0xFFC8: 0x2D,
    0xFFC9: 0x2B,
    0xFFD0: 0x2E,
    0xFFD1: 0x2B,
    0xFFD2: 0x2D,
    0xFFD3: 0x2B,
    0xFF08: 0x08,
    0xFFB0: 0x60,
    0xFFB1: 0x61,
    0xFFB2: 0x62,
    0xFFB3: 0x63,
    0xFFB4: 0x64,
    0xFFB5: 0x65,
    0xFFB6: 0x66,
    0xFFB7: 0x67,
    0xFFB8: 0x68,
    0xFFB9: 0x69,
    0xFFC0: 0x21,
    0xFFC1: 0x40,
    0xFFC2: 0x23,
    0xFFC3: 0x24,
    0xFFC4: 0x25,
    0xFFC5: 0x5E,
    0xFFC6: 0x26,
    0xFFC7: 0x2A,
    0xFFCA: 0x28,
    0xFFCB: 0x29,
    0xFFCC: 0x5F,
    0xFFCD: 0x2B,
    0xFFCE: 0x2D,
    0xFFCF: 0x2F,
}

def _get_extended_flag(vk):
    extended_vks = {
        0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F,
        0x5B, 0x5C, 0x5D, 0x5E, 0x5F,
        0xA6, 0xA7,
        0x1B,
    }
    return 0x0001 if vk in extended_vks else 0

def keysym_to_vk(keysym):
    if keysym in KEYSYM_TO_VK:
        return KEYSYM_TO_VK[keysym]
    if 0x0020 <= keysym <= 0x007E:
        if 0x61 <= keysym <= 0x7A:
            return keysym - 0x20
        return keysym
    if 0x00A0 <= keysym <= 0x00FF:
        vk = user32.VkKeyScanW(keysym) & 0xFF
        if vk != 0xFF:
            return vk
    if 0x0100 <= keysym <= 0x01FF:
        vk = user32.VkKeyScanW(keysym & 0xFF) & 0xFF
        if vk != 0xFF:
            return vk
    return 0

def send_key_event(vk, down=True):
    if vk == 0:
        return
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.dwFlags = KEYEVENTF_KEYDOWN if down else KEYEVENTF_KEYUP
    inp.union.ki.dwFlags |= _get_extended_flag(vk)
    inp.union.ki.wScan = user32.MapVirtualKeyW(vk, 0)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def send_unicode_key(codepoint, down=True):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = 0
    inp.union.ki.wScan = codepoint
    inp.union.ki.dwFlags = KEYEVENTF_UNICODE
    if not down:
        inp.union.ki.dwFlags |= KEYEVENTF_KEYUP
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def send_mouse_move(x, y, absolute=False):
    if absolute:
        sw, sh = get_screen_size()
        if sw > 0 and sh > 0:
            norm_x = int(x * 65535 / (sw - 1)) if sw > 1 else 0
            norm_y = int(y * 65535 / (sh - 1)) if sh > 1 else 0
        else:
            norm_x = 0
            norm_y = 0
        norm_x = max(0, min(65535, norm_x))
        norm_y = max(0, min(65535, norm_y))
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.union.mi.dx = norm_x
        inp.union.mi.dy = norm_y
        inp.union.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    else:
        if _USE_PYNPUT_MOUSE:
            _pynput_mouse.move(int(x), int(y))
        else:
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.union.mi.dx = x
            inp.union.mi.dy = y
            inp.union.mi.dwFlags = MOUSEEVENTF_MOVE
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def send_mouse_move_relative(dx, dy):
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.union.mi.dx = dx
    inp.union.mi.dy = dy
    inp.union.mi.dwFlags = MOUSEEVENTF_MOVE
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def send_mouse_button(button, down=True):
    if _USE_PYNPUT_MOUSE:
        btn = _pynput_mouse_button_map.get(button)
        if btn is None:
            return
        if down:
            _pynput_mouse.press(btn)
        else:
            _pynput_mouse.release(btn)
    else:
        flag_map = {
            "left": MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP,
            "right": MOUSEEVENTF_RIGHTDOWN if down else MOUSEEVENTF_RIGHTUP,
            "middle": MOUSEEVENTF_MIDDLEDOWN if down else MOUSEEVENTF_MIDDLEUP,
        }
        flags = flag_map.get(button)
        if flags is None:
            return
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.union.mi.dwFlags = flags
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def send_mouse_wheel(delta_x=0, delta_y=0):
    if _USE_PYNPUT_MOUSE:
        if delta_y != 0:
            _pynput_mouse.scroll(0, delta_y // 120)
        if delta_x != 0:
            _pynput_mouse.scroll(delta_x // 120, 0)
    else:
        if delta_y != 0:
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.union.mi.dwFlags = MOUSEEVENTF_WHEEL
            inp.union.mi.mouseData = delta_y
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        if delta_x != 0:
            inp = INPUT()
            inp.type = INPUT_MOUSE
            inp.union.mi.dwFlags = MOUSEEVENTF_HWHEEL
            inp.union.mi.mouseData = delta_x
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def get_screen_size():
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
