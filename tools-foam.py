"""Generate a seamlessly tiling surf-foam texture as an RGBA PNG.

Mirrors the role snow.png plays on jessedaviddyer.org: a subtle, static,
repeating overlay. Pure stdlib - no imaging libraries required.
"""
import math, random, struct, zlib

W, H = 512, 384
SEED = 20261208  # Tony's birthday, for a reproducible tile

buf = bytearray(W * H * 4)  # straight RGBA, premultiply-free source-over


def blend(x, y, r, g, b, a):
    """Source-over a single pixel, wrapping at the tile edges."""
    if a <= 0:
        return
    x %= W
    y %= H
    i = (y * W + x) * 4
    da = buf[i + 3] / 255.0
    sa = min(a, 1.0)
    out_a = sa + da * (1 - sa)
    if out_a <= 0:
        return
    for off, sc in ((0, r), (1, g), (2, b)):
        dc = buf[i + off] / 255.0
        buf[i + off] = int(round(((sc / 255.0) * sa + dc * da * (1 - sa)) / out_a * 255))
    buf[i + 3] = int(round(out_a * 255))


def bubble(cx, cy, rad, fill_a, rim_a):
    """A foam bubble: soft white disc with a slightly brighter rim.

    Coverage is computed from the distance field so edges stay smooth, and
    every pixel wraps - that is what makes the tile seamless.
    """
    lo, hi = int(math.floor(-rad - 2)), int(math.ceil(rad + 2))
    for dy in range(lo, hi + 1):
        for dx in range(lo, hi + 1):
            d = math.hypot(dx + 0.5, dy + 0.5)
            if d > rad + 1.5:
                continue
            cov = max(0.0, min(1.0, rad - d + 0.5))       # anti-aliased disc
            if cov <= 0:
                continue
            # Rim: peaks near the circumference, fades inward.
            rim = max(0.0, 1.0 - abs(d - (rad - 0.6)) / max(0.9, rad * 0.42))
            a = fill_a * cov * (1.0 - 0.35 * rim) + rim_a * rim * cov
            blend(int(cx) + dx, int(cy) + dy, 255, 255, 255, a)


rng = random.Random(SEED)

# Foam is patchy, not uniform: scatter most bubbles around drifting clusters,
# then sprinkle a sparse wash of spray across the whole tile.
for _ in range(16):
    ccx, ccy = rng.uniform(0, W), rng.uniform(0, H)
    spread = rng.uniform(26, 52)
    for _ in range(rng.randint(22, 40)):
        bx = ccx + rng.gauss(0, spread)
        by = ccy + rng.gauss(0, spread * 0.72)
        rad = rng.choice([0.9, 1.2, 1.5, 1.9, 2.4, 3.0, 3.8, 4.6])
        rad *= rng.uniform(0.85, 1.2)
        bubble(bx, by, rad, fill_a=rng.uniform(0.05, 0.12), rim_a=rng.uniform(0.10, 0.22))

for _ in range(620):  # fine spray between the clusters
    bubble(rng.uniform(0, W), rng.uniform(0, H),
           rng.uniform(0.6, 1.4), fill_a=rng.uniform(0.03, 0.09), rim_a=0.06)

for _ in range(10):  # a few larger, softer bubbles for depth
    bubble(rng.uniform(0, W), rng.uniform(0, H),
           rng.uniform(5.5, 8.0), fill_a=rng.uniform(0.02, 0.05), rim_a=rng.uniform(0.06, 0.12))

# --- encode PNG (color type 6, 8-bit RGBA) ---
raw = bytearray()
for y in range(H):
    raw.append(0)  # filter: None
    raw += buf[y * W * 4:(y + 1) * W * 4]


def chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


png = (b"\x89PNG\r\n\x1a\n"
       + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
       + chunk(b"IEND", b""))

out = "/Users/jeffdyer/work/anthonyameendyer/foam.png"
with open(out, "wb") as f:
    f.write(png)
print(f"wrote {out}  {W}x{H}  {len(png):,} bytes")
