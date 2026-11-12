"""Generate the demo occupancy grid committed under maps/.

    python3 scripts/make_demo_map.py

The result is a SYNTHETIC warehouse floor plan (10 m x 6 m at 5 cm/cell: two
shelf rows, aisles, a charging dock). It exists so that `bringup_sim` is a
one-command demo and so CI can load a map of known dimensions.

It is NOT a slam_toolbox artifact. If the README quotes mapping resolution or
map size, it must quote numbers from a real mapping run (see docs/BENCHMARK.md).
"""

from __future__ import annotations

import argparse
import os

RES = 0.05          # m per cell
W_METERS = 10.0
H_METERS = 6.0
FREE, OCC = 254, 0  # PGM grey levels


class Grid:
    def __init__(self, w: int, h: int) -> None:
        self.w, self.h = w, h
        self.px = bytearray([FREE]) * (w * h)

    def rect(self, x0: float, y0: float, x1: float, y1: float, value: int) -> None:
        """Fill a rectangle given in metres, origin at the map's bottom-left."""
        cx0, cx1 = sorted((int(x0 / RES), int(x1 / RES)))
        cy0, cy1 = sorted((int(y0 / RES), int(y1 / RES)))
        for cy in range(max(0, cy0), min(self.h, cy1)):
            row = cy * self.w
            for cx in range(max(0, cx0), min(self.w, cx1)):
                self.px[row + cx] = value

    def to_pgm(self) -> bytes:
        # PGM rows are written top-down, so flip vertically (ROS y axis points up).
        body = bytearray()
        for cy in range(self.h - 1, -1, -1):
            body += self.px[cy * self.w:(cy + 1) * self.w]
        return b'P5\n%d %d\n255\n' % (self.w, self.h) + bytes(body)


def build() -> Grid:
    w, h = int(W_METERS / RES), int(H_METERS / RES)
    g = Grid(w, h)

    wall = 0.10
    g.rect(0, 0, W_METERS, wall, OCC)                 # south wall
    g.rect(0, H_METERS - wall, W_METERS, H_METERS, OCC)  # north wall
    g.rect(0, 0, wall, H_METERS, OCC)                 # west wall
    g.rect(W_METERS - wall, 0, W_METERS, H_METERS, OCC)  # east wall

    # Two shelf rows, 1.2 m deep units with 2.0 m aisles between them.
    shelf_depth, shelf_len, pitch = 0.60, 3.00, 3.60
    for row_y in (1.60, 3.00):          # y of shelf row centreline
        for unit in range(2):
            x0 = 1.60 + unit * pitch
            g.rect(x0, row_y - shelf_depth / 2, x0 + shelf_len, row_y + shelf_depth / 2, OCC)

    # Charging dock footprint on the west aisle.
    g.rect(0.35, 4.45, 1.15, 5.05, OCC)
    return g


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', default=os.path.join(os.path.dirname(__file__), '..', 'warehouse_amr_description', 'maps'))
    args = ap.parse_args()
    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    g = build()
    pgm = os.path.join(out_dir, 'warehouse.pgm')
    with open(pgm, 'wb') as fh:
        fh.write(g.to_pgm())

    yaml_path = os.path.join(out_dir, 'warehouse.yaml')
    with open(yaml_path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(
            'image: warehouse.pgm\n'
            'mode: trinary\n'
            'resolution: %.2f\n'
            'origin: [0.0, 0.0, 0.0]\n'
            'negate: 0\n'
            'occupied_thresh: 0.65\n'
            'free_thresh: 0.25\n' % RES
        )
    print('wrote', pgm, '(%dx%d cells, %.1f x %.1f m)' % (g.w, g.h, W_METERS, H_METERS))
    print('wrote', yaml_path)


if __name__ == '__main__':
    main()
