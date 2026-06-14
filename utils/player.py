import math
import random
import pygame as pg
from pygame.math import Vector2
from .controller import Controller
from .torpedo import Torpedo
from .gamedata import GameData
from .sounds import Sounds


SHIELD_REGEN_DELAY = 10.0
SHIELD_REGEN_RATE = 3.0

# name, fire cooldown, tint color
WEAPONS = [
    ("TORPEDO", 0.30, (100, 200, 230)),
    ("CANNON",  0.06, (200, 220, 255)),
    ("RAILGUN", 2.00, (255, 240, 100)),
]

# Cannon: each pellet scatters randomly within ±this many degrees of aim
CANNON_SPREAD = 16
# Cannon: fires in bursts from a magazine, then reloads
CANNON_MAG_SIZE   = 20
CANNON_RELOAD_TIME = 2.0

# Railgun auto-aim: snap the shot onto the locked target if it's within this
# small arc (degrees) of where the ship is actually facing.
RAILGUN_AIM_ARC = 12


class Player:
    def __init__(self, asset, maxvel=550, acc=700, hit_radius=20):
        self.current_ship = asset
        self.pos = Vector2(0, 0)
        try:
            self.img = pg.image.load(f"Assets/{asset}.png")
        except Exception:
            self.img = pg.image.load("Assets/Viper.png")   # fallback if asset missing
        self.firing = False
        self.throttle = 0.0
        self.t_dir = Vector2(0, -1)
        self.dir = Vector2(0, -1)
        self.vel = Vector2(0, -1)
        self.acc = acc
        self.maxvel = maxvel
        self.engine_surf = pg.surface.Surface((16, 8), pg.SRCALPHA)
        self.target = None
        self.firing_timer = 999  # weapons start fully loaded — ready to fire immediately
        self.hit_radius = hit_radius
        self.alive = True
        self.flash_timer = 0
        self.damage_timer = SHIELD_REGEN_DELAY

        self.cannon_ammo = CANNON_MAG_SIZE
        self.cannon_reloading = False
        self.cannon_reload_timer = 0.0

        self.weapon_index = 0
        self._r1_prev = False
        self._l1_prev = False
        GameData.current_weapon = WEAPONS[0][0]

    def take_hit(self, damage):
        if GameData.curSP > 0:
            GameData.curSP = max(0, GameData.curSP - damage)
            Sounds.play("hit_shield")
        else:
            GameData.curHP = max(0, GameData.curHP - damage)
            Sounds.play("hit_hull")
        self.flash_timer = 0.15
        self.damage_timer = 0

    def heal_full(self):
        GameData.curHP = GameData.maxHP
        GameData.curSP = GameData.maxSP
        self.damage_timer = SHIELD_REGEN_DELAY
        Sounds.play("heal")

    def _retarget(self):
        from .ship import Ship
        if Ship.objects:
            self.target = min(Ship.objects, key=lambda s: (s.pos - self.pos).magnitude())
        else:
            self.target = None

    def _cycle_target(self):
        from .ship import Ship
        if not Ship.objects:
            self.target = None
            return
        if self.target not in Ship.objects:
            self.target = Ship.objects[0]
            return
        idx = Ship.objects.index(self.target)
        self.target = Ship.objects[(idx + 1) % len(Ship.objects)]

    def _fire(self):
        w = WEAPONS[self.weapon_index][0]
        t = self.target
        # Nose is in -self.dir world direction (player uses pos -= vel*delta)
        p = self.pos - self.dir * 12
        # Player uses pos -= vel*delta; torpedoes use pos += vel*delta.
        # Negate dir so torpedoes fly in the visual facing direction.
        d = -self.dir

        if w == "TORPEDO":
            Torpedo(p, d.rotate(45),  t, owner=self, kind="missile", speed=400, accel=2000, a_speed=360, maxvel=900, lifetime=5,    damage=10)
            Torpedo(p, d.rotate(-45), t, owner=self, kind="missile", speed=400, accel=2000, a_speed=360, maxvel=900, lifetime=5,    damage=10)
            Sounds.play("fire_torpedo")
        elif w == "CANNON":
            # Magazine-fed: one round per trigger pull, scattered within the spread cone
            angle = random.uniform(-CANNON_SPREAD, CANNON_SPREAD)
            Torpedo(p, d.rotate(angle), t, owner=self, kind="bullet", speed=1500, accel=0, a_speed=0, maxvel=1500, lifetime=0.8, damage=2)
            Sounds.play("fire_cannon")
        elif w == "RAILGUN":
            aim = d
            if t is not None and getattr(t, 'alive', False):
                to_target = t.pos - self.pos
                if to_target.magnitude() > 1:
                    to_target = to_target.normalize()
                    if abs(d.angle_to(to_target)) <= RAILGUN_AIM_ARC:
                        aim = to_target
            Torpedo(p, aim, t, owner=self, kind="slug", speed=6000, accel=0, a_speed=0, maxvel=6000, lifetime=0.25, damage=40)
            Sounds.play("fire_railgun")

    def update(self, delta):
        self.throttle = Controller.axesT
        if self.throttle > 0.1:
            self.vel += self.dir * self.throttle * self.acc * delta
        elif self.vel.magnitude() > 0:
            p = 0.5
            if self.throttle < -0.1:
                p = 2
            self.vel -= delta * self.acc * p * self.vel.normalize()
            self.vel = Vector2(0, 0) if self.vel.magnitude() < 2 else self.vel

        if self.vel.magnitude() > self.maxvel:
            self.vel = self.vel.normalize() * self.maxvel

        # Direction: mouse aim wins; fall back to left stick; else hold current facing
        if Controller.mouse_aim is not None:
            self.t_dir = Controller.mouse_aim
        elif Controller.axesL.magnitude() > 0.5:
            self.t_dir = Controller.axesL.normalize()
        self.dir = self.dir.normalize() if self.t_dir.magnitude() > 1 else self.dir

        if self.target is None or not getattr(self.target, 'alive', True):
            self._retarget()

        # Weapon cycle — edge-detect so one press = one switch
        r1_now = Controller.buttons["R1"]
        if r1_now and not self._r1_prev:
            self.weapon_index = (self.weapon_index + 1) % len(WEAPONS)
            GameData.current_weapon = WEAPONS[self.weapon_index][0]
            self.firing_timer = 999  # newly-equipped weapon is immediately ready to fire
            Sounds.play("weapon_switch")
        self._r1_prev = r1_now

        # Target cycle — L1 / Q
        l1_now = Controller.buttons["L1"]
        if l1_now and not self._l1_prev:
            self._cycle_target()
        self._l1_prev = l1_now

        weapon = WEAPONS[self.weapon_index][0]
        cooldown = WEAPONS[self.weapon_index][1]
        if weapon == "CANNON" and self.cannon_reloading:
            self.cannon_reload_timer -= delta
            if self.cannon_reload_timer <= 0:
                self.cannon_reloading = False
                self.cannon_ammo = CANNON_MAG_SIZE
        elif Controller.buttons["X"] and self.firing_timer >= cooldown:
            self._fire()
            self.firing_timer = 0
            if weapon == "CANNON":
                self.cannon_ammo -= 1
                if self.cannon_ammo <= 0:
                    self.cannon_reloading = True
                    self.cannon_reload_timer = CANNON_RELOAD_TIME
        self.firing_timer += delta

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
                (ang * 10 * delta) if abs(ang) < 25 else ang / abs(ang) * 400 * delta
            )

        self.pos -= self.vel * delta

        if self.flash_timer > 0:
            self.flash_timer -= delta

        self.damage_timer += delta
        if self.damage_timer >= SHIELD_REGEN_DELAY and GameData.curSP < GameData.maxSP:
            GameData.curSP = min(GameData.maxSP, GameData.curSP + SHIELD_REGEN_RATE * delta)

        ratio = abs(self.throttle) if self.throttle > -0.1 else 0.25
        color = (int(94 * ratio), int(205 * ratio), int(228 * ratio))
        self.engine_surf.fill(color)

    def draw(self, camera):
        rotated = pg.transform.rotate(self.img, self.dir.angle_to(Vector2(0, -1)))
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

        if self.flash_timer > 0:
            pg.draw.circle(
                camera.surface, (220, 60, 60),
                tuple(int(v) for v in camera.render_pos - self.pos), 28, 2
            )

        if self.vel.magnitude() > 5:
            vel = self.vel.normalize()
            pg.draw.line(
                camera.surface, "red",
                camera.render_pos - self.pos + vel * 25,
                camera.render_pos - self.pos + vel * 30,
                1,
            )
        pg.draw.line(
            camera.surface, "blue",
            camera.render_pos - self.pos + self.dir * 25,
            camera.render_pos - self.pos + self.dir * 30,
            1,
        )

        # Yellow tick pointing toward current target lock.
        # Screen coords are camera.render_pos - world_pos, so the on-screen direction
        # from player to target is (self.pos - target.pos), not (target.pos - self.pos).
        if self.target and getattr(self.target, 'alive', False):
            to_target_screen = self.pos - self.target.pos
            if to_target_screen.magnitude() > 5:
                d = to_target_screen.normalize()
                pg.draw.line(
                    camera.surface, (255, 200, 0),
                    camera.render_pos - self.pos + d * 36,
                    camera.render_pos - self.pos + d * 48,
                    1,
                )

        # Cooldown / reload arc: fills clockwise from 12 o'clock as the weapon becomes ready.
        # The cannon fires too rapidly for a per-shot arc to be useful — show it only
        # while the magazine is actually reloading.
        cooldown = WEAPONS[self.weapon_index][1]
        weapon_name = WEAPONS[self.weapon_index][0]
        if weapon_name == "CANNON":
            pct = (1.0 - self.cannon_reload_timer / CANNON_RELOAD_TIME) if self.cannon_reloading else 0.0
        else:
            pct = min(1.0, self.firing_timer / cooldown)
        if 0.01 < pct < 1.0:
            color = WEAPONS[self.weapon_index][2]
            radius = 22
            cx, cy = camera.render_pos - self.pos
            rect = pg.Rect(int(cx) - radius, int(cy) - radius, radius * 2, radius * 2)
            stop = math.pi / 2
            start = stop - pct * 2 * math.pi
            pg.draw.arc(camera.surface, color, rect, start, stop, 1)
