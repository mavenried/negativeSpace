import pygame as pg
from pygame import Vector2
import random
from .torpedo import Torpedo
from .gamedata import GameData
from .sounds import Sounds

# Map each enemy type to the derelict sprite it leaves behind
_DERELICT_SPRITE = {
    "ViperEnemy":    "ViperEnemy",
    "MaulerEnemy":   "MaulerEnemy",
    "PhantomEnemy":  "PhantomEnemy",
    "SentinelEnemy": "SentinelEnemy",
    "SwarmDrone":    "SwarmDrone",
    "WardenEnemy":   "WardenEnemy",
    "MarauderEnemy": "MarauderEnemy",
}


_sprite_cache = {}


def _make_sprite(filename, tint, scale):
    key = (filename, tint, scale)
    if key not in _sprite_cache:
        img = pg.image.load(f"Assets/{filename}").convert_alpha()
        if tint is not None:
            img.fill((*tint, 255), special_flags=pg.BLEND_MULT)
        if scale != 1.0:
            w, h = img.get_size()
            img = pg.transform.scale(img, (int(w * scale), int(h * scale)))
        _sprite_cache[key] = img
    return _sprite_cache[key]


class Ship:
    objects = []
    player = None

    def __init__(self, pos, ship_type):
        self.pos = pos
        self.ship_type = ship_type
        self.dir = Vector2(0, -1).rotate(random.randint(0, 360))
        self.vel = Vector2(0, 0)
        self.alive = True
        self.orbit_dir = random.choice([-1, 1])
        self.collision_timer = 0.0
        self.heals_on_kill = True
        # State machine fields (Phantom / Marauder / Warden)
        self.state = None
        self.state_timer = 0.0
        self.charge_dir = Vector2(0, -1)
        self.shield_active = False
        self.shield_timer = 0.0

        if ship_type == "ViperEnemy":
            self.img = _make_sprite("ViperEnemy.png", None, 1.0)
            self.hit_radius = 44
            self.hp = 45
            self.speed = random.uniform(380, 480)
            self.shoot_timer = random.uniform(0.3, 1.0)
            self.shoot_interval = (0.8, 1.5)

        elif ship_type == "MaulerEnemy":
            self.img = _make_sprite("MaulerEnemy.png", None, 1.0)
            self.hit_radius = 44
            self.hp = 150
            self.speed = random.uniform(220, 300)
            self.shoot_timer = random.uniform(1.0, 2.5)
            self.shoot_interval = (2.5, 4.0)

        elif ship_type == "PhantomEnemy":
            # Fast, low HP. Dashes in, fires a 2-shot burst, retreats to a new angle.
            self.img = _make_sprite("PhantomEnemy.png", (150, 255, 180), 0.8)
            self.hit_radius = 30
            self.hp = 30
            self.speed = random.uniform(500, 620)
            self.shoot_timer = random.uniform(0.3, 1.0)
            self.shoot_interval = (0.5, 1.2)
            self.state = "approach"

        elif ship_type == "SentinelEnemy":
            # Nearly stationary sniper. Stays at 800-1200 range, fires slow slugs.
            self.img = _make_sprite("SentinelEnemy.png", (255, 210, 80), 1.1)
            self.hit_radius = 48
            self.hp = 60
            self.speed = random.uniform(30, 50)
            self.shoot_timer = random.uniform(1.0, 3.0)
            self.shoot_interval = (3.5, 5.0)

        elif ship_type == "SwarmDrone":
            # Tiny, low HP, no weapons. Spawns in groups. Contact damage only.
            self.img = _make_sprite("SwarmDrone.png", (255, 80, 80), 0.5)
            self.hit_radius = 14
            self.hp = 12
            self.speed = random.uniform(380, 460)
            self.shoot_timer = 999.0
            self.shoot_interval = (999.0, 999.0)
            self.heals_on_kill = False

        elif ship_type == "WardenEnemy":
            # Tanky, slow. Absorbs 80% damage while shield is up (3s recharge after hit).
            self.img = _make_sprite("WardenEnemy.png", None, 1.0)
            self.hit_radius = 50
            self.hp = 300
            self.speed = random.uniform(160, 220)
            self.shoot_timer = random.uniform(1.0, 2.0)
            self.shoot_interval = (2.0, 3.5)
            self.shield_active = True

        elif ship_type == "MarauderEnemy":
            # Heavy ramming ship. Telegraphs then charges at 3.5× speed.
            self.img = _make_sprite("MarauderEnemy.png", (200, 80, 255), 1.8)
            self.hit_radius = 70
            self.hp = 270
            self.speed = random.uniform(180, 240)
            self.shoot_timer = random.uniform(1.5, 3.0)
            self.shoot_interval = (3.0, 5.0)
            self.state = "patrol"
            self.state_timer = random.uniform(3.0, 6.0)

        else:
            raise ValueError(f"Unknown ship type: {ship_type}")

        Ship.objects.append(self)

    _EXPLOSION_SIZE = {
        "ViperEnemy": "small", "PhantomEnemy": "small", "SwarmDrone": "small",
        "MaulerEnemy": "medium", "SentinelEnemy": "medium",
        "WardenEnemy": "medium", "MarauderEnemy": "large",
    }

    def take_hit(self, damage):
        if self.ship_type == "WardenEnemy" and self.shield_active:
            damage = max(1, int(damage * 0.2))
            self.shield_active = False
            self.shield_timer = 3.0
            Sounds.play("warden_shield_break")

        self.hp -= damage
        if self.hp <= 0 and self.alive:
            self.alive = False
            if self in Ship.objects:
                Ship.objects.remove(self)
            GameData.kills += 1
            size = Ship._EXPLOSION_SIZE.get(self.ship_type, "small")
            Sounds.play(f"explosion_{size}")
            from .explosion import Explosion
            Explosion(self.pos.copy(), size=size)
            if Ship.player is not None and self.heals_on_kill:
                Ship.player.heal_full()
            from .derilict import Derilict
            sprite = _DERELICT_SPRITE.get(self.ship_type, "ViperEnemy")
            Derilict(self.pos.copy(), sprite,
                     rotation=self.dir.angle_to(Vector2(0, -1)),
                     vel=self.vel.copy())

    def _fire(self, player, dist):
        shoot_pos = self.pos + self.dir * 12
        shoot_dir = (player.pos - self.pos).normalize()

        if self.ship_type == "ViperEnemy":
            if dist < 800:
                for angle in (-4, 0, 4):
                    Torpedo(shoot_pos, shoot_dir.rotate(angle), player,
                            owner=self, kind="bullet",
                            speed=1800, accel=0, a_speed=0,
                            maxvel=1800, lifetime=0.6, damage=6)
                Sounds.play("fire_bullet", 0.5)

        elif self.ship_type == "MaulerEnemy":
            Torpedo(shoot_pos, shoot_dir.rotate(12), player,
                    owner=self, kind="missile",
                    speed=400, accel=2000, a_speed=360,
                    maxvel=900, lifetime=6, damage=15)
            Torpedo(shoot_pos, shoot_dir.rotate(-12), player,
                    owner=self, kind="missile",
                    speed=400, accel=2000, a_speed=360,
                    maxvel=900, lifetime=6, damage=15)
            Sounds.play("fire_missile", 0.55)

        elif self.ship_type == "PhantomEnemy":
            # Fire only at close range; immediately begin retreat
            if dist < 260:
                for angle in (-6, 6):
                    Torpedo(shoot_pos, shoot_dir.rotate(angle), player,
                            owner=self, kind="bullet",
                            speed=1600, accel=0, a_speed=0,
                            maxvel=1600, lifetime=0.5, damage=8)
                self.state = "retreat"
                self.state_timer = 2.0
                Sounds.play("fire_bullet", 0.45)

        elif self.ship_type == "SentinelEnemy":
            Torpedo(shoot_pos, shoot_dir, player,
                    owner=self, kind="slug",
                    speed=1000, accel=0, a_speed=0,
                    maxvel=1000, lifetime=4.0, damage=25)
            Sounds.play("fire_slug", 0.6)

        elif self.ship_type == "SwarmDrone":
            pass  # contact damage via collision only

        elif self.ship_type == "WardenEnemy":
            for angle in (-20, 0, 20):
                Torpedo(shoot_pos, shoot_dir.rotate(angle), player,
                        owner=self, kind="missile",
                        speed=320, accel=1500, a_speed=200,
                        maxvel=700, lifetime=6, damage=12)
            Sounds.play("fire_missile", 0.50)

        elif self.ship_type == "MarauderEnemy":
            if self.state in ("patrol", "recover"):
                for angle in (-15, 15):
                    Torpedo(shoot_pos, shoot_dir.rotate(angle), player,
                            owner=self, kind="missile",
                            speed=350, accel=1800, a_speed=300,
                            maxvel=800, lifetime=5, damage=18)
                Sounds.play("fire_missile", 0.60)

    def _move(self, delta, dist, radial, perp):
        t = self.ship_type

        if t == "ViperEnemy":
            if dist > 220:
                d = (radial * 0.65 + perp * 0.35).normalize()
            elif dist < 120:
                d = (-radial * 0.5 + perp * 0.5).normalize()
            else:
                d = (radial * 0.1 + perp * 0.9).normalize()
            self.vel += d * self.speed * delta
            if self.vel.magnitude() > self.speed:
                self.vel = self.vel.normalize() * self.speed

        elif t == "MaulerEnemy":
            blend = max(0.0, 1.0 - dist / 400) * 0.35 if dist > 150 else 0.0
            d = (radial * (1 - blend) + perp * blend).normalize() if dist > 150 else radial
            self.vel += d * self.speed * delta
            if self.vel.magnitude() > self.speed:
                self.vel = self.vel.normalize() * self.speed

        elif t == "PhantomEnemy":
            if self.state == "approach":
                d = radial if dist > 80 else (-radial * 0.3 + perp * 0.7).normalize()
            else:  # retreat
                d = (-radial * 0.6 + perp * 0.4).normalize()
                self.state_timer -= delta
                if self.state_timer <= 0:
                    self.state = "approach"
                    self.orbit_dir *= -1
                    self.shoot_timer = random.uniform(0.4, 0.9)
            self.vel += d * self.speed * delta
            if self.vel.magnitude() > self.speed:
                self.vel = self.vel.normalize() * self.speed

        elif t == "SentinelEnemy":
            if dist < 600:
                d = -radial
            elif dist > 1200:
                d = (radial * 0.4 + perp * 0.6).normalize()
            else:
                d = perp
            self.vel += d * self.speed * delta
            if self.vel.magnitude() > self.speed:
                self.vel = self.vel.normalize() * self.speed

        elif t == "SwarmDrone":
            self.vel += radial * self.speed * delta
            if self.vel.magnitude() > self.speed:
                self.vel = self.vel.normalize() * self.speed

        elif t == "WardenEnemy":
            ob = max(0.0, 1.0 - dist / 500) * 0.5
            d = perp if dist < 100 else (radial * (1 - ob) + perp * ob).normalize()
            self.vel += d * self.speed * delta
            if self.vel.magnitude() > self.speed:
                self.vel = self.vel.normalize() * self.speed

        elif t == "MarauderEnemy":
            if self.state == "patrol":
                blend = max(0.0, 1.0 - dist / 500) * 0.25
                d = (radial * (1 - blend) + perp * blend).normalize()
                self.vel += d * self.speed * delta
                if self.vel.magnitude() > self.speed:
                    self.vel = self.vel.normalize() * self.speed
                self.state_timer -= delta
                if self.state_timer <= 0 and dist < 600:
                    self.state = "telegraph"
                    self.state_timer = 0.8
                    self.charge_dir = radial.copy()

            elif self.state == "telegraph":
                self.vel *= max(0.0, 1.0 - delta * 6)
                self.state_timer -= delta
                if self.state_timer <= 0:
                    self.state = "charge"
                    self.state_timer = 1.5

            elif self.state == "charge":
                spd = self.speed * 3.5
                self.vel += self.charge_dir * spd * delta
                if self.vel.magnitude() > spd:
                    self.vel = self.vel.normalize() * spd
                self.state_timer -= delta
                if self.state_timer <= 0:
                    self.state = "recover"
                    self.state_timer = 1.2

            elif self.state == "recover":
                self.vel *= max(0.0, 1.0 - delta * 3)
                self.state_timer -= delta
                if self.state_timer <= 0:
                    self.state = "patrol"
                    self.state_timer = random.uniform(2.0, 5.0)

    def update(self, delta):
        if Ship.player is None:
            return

        player = Ship.player
        to_player = player.pos - self.pos
        dist = to_player.magnitude()

        if self.collision_timer > 0:
            self.collision_timer -= delta

        if self.ship_type == "WardenEnemy" and not self.shield_active:
            self.shield_timer -= delta
            if self.shield_timer <= 0:
                self.shield_active = True

        if dist > 0.1:
            radial = to_player.normalize()
            perp = Vector2(-radial.y, radial.x) * self.orbit_dir
            self._move(delta, dist, radial, perp)

        if dist > 1:
            face_dir = (self.pos - player.pos).normalize()
            rate = 8 if (self.ship_type == "MarauderEnemy" and self.state in ("telegraph", "charge")) else 3
            self.dir = self.dir.lerp(face_dir, min(delta * rate, 1)).normalize()

        self.pos += self.vel * delta

        self.shoot_timer -= delta
        if self.shoot_timer <= 0:
            self.shoot_timer = random.uniform(*self.shoot_interval)
            self._fire(player, dist)

    @staticmethod
    def check_collisions(delta):
        objs = list(Ship.objects)
        player = Ship.player

        for i in range(len(objs)):
            if not objs[i].alive:
                continue
            for j in range(i + 1, len(objs)):
                if not objs[j].alive:
                    continue
                a, b = objs[i], objs[j]
                diff = a.pos - b.pos
                dist = diff.magnitude()
                min_dist = a.hit_radius + b.hit_radius
                if 0 < dist < min_dist:
                    push = diff.normalize()
                    overlap = min_dist - dist
                    a.vel += push * overlap * 8
                    b.vel -= push * overlap * 8
                    # Drones push each other apart but don't deal damage — prevents self-destruction
                    if a.ship_type == "SwarmDrone" or b.ship_type == "SwarmDrone":
                        continue
                    if a.collision_timer <= 0 and b.collision_timer <= 0:
                        a.take_hit(8)
                        b.take_hit(8)
                        a.collision_timer = 0.4
                        b.collision_timer = 0.4
                        Sounds.play("collision", 0.35)

        if player is not None:
            for ship in objs:
                if not ship.alive:
                    continue
                diff = ship.pos - player.pos
                dist = diff.magnitude()
                min_dist = ship.hit_radius + player.hit_radius
                if 0 < dist < min_dist:
                    push = diff.normalize()
                    overlap = min_dist - dist
                    ship.vel += push * overlap * 8
                    player.vel += push * overlap * 8
                    if ship.collision_timer <= 0:
                        ship.take_hit(8)
                        player.take_hit(12)
                        ship.collision_timer = 0.4
                        Sounds.play("collision", 0.55)

    def draw(self, camera):
        sc = camera.render_pos - self.pos
        rotated = pg.transform.rotate(self.img, self.dir.angle_to(Vector2(0, -1)))
        camera.surface.blit(rotated, rotated.get_rect(center=sc))

        if self.ship_type == "WardenEnemy" and self.shield_active:
            pg.draw.circle(
                camera.surface, (100, 160, 255),
                (int(sc.x), int(sc.y)), int(self.hit_radius * 1.4), 2
            )

        if self.ship_type == "MarauderEnemy" and self.state == "telegraph":
            color = (255, 140, 0) if (pg.time.get_ticks() // 80) % 2 else (180, 60, 0)
            cx, cy = int(sc.x), int(sc.y)
            pg.draw.circle(camera.surface, color, (cx, cy), int(self.hit_radius * 1.2), 3)
            # Arrow toward charge target (negate charge_dir for screen convention)
            tip = sc + (-self.charge_dir) * 90
            pg.draw.line(camera.surface, color, (cx, cy), (int(tip.x), int(tip.y)), 2)

    @staticmethod
    def update_all(delta):
        for ship in list(Ship.objects):
            ship.update(delta)
        Ship.check_collisions(delta)

    @staticmethod
    def draw_all(camera):
        for ship in Ship.objects:
            ship.draw(camera)
