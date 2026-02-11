from dataclasses import dataclass

@dataclass
class BoundGame:
    hwnd: int
    pid: int
    title: str
