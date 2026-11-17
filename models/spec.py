"""Generate the supplier RFQ package: models/rfq/RFQ_spec.pdf + STEP files.

Run:  python3 models/spec.py
"""
from pathlib import Path
import shutil
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import cadquery as cq
import build

OUT = Path(__file__).parent / "rfq"
REV, DATE = "A", "2026-11-17"
PROJECT = "Wall display mounts – jersey / scarf / ball"
BRAND = 'Brand: TBD (working name "The Dressing Room")'
A4 = (11.69, 8.27)
DENSITY = 1.05  # g/cm3, ABS

hanger = build.jersey_hanger(split=True)
pro = {s: build.jersey_hanger_pro(w, split=True) for s, w in build.PRO_SIZES.items()}

SNAP = ("Snap tongue (interface, ±0.1): 12 long x 5 x 10 mm, forked, two prongs "
        "2.5 mm thick, barbs 0.7 mm. Must click into HB-01 by hand, permanent.")
PARTS = [
    dict(id="HB-01", name="Hanger block (shared by all jersey hangers)",
         shape=hanger["hanger_block"], file="hanger_block", colour="Black + White",
         notes=["Used in SKU 1-4. One block + two arms = one hanger.",
                "Rear: dovetail slot, open at bottom, closed at top: 12.5 wide at "
                "rear face, 20.5 wide at 5.3 deep, 30 long (interface, ±0.1).",
                "Both sides: snap pocket 10.4 x 5.4 mm, 12.3 deep, with catch "
                "recess for 0.7 mm barbs (interface, ±0.1).",
                "Thick section – supplier to core out from the rear / bottom.",
                "Logo area 20 x 8 mm on front face – artwork TBD, quote as "
                "exchangeable mould insert.",
                "A-surfaces: front, top, both sides."]),
    dict(id="JA-01", name="Jersey hanger arm – basic (left = right, same part)",
         shape=hanger["jersey_hanger_arm"], file="jersey_hanger_arm", colour="Black",
         notes=["2 pcs per hanger. Symmetric about its mid-plane, so one part "
                "serves both sides.", SNAP,
                "Open loop frame, section approx. 7 x 8 mm, all outer corners R4.",
                "A-surfaces: all except the tongue."]),
    *[dict(id=f"PA-{s[0].upper()}", name=f"Pro arm – {s} (left = right, same part)",
           shape=pro[s][f"jersey_hanger_pro_{s}_arm"],
           file=f"jersey_hanger_pro_{s}_arm", colour="White",
           notes=[f"2 pcs per hanger. Assembled hanger width {int(w)} mm.",
                  SNAP,
                  "Bar 10 x 12 mm with shoulder pad 96 x 28 x 5 mm tilted 14°, "
                  "pad corners R9. Supplier may core the bar from the underside.",
                  "The three Pro sizes differ only in bar length – a family "
                  "mould with exchangeable inserts is welcome.",
                  "A-surfaces: pad top, bar front and top."])
      for s, w in build.PRO_SIZES.items()],
    dict(id="ST-01", name="Scarf track", shape=build.scarf_track()["scarf_track"],
         file="scarf_track", colour="Black",
         notes=["Bar 170 x 8 x 16 mm held 22 mm off the wall by a 6 mm blade.",
                "Rear block carries the same dovetail slot as HB-01 "
                "(interface, ±0.1).",
                "Top face flat. Bar edges rounded – no sharp edges (textile).",
                "A-surfaces: bar, all faces."]),
    dict(id="BM-01", name="Ball mount (size 5 ball, dia. 220 mm)",
         shape=build.ball_mount()["ball_mount"], file="ball_mount", colour="Black",
         notes=["Open C-ring, inner dia. 102 mm, ring 8 x 8 mm, 100° front "
                "opening, 3 mm x 45° seat chamfer on the top inner edge.",
                "Ring centre 114 mm from the wall. Top face flat.",
                "Rear block carries the same dovetail slot as HB-01 "
                "(interface, ±0.1).",
                "Must carry 1.5 kg on the ring without visible sag – supplier to "
                "confirm material / ribbing (PC-ABS or glass-filled PA allowed).",
                "A-surfaces: ring and top face."]),
    dict(id="AP-01", name="Wall plate – standard (adhesive or screws)",
         shape=build.adhesive_plate(), file="adhesive_plate", colour="Black",
         notes=["Used in SKU 1-5. Plate 50 x 69 x 2.5 mm, corners R6.",
                "Dovetail cleat on front: 12 wide at plate, 20 wide at 5 mm "
                "height, 29 long, top edge chamfered (interface, ±0.1).",
                "2 holes dia. 4.5 mm, countersunk dia. 9 mm, 16 mm pitch.",
                "Rear face flat within 0.2 mm (adhesive bond area).",
                "Supplied with die-cut double-sided acrylic foam tape "
                "(3M VHB 5952 or equivalent, 1.1 mm) 48 x 67 mm, pre-applied, "
                "with release liner."]),
    dict(id="AP-02", name="Wall plate – ball mount (adhesive or screws)",
         shape=build.adhesive_plate(w=60, below=20, above=70),
         file="adhesive_plate_ball", colour="Black",
         notes=["Used in SKU 6. Plate 60 x 119 x 2.5 mm, corners R6.",
                "Same dovetail cleat and screw holes as AP-01.",
                "Rear face flat within 0.2 mm (adhesive bond area).",
                "Supplied with die-cut foam tape 58 x 117 mm, pre-applied."]),
    dict(id="WC-01", name="Wall cleat – screw only (OPTIONAL, quote separately)",
         shape=build.wall_cleat(), file="wall_cleat", colour="Black",
         notes=["Smaller alternative to AP-01 for screw-only mounting.",
                "Same dovetail and screw holes as the cleat on AP-01.",
                "Only needed if we decide to offer a screw-only version."]),
]

SKUS = [
    ("SKU 1", "Jersey Hanger – black", "1x HB-01 (black), 2x JA-01, 1x AP-01, hardware kit"),
    ("SKU 2", "Jersey Hanger Pro – Compact, white", "1x HB-01 (white), 2x PA-C, 1x AP-01, hardware kit"),
    ("SKU 3", "Jersey Hanger Pro – Regular, white", "1x HB-01 (white), 2x PA-R, 1x AP-01, hardware kit"),
    ("SKU 4", "Jersey Hanger Pro – Wide, white", "1x HB-01 (white), 2x PA-W, 1x AP-01, hardware kit"),
    ("SKU 5", "Scarf Track – black", "1x ST-01, 1x AP-01, hardware kit"),
    ("SKU 6", "Ball Mount – black", "1x BM-01, 1x AP-02, hardware kit"),
]

GENERAL = [
    ("Process", "Injection moulding. 3D models (STEP) are attached for every part."),
    ("Material", "ABS or PC/ABS, virgin, UV-stabilised. Supplier to propose grade. "
                 "RoHS and REACH compliant."),
    ("Colours", "Black RAL 9005 and white RAL 9003, mass-coloured (no paint)."),
    ("Finish", "Fine matte texture (approx. VDI 3400 Ref. 24-27) on A-surfaces. "
               "No sink marks, flash, weld lines or gate marks on A-surfaces."),
    ("Tolerances", "General ISO 2768-m (±0.2 mm). Features marked 'interface' ±0.1 mm."),
    ("DFM", "Models show the design intent as solid bodies. Supplier may core out "
            "thick sections, add ribs and draft (min. 1°) on non-visible faces. "
            "Outer shape and all interface dimensions must not change. "
            "Send a DFM report for approval before cutting steel."),
    ("Assembly", "Arms click into the block by hand (insertion force < 40 N) and "
                 "must not pull out below 80 N. Block slides onto the wall plate "
                 "by hand, without rattle."),
    ("Load test", "Proposed, 24 h static, no failure or permanent sag: jersey "
                  "hangers 2 kg, scarf track 1 kg, ball mount 1.5 kg on the ring."),
    ("Hardware kit", "Per SKU: 2x countersunk screw 4 x 30 mm, 2x wall plug 6 mm, "
                     "in a small PE bag."),
    ("Packaging", "Flat-packed, parts not assembled. Plain recyclable carton per "
                  "SKU for now; printed retail box to be defined."),
]

QUOTE = [
    "1. Tooling cost per mould, number of cavities, steel grade and guaranteed shots.",
    "2. Unit price per SKU (incl. hardware kit, tape and packaging) at 500 / 1,000 / "
    "3,000 / 5,000 sets.",
    "3. MOQ per SKU and per colour.",
    "4. Lead time: DFM, T1 samples, mass production.",
    "5. Sample cost (5 sets per SKU) and shipping.",
    "6. Price basis FOB (name the port) and payment terms.",
    "7. Optional: price for a pilot run of 50-100 sets without tooling "
    "(3D printing MJF/SLS or vacuum casting).",
]


# --------------------------------------------------------------- drawing help
def edges2d(shape):
    out = []
    for e in shape.val().Edges():
        n = 2 if e.geomType() == "LINE" else 28
        out.append(np.array([p.toTuple() for p in e.positions(np.linspace(0, 1, n))]))
    return out


def dim(ax, p0, p1, text, off, horizontal):
    """Dimension line between p0 and p1 (data coords), offset by `off`."""
    (x0, y0), (x1, y1) = p0, p1
    if horizontal:
        y = off
        ax.annotate("", (x0, y), (x1, y), arrowprops=dict(arrowstyle="<->", lw=0.7))
        ax.plot([x0, x0], [y0, y], lw=0.4, c="0.5")
        ax.plot([x1, x1], [y1, y], lw=0.4, c="0.5")
        ax.text((x0 + x1) / 2, y, text, ha="center", va="bottom", fontsize=7.5)
    else:
        x = off
        ax.annotate("", (x, y0), (x, y1), arrowprops=dict(arrowstyle="<->", lw=0.7))
        ax.plot([x0, x], [y0, y0], lw=0.4, c="0.5")
        ax.plot([x1, x], [y1, y1], lw=0.4, c="0.5")
        ax.text(x, (y0 + y1) / 2, text, ha="right", va="center", fontsize=7.5,
                rotation=90)


def view(ax, edges, i, j, title, flip_i=False):
    lo = np.min([e.min(0) for e in edges], 0)
    hi = np.max([e.max(0) for e in edges], 0)
    sgn = -1 if flip_i else 1
    for e in edges:
        ax.plot(sgn * e[:, i], e[:, j], c="k", lw=0.6)
    a0, a1 = sorted((sgn * lo[i], sgn * hi[i]))
    b0, b1 = lo[j], hi[j]
    span = max(a1 - a0, b1 - b0)
    m = 0.10 * span + 3
    dim(ax, (a0, b0), (a1, b0), f"{hi[i] - lo[i]:.1f}", b0 - m, True)
    dim(ax, (a0, b0), (a0, b1), f"{hi[j] - lo[j]:.1f}", a0 - m, False)
    ax.set_xlim(a0 - 2.6 * m, a1 + m)
    ax.set_ylim(b0 - 2.6 * m, b1 + m)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=8, loc="left", color="0.3")


def iso(ax, shape):
    v, f = shape.val().tessellate(0.15, 0.3)
    t = np.array([p.toTuple() for p in v])[np.array(f)]
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    light = np.array([0.35, 0.75, 0.55]) / np.linalg.norm([0.35, 0.75, 0.55])
    col = np.outer(0.45 + 0.5 * np.clip(n @ light, 0, 1), (0.82, 0.82, 0.84))
    ax.add_collection3d(Poly3DCollection(t, facecolors=col, edgecolors=col, lw=0.1))
    p = t.reshape(-1, 3)
    c, r = (p.min(0) + p.max(0)) / 2, (p.max(0) - p.min(0)).max() / 2 * 0.85
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=22, azim=-62)
    ax.set_axis_off()
    ax.set_title("ISO (not to scale)", fontsize=8, loc="left", color="0.3")


def header(fig, title, page, total):
    fig.text(0.04, 0.955, title, fontsize=14, weight="bold")
    fig.text(0.04, 0.925, f"{PROJECT}   |   {BRAND}", fontsize=8.5, color="0.35")
    fig.text(0.96, 0.955, f"RFQ rev. {REV}  ·  {DATE}", fontsize=9, ha="right")
    fig.text(0.96, 0.925, f"Page {page} / {total}  ·  all dimensions in mm",
             fontsize=8.5, ha="right", color="0.35")
    fig.add_artist(plt.Line2D([0.04, 0.96], [0.91, 0.91], c="k", lw=0.8))


def wrapped(fig, x, y, items, width=64, size=8.5, gap=0.012, bullet="•  "):
    import textwrap
    for it in items:
        lines = textwrap.wrap(it, width)
        for k, ln in enumerate(lines):
            fig.text(x, y, (bullet if k == 0 else "    ") + ln, fontsize=size)
            y -= 0.024
        y -= gap
    return y


# ----------------------------------------------------------------------- pages
def cover(pdf, total):
    fig = plt.figure(figsize=A4)
    header(fig, "Request for quotation – general requirements", 1, total)
    y = 0.87
    import textwrap
    for k, v in GENERAL:
        fig.text(0.04, y, k, fontsize=9, weight="bold")
        for ln in textwrap.wrap(v, 118):
            fig.text(0.17, y, ln, fontsize=9)
            y -= 0.026
        y -= 0.012
    fig.text(0.04, y - 0.01, "Please quote", fontsize=11, weight="bold")
    y -= 0.05
    for q in QUOTE:
        for ln in textwrap.wrap(q, 135):
            fig.text(0.05, y, ln, fontsize=9)
            y -= 0.026
    pdf.savefig(fig)
    plt.close(fig)


def sku_page(pdf, total):
    fig = plt.figure(figsize=A4)
    header(fig, "Products (SKUs) and part list", 2, total)
    ax = fig.add_axes([0.04, 0.60, 0.92, 0.27])
    ax.axis("off")
    tb = ax.table(cellText=SKUS, colLabels=["SKU", "Product", "Contents of one set"],
                  colWidths=[0.08, 0.32, 0.60], loc="upper left", cellLoc="left")
    tb.auto_set_font_size(False)
    tb.set_fontsize(8.5)
    tb.scale(1, 1.5)
    rows = []
    for p in PARTS:
        bb = p["shape"].val().BoundingBox()
        vol = p["shape"].val().Volume() / 1000
        rows.append([p["id"], p["name"], f"{bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f}",
                     f"{vol:.1f}", f"{vol * DENSITY:.0f}", p["colour"],
                     p["file"] + ".step"])
    ax = fig.add_axes([0.04, 0.10, 0.92, 0.46])
    ax.axis("off")
    tb = ax.table(cellText=rows,
                  colLabels=["Part", "Description", "Envelope (mm)", "Solid vol. (cm³)",
                             "Max. weight (g)*", "Colour", "3D file"],
                  colWidths=[0.055, 0.33, 0.10, 0.09, 0.095, 0.085, 0.245],
                  loc="upper left", cellLoc="left")
    tb.auto_set_font_size(False)
    tb.set_fontsize(8)
    tb.scale(1, 1.5)
    fig.text(0.04, 0.07, "* Weight of the solid model in ABS, before coring. "
             "Moulded weight will be lower.", fontsize=8, color="0.35")
    fig.text(0.04, 0.045, "Moulds needed: HB-01, JA-01, PA-C / PA-R / PA-W (family "
             "mould welcome), ST-01, BM-01, AP-01, AP-02. WC-01 optional.",
             fontsize=8, color="0.35")
    pdf.savefig(fig)
    plt.close(fig)


def part_page(pdf, p, page, total):
    fig = plt.figure(figsize=A4)
    header(fig, f"{p['id']}  –  {p['name']}", page, total)
    e = edges2d(p["shape"])
    view(fig.add_axes([0.03, 0.47, 0.34, 0.41]), e, 0, 2, "FRONT (seen from the room)")
    view(fig.add_axes([0.37, 0.47, 0.22, 0.41]), e, 1, 2, "SIDE (wall on the left)")
    view(fig.add_axes([0.03, 0.04, 0.34, 0.41]), e, 0, 1, "TOP (wall at the bottom)")
    iso(fig.add_axes([0.36, 0.03, 0.25, 0.42], projection="3d"), p["shape"])
    bb = p["shape"].val().BoundingBox()
    vol = p["shape"].val().Volume() / 1000
    x = 0.63
    fig.text(x, 0.86, "Specification", fontsize=11, weight="bold")
    facts = [f"3D file: {p['file']}.step",
             f"Envelope: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm",
             f"Solid volume: {vol:.1f} cm³  (max. {vol * DENSITY:.0f} g in ABS, "
             f"before coring)",
             f"Colour: {p['colour']}",
             "Material / finish / tolerances: see page 1"]
    y = wrapped(fig, x, 0.82, facts, width=58, gap=0.004, bullet="")
    fig.text(x, y - 0.02, "Notes", fontsize=11, weight="bold")
    wrapped(fig, x, y - 0.06, p["notes"], width=56)
    pdf.savefig(fig)
    plt.close(fig)


if __name__ == "__main__":
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "step").mkdir(parents=True)
    for p in PARTS:
        cq.exporters.export(p["shape"], str(OUT / "step" / f"{p['file']}.step"))
    total = len(PARTS) + 2
    with PdfPages(OUT / "RFQ_spec.pdf") as pdf:
        cover(pdf, total)
        sku_page(pdf, total)
        for k, p in enumerate(PARTS):
            part_page(pdf, p, k + 3, total)
    print("wrote", OUT / "RFQ_spec.pdf", total, "pages")
