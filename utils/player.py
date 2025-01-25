import pygame as pg
from pygame.math import Vector2
from .controller import Controller


class Player:
    def __init__(self, current_ship):
        self.current_ship = current_ship
        self.pos = Vector2(0, 0)
        self.img = pg.image.load(f"Assets/{current_ship}.png")
        self.engine_on = False
        self.firing = False
        self.throttle = 0.0
        self.t_dir = Vector2(0, -1)
        self.dir = Vector2(0, -1)
        self.vel = Vector2(0, -1)
        self.acc = 500
        self.maxvel = 500
        self.engine_surf = pg.surface.Surface((16, 8), pg.SRCALPHA)

    def update(self, delta):
        self.throttle = Controller.axesL.y
        if self.throttle > 0.1:
            self.vel += self.dir * self.throttle * self.acc * delta
        elif self.vel.magnitude() > 0:
            self.vel -= delta * self.acc * 0.1 * self.vel.normalize()
            self.vel = Vector2(0, 0) if self.vel.magnitude() < 2 else self.vel
        if self.vel.magnitude() > self.maxvel:
            self.vel = self.vel.normalize() * self.maxvel

        self.t_dir += self.t_dir.rotate(Controller.axesL.x * 200 * delta)
        self.t_dir = (
            self.t_dir.normalize() if self.t_dir.magnitude() > 1 else self.t_dir
        )
        self.dir = self.dir.normalize() if self.t_dir.magnitude() > 1 else self.dir

        if Controller.buttons["X"]:
            self.firing = True

        if (abs(self.dir.angle_to(self.t_dir))) > 1:
            ang1 = self.dir.angle_to(self.t_dir)

            if abs(ang1) > 180:
                if ang1 > 180:
                    ang = ang1 - 360
                else:
                    ang = 360 + ang1
                    ang %= 360
            else:
                ang = ang1

            self.dir = self.dir.rotate(
                (ang * 4 * delta) if abs(ang) < 30 else ang / abs(ang) * 120 * delta
            )

        self.pos -= self.vel * delta

        ratio = self.throttle if self.throttle > -0.1 else 0.25
        color = (94 * ratio, 205 * ratio, 228 * ratio)
        self.engine_surf.fill(color)

        print(Controller.axesL)

    def draw(self, camera):
        rotated = pg.transform.rotate(
            self.img, self.dir.angle_to(Vector2(0, -1)))
        engine_rotated = pg.transform.rotate(
            self.engine_surf, self.dir.angle_to(Vector2(0, -1))
        )

        camera.surface.blit(
            engine_rotated,
            engine_rotated.get_rect(
                center=camera.render_pos
                - self.pos
                - Vector2(0, -12).rotate(-self.dir.angle_to(Vector2(0, -1)))
            ),
        )
        camera.surface.blit(
            rotated,
            rotated.get_rect(center=camera.render_pos - self.pos),
        )

        if self.vel.magnitude() > 5:
            vel = self.vel.normalize()
            pg.draw.line(
                camera.surface,
                "red",
                camera.render_pos - self.pos + vel * 25,
                camera.render_pos - self.pos + vel * 30,
                1,
            )
        pg.draw.line(
            camera.surface,
            "blue",
            camera.render_pos - self.pos + self.dir * 25,
            camera.render_pos - self.pos + self.dir * 30,
            1,
        )
