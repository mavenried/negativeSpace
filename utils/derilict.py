import pygame as pg
from pygame import Vector2
import random


class Derilict:
    objects = []
    _img_cache = {}

    def __init__(self, pos, sprite, rotation=None, vel=None) -> None:
        self.pos = pos
        self.alive = True
        self.hp = 20
        self.hit_radius = 44
        self.vel = vel.copy() if vel is not None else Vector2(0, 0)
        if rotation is None:
            rotation = random.randint(0, 360)
        if sprite not in Derilict._img_cache:
            img = pg.image.load(f"Assets/{sprite}.png").convert_alpha()
            Derilict._img_cache[sprite] = pg.transform.grayscale(img)
        self.img = pg.transform.rotate(Derilict._img_cache[sprite], rotation)

        Derilict.objects.append(self)

    def take_hit(self, damage):
        self.hp -= damage
        if self.hp <= 0 and self.alive:
            self.alive = False
            if self in Derilict.objects:
                Derilict.objects.remove(self)

    def update(self, delta):
        if self.vel.magnitude() > 0.5:
            self.vel *= max(0, 1 - delta * 0.08)
            self.pos += self.vel * delta

    def draw(self, camera):
        camera.surface.blit(
            self.img, self.img.get_rect(center=camera.render_pos - self.pos)
        )

    @staticmethod
    def update_all(delta):
        for obj in Derilict.objects:
            obj.update(delta)

    @staticmethod
    def draw_all(camera):
        for obj in Derilict.objects:
            obj.draw(camera)
