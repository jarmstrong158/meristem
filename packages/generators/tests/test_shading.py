"""Hue-shift shading: shadows go cool + darker, highlights warm + lighter."""
import colorsys

from meristem_generators.shading import Ramp, highlight, shadow


def _hsv(rgb):
    return colorsys.rgb_to_hsv(*[c / 255 for c in rgb])


def _arc(a, b):
    """Shortest distance between two hues on the wheel, in turns."""
    d = abs(a - b) % 1.0
    return min(d, 1.0 - d)


def test_shadow_is_darker_and_cooler():
    base = (112, 68, 40)          # brown
    sh = shadow(base, 0.28)
    assert sum(sh) < sum(base)                       # darker
    assert _hsv(sh)[2] < _hsv(base)[2]               # lower value
    # Cooler means CLOSER TO 0.65 ALONG THE WHEEL, not numerically greater.
    # The old assertion was `hue >= base hue`, which is only true if you treat
    # hue as a line -- and it was passing because the code had the same bug:
    # brown walked 23 deg -> 41 deg, up through yellow-green, and every warm
    # shadow in the suite came out olive.
    assert _arc(_hsv(sh)[0], 0.65) < _arc(_hsv(base)[0], 0.65)


def test_warm_shadows_do_not_drift_toward_green():
    """The olive-face regression, pinned. Skin and brown must rotate toward red."""
    for base in [(224, 160, 106), (200, 154, 120), (125, 78, 48), (112, 68, 40)]:
        h0 = _hsv(base)[0] * 360
        h1 = _hsv(shadow(base, 0.28))[0] * 360
        assert h1 < h0, f"{base}: shadow hue {h1:.1f} drifted up from {h0:.1f}"


def test_cool_ramps_are_unchanged_by_the_short_way():
    """Greens and blues already took the direct path; they must not move."""
    for base in [(90, 150, 70), (90, 120, 200)]:
        h0 = _hsv(base)[0]
        h1 = _hsv(shadow(base, 0.28))[0]
        assert _arc(h0, h1) < 0.06


def test_highlight_is_lighter_and_warmer():
    base = (112, 68, 40)
    hi = highlight(base, 0.16)
    assert sum(hi) > sum(base)                       # lighter
    assert _hsv(hi)[2] > _hsv(base)[2]


def test_ramp_gives_three_distinct_browns():
    r = Ramp((112, 68, 40))
    assert r.shadow != r.base != r.highlight
    # all three stay brownish (red-dominant channel), not grey/purple
    for c in (r.shadow, r.base, r.highlight):
        assert c[0] >= c[1] >= c[2]                  # R >= G >= B => warm brown, never grey/blue
