"""Parametric wall-mount display models for football jerseys, scarves and balls.

Coordinate system (as mounted): wall = plane Y=0, +Y out of the wall,
X = width, Z = up. All dimensions in millimetres.

Run:  python3 models/build.py     -> writes models/stl, models/step
"""
from pathlib import Path
import cadquery as cq

OUT = Path(__file__).parent

# ---------------------------------------------------------------- shared mount
# Every product slides down onto the same screwed-on dovetail wall cleat.
CLEAT_W_WALL = 12.0   # cleat width touching the wall
CLEAT_W_FRONT = 20.0  # cleat width at its front (wide) face
CLEAT_T = 5.0         # cleat thickness
CLEAT_H = 29.0        # cleat height
SLOT_LEN = 30.0       # slot length in the product (open at the bottom)
FIT = 0.25            # clearance per side, cleat <-> slot
SCREW_D = 4.5         # clearance hole for 4 mm countersunk screws
SCREW_HEAD_D = 9.0
JOINT_FIT = 0.2       # clearance per side, arm tongue <-> block pocket


def _trapezoid(w0, w1, t, length, y0=0.0):
    pts = [(-w0 / 2, y0), (w0 / 2, y0), (w1 / 2, t), (-w1 / 2, t)]
    return cq.Workplane("XY").polyline(pts).close().extrude(length)


def box(x0, x1, y0, y1, z0, z1):
    return (cq.Workplane("XY")
            .box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


def wall_cleat():
    """Dovetail cleat, origin at the centre of its wall face bottom edge."""
    c = _trapezoid(CLEAT_W_WALL, CLEAT_W_FRONT, CLEAT_T, CLEAT_H)
    c = c.faces(">Z").chamfer(1.2)  # lead-in at the top
    for z in (CLEAT_H / 2 - 8, CLEAT_H / 2 + 8):
        hole = cq.Solid.makeCylinder(SCREW_D / 2, CLEAT_T + 2,
                                     cq.Vector(0, -1, z), cq.Vector(0, 1, 0))
        depth = (SCREW_HEAD_D - SCREW_D) / 2
        sink = cq.Solid.makeCone(SCREW_D / 2, SCREW_HEAD_D / 2, depth,
                                 cq.Vector(0, CLEAT_T - depth, z),
                                 cq.Vector(0, 1, 0))
        c = c.cut(hole).cut(sink)
    return c


def cut_slot(body, z_bottom):
    """Cut the cleat slot into a body's back face, open at z_bottom."""
    slot = _trapezoid(CLEAT_W_WALL + 2 * FIT, CLEAT_W_FRONT + 2 * FIT,
                      CLEAT_T + 0.3, SLOT_LEN + 1, y0=-0.01)
    return body.cut(slot.translate((0, 0, z_bottom - 1)))


def mirror_x(obj):
    return obj.mirror("YZ")


# ------------------------------------------------------------ 1. jersey hanger
def jersey_hanger(width=380.0, split=False):
    """Basic hanger: centre block with two open loop arms.

    Returns dict of parts. split=True gives block + plug-in arms that fit a
    220 mm print bed; split=False gives a single piece.
    """
    D, bw, t = 38.0, 15.0, 8.0          # block depth, half width, arm thickness
    z0, z1 = -22.0, 12.0
    tip = width / 2
    outline = [(bw - 3, -7), (tip - 10, -7), (tip, 2), (75, 34), (bw - 3, z1)]

    wp = cq.Workplane("XY")
    outer = wp.polyline(outline).close().offset2D(-4).offset2D(4).extrude(t)
    inner = wp.polyline(outline).close().offset2D(-11).offset2D(4).extrude(t)
    arm = (outer.cut(inner)
           .rotate((0, 0, 0), (1, 0, 0), 90).translate((0, D, 0)))

    block = box(-bw, bw, 0, D, z0, z1).edges("|Y").fillet(3)
    block = cut_slot(block, z0)

    if not split:
        body = block.union(arm).union(mirror_x(arm))
        return {"jersey_hanger_onepiece": body}

    arm = arm.intersect(box(bw, tip + 1, 0, D, -50, 50))
    tongue = box(bw - 9, bw + 1, D - 7, D - 2, -5, 5)
    arm = arm.union(tongue)
    j = JOINT_FIT
    pocket = box(bw - 9 - j, bw + 1, D - 7 - j, D - 2 + j, -5 - j, 5 + j)
    block = block.cut(pocket).cut(mirror_x(pocket))
    return {"jersey_hanger_block": block,
            "jersey_hanger_arm_right": arm,
            "jersey_hanger_arm_left": mirror_x(arm)}


# -------------------------------------------------------- 2. jersey hanger pro
PRO_SIZES = {"compact": 300.0, "regular": 350.0, "wide": 400.0}


def jersey_hanger_pro(width=350.0, split=False):
    """Premium hanger: T-bar with two angled shoulder pads."""
    D, bw = 50.0, 16.0
    z0, z1 = -24.0, 10.0
    pad_len, pad_depth, pad_t, tilt = 96.0, 40.0, 5.0, 14.0
    import math
    xc = width / 2 - pad_len / 2 * math.cos(math.radians(tilt))

    bar = box(bw - 1, xc + 8, D - 12, D, -6, 6)
    pad = (cq.Workplane("XY").box(pad_len, pad_depth, pad_t)
           .edges("|Z").fillet(9)
           .rotate((0, 0, 0), (0, 1, 0), tilt)
           .translate((xc, D - pad_depth / 2, 7)))
    arm = bar.union(pad)

    block = box(-bw, bw, 0, D, z0, z1).edges("|Y").fillet(3)
    block = cut_slot(block, z0)

    name = f"jersey_hanger_pro_{[k for k, v in PRO_SIZES.items() if v == width][0]}"
    if not split:
        return {f"{name}_onepiece": block.union(arm).union(mirror_x(arm))}

    arm = arm.intersect(box(bw, width, 0, D, -80, 80))
    arm = arm.union(box(bw - 9, bw + 1, D - 9, D - 3, -4, 4))
    j = JOINT_FIT
    pocket = box(bw - 9 - j, bw + 1, D - 9 - j, D - 3 + j, -4 - j, 4 + j)
    block = block.cut(pocket).cut(mirror_x(pocket))
    return {"jersey_hanger_pro_block": block,
            f"{name}_arm_right": arm,
            f"{name}_arm_left": mirror_x(arm)}


# --------------------------------------------------------------- 3. scarf track
def scarf_track(width=170.0):
    """Rail for a scarf folded over it. Flat top: print upside down."""
    bw, bd, h = 15.0, 14.0, 34.0
    block = cut_slot(box(-bw, bw, 0, bd, -h, 0), -h)
    blade = box(-3, 3, bd - 1, 23, -16, 0)
    bar = box(-width / 2, width / 2, 22, 30, -16, 0)
    bar = bar.edges("|X").edges("<Z").fillet(3)
    bar = bar.edges("|X").edges(">Z").chamfer(1.5)
    bar = bar.edges("|Z").fillet(2)
    return {"scarf_track": block.union(blade).union(bar)}


# ---------------------------------------------------------------- 4. ball mount
def ball_mount(ball_d=220.0, seat_r=51.0):
    """Open C-ring cradle for a size-5 ball. Flat top: print upside down."""
    bw, bd, h, t, ring_w = 15.0, 14.0, 34.0, 8.0, 8.0
    cy = ball_d / 2 + 4                      # ball clears the wall by 4 mm
    r_out = seat_r + ring_w
    import math

    wp = cq.Workplane("XY")
    disc = wp.center(0, cy).circle(r_out).extrude(t)
    neck = wp.polyline([(-bw, bd - 4), (bw, bd - 4),
                        (34, cy - 42), (-34, cy - 42)]).close().extrude(t)
    plate = disc.union(neck)
    plate = plate.cut(wp.center(0, cy).circle(seat_r).extrude(t))
    # front opening of the C (100 degrees)
    a = math.radians(50)
    far = 3 * r_out
    wedge = wp.polyline([(0, cy), (far * math.sin(a), cy + far * math.cos(a)),
                         (-far * math.sin(a), cy + far * math.cos(a))]
                        ).close().extrude(t)
    plate = plate.cut(wedge)
    rm = seat_r + ring_w / 2
    for s in (1, -1):                        # rounded horn tips
        plate = plate.union(
            wp.center(s * rm * math.sin(a), cy + rm * math.cos(a))
            .circle(ring_w / 2).extrude(t))
    plate = plate.translate((0, 0, -t))
    seat = cq.Solid.makeCone(seat_r, seat_r + 3, 3,
                             cq.Vector(0, cy, -3), cq.Vector(0, 0, 1))
    plate = plate.cut(seat)                  # chamfered seat for the ball

    block = cut_slot(box(-bw, bw, 0, bd, -h, 0), -h)
    gusset = (cq.Workplane("YZ")
              .polyline([(bd - 1, -t + 1), (bd - 1, -h), (cy - 55, -t + 1)])
              .close().extrude(3, both=True))
    return {"ball_mount": block.union(plate).union(gusset)}


# ----------------------------------------------------------------------- build
def all_parts():
    parts = {"wall_cleat": wall_cleat()}
    parts.update(jersey_hanger(split=False))
    parts.update(jersey_hanger(split=True))
    for w in PRO_SIZES.values():
        parts.update(jersey_hanger_pro(w, split=False))
        parts.update(jersey_hanger_pro(w, split=True))
    parts.update(scarf_track())
    parts.update(ball_mount())
    return parts


if __name__ == "__main__":
    (OUT / "stl").mkdir(exist_ok=True)
    (OUT / "step").mkdir(exist_ok=True)
    for name, part in all_parts().items():
        solid = part.val()
        bb = solid.BoundingBox()
        assert solid.isValid(), name
        cq.exporters.export(part, str(OUT / "stl" / f"{name}.stl"),
                            tolerance=0.02, angularTolerance=0.15)
        cq.exporters.export(part, str(OUT / "step" / f"{name}.step"))
        print(f"{name:42s} {bb.xlen:6.1f} x {bb.ylen:5.1f} x {bb.zlen:5.1f} mm"
              f"  solids={len(part.solids().vals())}"
              f"  vol={solid.Volume() / 1000:6.1f} cm3")
