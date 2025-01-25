import pygame as pg
from .gamedata import GameData


class Ui:
    @staticmethod
    def render(screen):
        Ui.render_avatar(screen)
        Ui.render_healthbar(screen)

    @staticmethod
    def render_avatar(screen):
        image = pg.image.load(f"Assets/{GameData.current_ship}.png")
        screen.blit(image, image.get_rect(center=(20, 30)))

    @staticmethod
    def render_healthbar(screen):
        total_segments = int((GameData.maxHP + GameData.maxSP) / 5)
        health_segments = int(GameData.curHP / 5)
        sheild_segments = health_segments + int((GameData.curSP / 5))
        maxsheild_segments = int(GameData.maxHP / 5)
        pos = (40, 20)

        pg.draw.rect(screen, "grey", (*pos, 20 * maxsheild_segments, 20))
        pg.draw.rect(screen, "blue", (*pos, 20 * sheild_segments, 20))
        pg.draw.rect(screen, "red", (*pos, 20 * health_segments, 20))
        pg.draw.rect(screen, "white", (*pos, 20 * total_segments, 20), 2)
