"""Render shaded preview PNGs of the assembled products into models/previews."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import build

OUT = Path(__file__).parent / "previews"
OUT.mkdir(exist_ok=True)
LIGHT = np.array([0.35, 0.75, 0.55]); LIGHT /= np.linalg.norm(LIGHT)


def tris(part, tol=0.15):
    v, f = part.val().tessellate(tol, 0.3)
    v = np.array([p.toTuple() for p in v])
    return v[np.array(f)]


def render(name, items, elev=22, azim=-62):
    """items: list of (part, rgb)."""
    fig = plt.figure(figsize=(8, 6), dpi=160)
    ax = fig.add_subplot(111, projection="3d", proj_type="persp")
    allv = []
    for part, rgb in items:
        t = tris(part)
        n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        shade = 0.45 + 0.55 * np.clip(n @ LIGHT, 0, 1)
        col = np.clip(np.outer(shade, rgb), 0, 1)
        ax.add_collection3d(Poly3DCollection(t, facecolors=col, edgecolors=col,
                                             linewidths=0.1))
        allv.append(t.reshape(-1, 3))
    allv = np.vstack(allv)
    lo, hi = allv.min(0), allv.max(0)
    c, r = (lo + hi) / 2, (hi - lo).max() / 2 * 0.58
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off(); fig.patch.set_facecolor("#d9d5cf"); ax.set_facecolor("#d9d5cf")
    fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(OUT / f"{name}.png"); plt.close(fig)


BLACK, WHITE, GREY = (0.22, 0.22, 0.24), (0.95, 0.95, 0.93), (0.6, 0.6, 0.62)
cleat = build.wall_cleat()
render("wall_cleat", [(cleat, GREY)], azim=-50)
render("jersey_hanger", [(build.jersey_hanger()["jersey_hanger_onepiece"], BLACK)])
render("jersey_hanger_back",
       [(build.jersey_hanger()["jersey_hanger_onepiece"], BLACK)], azim=118, elev=-15)
split = build.jersey_hanger(split=True)
render("jersey_hanger_split_exploded",
       [(split["jersey_hanger_block"], BLACK),
        (split["jersey_hanger_arm_right"].translate((25, 0, 0)), BLACK),
        (split["jersey_hanger_arm_left"].translate((-25, 0, 0)), BLACK)])
for size, w in build.PRO_SIZES.items():
    p = build.jersey_hanger_pro(w)[f"jersey_hanger_pro_{size}_onepiece"]
    render(f"jersey_hanger_pro_{size}", [(p, WHITE)])
render("scarf_track", [(build.scarf_track()["scarf_track"], BLACK)])
render("scarf_track_top", [(build.scarf_track()["scarf_track"], BLACK)], elev=60, azim=-80)
render("ball_mount", [(build.ball_mount()["ball_mount"], BLACK)], elev=35)
render("ball_mount_below", [(build.ball_mount()["ball_mount"], BLACK)], elev=-25, azim=-120)
