"""
8-bit chiptune sound synthesis — all sounds generated from numpy waveforms,
no external audio files required.
"""
import numpy as np
import pygame as pg

SR = 22050  # sample rate


# ── primitive waveforms ───────────────────────────────────────────────────────

def _sq(freq, dur, duty=0.5):
    n = int(SR * dur)
    phase = (np.arange(n) * freq / SR) % 1.0
    return np.where(phase < duty, 1.0, -1.0).astype(np.float32)

def _tri(freq, dur):
    n = int(SR * dur)
    phase = (np.arange(n) * freq / SR) % 1.0
    return (1.0 - 4.0 * np.abs(phase - 0.5)).astype(np.float32)

def _saw(freq, dur):
    n = int(SR * dur)
    phase = (np.arange(n) * freq / SR) % 1.0
    return (2.0 * phase - 1.0).astype(np.float32)

def _noise(dur):
    return np.random.default_rng(42).uniform(-1.0, 1.0, int(SR * dur)).astype(np.float32)

def _noise_r(dur):
    return np.random.uniform(-1.0, 1.0, int(SR * dur)).astype(np.float32)

def _sweep(f0, f1, dur, duty=0.5):
    """Square wave with linear frequency sweep."""
    n = int(SR * dur)
    freq = np.linspace(f0, f1, n)
    phase = (np.cumsum(freq) / SR) % 1.0
    return np.where(phase < duty, 1.0, -1.0).astype(np.float32)

def _sweep_tri(f0, f1, dur):
    n = int(SR * dur)
    freq = np.linspace(f0, f1, n)
    phase = (np.cumsum(freq) / SR) % 1.0
    return (1.0 - 4.0 * np.abs(phase - 0.5)).astype(np.float32)


# ── envelope + shaping ────────────────────────────────────────────────────────

def _adsr(arr, a=0.005, d=0.1, s=0.7, r=0.05):
    n  = len(arr)
    an = min(int(a * SR), n)
    dn = min(int(d * SR), n - an)
    rn = min(int(r * SR), n - an - dn)
    sn = max(0, n - an - dn - rn)
    env = np.concatenate([
        np.linspace(0, 1, an),
        np.linspace(1, s, dn),
        np.full(sn, s),
        np.linspace(s, 0, rn),
    ])
    return (arr * env[:n]).astype(np.float32)

def _fadeout(arr, tail=0.04):
    n  = len(arr)
    fo = min(int(tail * SR), n)
    arr = arr.copy()
    arr[n - fo:] *= np.linspace(1, 0, fo)
    return arr

def _cat(*parts):
    return np.concatenate(parts).astype(np.float32)

def _mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n, np.float32)
    for p in parts:
        out[:len(p)] += p
    return out

def _pad(arr, dur):
    """Append silence to reach `dur` seconds total."""
    n = int(SR * dur)
    if len(arr) >= n:
        return arr[:n]
    return np.concatenate([arr, np.zeros(n - len(arr), np.float32)])

def _to_sound(arr, vol=0.45):
    a = np.clip(arr * vol, -1.0, 1.0)
    s = (a * 32767).astype(np.int16)
    stereo = np.ascontiguousarray(np.column_stack([s, s]))
    return pg.sndarray.make_sound(stereo)


# ── sound recipe builders ─────────────────────────────────────────────────────

def _build_all():
    d = {}

    # ── player weapons ────────────────────────────────────────────────────────
    # Torpedo: two rising sweeps (two missiles launching)
    m  = _adsr(_sweep(160, 420, 0.13), a=0.01, d=0.05, s=0.5, r=0.07)
    d["fire_torpedo"]  = _to_sound(m, 0.5)

    # Cannon: short punchy burst
    c  = _adsr(_sq(900, 0.045, duty=0.3), a=0.002, d=0.025, s=0.15, r=0.015)
    d["fire_cannon"]   = _to_sound(c, 0.45)

    # Railgun: charge up then sharp zap discharge
    charge  = _adsr(_sweep(600, 1800, 0.09), a=0.04, d=0.04, s=0.8, r=0.01)
    zap     = _adsr(_sweep(1800, 150, 0.22), a=0.001, d=0.06, s=0.3, r=0.14)
    d["fire_railgun"]  = _to_sound(_cat(charge, zap), 0.6)

    # ── enemy weapons ─────────────────────────────────────────────────────────
    # Bullet (Viper, Phantom): high-pitched short zap
    eb = _adsr(_sq(1200, 0.035, duty=0.25), a=0.001, d=0.02, s=0.1, r=0.01)
    d["fire_bullet"]   = _to_sound(eb, 0.35)

    # Missile (Mauler, Warden, Marauder): low whoosh
    em = _adsr(_sweep(180, 340, 0.11), a=0.008, d=0.04, s=0.4, r=0.06)
    d["fire_missile"]  = _to_sound(em, 0.40)

    # Slug (Sentinel): heavy thud
    sl = _mix(
        _adsr(_sq(90, 0.15), a=0.002, d=0.06, s=0.3, r=0.08),
        _adsr(_noise(0.15) * 0.4, a=0.001, d=0.04, s=0.2, r=0.10),
    )
    d["fire_slug"]     = _to_sound(sl, 0.5)

    # ── explosions ────────────────────────────────────────────────────────────
    # Small (SwarmDrone, Viper, Phantom)
    xs = _mix(
        _adsr(_noise(0.22), a=0.001, d=0.07, s=0.25, r=0.12),
        _adsr(_sweep(110, 28, 0.22), a=0.001, d=0.08, s=0.3, r=0.13) * 0.4,
    )
    d["explosion_small"]  = _to_sound(xs, 0.55)

    # Medium (Mauler, Sentinel)
    xm = _mix(
        _adsr(_noise(0.32), a=0.001, d=0.1, s=0.35, r=0.18),
        _adsr(_sweep(80, 18, 0.32), a=0.001, d=0.1, s=0.35, r=0.18) * 0.55,
    )
    d["explosion_medium"] = _to_sound(xm, 0.65)

    # Large (Warden, Marauder)
    xl = _mix(
        _adsr(_noise(0.50), a=0.001, d=0.14, s=0.45, r=0.26),
        _adsr(_sweep(60, 12, 0.50), a=0.001, d=0.14, s=0.4, r=0.26) * 0.65,
        _pad(_adsr(_sq(50, 0.22), a=0.001, d=0.1, s=0.3, r=0.12) * 0.4, 0.50),
    )
    d["explosion_large"]  = _to_sound(xl, 0.70)

    # ── player damage ─────────────────────────────────────────────────────────
    # Shield absorb: high ping
    sh = _adsr(_sq(1500, 0.09, duty=0.3), a=0.002, d=0.04, s=0.2, r=0.04)
    d["hit_shield"]  = _to_sound(sh, 0.40)

    # Hull damage: lower buzz + noise
    hh = _mix(
        _adsr(_sq(200, 0.13), a=0.001, d=0.05, s=0.4, r=0.07),
        _adsr(_noise(0.13) * 0.5, a=0.001, d=0.04, s=0.25, r=0.08),
    )
    d["hit_hull"]    = _to_sound(hh, 0.50)

    # Warden shield break: electronic crack
    wb = _adsr(_sweep(1800, 150, 0.28, duty=0.4), a=0.003, d=0.08, s=0.3, r=0.16)
    d["warden_shield_break"] = _to_sound(wb, 0.55)

    # ── heal ──────────────────────────────────────────────────────────────────
    # C4-E4-G4-C5 ascending arpeggio
    notes_heal = [262, 330, 392, 523]
    heal_parts = []
    for f in notes_heal:
        note = _adsr(_tri(f, 0.09), a=0.005, d=0.03, s=0.65, r=0.05)
        heal_parts.append(_pad(note, 0.10))
    d["heal"] = _to_sound(_cat(*heal_parts), 0.50)

    # ── UI / meta ─────────────────────────────────────────────────────────────
    # Weapon switch
    ws = _adsr(_sq(640, 0.055), a=0.002, d=0.025, s=0.35, r=0.025)
    d["weapon_switch"] = _to_sound(ws, 0.38)

    # Menu navigate
    mn = _adsr(_sq(820, 0.04), a=0.001, d=0.018, s=0.2, r=0.018)
    d["menu_move"]   = _to_sound(mn, 0.32)

    # Menu select: two ascending notes
    ms1 = _pad(_adsr(_sq(880, 0.04), a=0.001, d=0.02, s=0.3, r=0.015), 0.06)
    ms2 = _adsr(_sq(1320, 0.04), a=0.001, d=0.02, s=0.4, r=0.015)
    d["menu_select"] = _to_sound(_cat(ms1, ms2), 0.40)

    # Menu back / settings exit: two descending notes
    mb1 = _pad(_adsr(_sq(660, 0.04), a=0.001, d=0.02, s=0.3, r=0.015), 0.06)
    mb2 = _adsr(_sq(440, 0.04), a=0.001, d=0.02, s=0.3, r=0.015)
    d["menu_back"]   = _to_sound(_cat(mb1, mb2), 0.38)

    # Grace countdown tick
    ct = _adsr(_sq(880, 0.06, duty=0.4), a=0.001, d=0.03, s=0.25, r=0.02)
    d["countdown_tick"] = _to_sound(ct, 0.50)

    # Game over: G4 → E4 → C4 descending, slow
    go_notes = [392, 330, 262]
    go_parts = []
    for f in go_notes:
        note = _adsr(_sq(f, 0.20), a=0.005, d=0.09, s=0.55, r=0.10)
        go_parts.append(_pad(note, 0.26))
    d["game_over"]   = _to_sound(_cat(*go_parts), 0.55)

    # New best: sparkle arpeggio C5-E5-G5-C6
    nb_notes = [523, 659, 784, 1047]
    nb_parts = []
    for f in nb_notes:
        note = _adsr(_tri(f, 0.07), a=0.003, d=0.025, s=0.65, r=0.04)
        nb_parts.append(_pad(note, 0.09))
    d["new_best"]    = _to_sound(_cat(*nb_parts), 0.48)

    # Ship-ship / player-ship collision
    col = _mix(
        _adsr(_noise(0.13) * 0.6, a=0.001, d=0.04, s=0.3, r=0.08),
        _adsr(_sweep(160, 45, 0.13), a=0.001, d=0.05, s=0.35, r=0.07) * 0.65,
    )
    d["collision"]   = _to_sound(col, 0.48)

    return d


# ── public interface ──────────────────────────────────────────────────────────

class Sounds:
    enabled  = True
    _sounds  = None   # built lazily on first play()

    @staticmethod
    def _ensure():
        if Sounds._sounds is None:
            if not pg.get_init():
                return
            if not pg.mixer.get_init():
                pg.mixer.init(SR, -16, 2, 512)
            Sounds._sounds = _build_all()

    @staticmethod
    def play(name, vol=1.0):
        if not Sounds.enabled:
            return
        Sounds._ensure()
        if Sounds._sounds:
            snd = Sounds._sounds.get(name)
            if snd:
                snd.set_volume(min(1.0, vol))
                snd.play()
