"""TouchDesigner Web Server DAT router for messages in type:name:value format.

Bidirectional behavior:
- Browser -> TD via onWebSocketReceiveText
- TD -> Browser via push_parameter_change (called from Parameter Execute DAT)

Examples:
- slider:speed:0.5000
- toggle:showGrid:1
- button:reset:1
- color:color:0.3569,0.6941,0.7608,0.5373
- text:title:My cool project
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple


Handler = Callable[[str, str], None]

ENABLE_DEBUG = True
ECHO_RX_TO_SENDER = False
OPTIONAL_PARAMS = {"mouseposition", "keycapture"}
DEBUG_DAT_NAME = "router_debug"

CONNECTED_CLIENTS: List[Any] = []
LAST_WEBSERVER_DAT: Optional[Any] = None

print("[TD Router] Module loaded. If you do not see runtime logs, verify this DAT is assigned as Web Server DAT callbacks.")


def debug(message: str) -> None:
    if ENABLE_DEBUG:
        line = "[TD Router] " + str(message)
        print(line)

        # Optional in-network debug sink for quick visibility without Textport.
        debug_dat = op(DEBUG_DAT_NAME)
        if debug_dat is not None and hasattr(debug_dat, "text"):
            existing = debug_dat.text or ""
            debug_dat.text = (existing + "\n" + line).strip()


def _remember_server(webServerDAT: Any) -> None:
    global LAST_WEBSERVER_DAT
    LAST_WEBSERVER_DAT = webServerDAT


def _add_client(client: Any) -> None:
    if client not in CONNECTED_CLIENTS:
        CONNECTED_CLIENTS.append(client)


def _remove_client(client: Any) -> None:
    if client in CONNECTED_CLIENTS:
        CONNECTED_CLIENTS.remove(client)


def _debug_clients(prefix: str) -> None:
    ids = []
    for client in CONNECTED_CLIENTS:
        cid = getattr(client, "id", None)
        if cid is None:
            cid = str(client)
        ids.append(str(cid))
    debug(prefix + " | clients=" + str(len(CONNECTED_CLIENTS)) + " " + str(ids))


# ---------------------------
# Web Server DAT callbacks
# ---------------------------

def onHTTPRequest(webServerDAT: Any, request: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
    _remember_server(webServerDAT)
    response["statusCode"] = 200
    response["statusReason"] = "OK"
    response["data"] = "<b>TouchDesigner: </b>" + webServerDAT.name
    debug("HTTP request received from " + str(request.get("clientAddress", "")))
    return response


def onWebSocketOpen(webServerDAT: Any, client: Any, uri: str) -> None:
    _remember_server(webServerDAT)
    _add_client(client)
    debug("WebSocket opened: " + str(uri))
    _debug_clients("after open")
    return


def onWebSocketClose(webServerDAT: Any, client: Any) -> None:
    _remember_server(webServerDAT)
    _remove_client(client)
    debug("WebSocket closed")
    _debug_clients("after close")
    return


def onWebSocketReceiveText(webServerDAT: Any, client: Any, data: str) -> None:
    _remember_server(webServerDAT)

    raw = (data or "").strip()
    if not raw:
        return

    debug("RX text: " + raw)
    mirror_message(raw)

    msg_type, name, value = parse_segments(raw)
    if msg_type is None:
        debug("Invalid message format: " + raw)
        return

    handler = ROUTERS.get(msg_type)
    if handler is None:
        debug("Unknown message type: " + msg_type)
        return

    debug("Dispatching RX -> type=" + msg_type + ", name=" + name + ", value=" + value)
    handler(name, value)

    if ECHO_RX_TO_SENDER:
        try:
            webServerDAT.webSocketSendText(client, raw)
            debug("Echoed RX back to sender")
        except Exception as err:
            debug("Echo failed: " + str(err))

    return


def onWebSocketReceiveBinary(webServerDAT: Any, client: Any, data: bytes) -> None:
    _remember_server(webServerDAT)
    try:
        webServerDAT.webSocketSendBinary(client, data)
        debug("RX binary -> echoed binary")
    except Exception as err:
        debug("Binary echo failed: " + str(err))
    return


def onWebSocketReceivePing(webServerDAT: Any, client: Any, data: bytes) -> None:
    _remember_server(webServerDAT)
    try:
        webServerDAT.webSocketSendPong(client, data=data)
        debug("RX ping -> sent pong")
    except Exception as err:
        debug("Pong send failed: " + str(err))
    return


def onWebSocketReceivePong(webServerDAT: Any, client: Any, data: bytes) -> None:
    _remember_server(webServerDAT)
    debug("RX pong")
    return


def onServerStart(webServerDAT: Any) -> None:
    _remember_server(webServerDAT)
    debug("Server started: " + webServerDAT.name)
    debug("Debug sink DAT: create a Text DAT named '" + DEBUG_DAT_NAME + "' to see logs in-network.")
    debug_dump_controls_parameters()
    return


def onServerStop(webServerDAT: Any) -> None:
    _remember_server(webServerDAT)
    CONNECTED_CLIENTS[:] = []
    debug("Server stopped")
    return


# ---------------------------
# Incoming message routing (browser -> TD)
# ---------------------------

def parse_segments(raw: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    parts = raw.split(":", 2)
    if len(parts) != 3:
        return None, None, None

    msg_type = parts[0].strip().lower()
    name = parts[1].strip()
    value = parts[2].strip()

    if not msg_type or not name:
        return None, None, None

    return msg_type, name, value


def handle_slider(name: str, value: str) -> None:
    try:
        numeric = float(value)
    except ValueError:
        debug("slider parse error for " + name + ": " + value)
        return

    set_parameter("controls", name, numeric)


def handle_toggle(name: str, value: str) -> None:
    enabled = str(value).strip().lower() in ("1", "true", "on", "yes")
    set_parameter("controls", name, 1 if enabled else 0)


def handle_button(name: str, value: str) -> None:
    pressed = str(value).strip().lower() in ("1", "true", "on", "yes")
    target = op("controls")
    if target is None:
        debug("Missing operator: controls for button " + name)
        return

    parameter = find_parameter(target, name)
    if parameter is None:
        debug("Missing button parameter controls." + name)
        return

    try:
        parameter.val = 1 if pressed else 0
        state = "pressed" if pressed else "released"
        debug("Button " + state + ": " + str(parameter.name))
    except Exception:
        if hasattr(parameter, "pulse"):
            if pressed:
                parameter.pulse()
                debug("Button pressed (pulse): " + str(parameter.name))
            else:
                debug("Button released (pulse ignored): " + str(parameter.name))
        else:
            debug("Unable to set button parameter controls." + name)


def handle_color(name: str, value: str) -> None:
    try:
        red, green, blue, alpha = parse_rgba(value)
    except ValueError as err:
        debug("color parse error for " + name + ": " + str(err))
        return

    target = op("controls")
    if target is None:
        debug("Missing operator: controls")
        return

    # Always route incoming color payloads to the "color" parameter family.
    if not write_color_rgba(target, red, green, blue, alpha):
        debug("No writable color parameters found on controls")


def handle_text(name: str, value: str) -> None:
    set_parameter("controls", name, value)


def parse_rgba(value: str) -> Tuple[float, float, float, float]:
    pieces = [part.strip() for part in str(value).split(",")]
    if len(pieces) not in (3, 4):
        raise ValueError("expected r,g,b or r,g,b,a")

    red = float(pieces[0])
    green = float(pieces[1])
    blue = float(pieces[2])
    alpha = float(pieces[3]) if len(pieces) == 4 else 1.0

    for channel in (red, green, blue, alpha):
        if channel < 0 or channel > 1:
            raise ValueError("channels must be 0-1")

    return red, green, blue, alpha


# ---------------------------
# TD -> browser broadcasting
# ---------------------------

def broadcast_segment(msg_type: str, name: str, value: Any, webServerDAT: Any = None) -> None:
    server = webServerDAT if webServerDAT is not None else LAST_WEBSERVER_DAT
    if server is None:
        debug("broadcast_segment skipped: no Web Server DAT")
        return

    message = str(msg_type) + ":" + str(name) + ":" + str(value)
    if not CONNECTED_CLIENTS:
        debug("broadcast_segment skipped: no connected clients | " + message)
        return

    dead = []
    success = 0

    for client in CONNECTED_CLIENTS:
        try:
            server.webSocketSendText(client, message)
            success += 1
        except Exception as err:
            debug("broadcast failed for client: " + str(err))
            dead.append(client)

    for client in dead:
        _remove_client(client)

    debug("TX broadcast (" + str(success) + "/" + str(len(CONNECTED_CLIENTS) + len(dead)) + "): " + message)


def push_parameter_change(par: Any, prev: Any = None, webServerDAT: Any = None) -> None:
    # Call this from Parameter Execute DAT onValueChange.
    if par is None:
        debug("push_parameter_change skipped: par is None")
        return

    owner = getattr(par, "owner", None)
    if owner is None:
        debug("push_parameter_change skipped: par has no owner")
        return

    if str(owner.name).lower() != "controls":
        return

    name = str(par.name)
    lname = name.lower()
    tname = str(getattr(par, "tupletName", "")).lower()

    debug("Param changed: name=" + name + ", tuplet=" + tname + ", value=" + str(par.eval()))

    # Color tuple or any of its channels changed.
    if tname.startswith("color") or lname in COLOR_CHANNEL_NAMES:
        r, g, b, a = read_color_rgba(owner)
        payload = "{:.4f},{:.4f},{:.4f},{:.4f}".format(r, g, b, a)
        broadcast_segment("color", "color", payload, webServerDAT)
        return

    if lname in ("showgrid", "mouseposition", "keycapture"):
        val = "1" if float(par.eval()) > 0.5 else "0"
        broadcast_segment("toggle", lname, val, webServerDAT)
        return

    if lname in ("mode", "scenepreset", "title"):
        broadcast_segment("text", lname, str(par.eval()), webServerDAT)
        return

    if lname in BUTTON_PARAM_NAMES:
        val = "1" if float(par.eval()) > 0.5 else "0"
        broadcast_segment("button", lname, val, webServerDAT)
        return

    try:
        val = format_numeric_for_wire(par.eval())
        broadcast_segment("slider", lname, val, webServerDAT)
    except Exception as err:
        debug("Unhandled parameter type for " + lname + " | err=" + str(err))


def push_parameter_pulse(par: Any, webServerDAT: Any = None) -> None:
    # Call this from Parameter Execute DAT onPulse.
    if par is None:
        debug("push_parameter_pulse skipped: par is None")
        return

    owner = getattr(par, "owner", None)
    if owner is None:
        debug("push_parameter_pulse skipped: par has no owner")
        return

    if str(owner.name).lower() != "controls":
        return

    lname = str(par.name).lower()
    if lname not in BUTTON_PARAM_NAMES:
        return

    debug("Param pulse: name=" + str(par.name))
    # Pulse buttons are momentary; emit press then release.
    broadcast_segment("button", lname, "1", webServerDAT)
    broadcast_segment("button", lname, "0", webServerDAT)


# ---------------------------
# Parameter helpers
# ---------------------------

def find_parameter(target: Any, par_name: str) -> Any:
    parameter = getattr(target.par, par_name, None)
    if parameter is not None:
        return parameter

    requested = str(par_name).lower()
    for candidate in target.pars():
        if str(candidate.name).lower() == requested:
            return candidate

    return None


def set_parameter(op_path: str, par_name: str, value: Any) -> None:
    target = op(op_path)
    if target is None:
        debug("Missing operator: " + op_path)
        return

    parameter = find_parameter(target, par_name)
    if parameter is None:
        if str(par_name).lower() not in OPTIONAL_PARAMS:
            debug("Missing parameter " + op_path + "." + str(par_name))
        return

    try:
        parameter.val = value
        debug("Set " + op_path + "." + str(parameter.name) + " = " + str(value))
    except Exception as err:
        debug("Failed setting " + op_path + "." + str(parameter.name) + " | err=" + str(err))


def set_if_exists(target: Any, par_name: str, value: Any) -> bool:
    parameter = find_parameter(target, par_name)
    if parameter is None:
        return False

    try:
        parameter.val = value
        debug("Set " + str(target.path) + "." + str(parameter.name) + " = " + str(value))
        return True
    except Exception as err:
        debug("Failed setting " + str(target.path) + "." + str(parameter.name) + " | err=" + str(err))
        return False


def find_parameter_tuple_members(target: Any, par_name: str) -> List[Any]:
    requested = str(par_name).lower()
    matches = []
    numbered = {}

    for candidate in target.pars():
        tuple_name = getattr(candidate, "tupletName", None)
        if tuple_name is not None and str(tuple_name).lower() == requested:
            matches.append(candidate)

        cname = str(getattr(candidate, "name", "")).lower()
        if cname.startswith(requested):
            suffix = cname[len(requested):]
            if suffix.isdigit():
                numbered[int(suffix)] = candidate

    if matches:
        return matches

    if numbered:
        return [numbered[i] for i in sorted(numbered.keys())]

    return []


def set_color_tuple(target: Any, par_name: str, red: float, green: float, blue: float, alpha: float) -> bool:
    tuple_pars = find_parameter_tuple_members(target, par_name)
    if not tuple_pars:
        tuple_pars = find_parameter_tuple_members(target, par_name + "color")

    if not tuple_pars:
        return False

    values = [red, green, blue, alpha]
    tuple_values = values[:len(tuple_pars)]

    try:
        for parameter, value in zip(tuple_pars, tuple_values):
            parameter.val = value
    except Exception as err:
        tuple_name = getattr(tuple_pars[0], "tupletName", getattr(tuple_pars[0], "name", par_name))
        debug("Unable to set color tuple " + str(tuple_name) + " | err=" + str(err))
        return False

    if len(tuple_pars) == 3:
        set_if_exists(target, "alpha", alpha)

    tuple_name = getattr(tuple_pars[0], "tupletName", getattr(tuple_pars[0], "name", par_name))
    debug("Set " + str(target.path) + "." + str(tuple_name) + " = " + str(tuple_values))
    return True


def _safe_eval(owner_comp: Any, par_name: str, default_value: float) -> float:
    p = find_parameter(owner_comp, par_name)
    if p is None:
        return float(default_value)
    try:
        return float(p.eval())
    except Exception:
        return float(default_value)


def _safe_eval_any(owner_comp: Any, par_names: List[str], default_value: float) -> float:
    for par_name in par_names:
        p = find_parameter(owner_comp, par_name)
        if p is None:
            continue
        try:
            return float(p.eval())
        except Exception:
            continue
    return float(default_value)


def format_numeric_for_wire(value: Any) -> str:
    try:
        numeric = float(value)
    except Exception:
        return str(value)

    text = "{:.4f}".format(numeric).rstrip("0").rstrip(".")
    return text if text else "0"


def read_color_rgba(owner_comp: Any) -> Tuple[float, float, float, float]:
    tuple_pars = find_parameter_tuple_members(owner_comp, "color")

    if tuple_pars and len(tuple_pars) >= 3:
        values = []
        for p in tuple_pars[:4]:
            try:
                values.append(float(p.eval()))
            except Exception:
                values.append(0.0)

        if len(values) < 4:
            values.append(_safe_eval_any(owner_comp, ["alpha"], 1.0))

        return values[0], values[1], values[2], values[3]

    red = _safe_eval_any(owner_comp, ["color1", "colorr", "red"], 0.0)
    green = _safe_eval_any(owner_comp, ["color2", "colorg", "green"], 0.0)
    blue = _safe_eval_any(owner_comp, ["color3", "colorb", "blue"], 0.0)
    alpha = _safe_eval_any(owner_comp, ["alpha", "color4"], 1.0)
    return red, green, blue, alpha


def write_color_rgba(target: Any, red: float, green: float, blue: float, alpha: float) -> bool:
    if set_color_tuple(target, "color", red, green, blue, alpha):
        return True

    wrote_rgb = False
    wrote_rgb = set_if_exists(target, "color1", red) or wrote_rgb
    wrote_rgb = set_if_exists(target, "color2", green) or wrote_rgb
    wrote_rgb = set_if_exists(target, "color3", blue) or wrote_rgb

    wrote_rgb = set_if_exists(target, "colorr", red) or wrote_rgb
    wrote_rgb = set_if_exists(target, "colorg", green) or wrote_rgb
    wrote_rgb = set_if_exists(target, "colorb", blue) or wrote_rgb

    wrote_rgb = set_if_exists(target, "red", red) or wrote_rgb
    wrote_rgb = set_if_exists(target, "green", green) or wrote_rgb
    wrote_rgb = set_if_exists(target, "blue", blue) or wrote_rgb

    wrote_alpha = False
    wrote_alpha = set_if_exists(target, "color4", alpha) or wrote_alpha
    wrote_alpha = set_if_exists(target, "alpha", alpha) or wrote_alpha

    return wrote_rgb or wrote_alpha


# ---------------------------
# Misc helpers
# ---------------------------

def mirror_message(value: str) -> None:
    text_dat = op("text1")
    if text_dat is not None and hasattr(text_dat, "text"):
        text_dat.text = value


def debug_dump_controls_parameters() -> None:
    controls = op("controls")
    if controls is None:
        debug("controls not found for parameter dump")
        return

    debug("Controls parameter dump start")
    for p in controls.pars():
        pname = str(getattr(p, "name", ""))
        tname = str(getattr(p, "tupletName", ""))
        debug("  par=" + pname + " | tuplet=" + tname)
    debug("Controls parameter dump end")


ROUTERS: Dict[str, Handler] = {
    "slider": handle_slider,
    "toggle": handle_toggle,
    "button": handle_button,
    "color": handle_color,
    "text": handle_text,
}


COLOR_CHANNEL_NAMES = {
    "color",
    "color1",
    "color2",
    "color3",
    "color4",
    "colorr",
    "colorg",
    "colorb",
    "red",
    "green",
    "blue",
    "alpha",
}


BUTTON_PARAM_NAMES = {
    "reset",
    "intro",
    "drop",
    "blackout",
    "flash",
}
