"""Realistic example renders (Blender Cycles): each mount empty and in use.

The jerseys are real cloth simulations draped over the hanger models.

Run:  pip install bpy cadquery pillow scipy matplotlib
      python3 models/scenes_blender.py [scene ...]
Out:  models/previews/scene_*.png
"""
import sys
import math
from pathlib import Path
import numpy as np
import bpy
import bmesh
from PIL import Image, ImageDraw, ImageFont
from matplotlib.path import Path as MplPath
from matplotlib import font_manager
import build

OUT = Path(__file__).parent / "previews"
TMP = Path(__file__).parent / ".render_tmp"
OUT.mkdir(exist_ok=True)
TMP.mkdir(exist_ok=True)
S = 0.001                     # mm -> m
RES, SAMPLES = int(__import__("os").environ.get("RES", 1100)), int(__import__("os").environ.get("SAMPLES", 160))
FONT = font_manager.findfont("DejaVu Sans:bold")


# =================================================================== basics
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.device = "CPU"
    sc.render.resolution_x = sc.render.resolution_y = RES
    sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.file_format = "PNG"
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (1.0, 0.97, 0.94, 1)
    bg.inputs[1].default_value = 0.28
    sc.world = world
    return sc


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def principled(name, color, rough=0.5, **kw):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    for k, v in kw.items():
        b.inputs[k].default_value = v
    return m


def add_bump(mat, scale, strength, detail=4.0, tex="NOISE"):
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])


def image_material(name, img_path, rough=0.75, sheen=0.4, bump_scale=900,
                   bump_strength=0.12):
    m = principled(name, (1, 1, 1), rough)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(str(img_path))
    t.extension = "EXTEND"
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Sheen Weight"].default_value = sheen
    add_bump(m, bump_scale, bump_strength, detail=2.0)
    return m


def mesh_obj(name, verts, faces, smooth_angle=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    if smooth_angle is not None:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        me.set_sharp_from_angle(angle=smooth_angle)
    return link(bpy.data.objects.new(name, me))


def cad_obj(name, part, mat, tol=0.03):
    v, f = part.val().tessellate(tol, 0.1)
    o = mesh_obj(name, np.array([p.toTuple() for p in v]) * S, f, smooth_angle=0.5)
    o.data.materials.append(mat)
    return o


def plastic(color, name="plastic"):
    m = principled(name, color, rough=0.42)
    add_bump(m, 2500, 0.03)
    return m


BLACK_PLA = (0.012, 0.012, 0.014)
WHITE_PLA = (0.85, 0.85, 0.83)
GREY_PLA = (0.30, 0.30, 0.32)


def wall():
    x, z0, z1, t = 2.5, -2.5, 2.0, 0.2          # thick slab: robust collider
    v = np.array([(-x, 0, z0), (x, 0, z0), (x, 0, z1), (-x, 0, z1),
                  (-x, -t, z0), (x, -t, z0), (x, -t, z1), (-x, -t, z1)])
    f = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
         (2, 3, 7, 6), (3, 0, 4, 7)]
    o = mesh_obj("wall", v, f)
    m = principled("wallpaint", (0.80, 0.77, 0.72), rough=0.92)
    add_bump(m, 420, 0.035, detail=8)
    o.data.materials.append(m)
    return o


def lights(focus):
    fx, fy, fz = focus
    data = bpy.data.lights.new("key", "AREA")
    data.energy, data.size = 42, 1.1
    data.color = (1.0, 0.96, 0.90)
    key = link(bpy.data.objects.new("key", data))
    key.location = (fx - 0.9, 2.0, fz + 1.3)
    look_at(key, focus)
    data = bpy.data.lights.new("fill", "AREA")
    data.energy, data.size = 7, 2.0
    fill = link(bpy.data.objects.new("fill", data))
    fill.location = (fx + 1.4, 1.8, fz - 0.2)
    look_at(fill, focus)


def look_at(obj, target):
    from mathutils import Vector
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(pos, target, lens=60):
    data = bpy.data.cameras.new("cam")
    data.lens = lens
    data.clip_start, data.clip_end = 0.01, 50
    cam = link(bpy.data.objects.new("cam", data))
    cam.location = [p * S for p in pos]
    look_at(cam, [t * S for t in target])
    bpy.context.scene.camera = cam
    return cam


def render(name):
    path = TMP / f"{name}.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return Image.open(path).convert("RGB")


def pair(name, a, b):
    sheet = Image.new("RGB", (RES * 2 + 14, RES), (255, 255, 255))
    sheet.paste(a, (0, 0))
    sheet.paste(b, (RES + 14, 0))
    sheet.save(OUT / f"{name}.png")
    print("wrote", name, flush=True)


# =================================================================== jersey
J_X0, J_X1, J_Z0, J_Z1 = -350.0, 350.0, -700.0, 60.0
_SHOULDER = [(78, 44), (240, 6), (335, -92), (292, -150), (255, -96),
             (258, -690), (0, -690)]
OUT_BACK = [(0, 31), (55, 34)] + _SHOULDER            # panel facing the room
OUT_FRONT = [(0, -64), (30, -58), (56, -28), (71, 10)] + _SHOULDER  # wall side


def _full(half):
    return half + [(-x, z) for x, z in reversed(half[1:-1])]


def _nearest_on_outline(pts, poly):
    poly = np.asarray(poly, float)
    a, b = poly, np.roll(poly, -1, axis=0)
    ab = b - a
    t = ((pts[:, None, :] - a[None]) * ab[None]).sum(-1) / (ab * ab).sum(-1)[None]
    proj = a[None] + np.clip(t, 0, 1)[..., None] * ab[None]
    d = np.linalg.norm(proj - pts[:, None, :], axis=-1)
    i = d.argmin(1)
    return proj[np.arange(len(pts)), i], d.min(1)


def jersey_texture(path, body, trim, name, number):
    W = 2048
    H = int(W * (J_Z1 - J_Z0) / (J_X1 - J_X0))
    im = Image.new("RGB", (W, H), body)
    d = ImageDraw.Draw(im)
    px = lambda x, z: ((J_X1 - x) / (J_X1 - J_X0) * W, (J_Z1 - z) / (J_Z1 - J_Z0) * H)
    k = W / (J_X1 - J_X0)
    for s in (1, -1):                                   # side stripes, cuffs
        d.polygon([px(s * 236, -120), px(s * 246, -120), px(s * 249, -690),
                   px(s * 239, -690)], fill=trim)
        d.line([px(s * 325, -84), px(s * 284, -141)], fill=trim, width=int(13 * k))
        d.line([px(s * 78, 46), px(s * 240, 8)], fill=trim, width=int(4 * k))
    d.line([px(-80, 44), px(-55, 33), px(0, 30), px(55, 33), px(80, 44)],
           fill=trim, width=int(12 * k))                # collar
    f = ImageFont.truetype(FONT, int(46 * k))
    d.text(px(0, -95), name, font=f, fill=trim, anchor="mm")
    f = ImageFont.truetype(FONT, int(215 * k))
    d.text(px(0, -250), number, font=f, fill=trim, anchor="mm")
    im.save(path)


def make_jersey(y_mid, lift, puff, tex_path, body_rgb, step=6.0):
    """Two sewn panels (shoulders, sleeves and sides), open neck/cuffs/hem."""
    xs = np.arange(J_X0, J_X1 + step, step)
    zs = np.arange(J_Z0, J_Z1 + step, step)
    X, Z = np.meshgrid(xs, zs)
    cen = np.c_[(X[:-1, :-1] + step / 2).ravel(), (Z[:-1, :-1] + step / 2).ravel()]
    ny, nx = X.shape
    gid = np.arange(X.size).reshape(X.shape)
    pts = np.c_[X.ravel(), Z.ravel()]
    panels = []
    for half in (OUT_BACK, OUT_FRONT):
        poly = _full(half)
        keep = MplPath(poly).contains_points(cen).reshape(ny - 1, nx - 1)
        cnt = np.zeros(X.shape, int)
        for dy in (0, 1):
            for dx in (0, 1):
                cnt[dy:ny - 1 + dy, dx:nx - 1 + dx] += keep
        used = cnt.ravel() > 0
        boundary = used & (cnt.ravel() < 4)
        pos = pts.copy()
        snapped, _ = _nearest_on_outline(pts[boundary], poly)
        pos[boundary] = snapped
        _, dist = _nearest_on_outline(pos, poly)
        panels.append(dict(keep=keep, used=used, boundary=boundary, pos=pos,
                           dist=dist))
    A, B = panels
    # seam = boundary shared by both panels, minus hem and cuff openings
    same = np.linalg.norm(A["pos"] - B["pos"], axis=1) < 1e-6
    seam = A["boundary"] & B["boundary"] & same & (A["pos"][:, 1] > J_Z0 + 12)
    cuff_a, cuff_b = np.array([335.0, -92.0]), np.array([292.0, -150.0])
    ax = np.abs(A["pos"][:, 0])
    pz = A["pos"][:, 1]
    t = ((ax - cuff_a[0]) * (cuff_b[0] - cuff_a[0])
         + (pz - cuff_a[1]) * (cuff_b[1] - cuff_a[1])) / ((cuff_b - cuff_a) ** 2).sum()
    on_cuff = (np.abs((ax - cuff_a[0]) * (cuff_b[1] - cuff_a[1])
                      - (pz - cuff_a[1]) * (cuff_b[0] - cuff_a[0])) < 150) \
        & (t > 0.06) & (t < 0.94) & (ax > 285)
    seam &= ~on_cuff

    # distance to the nearest sewn seam: panels separate away from seams only,
    # so hem, cuffs and neck start open and the body hangs flat
    from scipy.spatial import cKDTree
    seam_tree = cKDTree(A["pos"][seam])
    for panel in (A, B):
        panel["dseam"] = seam_tree.query(panel["pos"])[0]

    verts, uvs, index = [], [], [{}, {}]
    for p, (panel, sign) in enumerate(((A, 1), (B, -1))):
        for g in np.flatnonzero(panel["used"]):
            if p == 1 and seam[g]:
                index[1][g] = index[0][g]
                continue
            x, z = panel["pos"][g]
            cap = 7.0 + (puff - 7.0) * min(1.0, max(0.0, (z + 220.0) / 170.0))
            h = 0.0 if seam[g] else min(cap, 0.42 * panel["dseam"][g] + 1.0)
            if sign < 0:
                h = min(h, y_mid - 3.5)   # stay clear of the wall
            index[p][g] = len(verts)
            verts.append((x * S, (y_mid + sign * h) * S, (z + lift) * S))
            uvs.append(((J_X1 - x) / (J_X1 - J_X0), (z - J_Z0) / (J_Z1 - J_Z0)))
    faces, mats = [], []
    for p, panel in enumerate((A, B)):
        for iy, ix in zip(*np.nonzero(panel["keep"])):
            q = [gid[iy, ix], gid[iy, ix + 1], gid[iy + 1, ix + 1], gid[iy + 1, ix]]
            f = [index[p][g] for g in q]
            if len(set(f)) < 4:
                continue
            faces.append(f if p == 1 else f[::-1])
            mats.append(p)
    o = mesh_obj("jersey", verts, faces)
    me = o.data
    uv = me.uv_layers.new(name="uv")
    for loop in me.loops:
        uv.data[loop.index].uv = uvs[loop.vertex_index]
    me.materials.append(image_material("jersey_back", tex_path))
    inner = principled("jersey_inner", [c * 0.8 for c in body_rgb], 0.8)
    inner.node_tree.nodes["Principled BSDF"].inputs["Sheen Weight"].default_value = 0.4
    me.materials.append(inner)
    me.polygons.foreach_set("material_index", mats)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    return o


def simulate_cloth(cloth, colliders, frames=70):
    sc = bpy.context.scene
    for c in colliders:
        c.modifiers.new("col", "COLLISION")
        c.collision.thickness_outer = 0.001
        c.collision.thickness_inner = 0.002
        c.collision.cloth_friction = 25
    mod = cloth.modifiers.new("cloth", "CLOTH")
    st = mod.settings
    st.quality = 12
    st.mass = 0.004
    st.tension_stiffness = st.compression_stiffness = 30
    st.shear_stiffness = 12
    st.bending_stiffness = 0.08
    st.tension_damping = st.compression_damping = st.shear_damping = 6
    st.bending_damping = 0.5
    st.air_damping = 2.5
    cs = mod.collision_settings
    cs.use_collision = True
    cs.distance_min = 0.0015
    cs.collision_quality = 4
    cs.use_self_collision = True
    cs.self_distance_min = 0.0025
    mod.point_cache.frame_start, mod.point_cache.frame_end = 1, frames
    sc.frame_start, sc.frame_end = 1, frames
    for f in range(1, frames + 1):
        sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    co = np.empty(len(cloth.data.vertices) * 3)
    cloth.evaluated_get(dg).data.vertices.foreach_get("co", co)
    cloth.modifiers.remove(mod)
    cloth.data.vertices.foreach_set("co", co)
    cloth.data.update()
    sc.frame_set(1)
    sub = cloth.modifiers.new("sub", "SUBSURF")
    sub.levels = sub.render_levels = 2
    sol = cloth.modifiers.new("thick", "SOLIDIFY")
    sol.thickness = 0.0012


# ==================================================================== scarf
def scarf_texture(path):
    W, H = 368, 2560
    im = Image.new("RGB", (W, H), (176, 20, 30))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 40, H], fill=(238, 236, 230))
    d.rectangle([W - 40, 0, W, H], fill=(238, 236, 230))
    for i in range(0, H, 512):
        d.rectangle([40, i + 180, W - 40, i + 330], fill=(238, 236, 230))
        d.rectangle([40, i + 205, W - 40, i + 222], fill=(20, 20, 24))
        d.rectangle([40, i + 288, W - 40, i + 305], fill=(20, 20, 24))
    im.save(path)


def make_scarf(width=184.0, front_len=660.0, back_len=600.0):
    r, yc, zc = 7.5, 26.0, -5.0
    path = [(yc + r, z) for z in np.arange(-front_len, zc, 5.0)]
    path += [(yc + r * math.cos(t), zc + r * math.sin(t))
             for t in np.linspace(0, math.pi, 14)]
    path += [(yc - r, z) for z in np.arange(zc, -back_len, -5.0)[1:]]
    path = np.array(path)
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    xs = np.arange(-width / 2, width / 2 + 4, 4.0)
    rng = np.random.default_rng(3)
    verts, uvs = [], []
    for (y, z), s in zip(path, seg):
        hang = min(1.0, max(0.0, (-z - 20) / 300.0))
        for x in xs:
            wav = 1.6 * math.sin(x / 17.0 + s / 190.0) * hang
            verts.append((x * S, (y + wav) * S, z * S))
            uvs.append(((x + width / 2) / width, s / seg[-1]))
    n, m = len(path), len(xs)
    faces = [(i * m + j, i * m + j + 1, (i + 1) * m + j + 1, (i + 1) * m + j)
             for i in range(n - 1) for j in range(m - 1)]
    o = mesh_obj("scarf", verts, faces)
    uv = o.data.uv_layers.new(name="uv")
    for loop in o.data.loops:
        uv.data[loop.index].uv = uvs[loop.vertex_index]
    o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
    tex = TMP / "scarf.png"
    scarf_texture(tex)
    o.data.materials.append(image_material("knit", tex, rough=0.95, sheen=0.8,
                                           bump_scale=1400, bump_strength=0.6))
    sub = o.modifiers.new("sub", "SUBSURF")
    sub.levels = sub.render_levels = 1
    tex = bpy.data.textures.new("drape", "CLOUDS")
    tex.noise_scale = 0.12
    dis = o.modifiers.new("drape", "DISPLACE")
    dis.texture, dis.strength, dis.direction = tex, 0.012, "Y"
    dis.texture_coords = "GLOBAL"
    sol = o.modifiers.new("thick", "SOLIDIFY")
    sol.thickness = 0.004
    sol.offset = 0
    # fringe: tassels at both ends
    fv, ff = [], []
    cols = [principled("fr_red", (0.42, 0.02, 0.03), 0.95),
            principled("fr_white", (0.85, 0.84, 0.80), 0.95)]
    fm = []
    for y, z_end in ((yc + r, -front_len), (yc - r, -back_len)):
        for i, x in enumerate(np.arange(-width / 2 + 3, width / 2 - 2, 5.0)):
            dx, dy = rng.normal(0, 1.2), rng.normal(0, 1.5)
            length = 48 + rng.normal(0, 3)
            b = len(fv)
            for k, zz in enumerate((0, -length)):
                ox, oy = (0, 0) if k == 0 else (dx, dy)
                for cx, cy in ((-1.5, -1.2), (1.5, -1.2), (1.5, 1.2), (-1.5, 1.2)):
                    fv.append(((x + cx + ox) * S, (y + cy + oy) * S, (z_end + zz) * S))
            for a in range(4):
                ff.append((b + a, b + (a + 1) % 4, b + 4 + (a + 1) % 4, b + 4 + a))
                fm.append((i // 2) % 2)
            ff.append((b + 7, b + 6, b + 5, b + 4))
            fm.append((i // 2) % 2)
    fr = mesh_obj("fringe", fv, ff)
    for c in cols:
        fr.data.materials.append(c)
    fr.data.polygons.foreach_set("material_index", fm)
    return o


# ===================================================================== ball
def make_ball(center, r=110.0):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    bmesh.ops.bevel(bm, geom=bm.verts[:], offset=100 / 3, offset_type="PERCENT",
                    segments=1, affect="VERTICES")
    seam = bm.verts.layers.float.new("seam")
    for v in bm.verts:
        v[seam] = 1.0
    panel = bm.faces.layers.int.new("panel")
    for f in bm.faces:
        f[panel] = 0 if len(f.verts) == 5 else 1
    res = bmesh.ops.inset_individual(bm, faces=bm.faces[:], thickness=0.012,
                                     use_even_offset=True)
    for f in res["faces"]:
        f[panel] = 2
    for f in bm.faces:
        if f[panel] != 2:
            for v in f.verts:
                v[seam] = 0.0
    inner = [f for f in bm.faces if f[panel] != 2]
    bmesh.ops.poke(bm, faces=inner)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=5, use_grid_fill=True)
    for v in bm.verts:
        v.co = v.co.normalized() * (r - 1.6 * v[seam]) * S
    me = bpy.data.meshes.new("ball")
    bm.to_mesh(me)
    mats = [principled("b_dark", (0.015, 0.015, 0.02), 0.32),
            principled("b_white", (0.88, 0.88, 0.86), 0.32),
            principled("b_seam", (0.10, 0.10, 0.10), 0.7)]
    for m in mats[:2]:
        add_bump(m, 1800, 0.05)
        m.node_tree.nodes["Principled BSDF"].inputs["Coat Weight"].default_value = 0.3
    idx = [f[panel] for f in bm.faces]
    bm.free()
    for m in mats:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", idx)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    o = link(bpy.data.objects.new("ball", me))
    o.location = [c * S for c in center]
    o.rotation_euler = (0.5, 0.3, 0.9)
    return o


# =================================================================== scenes
def mount(part, color, slot_z):
    cad_obj("cleat", build.wall_cleat().translate((0, 0, slot_z + 1)),
            plastic(GREY_PLA, "cleat"))
    return cad_obj("mount", part, plastic(color))


def scene_jersey(name, part, color, body, trim, label, number, y_mid, puff):
    cam_item = ((560, 1900, -120), (0, 20, -300))
    cam_mount = ((300, 620, 150), (0, 15, 2))

    reset()
    wall()
    mount(part, color, build.BLOCK_Z0)
    lights((0, 0, 0))
    camera(*cam_mount, lens=55)
    a = render(f"{name}_a")

    reset()
    w = wall()
    m = mount(part, color, build.BLOCK_Z0)
    tex = TMP / f"{name}_tex.png"
    rgb255 = tuple(int(255 * c ** (1 / 2.2)) for c in body)
    trim255 = tuple(int(255 * c ** (1 / 2.2)) for c in trim)
    jersey_texture(tex, rgb255, trim255, label, number)
    j = make_jersey(y_mid, lift=14.0, puff=puff, tex_path=tex, body_rgb=body,
                    step=float(__import__("os").environ.get("STEP", 8)))
    simulate_cloth(j, [w, m])
    lights((0, 0, -0.3))
    camera(*cam_item, lens=70)
    b = render(f"{name}_b")
    pair(name, a, b)


def scene_scarf():
    part = build.scarf_track()["scarf_track"]
    reset(); wall(); mount(part, BLACK_PLA, -34); lights((0, 0, 0))
    camera((210, 400, 120), (0, 12, -12), lens=55)
    a = render("scarf_a")
    reset(); wall(); mount(part, BLACK_PLA, -34); make_scarf()
    lights((0, 0, -0.3))
    camera((520, 1750, -150), (0, 20, -320), lens=70)
    b = render("scarf_b")
    pair("scene_scarf_track", a, b)


def scene_ball():
    part = build.ball_mount()["ball_mount"]
    reset(); wall(); mount(part, BLACK_PLA, -34); lights((0, 0, 0))
    camera((300, 520, 210), (0, 70, -8), lens=55)
    a = render("ball_a")
    reset(); wall(); mount(part, BLACK_PLA, -34); make_ball((0, 114, 95.5))
    lights((0, 0, 0.08))
    camera((480, 800, 60), (0, 80, 70), lens=55)
    b = render("ball_b")
    pair("scene_ball_mount", a, b)


def scene_mounting():
    reset(); wall(); lights((0, 0, 0))
    cad_obj("cleat", build.wall_cleat(), plastic(GREY_PLA))
    camera((150, 300, 70), (0, 0, 14), lens=55)
    a = render("mounting_a")
    reset(); wall(); lights((0, 0, 0))
    cad_obj("plate", build.adhesive_plate().translate((0, 2.5, 0)), plastic(GREY_PLA))
    camera((150, 300, 70), (0, 0, 14), lens=55)
    b = render("mounting_b")
    pair("scene_mounting", a, b)


SCENES = {
    "jersey": lambda: scene_jersey(
        "scene_jersey_hanger", build.jersey_hanger()["jersey_hanger_onepiece"],
        BLACK_PLA, (0.015, 0.16, 0.10), (0.9, 0.9, 0.86), "CAPTAIN", "10",
        y_mid=build.ARM_Y, puff=24),
    "pro": lambda: scene_jersey(
        "scene_jersey_hanger_pro",
        build.jersey_hanger_pro(350.0)["jersey_hanger_pro_regular_onepiece"],
        WHITE_PLA, (0.02, 0.04, 0.22), (0.95, 0.72, 0.10), "LEGEND", "7",
        y_mid=build.ARM_Y, puff=22),
    "scarf": scene_scarf,
    "ball": scene_ball,
    "mounting": scene_mounting,
}

if __name__ == "__main__":
    for key in (sys.argv[1:] or SCENES):
        SCENES[key]()
