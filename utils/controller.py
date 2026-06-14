import pygame as pg
from pygame.math import Vector2


def _detect_type(joy):
    n = joy.get_name().lower()
    if any(t in n for t in ("playstation", "dualshock", "dualsense", "ps4", "ps5", "sony", "dual sense", "dual shock")):
        return "ps"
    if any(t in n for t in ("xbox", "xinput", "microsoft", "x-box")):
        return "xbox"
    return "generic"


def _axis(joy, i, default=0.0):
    return joy.get_axis(i) if joy.get_numaxes() > i else default


def _btn(joy, i):
    return bool(joy.get_button(i)) if joy.get_numbuttons() > i else False


class Controller:
    axesL     = Vector2(0, 0)
    axesT     = 0.0
    mouse_aim = None   # Vector2 direction toward cursor; set by main.py each frame
    buttons   = {
        "A": False, "B": False, "X": False, "Y": False,
        "R1": False, "L1": False, "SH": False, "OP": False,
        "DPAD_UP": False, "DPAD_DOWN": False,
        "DPAD_LEFT": False, "DPAD_RIGHT": False,
    }

    @staticmethod
    def reset():
        Controller.axesL     = Vector2(0, 0)
        Controller.axesT     = 0.0
        Controller.mouse_aim = None
        Controller.buttons   = {k: False for k in Controller.buttons}

    # ── keyboard + mouse ─────────────────────────────────────────────────────
    # Controls:
    #   W / Up             — thrust forward
    #   S / Down           — brake
    #   Mouse move         — aim (ship faces cursor)
    #   LMB / Space        — fire
    #   RMB / F            — cycle target lock
    #   Tab                — cycle weapon
    #   = / +              — zoom in
    #   -                  — zoom out
    #   Enter              — confirm (menus)
    #   Escape             — back / cancel
    #   A / ← , D / →     — menu / settings navigation (DPAD_LEFT / RIGHT)
    @staticmethod
    def update(key):
        k  = key.get_pressed()
        mb = pg.mouse.get_pressed()

        # Thrust from W/S or Up/Down — direction comes from mouse_aim (set in main.py)
        if k[pg.K_w] or k[pg.K_UP]:
            Controller.axesT = 1.0
        elif k[pg.K_s] or k[pg.K_DOWN]:
            Controller.axesT = -1.0
        else:
            Controller.axesT = 0.0
        Controller.axesL = Vector2(0, 0)

        Controller.buttons["A"]  = bool(k[pg.K_RETURN])
        Controller.buttons["B"]  = bool(k[pg.K_ESCAPE])
        Controller.buttons["X"]  = bool(mb[0]) or bool(k[pg.K_SPACE])  # fire: LMB or Space
        Controller.buttons["Y"]  = False
        Controller.buttons["R1"] = bool(k[pg.K_TAB])                    # weapon cycle
        Controller.buttons["L1"] = bool(mb[2]) or bool(k[pg.K_f])      # target: RMB or F
        Controller.buttons["SH"] = False
        Controller.buttons["OP"] = False
        Controller.buttons["DPAD_UP"]    = bool(k[pg.K_EQUALS] or k[pg.K_KP_PLUS])
        Controller.buttons["DPAD_DOWN"]  = bool(k[pg.K_MINUS]  or k[pg.K_KP_MINUS])
        Controller.buttons["DPAD_LEFT"]  = bool(k[pg.K_LEFT]   or k[pg.K_a])
        Controller.buttons["DPAD_RIGHT"] = bool(k[pg.K_RIGHT]  or k[pg.K_d])

    # ── joystick (PS4 / PS5 / Xbox One / Xbox 360 / generic) ─────────────────
    # Axis layout (same for PS and Xbox via SDL2):
    #   0/1  left stick X/Y      3/4  right stick X/Y
    #   2    L2 / LT trigger     5    R2 / RT trigger
    #
    # Triggers: rest at −1 (PS) or 0 (some Xbox drivers), full press = +1.
    # max(0, axis) normalises both cases to 0..1.
    #
    # Face buttons (SDL2 raw joystick, same indices for both brands):
    #   0  A / Cross    1  B / Circle   2  X / Square   3  Y / Triangle
    #   4  LB / L1      5  RB / R1
    # Menu buttons differ:
    #   Xbox:  6 Back/View,  7 Start/Menu
    #   PS:    8 Share/Create, 9 Options
    @staticmethod
    def update_joysticks(joy):
        ctype = _detect_type(joy)

        # Left stick with deadzone
        raw = Vector2(_axis(joy, 0), _axis(joy, 1))
        Controller.axesL = raw.normalize() if raw.magnitude() > 0.15 else Vector2(0, 0)

        # Triggers → throttle  (max(0,…) clamps rest-at-−1 to 0, keeps rest-at-0)
        rt = max(0.0, _axis(joy, 5))
        lt = max(0.0, _axis(joy, 2))
        Controller.axesT = rt - lt

        # Face buttons (identical mapping for PS and Xbox)
        Controller.buttons["A"]  = _btn(joy, 0)   # A / Cross
        Controller.buttons["B"]  = _btn(joy, 1)   # B / Circle
        Controller.buttons["X"]  = _btn(joy, 2)   # X / Square  (fire)
        Controller.buttons["Y"]  = _btn(joy, 3)   # Y / Triangle
        Controller.buttons["L1"] = _btn(joy, 4)
        Controller.buttons["R1"] = _btn(joy, 5)

        # Menu / share buttons differ between brands
        if ctype == "ps":
            Controller.buttons["SH"] = _btn(joy, 8)   # Share / Create
            Controller.buttons["OP"] = _btn(joy, 9)   # Options
        else:
            Controller.buttons["SH"] = _btn(joy, 6)   # Back / View
            Controller.buttons["OP"] = _btn(joy, 7)   # Start / Menu

        # D-pad — prefer hat; fall back to PS button layout (some older drivers)
        if joy.get_numhats() > 0:
            hx, hy = joy.get_hat(0)
            Controller.buttons["DPAD_UP"]    = hy == 1
            Controller.buttons["DPAD_DOWN"]  = hy == -1
            Controller.buttons["DPAD_LEFT"]  = hx == -1
            Controller.buttons["DPAD_RIGHT"] = hx == 1
        elif ctype == "ps":
            # Raw PS4/PS5 d-pad as buttons when not in hat mode
            Controller.buttons["DPAD_UP"]    = _btn(joy, 11)
            Controller.buttons["DPAD_DOWN"]  = _btn(joy, 12)
            Controller.buttons["DPAD_LEFT"]  = _btn(joy, 13)
            Controller.buttons["DPAD_RIGHT"] = _btn(joy, 14)
