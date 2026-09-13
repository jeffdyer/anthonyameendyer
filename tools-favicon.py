"""Generate the favicon set for anthonyameendyer.org.

An abstract wave: two parallel swells in the card's cream, on a tile of the
deeper turquoise sampled from the water in Tony's photograph.

Drawn for 16px first. Thin strokes and three-deep stacks turn to mush at that
size, so there are two swells rather than three, each a sixth of the tile
thick, with a gap as wide as the strokes. Everything is rendered at 8x and box
filtered down, which is what gives the curves clean edges at sizes where a
single pixel is a large share of the mark.

Pure stdlib - no imaging libraries required.
"""
import math, struct, zlib

BG   = (0x47, 0xa2, 0xb0)   # deeper turquoise, just outside the shore break
INK  = (0xf9, 0xf7, 0xf1)   # the card's cream
SS   = 8                    # supersampling factor

RADIUS   = 0.18             # corner radius, as a share of the tile
CENTRES  = (0.34, 0.66)     # where each swell sits, top to bottom
AMP      = 0.100            # swell height, peak from centre
HALF     = 0.065            # half the stroke width


def wave_distance(x, y, cy):
    """Perpendicular distance from (x, y) to the swell centred on cy.

    Sampled rather than solved: the curve is walked in small steps and the
    nearest point wins. Cheap at this size, and it gives round ends and even
    thickness through the steep part of the curve, which measuring straight up
    the y axis would not.
    """
    best = 9.9
    steps = 64
    for i in range(steps + 1):
        sx = i / steps
        sy = cy + AMP * math.sin(2 * math.pi * (sx - 0.25))
        d = math.hypot(x - sx, y - sy)
        if d < best:
            best = d
    return best


def rounded_rect_alpha(x, y, r):
    """1 inside the tile, 0 outside, fractional across the corner arcs."""
    dx = max(r - x, x - (1 - r), 0.0)
    dy = max(r - y, y - (1 - r), 0.0)
    if dx == 0.0 or dy == 0.0:
        return 1.0 if (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0) else 0.0
    return 1.0 if math.hypot(dx, dy) <= r else 0.0


def render(size, rounded=True):
    """RGBA bytes for one square tile, top row first."""
    n = size * SS
    r = RADIUS if rounded else 0.0
    acc = [[0, 0, 0, 0] for _ in range(size * size)]

    for py in range(n):
        y = (py + 0.5) / n
        for px in range(n):
            x = (px + 0.5) / n
            if not rounded_rect_alpha(x, y, r):
                continue
            on_wave = any(wave_distance(x, y, cy) <= HALF for cy in CENTRES)
            col = INK if on_wave else BG
            cell = acc[(py // SS) * size + (px // SS)]
            cell[0] += col[0]; cell[1] += col[1]; cell[2] += col[2]; cell[3] += 255

    out = bytearray()
    total = SS * SS
    for cell in acc:
        a = cell[3] // total
        if a == 0:
            out += b'\x00\x00\x00\x00'
            continue
        # un-premultiply: the colour sums only cover the covered subsamples
        covered = cell[3] / 255
        out += bytes((round(cell[0] / covered), round(cell[1] / covered),
                      round(cell[2] / covered), a))
    return bytes(out)


def png(size, rgba):
    """Minimal RGBA PNG."""
    raw = bytearray()
    stride = size * 4
    for y in range(size):
        raw += b'\x00' + rgba[y * stride:(y + 1) * stride]   # filter type 0

    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(bytes(raw), 9))
            + chunk(b'IEND', b''))


def ico(pngs):
    """ICO wrapping PNG payloads - read by every browser in use."""
    head = struct.pack('<HHH', 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries, blob = b'', b''
    for size, data in pngs:
        entries += struct.pack('<BBBBHHII', size, size, 0, 0, 1, 32,
                               len(data), offset)
        offset += len(data)
        blob += data
    return head + entries + blob


def svg(box=32):
    """The same mark as vector, for browsers that prefer one.

    Each swell is one sine period, drawn as two cubic segments. The 0.36 on
    the control points is the usual approximation of a half sine by a cubic -
    close enough that it cannot be told from the rendered PNGs side by side.
    The group is clipped to the tile so the round caps do not paint over the
    corners they are supposed to leave open.
    """
    r = RADIUS * box
    sw = 2 * HALF * box
    paths = []
    for cy in CENTRES:
        c, a = cy * box, AMP * box
        hi, lo, mid = c - a, c + a, box / 2
        k = mid * 0.36
        paths.append(
            f'M0 {hi:g}C{k:g} {hi:g} {mid - k:g} {lo:g} {mid:g} {lo:g}'
            f'C{mid + k:g} {lo:g} {box - k:g} {hi:g} {box:g} {hi:g}')
    bg = '#%02x%02x%02x' % BG
    ink = '#%02x%02x%02x' % INK
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {box} {box}'>"
        f"<clipPath id='t'><rect width='{box}' height='{box}' rx='{r:g}'/></clipPath>"
        f"<rect width='{box}' height='{box}' rx='{r:g}' fill='{bg}'/>"
        f"<g clip-path='url(#t)' fill='none' stroke='{ink}' stroke-width='{sw:g}'"
        f" stroke-linecap='round'>"
        + ''.join(f"<path d='{d}'/>" for d in paths)
        + "</g></svg>\n")


if __name__ == '__main__':
    # 16, 32 and 48 all live inside the .ico; nothing needs them loose.
    open('favicon.ico', 'wb').write(
        ico([(s, png(s, render(s))) for s in (16, 32, 48)]))

    # iOS puts its own mask over this one, so it goes out square.
    open('apple-touch-icon.png', 'wb').write(png(180, render(180, rounded=False)))
    open('favicon.svg', 'w').write(svg())
    print('wrote favicon.ico, favicon.svg, apple-touch-icon.png')
