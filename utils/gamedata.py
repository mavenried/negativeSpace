# Player ship definitions
# (name, asset, maxHP, maxSP, maxvel, acc, hit_radius, description)
PLAYER_SHIPS = [
    ("Viper",    "Viper",    75,  25,  550, 700,  20, "Balanced all-rounder"),
    ("Phantom",  "Phantom",  45,  15,  800, 1000, 14, "Agile scout — fast, fragile"),
    ("Mauler",   "Mauler",   150, 50,  300, 500,  28, "Heavy assault — slow, durable"),
    ("Sentinel", "Sentinel", 90,  60,  200, 400,  24, "Long-range — high shields"),
    ("Warden",   "Warden",   200, 100, 180, 350,  32, "Shield tank — maximum protection"),
    ("Marauder", "Marauder", 180, 75,  260, 600,  36, "Ram hull — built to collide"),
]

# Per-stat maximums for normalising stat bars in the selection screen
_SHIP_STAT_MAX = {
    "maxHP":  max(s[2] for s in PLAYER_SHIPS),
    "maxSP":  max(s[3] for s in PLAYER_SHIPS),
    "maxvel": max(s[4] for s in PLAYER_SHIPS),
    "acc":    max(s[5] for s in PLAYER_SHIPS),
}


class GameData:
    current_ship   = "Viper"
    maxHP = 75;  curHP = 75
    maxSP = 25;  curSP = 25
    kills          = 0
    current_weapon = "TORPEDO"
    time           = 0.0
    font_file      = "rainyhearts.ttf"
