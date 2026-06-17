# JSW One TMT — Price Calculator

A mobile-friendly Streamlit dashboard that lets the **North / Central / East**
sales teams calculate the net TMT price for any cluster, with full price-list
history and an admin screen to publish new price lists & schemes.

## Quick start

```bash
pip install -r requirements.txt
python build_db.py        # builds data/north.db, central.db, east.db from data/seed/
streamlit run app.py
```

Open the URL Streamlit prints (works well on a phone browser).

## What it does

**🧮 Calculator**
- Pick **Team → Cluster/City** (or look up a cluster by **pincode**).
- Choose **Product** (JSW One 550 / JSW One 550 D), **Type** (Straight/Bend),
  **Diameter** (8 / 10 / 12-32 mm) and **Segment** (Retail/Project).
- See the **base price build-up** (list price + dia extra + bend extra).
- Adjust **components** — Freight to Dealer, JSW One ECP (add-on), Cash Discount,
  Distributor's Margin, Additional Price Support, Company/Distributor schemes.
  Defaults are stored per cluster and **editable live** for any quote.
- Get **Net Price / MT** and total for a quantity, with a full break-up.
- **Blended rate** across a diameter mix, and the **target-linked incentive**
  for a given % achievement (+ stocking incentive).

**📈 Price History** — every past price list per cluster, with date of change,
reference, both grades and a trend chart.

**⚙️ Admin**
- Edit per-cluster **component defaults** (saved to DB + committed CSV).
- **Publish a new price list** (effective date, reference, validity, note,
  bend/dia extras, and per-cluster prices) — old lists are retained as history.
- Download the **line-item template** to fill on every price/scheme change.

## Data model

Three **separate SQLite databases** (one per team) under `data/`, each with:
`clusters`, `price_lists`, `prices`, `components`, `incentive_tiers`,
`incentive_meta`, `pincodes`, `change_log`.

### Source of truth (committed, in `data/seed/`)
| File | Purpose |
|------|---------|
| `source_prices.py` | All price lists, clusters & incentive scheme (edit here, then `python build_db.py`) |
| `pincode_cluster.csv` | 11,504 pincodes → cluster → team |
| `components_<team>.csv` | Component defaults (auto-exported when edited in Admin) |
| `price_history.csv` | Flat export of the full price history (auto-exported) |

> The `*.db` files are **generated** and git-ignored — rebuild anytime with
> `python build_db.py`. Because this is the source of truth, price history and
> admin changes survive a fresh checkout once the CSV/`source_prices.py` edits
> are committed.

## Clusters & teams

Derived from the official price lists + the pincode-cluster master:

- **North** (10): Kashmir/Srinagar, Jammu, Chandigarh, Himachal, Uttarakhand,
  Punjab, Delhi, Haryana, Rajasthan, Uttar Pradesh.
- **Central** (4): Chhattisgarh, Madhya Pradesh, Gujarat, Maharashtra.
- **East** (6): Odisha (Central+Coastal), Odisha (West), Jharkhand, Bihar,
  Siliguri/Jalpaiguri/Cooch Behar, West Bengal (Durgapur).

## Notes & assumptions
- **JSW One 550 = Fe-550** ("Basic price + Frt"); **JSW One 550 D = Fe 550D**.
- UP West (Ghaziabad) and UP E+C (Kanpur) carry identical prices in every list
  supplied, and the pincode master has a single "Uttar Pradesh", so they are
  one cluster. Split later if their prices diverge.
- Some clusters have no Fe-550D in the source PDFs (Odisha, Maharashtra) — those
  are stored as blank and the calculator says so.
- Component defaults are seeded at **0** (the PDFs don't carry them) — set real
  values via the Admin screen.
- Prices exclude GST.
```
