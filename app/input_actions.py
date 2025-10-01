from __future__ import annotations

import time
from typing import Iterable, Literal

import pyautogui

from .coordinates import Point

pyautogui.FAILSAFE = False


def click(point: Point, button: Literal["left", "right"] = "left", delay: float = 0.05) -> None:
    pyautogui.moveTo(point.x, point.y)
    pyautogui.click(button=button)
    if delay:
        time.sleep(delay)


def perform_actions(actions: Iterable[dict], speed: float = 1.0) -> None:
    start = time.time()
    for action in actions:
        action_type = action.get("type")
        timestamp = action.get("time", 0.0)
        wait = max((timestamp - (time.time() - start)) / speed, 0.0)
        if wait:
            time.sleep(wait)
        if action_type == "click":
            button = action.get("button", "left")
            pos = action.get("position", {"x": 0, "y": 0})
            pyautogui.moveTo(pos.get("x", 0), pos.get("y", 0))
            if action.get("pressed", False):
                pyautogui.mouseDown(button=button)
            else:
                pyautogui.mouseUp(button=button)
        elif action_type == "move":
            pos = action.get("position", {"x": 0, "y": 0})
            pyautogui.moveTo(pos.get("x", 0), pos.get("y", 0))
        elif action_type == "keyDown":
            pyautogui.keyDown(action.get("key"))
        elif action_type == "keyUp":
            pyautogui.keyUp(action.get("key"))
        elif action_type == "press":
            pyautogui.press(action.get("key"))
        time.sleep(action.get("post_delay", 0.0))
