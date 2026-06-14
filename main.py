#! /bin/env python3
from random import randint
import math
import os
import pickle
import pathlib
import pygame as pg
import sys
import time
import random as _rnd
from pygame.math import Vector2

import utils
from utils.gamedata import GameData, PLAYER_SHIPS, _SHIP_STAT_MAX
from utils.controller import Controller
from utils.sounds import Sounds

# ── constants ────────────────────────────────────────────────────────────────
GRACE_DURATION = 5.0
SCORES_FILE    = pathlib.Path(__file__).parent / "scores.pkl"
SETTINGS_FILE  = pathlib.Path(__file__).parent / "settings.pkl"
ZOOM_MIN, ZOOM_MAX, ZOOM_SPEED = 0.35, 2.5, 1.2

# Available TTF/OTF fonts found in Assets/ — SDL_ttf (and so pygame) loads both
FONT_OPTIONS = sorted([
    f for f in os.listdir("Assets") if f.lower().endswith((".ttf", ".otf"))
]) if pathlib.Path("Assets").exists() else []

# ── pygame init ───────────────────────────────────────────────────────────────
pg.mixer.pre_init(22050, -16, 2, 512)
pg.init()
pg.joystick.init()

joysticks = []
screen = pg.display.set_mode((1920, 1080), pg.FULLSCREEN)
buffer = pg.Surface((800, 450))

delta = 1 / 60
clock = pg.time.Clock()

# ── settings load ─────────────────────────────────────────────────────────────
def load_settings():
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "rb") as f:
                return pickle.load(f)
        except Exception:
            return {}
    return {}

def save_settings():
    with open(SETTINGS_FILE, "wb") as f:
        pickle.dump({"font_file": GameData.font_file,
                     "ship_sel": ship_sel}, f)

_cfg = load_settings()
if FONT_OPTIONS:
    saved = _cfg.get("font_file", FONT_OPTIONS[0])
    GameData.font_file = saved if saved in FONT_OPTIONS else FONT_OPTIONS[0]

# ── score helpers ─────────────────────────────────────────────────────────────
def load_scores():
    if SCORES_FILE.exists():
        try:
            with open(SCORES_FILE, "rb") as f:
                return pickle.load(f)
        except Exception:
            return []
    return []

def save_score(t, kills):
    scores = load_scores()
    entry  = {"time": t, "kills": kills}
    scores.append(entry)
    scores.sort(key=lambda s: s["time"], reverse=True)
    scores = scores[:10]
    with open(SCORES_FILE, "wb") as f:
        pickle.dump(scores, f)
    rank = next((i for i, s in enumerate(scores)
                 if s["time"] == t and s["kills"] == kills), -1)
    return rank   # 0 = new best

_ship_preview_cache = {}

# ── static backdrop stars for menus ──────────────────────────────────────────
_menu_stars = [(_rnd.randint(0, 799), _rnd.randint(0, 449),
                _rnd.randint(30, 90)) for _ in range(120)]

def _draw_backdrop():
    buffer.fill((0, 0, 0))
    for x, y, b in _menu_stars:
        pg.draw.rect(buffer, (b, b, b), (x, y, 1, 1))

# ── game objects (initialised / reset by reset_game) ─────────────────────────
player = None
camera = None

def reset_game():
    global player, camera, _prev_tick, dying, death_timer
    _prev_tick = -1
    dying = False
    death_timer = 0.0

    # Apply selected ship stats
    _, asset, maxHP, maxSP, maxvel, acc, hr, _ = PLAYER_SHIPS[ship_sel]
    GameData.current_ship = asset
    GameData.maxHP = maxHP;  GameData.curHP = maxHP
    GameData.maxSP = maxSP;  GameData.curSP = maxSP

    utils.Ship.objects.clear()
    utils.Derilict.objects.clear()
    utils.Torpedo.torpedoes.clear()
    utils.Explosion.objects.clear()
    GameData.kills   = 0
    GameData.time    = 0.0

    player = utils.Player(asset, maxvel=maxvel, acc=acc, hit_radius=hr)
    camera = utils.Camera(Vector2(0, 0), buffer, player)
    utils.Ship.player      = player
    utils.Torpedo.ships    = utils.Ship.objects
    utils.Torpedo.players  = [player]

    utils.Derilict(Vector2(randint(-1000, 1000), randint(-1000, 1000)), "Debris2")
    utils.Derilict(Vector2(randint(-1000, 1000), randint(-1000, 1000)), "Debris1")

def spawn_wave():
    t      = GameData.time
    spread = 1400
    counts = {
        "ViperEnemy":    min(2 + int((t - GRACE_DURATION) / 25), 6),
        "MaulerEnemy":   min(max(0, int((t - 30)  / 25)), 3),
        "PhantomEnemy":  min(max(0, int((t - 60)  / 30)), 3),
        "SwarmDrone":    (6 if t >= 90 else 0),
        "SentinelEnemy": min(max(0, int((t - 120) / 45)), 2),
        "WardenEnemy":   min(max(0, int((t - 180) / 60)), 2),
        "MarauderEnemy": min(max(0, int((t - 240) / 60)), 2),
    }
    for ship_type, count in counts.items():
        for _ in range(count):
            utils.Ship(Vector2(randint(-spread, spread),
                               randint(-spread, spread)), ship_type)

# ── state machine ─────────────────────────────────────────────────────────────
state        = "menu"
menu_sel     = 0
ship_sel     = _cfg.get("ship_sel", 0)
if not (0 <= ship_sel < len(PLAYER_SHIPS)):
    ship_sel = 0
GameData.current_ship = PLAYER_SHIPS[ship_sel][0]
gameover_sel = 0
pause_sel    = 0
last_rank    = -1   # rank of last run's score (0 = new best)
dying        = False
death_timer  = 0.0
DEATH_DELAY  = 0.8  # seconds the death explosion plays before cutting to game over
_prev_tick   = -1   # last grace-countdown integer shown (for tick sound)

# edge-detect helpers for menu navigation
_prev_up = _prev_dn = _prev_ok = _prev_lt = _prev_rt = _prev_bk = False

def _nav_inputs():
    """Return (up_e, dn_e, ok_e, lt_e, rt_e, bk_e) edge-detected nav inputs."""
    keys = pg.key.get_pressed()
    up  = keys[pg.K_UP]     or keys[pg.K_w]                     or Controller.buttons["DPAD_UP"]
    dn  = keys[pg.K_DOWN]   or keys[pg.K_s]                     or Controller.buttons["DPAD_DOWN"]
    ok  = keys[pg.K_RETURN] or keys[pg.K_KP_ENTER] or keys[pg.K_SPACE] \
          or Controller.buttons["A"] or Controller.buttons["X"]
    lt  = keys[pg.K_LEFT]   or keys[pg.K_a]                     or Controller.buttons["DPAD_LEFT"]
    rt  = keys[pg.K_RIGHT]  or keys[pg.K_d]                     or Controller.buttons["DPAD_RIGHT"]
    bk  = keys[pg.K_ESCAPE]                                      or Controller.buttons["B"]
    global _prev_up, _prev_dn, _prev_ok, _prev_lt, _prev_rt, _prev_bk
    up_e = up and not _prev_up
    dn_e = dn and not _prev_dn
    ok_e = ok and not _prev_ok
    lt_e = lt and not _prev_lt
    rt_e = rt and not _prev_rt
    bk_e = bk and not _prev_bk
    _prev_up, _prev_dn, _prev_ok = up, dn, ok
    _prev_lt, _prev_rt, _prev_bk = lt, rt, bk
    return up_e, dn_e, ok_e, lt_e, rt_e, bk_e

# ── draw helpers ──────────────────────────────────────────────────────────────
_MENU_ITEMS     = ("START", "SETTINGS", "QUIT")
_PAUSE_ITEMS    = ("RESUME", "MAIN MENU", "QUIT")
_GAMEOVER_ITEMS = ("RETRY", "MAIN MENU", "QUIT")

def draw_menu():
    _draw_backdrop()
    s = utils.Ui.font(25).render("negativeSpace", False, (180, 210, 255))
    buffer.blit(s, s.get_rect(center=(400, 120)))
    s = utils.Ui.font(10).render("survive as long as you can", False, (80, 110, 140))
    buffer.blit(s, s.get_rect(center=(400, 150)))

    scores = load_scores()
    if scores:
        best = scores[0]
        bm, bs = int(best["time"]) // 60, int(best["time"]) % 60
        s = utils.Ui.font(10).render(
            f"best  {bm:02d}:{bs:02d}   {best['kills']} kills",
            False, (100, 160, 200))
        buffer.blit(s, s.get_rect(center=(400, 168)))

    for i, label in enumerate(_MENU_ITEMS):
        col = (255, 220, 60) if i == menu_sel else (140, 160, 180)
        pre = ">  " if i == menu_sel else "   "
        s = utils.Ui.font(15).render(pre + label, False, col)
        buffer.blit(s, s.get_rect(center=(400, 215 + i * 32)))

def draw_settings():
    _draw_backdrop()
    s = utils.Ui.font(25).render("SETTINGS", False, (180, 210, 255))
    buffer.blit(s, s.get_rect(center=(400, 90)))

    s = utils.Ui.font(10).render("FONT", False, (90, 120, 155))
    buffer.blit(s, s.get_rect(center=(400, 162)))

    fname = pathlib.Path(GameData.font_file).stem
    s = utils.Ui.font(10).render(f"<   {fname}   >", False, (255, 220, 60))
    buffer.blit(s, s.get_rect(center=(400, 180)))

    # Live preview using the selected font
    s = utils.Ui.font(10).render("the quick brown fox  0123456789", False, (160, 175, 195))
    buffer.blit(s, s.get_rect(center=(400, 210)))

    pg.draw.line(buffer, (50, 65, 85), (200, 260), (600, 260), 1)

    s = utils.Ui.font(15).render(">  BACK", False, (255, 220, 60))
    buffer.blit(s, s.get_rect(center=(400, 300)))

    s = utils.Ui.font(10).render(
        "LEFT / RIGHT  to change     ENTER / ESC  to save and go back",
        False, (55, 75, 95))
    buffer.blit(s, s.get_rect(center=(400, 425)))

def draw_gameover():
    _draw_backdrop()

    s = utils.Ui.font(25).render("GAME OVER", False, (255, 70, 70))
    buffer.blit(s, s.get_rect(center=(400, 48)))

    t, k = GameData.time, GameData.kills
    tm, ts = int(t) // 60, int(t) % 60
    s = utils.Ui.font(10).render(
        f"time survived:  {tm:02d}:{ts:02d}      kills:  {k}",
        False, (200, 200, 200))
    buffer.blit(s, s.get_rect(center=(400, 80)))

    if last_rank == 0:
        s = utils.Ui.font(10).render("NEW BEST!", False, (255, 220, 60))
        buffer.blit(s, s.get_rect(center=(400, 96)))

    pg.draw.line(buffer, (60, 70, 90), (180, 112), (620, 112), 1)

    s = utils.Ui.font(10).render("  rank    time    kills", False, (90, 110, 140))
    buffer.blit(s, (200, 118))

    row_h  = utils.Ui.font(10).get_linesize() + 2
    scores = load_scores()
    for idx, sc in enumerate(scores[:8]):
        sm, ss = int(sc["time"]) // 60, int(sc["time"]) % 60
        is_new = (last_rank == idx)
        col = (255, 220, 60) if is_new else (160, 180, 200)
        tag = "  <" if is_new else ""
        s = utils.Ui.font(10).render(
            f"  {idx+1:>2}.     {sm:02d}:{ss:02d}     {sc['kills']:>3}{tag}",
            False, col)
        buffer.blit(s, (200, 134 + idx * row_h))

    pg.draw.line(buffer, (60, 70, 90), (180, 134 + 8 * row_h), (620, 134 + 8 * row_h), 1)

    for i, label in enumerate(_GAMEOVER_ITEMS):
        col = (255, 220, 60) if i == gameover_sel else (140, 160, 180)
        pre = ">  " if i == gameover_sel else "   "
        s = utils.Ui.font(15).render(pre + label, False, col)
        buffer.blit(s, s.get_rect(center=(400, 290 + i * 32)))


def draw_pause():
    # Keep showing the frozen game frame behind a dimming overlay
    overlay = pg.Surface((800, 450), pg.SRCALPHA)
    overlay.fill((0, 0, 0, 165))
    buffer.blit(overlay, (0, 0))

    s = utils.Ui.font(25).render("PAUSED", False, (180, 210, 255))
    buffer.blit(s, s.get_rect(center=(400, 160)))

    for i, label in enumerate(_PAUSE_ITEMS):
        col = (255, 220, 60) if i == pause_sel else (140, 160, 180)
        pre = ">  " if i == pause_sel else "   "
        s = utils.Ui.font(15).render(pre + label, False, col)
        buffer.blit(s, s.get_rect(center=(400, 220 + i * 32)))

    s = utils.Ui.font(10).render("ESC  to resume", False, (90, 110, 140))
    buffer.blit(s, s.get_rect(center=(400, 340)))

def draw_ship_select():
    _draw_backdrop()

    # Number key hints — highlight current
    kw = utils.Ui.font(10).size("0")[0] + 4
    ox = 400 - (len(PLAYER_SHIPS) * kw) // 2
    for i in range(len(PLAYER_SHIPS)):
        col = (255, 220, 60) if i == ship_sel else (55, 75, 95)
        s = utils.Ui.font(10).render(str(i + 1), False, col)
        buffer.blit(s, s.get_rect(center=(ox + i * kw, 22)))

    s = utils.Ui.font(25).render("SELECT  SHIP", False, (180, 210, 255))
    buffer.blit(s, s.get_rect(center=(400, 48)))

    _, asset, maxHP, maxSP, maxvel, acc, hr, desc = PLAYER_SHIPS[ship_sel]
    name = PLAYER_SHIPS[ship_sel][0]

    s = utils.Ui.font(15).render(f"<   {name}   >", False, (255, 220, 60))
    buffer.blit(s, s.get_rect(center=(400, 88)))

    s = utils.Ui.font(10).render(desc, False, (130, 155, 185))
    buffer.blit(s, s.get_rect(center=(400, 110)))

    # Ship sprite preview (centred in an 80×80 box).
    # Fall back to the matching enemy sprite when no dedicated player asset exists yet.
    asset_path = pathlib.Path("Assets") / f"{asset}.png"
    if not asset_path.exists():
        asset_path = pathlib.Path("Assets") / f"{asset}Enemy.png"
    box_cx, box_cy = 400, 175
    if asset_path.exists():
        try:
            if asset not in _ship_preview_cache:
                img = pg.image.load(str(asset_path))
                pw, ph = img.get_size()
                sc = min(80 / pw, 80 / ph, 1.0)
                if sc < 1.0:
                    img = pg.transform.scale(img, (int(pw * sc), int(ph * sc)))
                _ship_preview_cache[asset] = img
            img = _ship_preview_cache[asset]
            buffer.blit(img, img.get_rect(center=(box_cx, box_cy)))
        except Exception:
            pass
    else:
        # Dashed placeholder box + "?" when the asset hasn't been made yet
        pg.draw.rect(buffer, (35, 45, 60),  (box_cx - 40, box_cy - 40, 80, 80))
        pg.draw.rect(buffer, (65, 85, 110), (box_cx - 40, box_cy - 40, 80, 80), 1)
        s = utils.Ui.font(20).render("?", False, (80, 105, 140))
        buffer.blit(s, s.get_rect(center=(box_cx, box_cy)))
        s = utils.Ui.font(10).render("no asset yet", False, (55, 75, 95))
        buffer.blit(s, s.get_rect(center=(box_cx, box_cy + 28)))

    # Stat bars
    bar_labels = [("HULL",   maxHP,  _SHIP_STAT_MAX["maxHP"],  (210, 55,  55)),
                  ("SHIELD", maxSP,  _SHIP_STAT_MAX["maxSP"],  (55,  90, 210)),
                  ("SPEED",  maxvel, _SHIP_STAT_MAX["maxvel"], (55, 190, 180)),
                  ("ACCEL",  acc,    _SHIP_STAT_MAX["acc"],    (200, 160,  55))]
    bar_w = 110
    lx, bx, y0, row = 238, 298, 244, 22
    for label, val, mx, col in bar_labels:
        ls = utils.Ui.font(10).render(label, False, (90, 115, 145))
        buffer.blit(ls, (lx, y0))
        fill = int(val / mx * bar_w)
        pg.draw.rect(buffer, (35, 42, 52),  (bx, y0, bar_w, 9))
        pg.draw.rect(buffer, col,           (bx, y0, fill,  9))
        pg.draw.rect(buffer, (70, 85, 100), (bx, y0, bar_w, 9), 1)
        y0 += row

    # Hit-radius note (useful for sizing the sprite)
    s = utils.Ui.font(10).render(f"hit radius  {hr} px", False, (70, 90, 115))
    buffer.blit(s, s.get_rect(center=(400, y0 + 8)))

    # Position dots
    dot_y = 360
    gap   = 16
    dx0   = 400 - (len(PLAYER_SHIPS) - 1) * gap // 2
    for i in range(len(PLAYER_SHIPS)):
        col = (255, 220, 60) if i == ship_sel else (50, 65, 85)
        r   = 3 if i == ship_sel else 2
        pg.draw.circle(buffer, col, (dx0 + i * gap, dot_y), r)

    s = utils.Ui.font(10).render(
        "1-7  select     < >  cycle     ENTER  start     ESC  back",
        False, (50, 68, 90))
    buffer.blit(s, s.get_rect(center=(400, 430)))


def debug():
    txt = (f"{1/delta:<3.0f} fps  |  "
           f"({player.vel.x:.0f}, {player.vel.y:.0f})  |  "
           f"({player.pos.x:.0f}, {player.pos.y:.0f})  |  "
           f"zoom {camera.zoom:.2f}")
    buffer.blit(utils.Ui.font(10).render(txt, False, (255, 255, 255)), (5, 430))

# ── main loop ─────────────────────────────────────────────────────────────────
while True:
    stime = time.time()

    for event in pg.event.get():
        if event.type == pg.QUIT:
            pg.quit(); sys.exit()
        if event.type == pg.JOYDEVICEADDED:
            joysticks.append(pg.joystick.Joystick(event.device_index))
        if event.type == pg.MOUSEWHEEL and state == "playing":
            camera.target_zoom = max(ZOOM_MIN, min(ZOOM_MAX,
                camera.target_zoom + event.y * 0.15))
        if event.type == pg.KEYDOWN and state == "ship_select":
            if pg.K_1 <= event.key <= pg.K_9:
                i = event.key - pg.K_1
                if i < len(PLAYER_SHIPS):
                    ship_sel = i
                    GameData.current_ship = PLAYER_SHIPS[ship_sel][0]
                    Sounds.play("menu_move")

    # Hide cursor during play; show on menus
    pg.mouse.set_visible(state != "playing")

    Controller.reset()
    if joysticks:
        Controller.update_joysticks(joysticks[0])
    else:
        Controller.update(pg.key)

    up_e, dn_e, ok_e, lt_e, rt_e, bk_e = _nav_inputs()

    # ── MENU ──────────────────────────────────────────────────────────────────
    if state == "menu":
        if up_e or dn_e:
            menu_sel = (menu_sel + (1 if dn_e else -1)) % len(_MENU_ITEMS)
            Sounds.play("menu_move")
        if ok_e:
            if menu_sel == 0:
                Sounds.play("menu_select")
                state = "ship_select"
            elif menu_sel == 1:
                Sounds.play("menu_select")
                state = "settings"
            else:
                Sounds.play("menu_back")
                pg.quit(); sys.exit()
        draw_menu()
        screen.blit(pg.transform.scale_by(buffer, 2.4), (0, 0))

    # ── SHIP SELECT ───────────────────────────────────────────────────────────
    elif state == "ship_select":
        if lt_e or rt_e:
            ship_sel = (ship_sel + (1 if rt_e else -1)) % len(PLAYER_SHIPS)
            GameData.current_ship = PLAYER_SHIPS[ship_sel][0]
            Sounds.play("menu_move")
        if ok_e:
            save_settings()
            Sounds.play("menu_select")
            reset_game()
            state = "playing"
        if bk_e:
            Sounds.play("menu_back")
            state = "menu"
        draw_ship_select()
        screen.blit(pg.transform.scale_by(buffer, 2.4), (0, 0))

    # ── SETTINGS ──────────────────────────────────────────────────────────────
    elif state == "settings":
        if FONT_OPTIONS and (lt_e or rt_e):
            idx = FONT_OPTIONS.index(GameData.font_file) if GameData.font_file in FONT_OPTIONS else 0
            idx = (idx + (1 if rt_e else -1)) % len(FONT_OPTIONS)
            GameData.font_file = FONT_OPTIONS[idx]
            Sounds.play("menu_move")
        if ok_e or bk_e:
            Sounds.play("menu_back")
            save_settings()
            state = "menu"
        draw_settings()
        screen.blit(pg.transform.scale_by(buffer, 2.4), (0, 0))

    # ── PLAYING ───────────────────────────────────────────────────────────────
    elif state == "playing":
        if bk_e and not dying:
            Sounds.play("menu_back")
            state = "paused"
            pause_sel = 0
            screen.blit(pg.transform.scale_by(buffer, 2.4), (0, 0))
        else:
            GameData.time += delta

            # Zoom control (scroll wheel handled in event loop; hold =/- or dpad)
            if Controller.buttons["DPAD_UP"]:
                camera.target_zoom = min(ZOOM_MAX, camera.target_zoom + ZOOM_SPEED * delta)
            if Controller.buttons["DPAD_DOWN"]:
                camera.target_zoom = max(ZOOM_MIN, camera.target_zoom - ZOOM_SPEED * delta)

            # Mouse aim: compute direction from player's screen pos to cursor (buffer space)
            mouse_buf = Vector2(pg.mouse.get_pos()) / 2.4
            if not joysticks:
                diff = mouse_buf - (camera.render_pos - player.pos)
                Controller.mouse_aim = diff.normalize() if diff.magnitude() > 5 else Controller.mouse_aim

            player.update(delta)
            utils.Ship.update_all(delta)
            utils.Derilict.update_all(delta)
            utils.Torpedo.update_all(delta)
            utils.Explosion.update_all(delta)

            if GameData.time >= GRACE_DURATION and not utils.Ship.objects:
                spawn_wave()

            # Grace countdown tick sound
            remaining = max(0.0, GRACE_DURATION - GameData.time)
            tick = math.ceil(remaining)
            if 0 < tick <= GRACE_DURATION and tick != _prev_tick:
                Sounds.play("countdown_tick")
                _prev_tick = tick

            # Death check — let the explosion play out before cutting to the game-over screen
            if GameData.curHP <= 0 and not dying:
                dying = True
                death_timer = DEATH_DELAY
                Sounds.play("explosion_large")
                utils.Explosion(player.pos.copy(), size="large")

            if dying:
                death_timer -= delta
                if death_timer <= 0:
                    dying = False
                    last_rank = save_score(GameData.time, GameData.kills)
                    Sounds.play("game_over")
                    if last_rank == 0:
                        Sounds.play("new_best")
                    state = "game_over"
                    gameover_sel = 0

            # Draw world into camera.surface (camera.update clears + resizes per zoom)
            camera.update(delta)
            utils.Derilict.draw_all(camera)
            utils.Ship.draw_all(camera)
            utils.Torpedo.draw_all(camera)
            if not dying:
                player.draw(camera)
            utils.Explosion.draw_all(camera)

            # Flush world surface → buffer, then draw fixed-space overlays onto buffer
            camera.flush()
            utils.Ui.render(buffer, max(0.0, GRACE_DURATION - GameData.time))

            # Crosshair (keyboard/mouse mode only — replaces the hidden system cursor)
            if not joysticks:
                cx = max(4, min(795, int(mouse_buf.x)))
                cy = max(4, min(445, int(mouse_buf.y)))
                col = utils.Ui._weapon_colors.get(GameData.current_weapon, (200, 200, 200))
                g, a = 3, 6   # gap and arm length
                pg.draw.line(buffer, col, (cx-g-a, cy), (cx-g,   cy), 1)
                pg.draw.line(buffer, col, (cx+g,   cy), (cx+g+a, cy), 1)
                pg.draw.line(buffer, col, (cx, cy-g-a), (cx,   cy-g), 1)
                pg.draw.line(buffer, col, (cx, cy+g),   (cx, cy+g+a), 1)
                pg.draw.circle(buffer, col, (cx, cy), g, 1)

            debug()

            screen.blit(pg.transform.scale_by(buffer, 2.4), (0, 0))

    # ── PAUSED ────────────────────────────────────────────────────────────────
    elif state == "paused":
        if up_e or dn_e:
            pause_sel = (pause_sel + (1 if dn_e else -1)) % len(_PAUSE_ITEMS)
            Sounds.play("menu_move")
        if ok_e or bk_e:
            if bk_e or pause_sel == 0:
                Sounds.play("menu_select" if ok_e else "menu_back")
                state = "playing"
            elif pause_sel == 1:
                Sounds.play("menu_back")
                state = "menu"
            else:
                Sounds.play("menu_back")
                pg.quit(); sys.exit()
        draw_pause()
        screen.blit(pg.transform.scale_by(buffer, 2.4), (0, 0))

    # ── GAME OVER ─────────────────────────────────────────────────────────────
    elif state == "game_over":
        if up_e or dn_e:
            gameover_sel = (gameover_sel + (1 if dn_e else -1)) % len(_GAMEOVER_ITEMS)
            Sounds.play("menu_move")
        if ok_e:
            if gameover_sel == 0:
                Sounds.play("menu_select")
                reset_game()
                state = "playing"
            elif gameover_sel == 1:
                Sounds.play("menu_select")
                state = "menu"
            else:
                Sounds.play("menu_back")
                pg.quit(); sys.exit()
        draw_gameover()
        screen.blit(pg.transform.scale_by(buffer, 2.4), (0, 0))

    pg.display.flip()
    clock.tick(0)
    delta = time.time() - stime
