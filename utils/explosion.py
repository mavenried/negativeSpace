import pygame as pg
from pygame import Vector2


class Explosion:
    """Death effect: a burst of staggered, fading concentric rings."""

    objects = []

    _SIZE = {
        "small":  {"duration": 0.40, "max_radius": 36, "rings": 3, "color": (255, 200, 120)},
        "medium": {"duration": 0.55, "max_radius": 60, "rings": 3, "color": (255, 170, 90)},
        "large":  {"duration": 0.75, "max_radius": 95, "rings": 4, "color": (255, 140, 70)},
    }

    def __init__(self, pos, size="medium"):
        self.pos = Vector2(pos)
        self.elapsed = 0.0
        cfg = Explosion._SIZE.get(size, Explosion._SIZE["medium"])
        self.duration   = cfg["duration"]
        self.max_radius = cfg["max_radius"]
        self.rings      = cfg["rings"]
        self.color      = cfg["color"]
        self.alive = True

        Explosion.objects.append(self)

    def update(self, delta):
        self.elapsed += delta
        if self.elapsed >= self.duration:
            self.alive = False
            if self in Explosion.objects:
                Explosion.objects.remove(self)

    def draw(self, camera):
        sc = camera.render_pos - self.pos
        cx, cy = int(sc.x), int(sc.y)

        # Each ring runs the same short life, staggered so they ripple outward in sequence
        ring_life = self.duration * 0.6
        stagger = (self.duration - ring_life) / max(1, self.rings - 1)
        for i in range(self.rings):
            t = self.elapsed - i * stagger
            if t <= 0 or t >= ring_life:
                continue
            progress = t / ring_life
            radius = int(2 + progress * self.max_radius)
            fade = 1.0 - progress
            color = tuple(int(c * fade) for c in self.color)
            pg.draw.circle(camera.surface, color, (cx, cy), radius, 2)

    @staticmethod
    def update_all(delta):
        for fx in list(Explosion.objects):
            fx.update(delta)

    @staticmethod
    def draw_all(camera):
        for fx in Explosion.objects:
            fx.draw(camera)
