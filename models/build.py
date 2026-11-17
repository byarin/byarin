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


def adhesive_plate(w=50.0, below=20.0, above=20.0, t=2.5):
    """Stick-on wall plate (double-sided VHB tape / mounting adhesive) carrying
    the same dovetail cleat. Also has the screw holes, so it can be drilled.
    Origin matches wall_cleat(); the wall is at Y=-t."""
    plate = (box(-w / 2, w / 2, -t, 0, -below, CLEAT_H + above)
             .edges("|Y").fillet(6))
    body = plate.union(_trapezoid(CLEAT_W_WALL, CLEAT_W_FRONT, CLEAT_T, CLEAT_H)
                       .faces(">Z").chamfer(1.2))
    for z in (CLEAT_H / 2 - 8, CLEAT_H / 2 + 8):
        hole = cq.Solid.makeCylinder(SCREW_D / 2, CLEAT_T + t + 2,
                                     cq.Vector(0, -t - 1, z), cq.Vector(0, 1, 0))
        depth = (SCREW_HEAD_D - SCREW_D) / 2
        sink = cq.Solid.makeCone(SCREW_D / 2, SCREW_HEAD_D / 2, depth,
                                 cq.Vector(0, CLEAT_T - depth, z),
                                 cq.Vector(0, 1, 0))
        body = body.cut(hole).cut(sink)
    return body


def cut_slot(body, z_bottom):
    """Cut the cleat slot into a body's back face, open at z_bottom."""
    slot = _trapezoid(CLEAT_W_WALL + 2 * FIT, CLEAT_W_FRONT + 2 * FIT,
                      CLEAT_T + 0.3, SLOT_LEN + 1, y0=-0.01)
    return body.cut(slot.translate((0, 0, z_bottom - 1)))


def mirror_x(obj):
    return obj.mirror("YZ")


# ------------------------------------------------- shared hanger block + joint
# One centre block serves the basic hanger and every Pro size. Arms click in
# from the sides with a forked snap tongue (no glue), so a hanger ships flat.
BLOCK_D = 40.0        # block depth = stand-off from the wall
BLOCK_HW = 15.0       # block half width
BLOCK_Z0, BLOCK_Z1 = -22.0, 12.0
TONGUE_LEN = 12.0     # how far the tongue reaches into the block
TONGUE_HZ = 5.0       # tongue half height
TONGUE_Y0, TONGUE_Y1 = BLOCK_D - 7.0, BLOCK_D - 2.0
PRONG_T = 2.5         # thickness of each flexing prong
BARB = 0.7            # barb height


def prism_xz(pts, y0, y1):
    """Extrude an (x, z) polygon from y0 to y1."""
    return (cq.Workplane("XY").polyline(pts).close().extrude(y1 - y0)
            .rotate((0, 0, 0), (1, 0, 0), 90).translate((0, y1, 0)))


def snap_tongue():
    """Forked tongue for the right-hand arm (mirror for the left)."""
    x_tip, x_root = BLOCK_HW - TONGUE_LEN, BLOCK_HW + 1
    t = box(x_tip, x_root, TONGUE_Y0, TONGUE_Y1, -TONGUE_HZ, TONGUE_HZ)
    gap = TONGUE_HZ - PRONG_T
    t = t.cut(box(x_tip - 1, BLOCK_HW - 1, TONGUE_Y0 - 1, TONGUE_Y1 + 1, -gap, gap))
    for s in (1, -1):
        z = s * TONGUE_HZ
        barb = prism_xz([(x_tip + 0.5, z - s * 0.2), (x_tip + 3.5, z + s * BARB),
                         (x_tip + 3.5, z - s * 0.2)], TONGUE_Y0, TONGUE_Y1)
        t = t.union(barb)
    return t


def snap_pocket():
    j = JOINT_FIT
    x_tip = BLOCK_HW - TONGUE_LEN
    p = box(x_tip - 0.3, BLOCK_HW + 1, TONGUE_Y0 - j, TONGUE_Y1 + j,
            -TONGUE_HZ - j, TONGUE_HZ + j)
    catch = box(x_tip - 0.3, x_tip + 3.5 + j, TONGUE_Y0 - j, TONGUE_Y1 + j,
                -TONGUE_HZ - BARB - 0.1, TONGUE_HZ + BARB + 0.1)
    return p.union(catch)


def hanger_block(pockets=True):
    block = box(-BLOCK_HW, BLOCK_HW, 0, BLOCK_D, BLOCK_Z0, BLOCK_Z1)
    block = cut_slot(block.edges("|Y").fillet(3), BLOCK_Z0)
    if pockets:
        block = block.cut(snap_pocket()).cut(mirror_x(snap_pocket()))
    return block


def _assemble(name, arm, split, x_max):
    if not split:
        return {f"{name}_onepiece":
                hanger_block(False).union(arm).union(mirror_x(arm))}
    arm = arm.intersect(box(BLOCK_HW, x_max, 0, BLOCK_D, -90, 90))
    arm = arm.union(snap_tongue())
    return {"hanger_block": hanger_block(),
            f"{name}_arm_right": arm,
            f"{name}_arm_left": mirror_x(arm)}


# ------------------------------------------------------------ 1. jersey hanger
def jersey_hanger(width=380.0, split=False):
    """Basic hanger: shared block with two open loop arms."""
    D, bw, t = BLOCK_D, BLOCK_HW, 8.0
    tip = width / 2
    outline = [(bw - 3, -7), (tip - 10, -7), (tip, 2), (75, 34),
               (bw - 3, BLOCK_Z1)]
    wp = cq.Workplane("XY")
    outer = wp.polyline(outline).close().offset2D(-4).offset2D(4).extrude(t)
    inner = wp.polyline(outline).close().offset2D(-11).offset2D(4).extrude(t)
    arm = (outer.cut(inner)
           .rotate((0, 0, 0), (1, 0, 0), 90).translate((0, D, 0)))
    return _assemble("jersey_hanger", arm, split, tip + 1)


# -------------------------------------------------------- 2. jersey hanger pro
PRO_SIZES = {"compact": 300.0, "regular": 350.0, "wide": 400.0}


def jersey_hanger_pro(width=350.0, split=False):
    """Premium hanger: shared block, T-bar with two angled shoulder pads."""
    import math
    D, bw = BLOCK_D, BLOCK_HW
    pad_len, pad_depth, pad_t, tilt = 96.0, 30.0, 5.0, 14.0
    xc = width / 2 - pad_len / 2 * math.cos(math.radians(tilt))
    bar = box(bw - 1, xc + 8, D - 10, D, -6, 6)
    pad = (cq.Workplane("XY").box(pad_len, pad_depth, pad_t)
           .edges("|Z").fillet(9)
           .rotate((0, 0, 0), (0, 1, 0), tilt)
           .translate((xc, D - pad_depth / 2, 7)))
    size = [k for k, v in PRO_SIZES.items() if v == width][0]
    return _assemble(f"jersey_hanger_pro_{size}", bar.union(pad), split, width)


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
    parts = {"wall_cleat": wall_cleat(),
             # 50 x 69 mm pad: jerseys and scarves
             "adhesive_plate": adhesive_plate(),
             # 60 x 119 mm pad, extra height above the cleat to resist the
             # ball's forward lever arm
             "adhesive_plate_ball": adhesive_plate(w=60, below=20, above=70)}
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
