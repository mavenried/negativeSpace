from pygame import Vector2
import pygame as pg


class Torpedo:
    image = pg.image.load("Assets/Bullet.png")
    torpedoes = []
    ships = None    # set to Ship.objects from main.py
    players = []    # set to [player] from main.py

    @staticmethod
    def update_all(delta):
        for torpedo in list(Torpedo.torpedoes):
            torpedo.update(delta)

    @staticmethod
    def draw_all(camera):
        for torpedo in Torpedo.torpedoes:
            torpedo.draw(camera)

    def __init__(self, pos: Vector2, dir: Vector2, target=None, *,
                 owner=None, kind="missile", speed=400, accel=2000, a_speed=360,
                 maxvel=900, lifetime=5, damage=10):
        self.pos = pos
        self.vel = dir.normalize() * speed
        self.heading = dir.normalize()
        self.target = target
        self.owner = owner
        self.elapsed = 0
        self.maxlifetime = lifetime
        self.maxvel = maxvel
        self.accel = accel
        self.a_speed = a_speed
        self.damage = damage
        self.kind = kind

        Torpedo.torpedoes.append(self)

    def update(self, delta):
        alive = True

        # Homing: steer toward target, sync heading to velocity so they never diverge
        if self.target and getattr(self.target, 'alive', True):
            target_dir = self.target.pos - self.pos
            dist = target_dir.magnitude()
            if self.a_speed > 0 and dist > 1:
                if self.vel.magnitude() > 0:
                    self.heading = self.vel.normalize()
                rotate_amount = self.heading.cross(target_dir.normalize())
                self.heading = self.heading.rotate(rotate_amount * self.a_speed * delta).normalize()
                current_speed = min(self.vel.magnitude() + self.accel * delta, self.maxvel)
                self.vel = self.heading * current_speed
        else:
            self.target = None

        # Collision: check every registered damageable object, not just the lock
        all_targets = list(Torpedo.ships or []) + list(Torpedo.players or [])
        for obj in all_targets:
            if obj is self.owner:
                continue
            if not getattr(obj, 'alive', True):
                continue
            check_r = obj.hit_radius * (2.5 if self.kind == "slug" else 1)
            if (self.pos - obj.pos).magnitude() < check_r:
                if hasattr(obj, 'take_hit'):
                    obj.take_hit(self.damage)
                alive = False
                break

        self.elapsed += delta
        if self.elapsed > self.maxlifetime:
            alive = False

        if not alive:
            if self in Torpedo.torpedoes:
                Torpedo.torpedoes.remove(self)
            return

        self.pos += self.vel * delta

    def draw(self, camera):
        screen_pos = camera.render_pos - self.pos
        if self.kind == "bullet":
            pg.draw.circle(
                camera.surface, (200, 220, 255),
                (int(screen_pos.x), int(screen_pos.y)), 2
            )
        elif self.kind == "slug":
            if self.vel.magnitude() > 0:
                back = screen_pos - self.vel.normalize() * 300
                pg.draw.line(
                    camera.surface, (255, 255, 160),
                    (int(screen_pos.x), int(screen_pos.y)),
                    (int(back.x), int(back.y)), 2
                )
                # Bright core
                mid = screen_pos - self.vel.normalize() * 150
                pg.draw.line(
                    camera.surface, (255, 255, 255),
                    (int(screen_pos.x), int(screen_pos.y)),
                    (int(mid.x), int(mid.y)), 1
                )
        else:
            image = pg.transform.rotate(self.image, self.vel.angle_to(Vector2(0, -1)))
            camera.surface.blit(image, image.get_rect(center=screen_pos))
