import ctypes
import os

from pynput.keyboard import Controller as _KBController
from pynput.keyboard import Key as _Key

VK_VOLUME_UP = 0xAF
VK_VOLUME_DOWN = 0xAE
VK_MEDIA_PLAY_PAUSE = 0xB3

_KEYEVENTF_KEYUP = 0x0002

_VK_KEY_MAP = {
    VK_VOLUME_UP: _Key.media_volume_up,
    VK_VOLUME_DOWN: _Key.media_volume_down,
    VK_MEDIA_PLAY_PAUSE: _Key.media_play_pause,
}

IS_WINDOWS = os.name == "nt"


class MediaCtl:
    """Teclas multimidia globais via keybd_event (Windows) ou pynput (Linux/macOS).

    dry_run=True nao envia teclas (para testes).
    """

    def __init__(self, dry_run=False):
        self.dry_run = bool(dry_run)
        self.sent = []

    def _press(self, vk):
        if self.dry_run:
            self.sent.append(vk)
            return
        if IS_WINDOWS:
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk, 0, _KEYEVENTF_KEYUP, 0)
            return
        pynput_key = _VK_KEY_MAP.get(vk)
        if pynput_key is None:
            return
        try:
            kb = _KBController()
            kb.press(pynput_key)
            kb.release(pynput_key)
        except Exception:
            pass

    def volume(self, steps):
        steps = max(-20, min(20, int(steps)))
        vk = VK_VOLUME_UP if steps > 0 else VK_VOLUME_DOWN
        for _ in range(abs(steps)):
            self._press(vk)
        return steps

    def play_pause(self):
        self._press(VK_MEDIA_PLAY_PAUSE)
