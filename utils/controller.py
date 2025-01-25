from builtins import staticmethod
import pygame as pg
from pygame.math import Vector2


class Controller:
    axesL = Vector2(0, 0)
    axesR = Vector2(0, 0)
    triggers = [0, 0]
    buttons = {
        "A": False,
        "B": False,
        "X": False,
        "Y": False,
        "R1": False,
        "L1": False,
        "SH": False,
        "OP": False,
    }

    @staticmethod
    def reset():
        Controller.axesL = Vector2(0, 0)
        Controller.axesR = Vector2(0, 0)
        Controller.triggers = [0, 0]
        Controller.buttons = {
            "A": False,
            "B": False,
            "X": False,
            "Y": False,
            "R1": False,
            "L1": False,
            "SH": False,
            "OP": False,
        }

    @staticmethod
    def update(key):
        Controller.axesR = Vector2(
            key.get_pressed()[pg.K_l] - key.get_pressed()[pg.K_j],
            key.get_pressed()[pg.K_k] - key.get_pressed()[pg.K_i],
        )
        Controller.axesR = (
            Controller.axesR.normalize()
            if Controller.axesR.magnitude() > 0
            else Vector2(0, 0)
        )

        Controller.axesL = Vector2(
            key.get_pressed()[pg.K_d]
            - key.get_pressed()[pg.K_a]
            + key.get_pressed()[pg.K_RIGHT]
            - key.get_pressed()[pg.K_LEFT],
            key.get_pressed()[pg.K_w]
            - key.get_pressed()[pg.K_s]
            + key.get_pressed()[pg.K_UP]
            - key.get_pressed()[pg.K_DOWN],
        )
        Controller.axesL = (
            Controller.axesL.normalize()
            if Controller.axesL.magnitude() > 0
            else Vector2(0, 0)
        )

        Controller.buttons["A"] = key.get_pressed()[pg.K_SPACE]
        Controller.buttons["B"] = key.get_pressed()[pg.K_b]
        Controller.buttons["X"] = key.get_pressed()[pg.K_x]
        Controller.buttons["Y"] = key.get_pressed()[pg.K_y]

    @staticmethod
    def update_joysticks(joystick):
        Controller.axesL = Vector2(joystick.get_axis(0), joystick.get_axis(1))
        Controller.axesR = Vector2(joystick.get_axis(3), joystick.get_axis(4))
        Controller.buttons["A"] = joystick.get_button(0)
        Controller.buttons["B"] = joystick.get_button(1)
        Controller.buttons["X"] = joystick.get_button(2)
        Controller.buttons["Y"] = joystick.get_button(3)
