"""Poses must move a sprite without redrawing it.

The whole reason poses are transforms rather than fresh art is that a transform
cannot take a sprite off-model. These tests hold that line: if a pose ever
introduces a colour the idle did not have, it has started painting, and every
palette guarantee upstream stops meaning anything.
"""
from PIL import Image

from meristem_generators.poses import (POSE_BANDS, apply_pose, fade, lean,
                                       pose_band, shift, squash)


def _idle(w=32, h=32):
    """A small asymmetric figure: a body, a lighter head, a tall thin prop.

    Asymmetric on purpose -- a symmetric test sprite hides sign errors in lean,
    and the tall prop is what exposed the death pose shearing itself apart.
    """
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for y in range(14, 28):
        for x in range(11, 21):
            px[x, y] = (90, 120, 70, 255)          # body
    for y in range(6, 14):
        for x in range(13, 19):
            px[x, y] = (210, 160, 110, 255)        # head
    for y in range(4, 30):
        px[23, y] = (170, 140, 90, 255)            # prop
    return img


def _colours(img):
    return {p[:3] for p in img.getdata() if p[3] > 0}


def _opaque(img):
    return sum(1 for p in img.getdata() if p[3] > 0)


def test_every_band_yields_the_frames_it_declares():
    idle = _idle()
    for band, specs in POSE_BANDS.items():
        assert len(pose_band(idle, band)) == len(specs), band


def test_poses_never_introduce_a_colour():
    """The core guarantee. A pose may move or hide pixels, never invent one."""
    idle = _idle()
    base = _colours(idle)
    for band in POSE_BANDS:
        for i, f in enumerate(pose_band(idle, band)):
            extra = _colours(f) - base
            assert not extra, f"{band}[{i}] introduced {extra}"


def test_lean_is_a_shear_not_a_rotation():
    """A rotation resamples and softens edges; a shear only moves whole rows."""
    idle = _idle()
    leaned = lean(idle, 6)
    assert _colours(leaned) <= _colours(idle)
    # feet row is the anchor and must not move
    assert [p[3] > 0 for p in idle.crop((0, 31, 32, 32)).getdata()] == \
           [p[3] > 0 for p in leaned.crop((0, 31, 32, 32)).getdata()]


def test_lean_moves_the_top_in_the_signed_direction():
    idle = _idle()
    def top_x(img):
        return min(x for x in range(32) for y in range(0, 10)
                   if img.getpixel((x, y))[3] > 0)
    assert top_x(lean(idle, 5)) > top_x(idle)
    assert top_x(lean(idle, -5)) < top_x(idle)


def test_shift_preserves_every_pixel_that_stays_on_canvas():
    idle = _idle()
    assert _opaque(shift(idle, 2, 1)) == _opaque(idle)


def test_squash_removes_rows_rather_than_scaling():
    idle = _idle()
    out = squash(idle, 3)
    assert out.size == idle.size
    assert _colours(out) <= _colours(idle)
    assert _opaque(out) < _opaque(idle)


def test_fade_touches_alpha_only():
    idle = _idle()
    out = fade(idle, 0.5)
    assert _colours(out) == _colours(idle)
    assert max(p[3] for p in out.getdata()) < 255


def test_lean_gradient_is_gentle():
    """Shear coherence lives in `lean`, so test it there rather than trying to
    recover it from a finished pose.

    Two earlier versions of this test measured the composite frame and both
    were wrong: the silhouette's left edge jumps wherever one part of the figure
    ends and another begins, and `squash` removes rows so row y in the output is
    not row y of the input at all. The primitive is where the property is.
    """
    idle = _idle()
    for amount in (-7, -3, 3, 7):
        out = lean(idle, amount)
        offsets = []
        for y in range(32):
            src = [x for x in range(32) if idle.getpixel((x, y))[3] > 0]
            dst = [x for x in range(32) if out.getpixel((x, y))[3] > 0]
            if src and dst:
                offsets.append(min(dst) - min(src))
        for p, q in zip(offsets, offsets[1:]):
            assert abs(p - q) <= 1, f"lean({amount}) steps {abs(p - q)}px between rows"


def test_death_lean_stays_within_budget():
    """Death sinks and fades; it must not shear the figure apart.

    An earlier version leaned the final frame 13px on a 32px sprite. It read as
    a corrupted sprite rather than a falling body, and a tall prop skewed worst
    because a shear moves its top furthest from its base. A quarter of the
    sprite's width is the ceiling.
    """
    CEILING = 8
    for i, (_, _, lean_px, _, _) in enumerate(POSE_BANDS["death"]):
        assert abs(lean_px) <= CEILING, f"death[{i}] leans {abs(lean_px)}px"


def test_death_sinks_and_fades():
    idle = _idle()
    frames = pose_band(idle, "death")
    tops = []
    for f in frames:
        ys = [y for y in range(32) for x in range(32) if f.getpixel((x, y))[3] > 0]
        tops.append(min(ys))
    assert tops == sorted(tops), "each death frame should sit lower than the last"
    assert frames[-1].getextrema()[3][1] < 255, "final death frame should fade"


def test_recovery_frames_return_to_idle():
    """The last frame of bow and stave is deliberately an identity transform --
    the action ends where idle begins, so the loop does not snap."""
    idle = _idle()
    for band in ("bow", "stave"):
        assert list(pose_band(idle, band)[-1].getdata()) == list(idle.getdata()), band


def test_apply_pose_is_deterministic():
    idle = _idle()
    spec = POSE_BANDS["sword"][1]
    assert list(apply_pose(idle, spec).getdata()) == list(apply_pose(idle, spec).getdata())
