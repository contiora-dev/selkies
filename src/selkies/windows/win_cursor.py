import ctypes
import ctypes.wintypes as wintypes
import logging
import io
from PIL import Image

logger = logging.getLogger("win_cursor")

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

user32.GetCursorInfo.argtypes = [ctypes.c_void_p]
user32.GetCursorInfo.restype = wintypes.BOOL

user32.GetIconInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
user32.GetIconInfo.restype = wintypes.BOOL

user32.GetDC.argtypes = [wintypes.HANDLE]
user32.GetDC.restype = wintypes.HANDLE

user32.ReleaseDC.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
user32.ReleaseDC.restype = ctypes.c_int

gdi32.CreateCompatibleDC.argtypes = [wintypes.HANDLE]
gdi32.CreateCompatibleDC.restype = wintypes.HANDLE

gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HANDLE

gdi32.SelectObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
gdi32.SelectObject.restype = wintypes.HANDLE

gdi32.StretchBlt.argtypes = [
    wintypes.HANDLE, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HANDLE, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.DWORD,
]
gdi32.StretchBlt.restype = wintypes.BOOL

gdi32.GetDIBits.argtypes = [
    wintypes.HANDLE, wintypes.HANDLE, ctypes.c_uint, ctypes.c_uint,
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint,
]
gdi32.GetDIBits.restype = ctypes.c_int

gdi32.DeleteDC.argtypes = [wintypes.HANDLE]
gdi32.DeleteDC.restype = wintypes.BOOL

gdi32.DeleteObject.argtypes = [wintypes.HANDLE]
gdi32.DeleteObject.restype = wintypes.BOOL


class ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", wintypes.BOOL),
        ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD),
        ("hbmMask", wintypes.HANDLE),
        ("hbmColor", wintypes.HANDLE),
    ]


class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hCursor", wintypes.HANDLE),
        ("ptScreenPos", wintypes.POINT),
    ]


CURSOR_SHOWING = 0x0001

def capture_cursor(scale=1.0, size=32):
    if size <= 0:
        size = 32
    cursor_info = CURSORINFO()
    cursor_info.cbSize = ctypes.sizeof(CURSORINFO)

    if not user32.GetCursorInfo(ctypes.byref(cursor_info)):
        return None

    if not (cursor_info.flags & CURSOR_SHOWING):
        return None

    if not cursor_info.hCursor:
        return None

    icon_info = ICONINFO()
    if not user32.GetIconInfo(cursor_info.hCursor, ctypes.byref(icon_info)):
        return None

    try:
        hdc = user32.GetDC(None)
        if not hdc:
            return None

        try:
            bmp = Image.new("RGBA", (size, size), (0, 0, 0, 0))

            if icon_info.hbmColor:
                bmp_dc = gdi32.CreateCompatibleDC(hdc)
                old_bmp = gdi32.SelectObject(bmp_dc, icon_info.hbmColor)

                try:
                    temp_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                    dc_for_img = gdi32.CreateCompatibleDC(hdc)
                    bmp_handle = gdi32.CreateCompatibleBitmap(hdc, size, size)
                    old_temp = gdi32.SelectObject(dc_for_img, bmp_handle)

                    gdi32.StretchBlt(
                        dc_for_img, 0, 0, size, size,
                        bmp_dc, 0, 0, size, size,
                        0x00CC0020,
                    )

                    bmp_data = (ctypes.c_ubyte * (size * size * 4))()
                    bmi = ctypes.create_string_buffer(40)
                    ctypes.memset(bmi, 0, 40)
                    bmi_struct = ctypes.cast(bmi, ctypes.POINTER(ctypes.c_uint32))
                    bmi_struct[0] = 40
                    ctypes.cast(bmi, ctypes.POINTER(ctypes.c_int32))[2] = size
                    ctypes.cast(bmi, ctypes.POINTER(ctypes.c_int32))[3] = size * 4
                    ctypes.cast(bmi, ctypes.POINTER(ctypes.c_int32))[4] = 1
                    ctypes.cast(bmi, ctypes.POINTER(ctypes.c_int32))[5] = 32

                    gdi32.GetDIBits(
                        dc_for_img, bmp_handle, 0, size,
                        bmp_data, bmi, 0,
                    )

                    temp_img = Image.frombytes("RGBA", (size, size), bytes(bmp_data), "raw", "BGRA")

                    gdi32.SelectObject(dc_for_img, old_temp)
                    gdi32.DeleteDC(dc_for_img)
                    gdi32.DeleteObject(bmp_handle)
                finally:
                    gdi32.SelectObject(bmp_dc, old_bmp)
                    gdi32.DeleteDC(bmp_dc)

                if icon_info.hbmMask:
                    mask_dc = gdi32.CreateCompatibleDC(hdc)
                    old_mask = gdi32.SelectObject(mask_dc, icon_info.hbmMask)

                    try:
                        mask_bmp = gdi32.CreateCompatibleBitmap(hdc, size, size)
                        mask_temp_dc = gdi32.CreateCompatibleDC(hdc)
                        old_mask_bmp = gdi32.SelectObject(mask_temp_dc, mask_bmp)
                        gdi32.StretchBlt(
                            mask_temp_dc, 0, 0, size, size,
                            mask_dc, 0, 0, size, size,
                            0x00CC0020,
                        )

                        mask_bmi = ctypes.create_string_buffer(40)
                        ctypes.memset(mask_bmi, 0, 40)
                        ctypes.cast(mask_bmi, ctypes.POINTER(ctypes.c_uint32))[0] = 40
                        ctypes.cast(mask_bmi, ctypes.POINTER(ctypes.c_int32))[2] = size
                        ctypes.cast(mask_bmi, ctypes.POINTER(ctypes.c_int32))[3] = size * 4
                        ctypes.cast(mask_bmi, ctypes.POINTER(ctypes.c_int32))[4] = 1
                        ctypes.cast(mask_bmi, ctypes.POINTER(ctypes.c_int32))[5] = 32

                        mask_bytes = (ctypes.c_ubyte * (size * size * 4))()
                        gdi32.GetDIBits(
                            mask_temp_dc, mask_bmp, 0, size,
                            mask_bytes, mask_bmi, 0,
                        )

                        mask_img = Image.frombytes("RGBA", (size, size), bytes(mask_bytes), "raw", "BGRA")
                        cursor_pixels = temp_img.load()
                        mask_pixels = mask_img.load()

                        for y in range(size):
                            for x in range(size):
                                if mask_pixels[x, y][3] == 0:
                                    cursor_pixels[x, y] = (0, 0, 0, 0)

                        bmp = temp_img

                        gdi32.SelectObject(mask_temp_dc, old_mask_bmp)
                        gdi32.DeleteDC(mask_temp_dc)
                        gdi32.DeleteObject(mask_bmp)
                    finally:
                        gdi32.SelectObject(mask_dc, old_mask)
                        gdi32.DeleteDC(mask_dc)
            else:
                bmp = Image.new("RGBA", (size, size), (0, 0, 0, 0))

        finally:
            user32.ReleaseDC(None, hdc)

        hotspot_x = icon_info.xHotspot
        hotspot_y = icon_info.yHotspot

        buf = io.BytesIO()
        bmp.save(buf, format="PNG")
        png_data = buf.getvalue()

        return {
            "png_data": png_data,
            "hotspot_x": hotspot_x,
            "hotspot_y": hotspot_y,
            "width": size,
            "height": size,
        }

    except Exception as e:
        logger.error(f"Error capturing cursor: {e}")
        return None
    finally:
        if icon_info.hbmMask:
            gdi32.DeleteObject(icon_info.hbmMask)
        if icon_info.hbmColor:
            gdi32.DeleteObject(icon_info.hbmColor)
