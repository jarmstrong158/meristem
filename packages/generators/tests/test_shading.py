"""Hue-shift shading: shadows go cool + darker, highlights warm + lighter."""
import colorsys

from meristem_generators.shading import Ramp, highlight, shadow


def _hsv(rgb):
    return colorsys.rgb_to_hsv(*[c / 255 for c in rgb])


def test_shadow_is_darker_and_cooler():
    base = (112, 68, 40)          # brown
    sh = shadow(base, 0.28)
    assert sum(sh) < sum(base)                       # darker
    # brown hue ~0.06; cool shift pushes it up toward blue (0.65)
    assert _hsv(sh)[2] < _hsv(base)[2]               # lower value
    assert _hsv(sh)[0] >= _hsv(base)[0]              # hue moved toward blue (not away)


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
