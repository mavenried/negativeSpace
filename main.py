#! /bin/env python3
from random import randint
import pygame as pg
import sys
import time
from pygame.math import Vector2


import utils

pg.init()
pg.joystick.init()
font = pg.font.SysFont("Jetbrainsmono Nerd Font", 12)

joysticks = []
screen = pg.display.set_mode((1920, 1080), pg.FULLSCREEN)
buffer = pg.surface.Surface((800, 450))
delta = 1 / 60

player = utils.Player(utils.GameData.current_ship)
camera = utils.Camera(Vector2(0, 0), buffer, player)
utils.Derilict(Vector2(randint(-1000, 1000), randint(-1000, 1000)), "ship Mauler")
utils.Derilict(Vector2(randint(-1000, 1000), randint(-1000, 1000)), "ship Viper")
utils.Derilict(Vector2(randint(-1000, 1000), randint(-1000, 1000)), "ship MaulerEnemy")
utils.Derilict(Vector2(randint(-1000, 1000), randint(-1000, 1000)), "ship ViperEnemy")

clock = pg.time.Clock()


def debug(*args):
    camera.surface.blit(font.render(" | ".join(args), True, "white"), (5, 430))


while True:
    stime = time.time()
    for event in pg.event.get():
        if event.type == pg.QUIT:
            pg.quit()
            sys.exit()
        if event.type == pg.JOYDEVICEADDED:
            joysticks.append(pg.joystick.Joystick(event.device_index))

    utils.Controller.reset()
    if any(joysticks):
        utils.Controller.update_joysticks(joysticks[0])
    utils.Controller.update(pg.key)
    camera.surface.fill("#000000")

    player.update(delta)
    utils.Derilict.update_all(delta)
    camera.update(delta)
    utils.Derilict.draw_all(camera)
    player.draw(camera)

    debug(
        f"{1 / delta:<3.0f}",
        f"({player.vel.x:.0f}, {player.vel.y:.0f})",
        f"({player.pos.x:.0f}, {player.pos.y:.0f})",
    )

    screen.blit(pg.transform.scale_by(buffer, 2.4), (0, 0))
    utils.Ui.render(screen)
    pg.display.flip()
    clock.tick(0)
    delta = time.time() - stime
