import pygame as pg
from pygame import Vector2
import random
import math


class Camera:
    def __init__(self, pos, buffer, target):
        self.pos = pos
        self._buffer = buffer          # fixed 800x450 output surface
        self.target = target
        self.zoom = 1.0
        self.target_zoom = 1.0
        self.surface = pg.Surface((800, 450))   # world render surface (resizes with zoom)
        self.render_pos = pos + Vector2(400, 225)

        self.stars = pg.Surface((800, 500), pg.SRCALPHA)
        for i in range(10):
            for j in range(7):
                rx, ry = random.randint(-30, 30), random.randint(-30, 30)
                rc = random.randint(0, 12)
                pg.draw.rect(self.stars,
                             "darkgrey" if rc < 10 else "orange",
                             (80 * i + rx, 80 * j + ry, 1, 1))

        self.stars_bg = pg.Surface((800, 500), pg.SRCALPHA)
        for i in range(6):
            for j in range(4):
                rx, ry = random.randint(-50, 50), random.randint(-40, 40)
                pg.draw.rect(self.stars_bg, (40, 40, 50),
                             (130 * i + rx, 125 * j + ry, 1, 1))

    def flush(self):
        """Scale world surface into the fixed 800x450 buffer."""
        pg.transform.scale(self.surface, (800, 450), self._buffer)

    def update(self, delta):
        # Smooth zoom interpolation
        self.zoom += (self.target_zoom - self.zoom) * min(1.0, delta * 8)

        # Camera tracks target
        if (self.target.pos - self.pos).length() > 0:
            self.pos += (self.target.pos - self.pos) * delta * 40

        # Resize world surface to match zoom level, then clear it
        vw = max(80, int(800 / self.zoom))
        vh = max(45, int(450 / self.zoom))
        if self.surface.get_size() != (vw, vh):
            self.surface = pg.Surface((vw, vh))
        self.surface.fill((0, 0, 0))

        # render_pos: world surface position that maps to the top-left origin.
        # Objects draw at (render_pos - world_pos), so camera center = (vw/2, vh/2).
        self.render_pos = self.pos + Vector2(vw / 2, vh / 2)

        # Tile enough star layers to cover the full world surface
        tx = math.ceil(vw / 800) + 2
        ty = math.ceil(vh / 500) + 2

        bx = int((self.pos.x * 0.25) % 800)
        by = int((self.pos.y * 0.25) % 500)
        for i in range(-1, tx):
            for j in range(-1, ty):
                self.surface.blit(self.stars_bg, (bx + i * 800, by + j * 500))

        px = int(self.pos.x % 800)
        py = int(self.pos.y % 500)
        for i in range(-1, tx):
            for j in range(-1, ty):
                self.surface.blit(self.stars, (px + i * 800, py + j * 500))
