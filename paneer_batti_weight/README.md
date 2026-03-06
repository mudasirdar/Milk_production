# Paneer Batti Weight — Odoo Custom Module

## What This Module Does

When selling **Paneer Batti**, the paneer is packed inside heavy containers called *battis*.
This module adds tare weight deduction to your sale orders so you only invoice for the
**net paneer weight** — not the container weight.

```
Formula:
Net Paneer Weight = Gross Weight − (Number of Battis × Batti Weight per Container)

Example:
  Gross Weight  = 60.000 kg
  Battis        = 7
  Batti Weight  = 0.400 kg each
  ─────────────────────────────
  Net Weight    = 60 − (7 × 0.4) = 60 − 2.8 = 57.200 kg  ✓
```

---

## Compatibility

| Odoo Version | Community | Enterprise |
|---|---|---|
| 17.0 | ✅ | ✅ |
| 18.0 | ✅ | ✅ |
| 19.0 | ✅ | ✅ |

> Uses Odoo 17+ modern XML syntax (`column_invisible`, inline `invisible`/`required`/`readonly`
> Python expressions). The old `attrs` and `states` approach is NOT used.

---

## Installation

### Step 1 — Copy the module
Place the `paneer_batti_weight` folder in your custom addons directory.

### Step 2 — Add to addons path
In your `odoo.conf`:
```ini
addons_path = /path/to/odoo/addons,/path/to/your/custom_addons
```

### Step 3 — Restart Odoo server
```bash
# Systemd
sudo systemctl restart odoo

# Direct
python odoo-bin -c odoo.conf --update=paneer_batti_weight
```

### Step 4 — Install in Odoo UI
1. Go to **Settings → Activate Developer Mode**
2. Go to **Apps → Update Apps List** (click the button)
3. Search: `Paneer Batti Weight`
4. Click **Install**

---

## Setup After Installation

### ⚠️ CRITICAL: Set Internal Reference on Product

The module identifies Paneer Batti **only by its Internal Reference**.
Without this step, nothing will work.

1. Go to **Inventory** or **Sales → Products**
2. Open (or create) the **Paneer Batti** product
3. Under the **General Information** tab:
   - Set **Internal Reference** = `paneer_batti`  ← must be exactly this
   - Set **Unit of Measure** = `kg`
4. Go to the **Sales** tab:
   - You will see a new section **"Batti / Container Settings"**
   - Set **Tare Weight per Batti** = `0.4` (adjust to your actual batti weight)
5. Click **Save**

> The Internal Reference must be `paneer_batti` — lowercase, underscore, no spaces.
> If you want to use a different reference, change `PANEER_BATTI_INTERNAL_REF` in
> `models/sale_order_line.py` line 12 before installing.

---

## Using It on a Sale Order

1. Go to **Sales → Orders → New**
2. Add **Paneer Batti** to the order lines
3. Four new columns appear **only on the Paneer Batti row**:

| Column | Action |
|---|---|
| **Gross Wt (kg)** | Enter total weight including containers, e.g. `60` |
| **No. of Battis** | Enter number of containers, e.g. `7` |
| **Batti Wt (kg)** | Pre-filled from product (`0.4`), override if needed |
| **Net Paneer Wt (kg)** | **Auto-calculated** — shows `57.2` |

4. The **Quantity** column automatically updates to `57.2`
5. The invoice will be generated for **57.2 kg** only ✅

---

## How Columns Behave

| Situation | Result |
|---|---|
| Line product = Paneer Batti | All 4 weight columns appear |
| Line product = anything else | Columns are completely hidden for that row |
| Mixed order (Paneer Batti + Milk + Butter) | Only the Paneer Batti row shows the columns |
| Data entry error (gross < tare) | Net weight floors at `0.0`, no negative qty |

---

## Module File Structure

```
paneer_batti_weight/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── product_template.py    ← Adds tare_weight_per_batti on product
│   └── sale_order_line.py     ← All weight logic + auto-compute + qty sync
└── views/
    ├── product_template_views.xml  ← Batti settings section on product form
    └── sale_order_views.xml        ← Batti columns on sale order lines
```

---

## Customization Reference

### Change the product identifier
Edit `models/sale_order_line.py` line 12:
```python
PANEER_BATTI_INTERNAL_REF = 'paneer_batti'   # ← change to your internal ref
```

### Change default batti weight
Either update it on the product form in Odoo (recommended),
or change the `default=0.4` in `models/product_template.py`.

---

## Technical Notes (for Odoo Developers)

- **No `attrs` used** — all view conditions use Odoo 17+ inline Python expressions
- **`column_invisible`** used on tree fields (not `invisible`) to hide full columns
- `is_paneer_batti` is a stored computed Boolean — safe to use in `column_invisible`
- `net_weight` is computed+stored, also synced via `@api.onchange` for live UI feedback
- Works on both **Community** and **Enterprise** — only depends on `sale` and `product`
- No Enterprise-only modules in `depends`
