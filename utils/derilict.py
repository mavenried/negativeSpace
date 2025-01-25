import pygame as pg
from pygame import Vector2
import random


class Derilict:
    objects = []

    def __init__(self, pos, obj_type) -> None:
        self.pos = pos
        self.dir = Vector2(0, -1).rotate(random.randint(0, 360))
        type = obj_type.split()
        if type[0] == "ship":
            self.img = pg.transform.rotate(
                pg.image.load(f"Assets/{type[1]}.png"),
                self.dir.angle_to(Vector2(0, -1)),
            )

        Derilict.objects.append(self)

    def draw(self, camera):
        camera.surface.blit(
            self.img, self.img.get_rect(center=camera.render_pos - self.pos)
        )

    @staticmethod
    def update_all(delta):
        pass

    @staticmethod
    def draw_all(camera):
        for obj in Derilict.objects:
            obj.draw(camera)
