import win32gui

def get_client_rect_in_screen(hwnd: int):
    """
    返回 (x, y, w, h) —— 目标窗口 client 区域在屏幕坐标系下的位置和大小
    """
    left, top, right, bottom = win32gui.GetClientRect(hwnd)  # client rect in client coords
    x, y = win32gui.ClientToScreen(hwnd, (0, 0))             # client (0,0) -> screen
    w = right - left
    h = bottom - top
    return x, y, w, h
