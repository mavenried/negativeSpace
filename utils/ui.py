import math
import pathlib
import pygame as pg
from .gamedata import GameData


class Ui:
    _avatar_cache = {}
    _font_cache   = {}   # size -> Font
    _font_key     = None # last GameData.font_file value

    @staticmethod
    def font(size):
        """Return a cached Font for the currently selected font file and size."""
        key = GameData.font_file
        if Ui._font_key != key:
            Ui._font_cache = {}
            Ui._font_key   = key
        if size not in Ui._font_cache:
            path = str(pathlib.Path("Assets") / key) if key else None
            try:
                Ui._font_cache[size] = pg.font.Font(path, size)
            except Exception:
                Ui._font_cache[size] = pg.font.SysFont("DepartureMono Nerd Font", size)
        return Ui._font_cache[size]

    _weapon_colors = {
        "TORPEDO": (100, 200, 230),
        "CANNON":  (200, 220, 255),
        "RAILGUN": (255, 240, 100),
    }

    @staticmethod
    def render(surface, grace_remaining=0.0):
        Ui.render_avatar(surface)
        Ui.render_healthbar(surface)
        Ui.render_kills(surface)
        Ui.render_weapon(surface)
        Ui.render_timer(surface)
        if grace_remaining > 0:
            Ui.render_grace(surface, grace_remaining)

    @staticmethod
    def render_avatar(surface):
        ship = GameData.current_ship
        if ship not in Ui._avatar_cache:
            try:
                Ui._avatar_cache[ship] = pg.image.load(f"Assets/{ship}.png")
            except Exception:
                Ui._avatar_cache[ship] = pg.image.load("Assets/Viper.png")
        image = Ui._avatar_cache[ship]
        surface.blit(image, image.get_rect(center=(16, 20)))

    @staticmethod
    def render_healthbar(surface):
        seg = 8; h = 6
        total_segs = int((GameData.maxHP + GameData.maxSP) / 5)
        hp_segs    = int(GameData.curHP / 5)
        sp_segs    = int(GameData.curSP / 5)
        x, y = 32, 11
        pg.draw.rect(surface, (55, 55, 55),    (x, y, seg * total_segs, h))
        pg.draw.rect(surface, (55, 90, 210),   (x + seg * hp_segs, y, seg * sp_segs, h))
        pg.draw.rect(surface, (210, 55, 55),   (x, y, seg * hp_segs, h))
        pg.draw.rect(surface, (200, 200, 200), (x, y, seg * total_segs, h), 1)

    @staticmethod
    def render_kills(surface):
        surf = Ui.font(10).render(f"KILLS  {GameData.kills}", False, (180, 180, 180))
        surface.blit(surf, (32, 21))

    @staticmethod
    def render_weapon(surface):
        color = Ui._weapon_colors.get(GameData.current_weapon, (255, 255, 255))
        surf  = Ui.font(10).render(GameData.current_weapon, False, color)
        surface.blit(surf, (32, 33))

    @staticmethod
    def render_timer(surface):
        t    = max(0.0, GameData.time)
        mins = int(t) // 60
        secs = int(t) % 60
        surf = Ui.font(10).render(f"{mins:02d}:{secs:02d}", False, (200, 200, 200))
        surface.blit(surf, (800 - surf.get_width() - 5, 5))

    @staticmethod
    def render_grace(surface, remaining):
        n    = math.ceil(remaining)
        surf = Ui.font(20).render(f"LAUNCHING IN  {n}", False, (255, 220, 80))
        surface.blit(surf, surf.get_rect(center=(400, 225)))
