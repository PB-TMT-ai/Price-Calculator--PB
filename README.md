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

## Access (passwords)

The app opens with a sign-in screen and is branded in the **JSW One** style.

| Role | Password | Can see |
|------|----------|---------|
| Sales team | `1111` | Calculator (current price list only) |
| Admin | `9999` | Calculator (any list) + **Past Price Lists** |

> The sales team's Calculator is locked to the **current** price list. All
> **older price lists are Admin-only**, under the **Past Price Lists** screen.

To change them, add a `.streamlit/secrets.toml`:

```toml
[passwords]
sales = "1111"
admin = "9999"
```

## What it does

**🧮 Calculator**
- Pick **Zone → State → Cluster/City** (State is filtered by Zone, Cluster by State).
- Choose **Product** (JSW One 550 / JSW One 550 D), **Type** (Straight/Bend),
  **Diameter** (8 / 10 / 12-32 mm) and **Segment** (Retail/Project).
- See the **base price build-up** (list price + dia extra + bend extra).
- Adjust **components** (defaults stored per cluster, **editable live**).
- Result follows the official **Net Landed to Dealer** waterfall:

  ```
  ( PL + Distributor margin + Admin/manpower + Handling + Bending + CD + QD
    + Dealer annual schemes/meets/tours + Contractor loyalty + JSW One ECP
    + Shortage + Freight to dealer )
  − ( Additional price support + Scheme (operational pricing)
      + Target-linked incentive + Stocking incentive )
  = Net Landed to Dealer
  ```
  PL + Bending come from the price list; the target-linked incentive depends on
  the chosen **achievement %**. Full per-MT break-up and quantity total shown.
- **Blended rate** across a diameter mix.
- **Navigation** (Calculator / Past Price Lists) lives in the sidebar,
  separate from the Zone/State/Cluster filters.

**📈 Past Price Lists** *(admin only)* — every past price list per cluster, with
date of change, reference, both grades and a trend chart.

### Updating prices / schemes
There is **no in-app editing**. Price lists and schemes are maintained in
`data/seed/source_prices.py`; send updated PLs/schemes to the maintainer, who
edits the source and redeploys. The DB is rebuilt from source on deploy
(`python build_db.py`), so a redeploy/reboot picks up the new data.

## Data model

Three **separate SQLite databases** (one per team) under `data/`, each with:
`clusters`, `price_lists`, `prices`, `components`, `incentive_tiers`,
`incentive_meta`, `pincodes`, `change_log`.

### Source of truth (committed, in `data/seed/`)
| File | Purpose |
|------|---------|
| `source_prices.py` | All price lists, clusters & incentive scheme (edit here, then `python build_db.py`) |
| `pincode_cluster.csv` | 11,504 pincodes → cluster → team |
| `components_<team>.csv` | Per-cluster component defaults |
| `price_history.csv` | Flat export of the full price history |

> The `*.db` files are **generated** and git-ignored — rebuild anytime with
> `python build_db.py`. Source files are the single source of truth, so the data
> survives a fresh checkout/redeploy once `source_prices.py` edits are committed.

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
