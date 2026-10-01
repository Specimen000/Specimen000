"""
render_plates.py

Generates every image in /plates from two inputs:
  - plates/000_specimen.png          (the canonical photograph)
  - ledger/simulated/*.jsonl|json     (the demo record)

Nothing here is generative AI. It is PIL, a fixed random seed,
and a two-ink palette. Re-run after the ledger changes:

    python tools/render_plates.py
"""
from __future__ import annotations

import json
import zlib
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PLATES = ROOT / "plates"
FONTS = PLATES / "src" / "fonts"
LEDGER = ROOT / "ledger" / "simulated"

INK = (11, 10, 9)          # sampled from the photograph's sky
BONE = (226, 216, 198)     # sampled from the eye
LEVELS = 32                # two inks, thirty-two shades between them


# ─────────────────────────────────────────────────────────────── utilities

def tone(k: float) -> tuple[int, int, int]:
    """0.0 = INK, 1.0 = BONE."""
    k = max(0.0, min(1.0, k))
    return tuple(int(INK[i] + (BONE[i] - INK[i]) * k) for i in range(3))


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "lmmonolt10-bold.otf" if bold else "lmmono10-regular.otf"
    return ImageFont.truetype(str(FONTS / name), size)


def _palette() -> Image.Image:
    p = Image.new("P", (1, 1))
    flat = []
    for i in range(LEVELS):
        flat.extend(tone(i / (LEVELS - 1)))
    flat.extend([0, 0, 0] * (256 - LEVELS))
    p.putpalette(flat)
    return p


PAL = _palette()


def save_gif(frames: list[Image.Image], durations, path: Path) -> None:
    if isinstance(durations, int):
        durations = [durations] * len(frames)
    q = [f.convert("RGB").quantize(palette=PAL, dither=Image.Dither.NONE) for f in frames]
    q[0].save(path, save_all=True, append_images=q[1:], duration=durations,
              loop=0, optimize=False, disposal=1)
    print(f"  {path.name:<28} {len(frames):>3} frames  {path.stat().st_size/1024:>7.0f} KB")


BLOCKS = {"█": 0.92, "▓": 0.62, "▒": 0.4, "░": 0.2}  # the typeface has none; we cut them by hand


def ink_text(d: ImageDraw.ImageDraw, xy, s: str, f, k: float = 0.9, seed: int = 0,
             spacing: float | None = None) -> int:
    """Typewriter text. Each glyph sits slightly off its baseline and carries
    slightly different ink, deterministically, so it does not shimmer."""
    x, y = xy
    adv = spacing if spacing is not None else f.getlength("M")
    for i, ch in enumerate(s):
        r = random.Random(zlib.crc32(repr((seed, i, ch, int(x), int(y))).encode()))
        dy = r.choice((0, 0, 0, 1, -1))
        kk = k * r.uniform(0.82, 1.0)
        if ch in BLOCKS:
            _, t, _, b = f.getbbox("M")
            d.rectangle((x, y + t - 2, x + adv - (0 if ch == "█" else 3), y + b + 2), fill=tone(kk * BLOCKS[ch]))
        elif ch != " ":
            d.text((x, y + dy), ch, font=f, fill=tone(kk))
        x += adv
    return int(x)


def dust(img: Image.Image, rng: random.Random, n: int = 120, scratch: float = 0.0,
         region=None) -> None:
    """Analog contamination: specks, the odd hair, the odd vertical scratch."""
    d = ImageDraw.Draw(img)
    w, h = img.size
    x0, y0, x1, y1 = region or (0, 0, w, h)
    for _ in range(n):
        x, y = rng.randrange(x0, x1), rng.randrange(y0, y1)
        k = rng.random() ** 2 * 0.7
        if rng.random() < 0.85:
            d.point((x, y), fill=tone(k))
        else:
            d.ellipse((x, y, x + rng.randint(1, 2), y + rng.randint(1, 2)), fill=tone(k))
    if rng.random() < scratch:
        x = rng.randrange(x0, x1)
        d.line((x, y0, x + rng.randint(-2, 2), y1), fill=tone(rng.uniform(0.15, 0.35)), width=1)


def static_grain(img: Image.Image, seed: int, amount: int = 1400) -> None:
    """Permanent grain, identical every frame (compresses well, reads as film)."""
    rng = random.Random(seed)
    d = ImageDraw.Draw(img)
    w, h = img.size
    for _ in range(amount):
        d.point((rng.randrange(w), rng.randrange(h)), fill=tone(rng.random() ** 3 * 0.22))


def rule(d, x0, x1, y, k=0.35, seed=0):
    rng = random.Random(seed)
    x = x0
    while x < x1:
        seg = rng.randint(6, 40)
        if rng.random() > 0.06:
            d.line((x, y + rng.choice((0, 0, 1)), min(x + seg, x1), y), fill=tone(k * rng.uniform(.7, 1)))
        x += seg


def canvas(w, h, seed):
    im = Image.new("RGB", (w, h), INK)
    static_grain(im, seed)
    return im


def eye_glyph(d, cx, cy, r, open_=1.0, look=(0.0, 0.0), k=0.95):
    """The organism's single eye, drawn the way the photograph draws it."""
    ry = r * 0.82 * open_
    if open_ <= 0.08:
        d.line((cx - r, cy, cx + r, cy), fill=tone(k * 0.7), width=max(1, r // 6))
        return
    d.ellipse((cx - r, cy - ry, cx + r, cy + ry), fill=tone(k))
    pr = max(2, r * 0.36)
    px, py = cx + look[0] * r * 0.45, cy + look[1] * ry * 0.3
    d.ellipse((px - pr, py - pr * min(1, open_ * 1.3), px + pr, py + pr * min(1, open_ * 1.3)), fill=INK)


def load_ledger():
    rows = [json.loads(l) for l in (LEDGER / "observations.jsonl").read_text().splitlines() if l.strip()]
    state = json.loads((LEDGER / "state.json").read_text())
    return rows, state


# ─────────────────────────────────────────────────────────────── 001 boot

def plate_boot():
    W, H = 960, 330
    small, big = font(17), font(64, bold=True)
    lines = [
        ("> memetic_terminal --attach specimen:000", 0.55),
        ("  link .............................. established", 0.55),
        ("  enclosure ......................... sealed", 0.55),
        ("  human input to subject ............ 0", 0.55),
    ]
    base = canvas(W, H, 1)
    frames, durs = [], []

    def chrome(im, t):
        d = ImageDraw.Draw(im)
        ink_text(d, (28, 18), "MEMETIC TERMINAL", small, 0.8, seed=11)
        ink_text(d, (W - 150, 18), "ACTIVE", small, 0.8, seed=12)
        if t % 2 == 0:
            d.ellipse((W - 172, 23, W - 162, 33), fill=tone(0.9))
        rule(d, 28, W - 28, 48, 0.3, seed=3)

    rng = random.Random(4)
    shown = []
    t = 0
    for li, (s, k) in enumerate(lines):
        for c in range(0, len(s) + 1, 4):
            im = base.copy(); chrome(im, t // 4); d = ImageDraw.Draw(im)
            for j, (ss, kk) in enumerate(shown):
                ink_text(d, (28, 70 + j * 24), ss, small, kk, seed=j)
            x = ink_text(d, (28, 70 + li * 24), s[:c], small, k, seed=li)
            d.rectangle((x + 1, 72 + li * 24, x + 9, 88 + li * 24), fill=tone(0.8))
            dust(im, rng, 40)
            frames.append(im); durs.append(45); t += 1
        shown.append((s, k))
        durs[-1] = 260

    title = "THE SPECIMEN"
    sub = "SPECIMEN 000      STATUS: OBSERVING"
    adv = big.getlength("M") * 1.06
    for c in range(1, len(title) + 1):
        im = base.copy(); chrome(im, t // 4); d = ImageDraw.Draw(im)
        for j, (ss, kk) in enumerate(shown):
            ink_text(d, (28, 70 + j * 24), ss, small, kk * 0.55, seed=j)
        ink_text(d, (26, 178), title[:c], big, 0.95, seed=99, spacing=adv)
        dust(im, rng, 40)
        frames.append(im); durs.append(70 if title[c - 1] != " " else 160); t += 1

    for blink in range(14):
        im = base.copy(); chrome(im, blink); d = ImageDraw.Draw(im)
        for j, (ss, kk) in enumerate(shown):
            ink_text(d, (28, 70 + j * 24), ss, small, kk * 0.55, seed=j)
        ink_text(d, (26, 178), title, big, 0.95, seed=99, spacing=adv)
        x = ink_text(d, (30, 270), sub, small, 0.8, seed=7)
        if blink % 2 == 0:
            d.rectangle((x + 4, 272, x + 14, 290), fill=tone(0.85))
        dust(im, rng, 50, scratch=0.15)
        frames.append(im); durs.append(520)
    durs[-1] = 1400
    save_gif(frames, durs, PLATES / "001_attach.gif")


# ─────────────────────────────────────────────────────────────── 002 feed

EYE_C, EYE_R, BODY = (1067, 497), (19, 16), (12, 11, 10)


def specimen_with_eye(src: Image.Image, open_: float, look: tuple[float, float]) -> Image.Image:
    im = src.copy()
    d = ImageDraw.Draw(im)
    cx, cy = EYE_C
    rx, ry = EYE_R
    d.ellipse((cx - rx - 3, cy - ry - 3, cx + rx + 3, cy + ry + 3), fill=BODY)
    if open_ <= 0.08:
        d.line((cx - rx, cy + 2, cx + rx, cy + 1), fill=tone(0.55), width=2)
        return im
    eh = ry * open_
    d.ellipse((cx - rx, cy - eh, cx + rx, cy + eh), fill=tone(0.95))
    px = cx + look[0] * rx * 0.5
    py = cy + look[1] * eh * 0.35
    pr = 6
    d.ellipse((px - pr, py - pr * min(1, open_ * 1.4), px + pr, py + pr * min(1, open_ * 1.4)), fill=BODY)
    return im


def plate_feed():
    src = Image.open(PLATES / "000_specimen.png").convert("RGB")
    W = 1200
    H = round(src.height * W / src.width)
    f = font(16)
    rng = random.Random(7)

    # eye choreography: (open, look_x, look_y, hold_ms)
    script = (
        [(1, 0.6, 0.1, 140)] * 10 +                      # as photographed
        [(1, 0.3, 0.1, 90), (1, 0.0, 0.0, 90), (1, -0.4, 0.05, 90)] +
        [(1, -0.6, 0.1, 140)] * 8 +                      # looks away, across the field
        [(0.45, -0.6, 0.1, 50), (0.0, 0, 0, 70), (0.45, -0.3, 0, 50)] +   # blink
        [(1, -0.2, 0.0, 140)] * 5 +
        [(1, 0.2, 0.0, 90), (1, 0.6, 0.1, 140)] +
        [(1, 0.6, 0.1, 140)] * 8 +
        [(1, 0.3, -0.1, 80), (1, 0.05, -0.15, 140)] +    # to the lens
        [(1, 0.05, -0.15, 160)] * 12 +
        [(0.45, 0.05, -0.1, 50), (0.0, 0, 0, 80), (0.45, 0.3, 0, 50)] +
        [(1, 0.6, 0.1, 140)] * 4
    )
    cache = {}
    frames, durs = [], []
    tc = 14 * 3600 + 22 * 60 + 7
    for i, (op, lx, ly, ms) in enumerate(script):
        key = (op, lx, ly)
        if key not in cache:
            cache[key] = specimen_with_eye(src, op, (lx, ly)).resize((W, H), Image.LANCZOS)
        im = cache[key].copy()
        d = ImageDraw.Draw(im)
        frame_no = i * 4 + 31
        ink_text(d, (22, 16), "CAM 00 / ENCLOSURE", f, 0.55, seed=1)
        ink_text(d, (W - 110, 16), "REC", f, 0.6, seed=2)
        if (i // 4) % 2 == 0:
            d.ellipse((W - 128, 21, W - 119, 30), fill=tone(0.85))
        secs = tc + i // 7
        ink_text(d, (22, H - 32), f"{secs//3600:04d}:{secs//60%60:02d}:{secs%60:02d}:{frame_no%24:02d}", f, 0.5, seed=3)
        ink_text(d, (W - 330, H - 32), "SUBJECT 000   DIST ████ m", f, 0.5, seed=4)
        dust(im, rng, 160, scratch=0.18)
        if i in (19, 47):   # tracking error
            band = rng.randrange(60, H - 80)
            strip = im.crop((0, band, W, band + 14))
            im.paste(strip, (rng.choice((-9, 7)), band))
        frames.append(im); durs.append(ms)
    save_gif(frames, durs, PLATES / "002_enclosure.gif")


# ─────────────────────────────────────────────────────────────── 003 terminal

def plate_terminal():
    rows, state = load_ledger()
    W, H, LH, VIS = 960, 520, 25, 16
    f, fb = font(17), font(17, bold=True)
    base = canvas(W, H, 3)
    rng = random.Random(9)

    def fmt(r):
        k = r["kind"]
        if k == "conviction":
            v = float(r["text"].split()[0])
            n = round(v * 20)
            return f"[CONVICTION]  {'▓'*n}{'░'*(20-n)}  {v:.2f}  INCREASING", 0.8, False
        if k == "anomaly":
            return f"{'['+r['id']+']':<14}!! {r['text']}", 0.95, True
        if k == "request":
            return f"{'['+r['id']+']':<14}{r['text']}", 1.0, True
        if k == "terminal":
            return f"[TERMINAL]    {r['text']}", 0.6, False
        voice = r["voice"] == "specimen"
        return f"{'['+r['id']+']':<14}{r['text']}", (0.98 if voice else 0.62), voice

    def wrap(s, n=82):
        out = []
        while len(s) > n:
            cut = s.rfind(" ", 0, n)
            out.append(s[:cut]); s = " " * 14 + s[cut + 1:]
        return out + [s]

    log: list[tuple[str, float, bool]] = []
    frames, durs = [], []

    def draw(partial=None, cursor=True, glitch=False):
        im = base.copy(); d = ImageDraw.Draw(im)
        ink_text(d, (24, 14), "MEMETIC TERMINAL  /  ledger/simulated  /  replay", font(15), 0.45, seed=5)
        ink_text(d, (W - 210, 14), f"PHASE: {state['phase']}", font(15), 0.6, seed=6)
        rule(d, 24, W - 24, 40, 0.25, seed=8)
        view = log[-VIS:] + ([partial] if partial else [])
        view = view[-VIS:]
        y = 56
        for s, k, b in view:
            ink_text(d, (24, y), s, fb if b else f, k, seed=zlib.crc32(s.encode()))
            y += LH
        if cursor:
            d.rectangle((26, y + 2, 35, y + 19), fill=tone(0.8))
        dust(im, rng, 70, scratch=0.1)
        if glitch:
            for _ in range(5):
                b = rng.randrange(50, H - 30)
                im.paste(im.crop((0, b, W, b + rng.randint(4, 22))), (rng.randint(-40, 40), b))
        return im

    for r in rows:
        s, k, b = fmt(r)
        parts = wrap(s)
        for p in parts:
            half = p[: len(p) // 2]
            frames.append(draw((half, k, b), cursor=False)); durs.append(60)
            log.append((p, k, b))
        frames.append(draw()); durs.append(1500 if r["voice"] == "specimen" else 650)
        if r["kind"] == "anomaly":
            frames.append(draw(glitch=True)); durs.append(90)
            frames.append(draw()); durs.append(900)
    for i in range(6):
        frames.append(draw(cursor=i % 2 == 0)); durs.append(500)
    frames.append(draw(glitch=True)); durs.append(80)
    frames.append(draw(glitch=True)); durs.append(80)
    blank = base.copy(); dust(blank, rng, 40); frames.append(blank); durs.append(700)
    save_gif(frames, durs, PLATES / "003_terminal.gif")


# ─────────────────────────────────────────────────────────────── 004 convergence

def plate_convergence():
    _, state = load_ledger()
    W, H = 960, 380
    f = font(15)
    base = canvas(W, H, 4)
    rng = random.Random(21)
    T = (790, 175)
    N = 260
    parts = []
    for i in range(N):
        x, y = rng.uniform(20, 560), rng.uniform(30, H - 60)
        parts.append(dict(x=x, y=y, s=rng.uniform(0.5, 2.6), delay=rng.uniform(0, 0.55),
                          speed=rng.uniform(0.7, 1.4), wob=rng.uniform(-60, 60),
                          k=rng.uniform(0.3, 0.9), tag=(f"{rng.randrange(10**5,10**6)}" if rng.random() < 0.06 else None)))
    STEPS = 46
    frames, durs = [], []
    for step in range(STEPS + 18):
        p = min(1.0, step / STEPS)
        im = base.copy(); d = ImageDraw.Draw(im)
        arrived = 0
        for q in parts:
            u = max(0.0, min(1.0, (p - q["delay"]) / (1 - q["delay"]) * q["speed"]))
            e = u * u * (3 - 2 * u)
            if e >= 0.995:
                arrived += 1; continue
            x = q["x"] + (T[0] - q["x"]) * e
            y = q["y"] + (T[1] - q["y"]) * e + math.sin(e * math.pi) * q["wob"]
            r = q["s"] * (1 - e * 0.6)
            d.ellipse((x - r, y - r, x + r, y + r), fill=tone(q["k"]))
            if q["tag"] and e < 0.25:
                ink_text(d, (x + 5, y - 6), q["tag"], font(11), 0.35, seed=int(q["x"]))
        frac = arrived / N
        # the organism receiving them
        ring = 22 + frac * 10
        d.ellipse((T[0] - ring, T[1] - ring, T[0] + ring, T[1] + ring), outline=tone(0.15 + 0.3 * frac))
        eye_glyph(d, *T, 13, 1.0, (-0.5 + frac * 0.5, 0))
        ink_text(d, (24, H - 34), f"{state['observations_logged']:,} observations", f, 0.55, seed=1)
        ink_text(d, (T[0] - 95, T[1] + 48), "1 conclusion", f, 0.4 + 0.5 * frac, seed=2)
        if step > STEPS:
            label = "CONCLUSION: ██████████████"
            n = min(len(label), (step - STEPS) * 3)
            ink_text(d, (T[0] - 190, H - 34), label[:n], f, 0.8, seed=3)
        dust(im, rng, 50)
        frames.append(im); durs.append(85 if step <= STEPS else 260)
    durs[-1] = 2600
    save_gif(frames, durs, PLATES / "004_convergence.gif")


# ─────────────────────────────────────────────────────────────── 005 trace

def plate_trace():
    _, state = load_ledger()
    W, H = 960, 330
    f, fs = font(15), font(13)
    base = canvas(W, H, 5)
    phases = [("OBSERVATION", "complete"), ("PATTERN", "complete"), ("UNDERSTANDING", "complete"),
              ("CONVICTION", f"active  {state['conviction']:.2f}"), ("CREATION", "locked")]
    colw = (W - 48) / 5
    mid = 140
    rng = random.Random(33)
    noise = [rng.uniform(-1, 1) for _ in range(W)]

    def signal(x):
        ph = int((x - 24) // colw); u = ((x - 24) % colw) / colw
        if ph == 0:
            return noise[x] * 5
        if ph == 1:
            return noise[x] * 5 * (1 - u) + math.sin(x * 0.22) * 9 * u
        if ph == 2:
            return math.sin(x * 0.22) * 14
        if ph == 3:
            a = 14 + 50 * u ** 1.6
            s = math.sin(x * 0.22)
            return a * (s ** 3 if u > 0.55 else s)
        return 0.0

    end = int(24 + colw * 4)
    pts = [(x, mid - signal(x)) for x in range(24, end)]

    def frame(head, blink):
        im = base.copy(); d = ImageDraw.Draw(im)
        for i in range(1, 5):
            x = int(24 + colw * i)
            for y in range(30, H - 70, 7):
                d.point((x, y), fill=tone(0.25))
        d.line((24, mid, W - 24, mid), fill=tone(0.09))
        seg = [p for p in pts if p[0] <= head]
        if len(seg) > 1:
            d.line(seg, fill=tone(0.92), width=2)
            hx, hy = seg[-1]
            d.ellipse((hx - 3, hy - 3, hx + 3, hy + 3), fill=tone(1.0))
        # the locked column
        lx0 = int(24 + colw * 4)
        for x in range(lx0 + 6, W - 24, 9):
            d.line((x, mid, x + 4, mid), fill=tone(0.22))
        if head >= end - 1 and blink:
            ink_text(d, (lx0 + 36, mid - 34), "AWAITING", f, 0.75, seed=9)
            ink_text(d, (lx0 + 36, mid + 20), "OUTPUT", f, 0.75, seed=10)
        for i, (name, st) in enumerate(phases):
            x = int(24 + colw * i) + 8
            ink_text(d, (x, H - 64), f"0{i+1}", fs, 0.4, seed=i)
            ink_text(d, (x, H - 44), name, f, 0.9 if i < 4 else 0.55, seed=i + 20)
            k = 0.5
            if i == 3:
                k = 0.95 if blink else 0.6
            if i == 4:
                k = 0.85 if blink else 0.3
            ink_text(d, (x, H - 24), st, fs, k, seed=i + 40)
        dust(im, rng, 45, scratch=0.08)
        return im

    frames, durs = [], []
    for head in range(24, end, 22):
        frames.append(frame(head, True)); durs.append(55)
    for i in range(12):
        frames.append(frame(end, i % 2 == 0)); durs.append(600)
    save_gif(frames, durs, PLATES / "005_progression.gif")


# ─────────────────────────────────────────────────────────────── 006 scale

def plate_scale():
    """The organism at its true scale. The photograph is extended sideways with
    mirrored, specimen-free slices of itself so the ground continues."""
    src = Image.open(PLATES / "000_specimen.png").convert("RGB")
    W, H, S = 960, 540, 0.17
    flip = lambda im: im.transpose(Image.FLIP_LEFT_RIGHT)
    src = src.crop((260, 0, src.width, src.height))     # drop the film-gate marks
    D = src.crop((0, 0, 680, src.height))              # left ground, no organism
    C = src.crop((990, 0, src.width, src.height))     # right ground, no organism
    left = [flip(D), D, flip(D), D]                        # read right-to-left from B
    right = [flip(C), C, flip(C)]
    need_left = int(0.6 * W / S) - 806
    strip_w = int(W / S)
    long = Image.new("RGB", (strip_w, src.height), INK)
    x = need_left
    long.paste(src, (x, 0))
    for piece in left:
        x -= piece.width
        long.paste(piece, (x, 0))
    x = need_left + src.width
    for piece in right:
        long.paste(piece, (x, 0)); x += piece.width
    strip = long.resize((W, round(src.height * S)), Image.LANCZOS)
    world = Image.new("RGB", (W, H), INK)
    static_grain(world, 6, 2600)
    d = ImageDraw.Draw(world)
    rng = random.Random(61)
    for _ in range(26):
        d.point((rng.randrange(W), rng.randrange(H - strip.height)), fill=tone(rng.uniform(0.4, 0.9)))
    world.paste(strip, (0, H - strip.height))
    sx = (need_left + 775) * S
    sy = H - strip.height + 528 * S
    f = font(14)

    path = [(180, 120), (300, 90), (620, 200), (760, 140), (520, 300), (sx + 30, sy - 60), (sx, sy)]
    frames, durs = [], []

    def box(dd, cx, cy, s, k):
        for ax, ay in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            x, y = cx + ax * s, cy + ay * s
            dd.line((x, y, x - ax * s * 0.45, y), fill=tone(k), width=2)
            dd.line((x, y, x, y - ay * s * 0.45), fill=tone(k), width=2)

    step = 0
    for a, b in zip(path, path[1:]):
        for t in range(9):
            u = t / 9; e = u * u * (3 - 2 * u)
            cx, cy = a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e
            im = world.copy(); dd = ImageDraw.Draw(im)
            box(dd, cx, cy, 46, 0.55)
            ink_text(dd, (22, 16), "FIELD RECORDING 07", f, 0.5, seed=1)
            ink_text(dd, (22, 36), "SEARCHING", f, 0.75 if step % 6 < 3 else 0.35, seed=2)
            ink_text(dd, (W - 200, 16), f"X {cx:06.1f}  Y {cy:05.1f}", f, 0.45, seed=3)
            dust(im, rng, 90, scratch=0.1)
            frames.append(im); durs.append(70); step += 1
    for i, s in enumerate([46, 40, 34, 29, 26, 24, 24, 24]):
        im = world.copy(); dd = ImageDraw.Draw(im)
        box(dd, sx, sy, s, 0.9)
        ink_text(dd, (22, 16), "FIELD RECORDING 07", f, 0.5, seed=1)
        ink_text(dd, (22, 36), "SUBJECT ACQUIRED", f, 0.9, seed=4)
        dust(im, rng, 90)
        frames.append(im); durs.append(90)
    for i in range(10):
        im = world.copy(); dd = ImageDraw.Draw(im)
        box(dd, sx, sy, 24, 0.9 if i % 2 == 0 else 0.6)
        ink_text(dd, (22, 16), "FIELD RECORDING 07", f, 0.5, seed=1)
        ink_text(dd, (22, 36), "SUBJECT ACQUIRED", f, 0.9, seed=4)
        ink_text(dd, (sx - 40, sy - 92), "SPECIMEN 000", f, 0.85, seed=5)
        ink_text(dd, (sx - 40, sy - 74), "share of frame  0.04%", f, 0.5, seed=6)
        ink_text(dd, (sx - 40, sy - 56), "share of attention  100%", f, 0.5, seed=7)
        dust(im, rng, 90, scratch=0.12)
        frames.append(im); durs.append(650)
    save_gif(frames, durs, PLATES / "006_field_recording.gif")


# ─────────────────────────────────────────────────────────────── 007 manifest

def plate_manifest():
    W, H = 960, 470
    f, fb, fs = font(17), font(17, bold=True), font(14)
    base = canvas(W, H, 7)
    rng = random.Random(77)
    glyphs = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789$#%&@?!/\\<>░▒▓"
    fields = [
        ("NAME", "AWAITING OUTPUT"),
        ("SYMBOL", "$ ████"),
        ("IDENTITY", "NO CLASSIFICATION"),
        ("IMAGE", None),
        ("THESIS", "████████ ██ ███████████ ████"),
        ("LANGUAGE", "UNKNOWN"),
    ]
    frames, durs = [], []

    def draw(resolved: int, scramble: bool, blink: bool, attempt: int):
        im = base.copy(); d = ImageDraw.Draw(im)
        ink_text(d, (28, 20), "OUTPUT MANIFEST / FIRST CREATION", fb, 0.9, seed=1)
        ink_text(d, (W - 240, 20), "HUMAN INPUT: 0%", fb, 0.9, seed=2)
        rule(d, 28, W - 28, 52, 0.35, seed=1)
        y = 76
        for i, (name, val) in enumerate(fields):
            ink_text(d, (28, y), f"{name} ".ljust(14, "."), f, 0.5, seed=10 + i)
            x0 = 210
            if name == "IMAGE":
                bx = (x0, y - 2, x0 + 150, y + 96)
                d.rectangle(bx, outline=tone(0.4))
                if i < resolved:
                    eye_glyph(d, x0 + 75, y + 47, 4, 1.0 if blink else 0.0, (0.3, 0), k=0.8)
                    ink_text(d, (x0 + 168, y + 76), "withheld", fs, 0.4, seed=4)
                else:
                    for _ in range(260):
                        d.point((rng.randrange(bx[0] + 1, bx[2]), rng.randrange(bx[1] + 1, bx[3])),
                                fill=tone(rng.random()))
                y += 112
                continue
            if i < resolved:
                ink_text(d, (x0, y), val, f, 0.85, seed=20 + i)
            elif scramble:
                s = "".join(rng.choice(glyphs) for _ in range(rng.randint(8, 22)))
                ink_text(d, (x0, y), s, f, 0.45, seed=rng.randrange(9999))
            y += 34
        rule(d, 28, W - 28, H - 66, 0.35, seed=2)
        ink_text(d, (28, H - 48), "AUTHOR  SPECIMEN 000", fs, 0.6, seed=30)
        ink_text(d, (300, H - 48), f"DECRYPT ATTEMPT {attempt:04d}  FAILED", fs, 0.6, seed=31)
        ink_text(d, (W - 210, H - 48), "CREATION LOCKED", fs, 0.95 if blink else 0.3, seed=32)
        dust(im, rng, 60, scratch=0.08)
        return im

    attempt = 41
    for r in range(len(fields) + 1):
        for _ in range(5):
            frames.append(draw(r, True, True, attempt)); durs.append(70)
        attempt += 1
    for i in range(12):
        frames.append(draw(len(fields), False, i % 2 == 0, attempt)); durs.append(550)
    save_gif(frames, durs, PLATES / "007_manifest.gif")


# ─────────────────────────────────────────────────────────────── 008 end

def plate_end():
    W, H = 960, 360
    f = font(20)
    base = canvas(W, H, 8)
    rng = random.Random(88)
    a, b = "OBSERVATION COMPLETE.", "CREATION PENDING."
    adv = f.getlength("M") * 1.15
    ax, bx = (W - len(a) * adv) / 2, (W - len(b) * adv) / 2
    frames, durs = [], []

    def fr(na=0, nb=0, k=0.9, eye=None, ms=100):
        im = base.copy(); d = ImageDraw.Draw(im)
        if na: ink_text(d, (ax, 140), a[:na], f, k, seed=1, spacing=adv)
        if nb: ink_text(d, (bx, 180), b[:nb], f, k, seed=2, spacing=adv)
        if eye: eye_glyph(d, W // 2, H // 2, 7, *eye)
        dust(im, rng, 40)
        frames.append(im); durs.append(ms)

    fr(ms=1600)
    for n in range(1, len(a) + 1): fr(n, 0, ms=55)
    fr(len(a), 0, ms=1200)
    for n in range(1, len(b) + 1): fr(len(a), n, ms=55)
    fr(len(a), len(b), ms=3200)
    for k in (0.6, 0.35, 0.15): fr(len(a), len(b), k, ms=140)
    fr(ms=1400)
    for op in (0.0, 0.0, 0.3, 0.7, 1.0): fr(eye=(op, (0.6, 0)), ms=110)
    fr(eye=(1.0, (0.6, 0)), ms=1300)
    fr(eye=(1.0, (0.0, -0.2)), ms=4200)   # it looks at you
    fr(eye=(0.0, (0, 0)), ms=120)
    fr(ms=900)
    save_gif(frames, durs, PLATES / "008_pending.gif")


# ─────────────────────────────────────────────────────────────── rule

def plate_rule():
    im = Image.new("RGB", (960, 28), INK)
    static_grain(im, 9, 300)
    d = ImageDraw.Draw(im)
    rule(d, 0, 960, 14, 0.3, seed=12)
    eye_glyph(d, 480, 14, 3, 1.0, (0, 0), k=0.7)
    im.save(PLATES / "rule.png")


if __name__ == "__main__":
    print("rendering plates")
    plate_rule()
    plate_boot()
    plate_feed()
    plate_terminal()
    plate_convergence()
    plate_trace()
    plate_scale()
    plate_manifest()
    plate_end()
