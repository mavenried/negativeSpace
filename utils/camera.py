import pygame as pg
from pygame import Vector2
import random


class Camera:
    def __init__(self, pos, surface, target):
        self.pos = pos
        self.surface = surface
        self.stars = pg.surface.Surface((800, 500), pg.SRCALPHA)
        self.target = target
        self.render_pos = pos + Vector2(400, 250)

        for i in range(10):
            for j in range(7):
                rx = random.randint(-30, 30)
                ry = random.randint(-30, 30)
                rc = random.randint(0, 12)
                pg.draw.rect(
                    self.stars,
                    "darkgrey" if rc < 10 else "orange",
                    (80 * i + rx, 80 * j + ry, 1, 1),
                )

    def update(self, delta):
        for pos in [
            (self.pos.x % 800, self.pos.y % 500),
            (self.pos.x % 800, self.pos.y % 500 + 500),
            (self.pos.x % 800, self.pos.y % 500 - 500),
            (self.pos.x % 800 + 800, self.pos.y % 500),
            (self.pos.x % 800 + 800, self.pos.y % 500 + 500),
            (self.pos.x % 800 + 800, self.pos.y % 500 - 500),
            (self.pos.x % 800 - 800, self.pos.y % 500),
            (self.pos.x % 800 - 800, self.pos.y % 500 + 500),
            (self.pos.x % 800 - 800, self.pos.y % 500 - 500),
        ]:
            self.surface.blit(self.stars, pos)
            if (self.target.pos - self.pos).length() > 0:
                self.pos += (self.target.pos - self.pos) * delta * 40
            self.render_pos = self.pos + Vector2(400, 250)
