# Eye-axis interactive overlay (human_review.html)

## Controls (Section A cards)

Each review-queue chip has a **green** (`#3dd68c`) undirected eye axis drawn on a canvas over the dual PNG (blue NHLE + gold LiDAR stay baked in).

- **Readout:** `Eye az: XX.X°` (0–180°, undirected, north-up)
- **Buttons:** `−5°` `−1°` `+1°` `+5°`
- **Slider:** 0–180, step 0.5
- **Use eye reading:** sets Prefer → `eye` and saves the current angle
- **Drag** on the chip (pointer) also rotates the green line
- Default eye azimuth = that card’s **LiDAR az** (nudged from there)

Prefer dropdown includes `prefer = eye`. Choosing `eye` from the dropdown (without the button) still saves the current overlay angle as `azimuth_eye_deg`.

## Geometry

- Undirected **0–180°**, image top = N, +x = E
- Azimuth θ° from north clockwise to the long axis
- Line through centre: direction `(sin θ, −cos θ)` in pixel space (x right, y down)

## Persistence / Copy JSON

- `localStorage` key: `wiltshire-lb-orientation-prefer-v2` (migrates string map from v1 on first load)
- Per site: `{ "prefer": "lidar"|"nhle"|"hold"|"eye", "azimuth_eye_deg"?: number }`
  - When `prefer` is `eye`, `azimuth_eye_deg` is required (0–180)
  - Storage may keep `azimuth_eye_deg` even for lidar/nhle/hold so the overlay restores; **Copy JSON** only includes it for eye answers
- Clear removes v2 (and leftover v1) and resets selects + eye overlays to LiDAR defaults

### Example Copy JSON (one eye site)

```json
{
  "schema": "wiltshire-lb-orientation-prefer-v2",
  "undirected_deg": "0-180",
  "north_up": true,
  "answers": {
    "SU04NW100": {
      "prefer": "eye",
      "azimuth_eye_deg": 72.5
    }
  },
  "all": {
    "SU04NW100": {
      "prefer": "eye",
      "azimuth_eye_deg": 72.5
    }
  }
}
```

Open `human_review.html` from `scripts/orientation_batch_out/` so dual PNG paths resolve.

## Section C — Indistinct / refused (quick eye-pass)

Section C is a lighter card grid (n=63, highest `azimuth_lidar_conf` first) over plain web JPGs with the same green eye overlay / localStorage **v2** / Copy JSON path as Section A.

Prefer values for indistinct sites:

| prefer | meaning |
|--------|---------|
| `eye` | Clear long axis visible; export includes `azimuth_eye_deg` |
| `leave_indistinct` | Still no clear barrow axis |
| `not_barrow` | Looks like track / ditch / plough / other non-barrow |
| `hold` | Needs another look |

Default green eye az = refused `azimuth_lidar_deg` when non-null, else **90°** (E–W). Meta shows conf + “refused az” (or —). Toolbar Copy JSON / Clear at Section A also cover Section C cards (`article.card[data-id]`); Section C has a small Copy JSON repeat.
