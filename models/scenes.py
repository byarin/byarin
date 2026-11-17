"""Render example scenes: each mount on a wall, empty and with its item.

Needs VTK with offscreen GL (apt install libosmesa6 libegl1).
Run:  python3 models/scenes.py   -> models/previews/scene_*.png
"""
from pathlib import Path
import numpy as np
import vtk
from vtk.util import numpy_support as ns
from matplotlib.path import Path as MplPath
from scipy import ndimage
from PIL import Image
import build

OUT = Path(__file__).parent / "previews"
OUT.mkdir(exist_ok=True)
SIZE = 1000          # final panel size (rendered at 2x and downsampled)
WALL = (0.90, 0.88, 0.85)
BLACK, WHITE, GREY = (0.07, 0.07, 0.08), (0.96, 0.96, 0.94), (0.55, 0.55, 0.57)


# ------------------------------------------------------------------- helpers
def polydata(verts, tris, cell_rgb=None):
    pd = vtk.vtkPolyData()
    pts = vtk.vtkPoints()
    pts.SetData(ns.numpy_to_vtk(np.ascontiguousarray(verts, dtype=np.float64),
                                deep=True))
    pd.SetPoints(pts)
    tris = np.asarray(tris, dtype=np.int64)
    cells = np.hstack([np.full((len(tris), 1), 3, dtype=np.int64), tris])
    ca = vtk.vtkCellArray()
    ca.ImportLegacyFormat(ns.numpy_to_vtkIdTypeArray(cells.ravel(), deep=True))
    pd.SetPolys(ca)
    if cell_rgb is not None:
        arr = ns.numpy_to_vtk((np.clip(cell_rgb, 0, 1) * 255).astype(np.uint8),
                              deep=True)
        arr.SetName("rgb")
        pd.GetCellData().SetScalars(arr)
    return pd


def actor(pd, color=None, smooth=True, spec=0.15, feature=40):
    if smooth:
        n = vtk.vtkPolyDataNormals()
        n.SetInputData(pd)
        n.SetFeatureAngle(feature)
        n.SplittingOn()
        n.Update()
        pd = n.GetOutput()
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(pd)
    a = vtk.vtkActor()
    a.SetMapper(m)
    p = a.GetProperty()
    if color is not None:
        m.ScalarVisibilityOff()
        p.SetColor(*color)
    p.SetAmbient(0.32)
    p.SetDiffuse(0.75)
    p.SetSpecular(spec)
    p.SetSpecularPower(25)
    return a


def cad(part, color, tol=0.05):
    v, f = part.val().tessellate(tol, 0.15)
    return actor(polydata([p.toTuple() for p in v], f), color, spec=0.25)


def wall(z0=-900, z1=400, half=900):
    v = [(-half, 0, z0), (half, 0, z0), (half, 0, z1), (-half, 0, z1)]
    return actor(polydata(v, [(0, 2, 1), (0, 3, 2)]), WALL, smooth=False, spec=0)


def render(actors, cam_pos, focal, view_angle, name):
    ren = vtk.vtkRenderer()
    ren.SetBackground(*WALL)
    for a in actors:
        ren.AddActor(a)
    ren.AutomaticLightCreationOff()
    key = vtk.vtkLight()                       # shadow-casting key light
    key.SetPositional(True)
    key.SetPosition(focal[0] - 900, 2600, focal[2] + 1500)
    key.SetFocalPoint(*focal)
    key.SetConeAngle(40)
    key.SetIntensity(0.85)
    ren.AddLight(key)
    fill = vtk.vtkLight()
    fill.SetLightTypeToCameraLight()
    fill.SetPosition(0.3, 0.2, 1)
    fill.SetIntensity(0.30)
    ren.AddLight(fill)

    shadows = vtk.vtkShadowMapPass()
    shadows.GetShadowMapBakerPass().SetResolution(4096)
    seq = vtk.vtkSequencePass()
    passes = vtk.vtkRenderPassCollection()
    passes.AddItem(shadows.GetShadowMapBakerPass())
    passes.AddItem(shadows)
    seq.SetPasses(passes)
    cam_pass = vtk.vtkCameraPass()
    cam_pass.SetDelegatePass(seq)
    ren.SetPass(cam_pass)

    cam = ren.GetActiveCamera()
    cam.SetPosition(*cam_pos)
    cam.SetFocalPoint(*focal)
    cam.SetViewUp(0, 0, 1)
    cam.SetViewAngle(view_angle)
    ren.ResetCameraClippingRange()

    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.SetSize(SIZE * 2, SIZE * 2)
    rw.AddRenderer(ren)
    rw.Render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.Update()
    img = w2i.GetOutput()
    h, w, _ = img.GetDimensions()[1], img.GetDimensions()[0], 0
    arr = ns.vtk_to_numpy(img.GetPointData().GetScalars()).reshape(h, w, -1)
    im = Image.fromarray(arr[::-1, :, :3]).resize((SIZE, SIZE), Image.LANCZOS)
    im.save(OUT / f"{name}.png")
    return im


def pair(name, empty, loaded):
    sheet = Image.new("RGB", (SIZE * 2 + 12, SIZE), (255, 255, 255))
    sheet.paste(empty, (0, 0))
    sheet.paste(loaded, (SIZE + 12, 0))
    sheet.save(OUT / f"{name}.png")
    for part in ("_empty", "_loaded"):
        (OUT / f"{name}{part}.png").unlink()


# --------------------------------------------------------------------- items
def jersey(y_mid, body=(0.05, 0.32, 0.24), trim=WHITE, number="10",
           puff=20.0, edge=34.0):
    """Soft 'pillow' shirt mesh hanging with its back to the viewer."""
    half = [(0, 36), (78, 44), (240, 6), (335, -92), (292, -150), (255, -96),
            (258, -690), (0, -690)]
    outline = half + [(-x, z) for x, z in reversed(half[1:-1])]
    step = 1.0
    xs = np.arange(-345, 345 + step, step)
    zs = np.arange(-700, 55 + step, step)
    X, Z = np.meshgrid(xs, zs)
    inside = MplPath(outline).contains_points(
        np.c_[X.ravel(), Z.ravel()]).reshape(X.shape)
    d = ndimage.distance_transform_edt(inside) * step
    u = np.clip(d / edge, 0, 1)
    h = puff * np.sqrt(1 - (1 - u) ** 2)
    # soft vertical folds so the cloth does not look like a slab
    folds = 2.2 * np.sin(X / 37.0 + 0.6 * np.sin(Z / 140.0)) * u \
        * np.clip((-Z - 60) / 250.0, 0, 1)

    idx = np.arange(X.size).reshape(X.shape)
    cell_ok = inside[:-1, :-1] & inside[1:, :-1] & inside[:-1, 1:] & inside[1:, 1:]
    a, b = idx[:-1, :-1][cell_ok], idx[:-1, 1:][cell_ok]
    c, e = idx[1:, 1:][cell_ok], idx[1:, :-1][cell_ok]
    tris = np.vstack([np.c_[a, b, c], np.c_[a, c, e]])

    cx = (X[:-1, :-1] + step / 2)[cell_ok]
    cz = (Z[:-1, :-1] + step / 2)[cell_ok]
    cd = d[:-1, :-1][cell_ok]
    rgb = np.tile(body, (len(cx), 1)).astype(float)
    collar = (cd < 12) & (cz > 20) & (np.abs(cx) < 95)
    cuff = (cd < 12) & (np.abs(cx) > 268) & (cz < -80)
    side = (np.abs(cx) > 236) & (np.abs(cx) < 250) & (cz < -110)
    rgb[collar | cuff | side] = trim
    rgb = np.vstack([rgb, rgb])

    out = []
    for sign, depth in ((1, 1.0), (-1, 0.55)):
        Y = y_mid + sign * (h * depth) + folds
        v = np.c_[X.ravel(), Y.ravel(), Z.ravel()]
        out.append(actor(polydata(v, tris if sign > 0 else tris[:, ::-1], rgb),
                         spec=0.05, feature=180))

    txt = vtk.vtkVectorText()
    txt.SetText(number)
    txt.Update()
    pts = ns.vtk_to_numpy(txt.GetOutput().GetPoints().GetData())
    s = 190.0 / pts[:, 1].max()
    cxm = (pts[:, 0].max() + pts[:, 0].min()) / 2
    p3 = np.c_[-(pts[:, 0] - cxm) * s,
               np.full(len(pts), y_mid + puff + 2.6),
               pts[:, 1] * s - 330]
    num = vtk.vtkPolyData()
    num.DeepCopy(txt.GetOutput())
    vp = vtk.vtkPoints()
    vp.SetData(ns.numpy_to_vtk(p3, deep=True))
    num.SetPoints(vp)
    na = actor(num, trim, smooth=False, spec=0)
    na.GetProperty().SetAmbient(0.6)
    out.append(na)
    return out


def scarf(width=184.0, front_len=640.0, back_len=600.0):
    """Scarf folded over the scarf-track bar (bar: Y 22..30, top at Z=0)."""
    r, yc, zc = 6.5, 26.0, -4.0
    seg = []
    for z in np.arange(-front_len, zc, 4.0):
        seg.append((yc + r, z))
    for t in np.linspace(0, np.pi, 24):
        seg.append((yc + r * np.cos(t), zc + r * np.sin(t)))
    for z in np.arange(zc, -back_len, -4.0)[1:]:
        seg.append((yc - r, z))
    seg = np.array(seg)
    xs = np.arange(-width / 2, width / 2 + 2, 2.0)
    n, m = len(seg), len(xs)
    Xg, _ = np.meshgrid(xs, np.arange(n))
    Yg = np.repeat(seg[:, 0:1], m, 1) + 1.2 * np.sin(Xg / 14.0)
    Zg = np.repeat(seg[:, 1:2], m, 1)
    v = np.c_[Xg.ravel(), Yg.ravel(), Zg.ravel()]
    idx = np.arange(n * m).reshape(n, m)
    a, b = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel()
    c, e = idx[1:, 1:].ravel(), idx[1:, :-1].ravel()
    cx = (Xg[:-1, :-1] + 1).ravel()
    cz = Zg[:-1, :-1].ravel()
    red, white = np.array((0.75, 0.08, 0.12)), np.array(WHITE)
    rgb = np.tile(red, (len(cx), 1))
    rgb[np.abs(cx) > width / 2 - 22] = white
    block = ((cz % 230) < 70) & (np.abs(cx) < width / 2 - 22)
    rgb[block] = white
    end = np.minimum(cz + front_len, cz + back_len)
    is_front = np.arange(n - 1).repeat(m - 1) < n // 2
    dist_end = np.where(is_front, cz + front_len, cz + back_len)
    fringe = dist_end < 42
    keep = ~(fringe & ((cx % 7) < 3))
    rgb[fringe] = np.where(((cx[fringe] // 7) % 2)[:, None] == 0, red, white)
    tris = np.vstack([np.c_[a, b, c][keep], np.c_[a, c, e][keep]])
    rgb = np.vstack([rgb[keep], rgb[keep]])
    act = actor(polydata(v, tris, rgb), spec=0.03, feature=180)
    return [act]


def ball(center, r=110.0):
    src = vtk.vtkSphereSource()
    src.SetRadius(r)
    src.SetThetaResolution(720)
    src.SetPhiResolution(720)
    src.SetCenter(*center)
    src.Update()
    pd = src.GetOutput()
    cen = ns.vtk_to_numpy(pd.GetPoints().GetData()) - np.array(center)
    cen /= np.linalg.norm(cen, axis=1, keepdims=True)
    g = (1 + 5 ** 0.5) / 2
    ico = np.array([(0, s1, s2 * g) for s1 in (1, -1) for s2 in (1, -1)]
                   + [(s1, s2 * g, 0) for s1 in (1, -1) for s2 in (1, -1)]
                   + [(s2 * g, 0, s1) for s1 in (1, -1) for s2 in (1, -1)], float)
    ico /= np.linalg.norm(ico, axis=1, keepdims=True)
    rot = np.array([[0.86, -0.3, 0.41], [0.42, 0.87, -0.25], [-0.28, 0.39, 0.88]])
    q, _ = np.linalg.qr(rot)
    dots = (cen @ (ico @ q.T).T).max(1)
    rgb = np.tile(WHITE, (len(cen), 1)).astype(float)
    rgb[dots > np.cos(0.36)] = (0.08, 0.08, 0.10)
    rgb[(dots <= np.cos(0.36)) & (dots > np.cos(0.40))] = (0.95, 0.75, 0.10)
    arr = ns.numpy_to_vtk((rgb * 255).astype(np.uint8), deep=True)
    pd.GetPointData().SetScalars(arr)
    return [actor(pd, smooth=False, spec=0.35, feature=180)]


# -------------------------------------------------------------------- scenes
def mount(part, color, slot_z):
    cleat = build.wall_cleat().translate((0, 0, slot_z + 1))
    return [cad(part, color), cad(cleat, GREY)]


def scene_jersey(name, part, color, slot_z, y_mid, body, **kw):
    base = [wall()] + mount(part, color, slot_z)
    e = render(base, (330, 560, 130), (0, 15, 0), 30, f"{name}_empty")
    l = render(base + jersey(y_mid, body=body, **kw),
               (520, 1750, -150), (0, 20, -320), 30, f"{name}_loaded")
    pair(name, e, l)


if __name__ == "__main__":
    scene_jersey("scene_jersey_hanger",
                 build.jersey_hanger()["jersey_hanger_onepiece"], BLACK, -22,
                 y_mid=31, body=(0.05, 0.32, 0.24))
    scene_jersey("scene_jersey_hanger_pro",
                 build.jersey_hanger_pro(350.0)["jersey_hanger_pro_regular_onepiece"],
                 WHITE, -24, y_mid=31, body=(0.10, 0.16, 0.42), puff=25.0, edge=16.0)

    # mounting options: screw cleat vs stick-on plate
    cam = ((150, 260, 70), (0, 0, 14), 30)
    e = render([wall(), cad(build.wall_cleat(), GREY)], *cam, "scene_mounting_empty")
    l = render([wall(), cad(build.adhesive_plate().translate((0, 2.5, 0)), GREY)],
               *cam, "scene_mounting_loaded")
    pair("scene_mounting", e, l)

    base = [wall()] + mount(build.scarf_track()["scarf_track"], BLACK, -34)
    e = render(base, (190, 330, 120), (0, 12, -12), 30, "scene_scarf_track_empty")
    l = render(base + scarf(), (520, 1500, -150), (0, 20, -310), 30,
               "scene_scarf_track_loaded")
    pair("scene_scarf_track", e, l)

    base = [wall(z0=-500)] + mount(build.ball_mount()["ball_mount"], BLACK, -34)
    e = render(base, (260, 420, 190), (0, 70, -10), 30, "scene_ball_mount_empty")
    l = render(base + ball((0, 114, 95.5)), (420, 640, 150), (0, 80, 70), 30,
               "scene_ball_mount_loaded")
    pair("scene_ball_mount", e, l)
