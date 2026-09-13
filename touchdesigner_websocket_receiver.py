"""TouchDesigner WebSocket receiver template.

Use this as a Text DAT or as the contents of a WebSocket DAT callbacks DAT.
It expects plain text messages coming from test.html, for example:
- cue:intro
- brightness:0.72
- speed:1.25
- color:#00d4ff
- strobe:1
- mode:glitch

Setup idea in TouchDesigner:
1. Create a WebSocket DAT and set it to listen on port 9980.
2. Point its Callbacks DAT to a Text DAT containing this code.
3. Replace the example operator paths in ROUTES with your own network.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Tuple


# Update these paths to match your TouchDesigner network.
# Each entry maps an incoming key to a target operator and a parser.
ROUTES = {
    "brightness": ("controls", "brightness", float),
    "speed": ("controls", "speed", float),
    "scale": ("controls", "scale", float),
    "crossfade": ("controls", "crossfade", float),
    "bpm": ("controls", "bpm", int),
    "scene": ("controls", "scene", str),
    "mode": ("controls", "mode", str),
    "strobe": ("controls", "strobe", lambda v: int(str(v).strip() in ("1", "true", "True", "on", "yes"))),
    "color": ("controls", "color", str),
}


def onConnect(dat: Any) -> None:
    debug("WebSocket connected")


def onDisconnect(dat: Any) -> None:
    debug("WebSocket disconnected")


def onReceiveText(dat: Any, rowIndex: int, message: str) -> None:
    raw = (message or "").strip()
    if not raw:
        return

    key, value = parse_message(raw)
    if key is None:
        debug(f"Ignored message: {raw}")
        return

    handle_message(key, value, raw)


def parse_message(message: str) -> Tuple[Optional[str], Optional[str]]:
    if ":" not in message:
        return message.strip(), None

    key, value = message.split(":", 1)
    return key.strip(), value.strip()


def handle_message(key: str, value: Optional[str], raw: str) -> None:
    if key == "cue":
        handle_cue(value)
        return

    route = ROUTES.get(key)
    if route is None:
        debug(f"No route for {raw}")
        return

    op_path, par_name, parser = route
    op_target = op(op_path)
    if op_target is None:
        debug(f"Missing operator: {op_path}")
        return

    parsed_value = value
    if value is not None:
        try:
            parsed_value = parser(value)
        except Exception as err:
            debug(f"Parse failed for {key}:{value} -> {err}")
            return

    apply_value(op_target, par_name, parsed_value)


def handle_cue(value: Optional[str]) -> None:
    if value is None:
        debug("Cue message missing value")
        return

    trigger = op("controls")
    if trigger is None:
        debug(f"Cue received: {value}")
        return

    # Replace this with your actual trigger parameter name.
    if hasattr(trigger.par, "cue"):
        trigger.par.cue.pulse()
    elif hasattr(trigger.par, "trigger"):
        trigger.par.trigger.pulse()
    else:
        debug(f"Cue received: {value}")


def apply_value(target: Any, par_name: str, value: Any) -> None:
    if value is None:
        return

    if par_name == "color":
        r, g, b = parse_hex_color(str(value))
        set_parameter(target, "colorr", r)
        set_parameter(target, "colorg", g)
        set_parameter(target, "colorb", b)
        return

    set_parameter(target, par_name, value)


def set_parameter(target: Any, par_name: str, value: Any) -> None:
    if not hasattr(target, "par"):
        debug(f"Target has no parameters: {target}")
        return

    parameter = getattr(target.par, par_name, None)
    if parameter is None:
        debug(f"Missing parameter {par_name} on {target}")
        return

    parameter.val = value
    debug(f"Set {target.path}.{par_name} = {value}")


def parse_hex_color(value: str) -> Tuple[float, float, float]:
    text = value.strip().lstrip("#")
    if len(text) != 6:
        raise ValueError(f"Expected 6-digit hex color, got {value!r}")

    red = int(text[0:2], 16) / 255.0
    green = int(text[2:4], 16) / 255.0
    blue = int(text[4:6], 16) / 255.0
    return red, green, blue


def debug(message: str) -> None:
    print(f"[TD WebSocket] {message}")
