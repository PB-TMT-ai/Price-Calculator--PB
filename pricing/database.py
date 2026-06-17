"""
Database layer for the price calculator.

Each sales team (North / Central / East) gets its own SQLite database under
data/<team>.db, holding only that team's clusters, price-list history,
component defaults, pincodes and the incentive scheme.

The databases are *generated* from the committed sources:
  - data/seed/source_prices.py    (price lists, clusters, incentive scheme)
  - data/seed/pincode_cluster.csv (pincode -> cluster -> team)
so they can always be rebuilt on a fresh checkout with `python build_db.py`.

Admin edits made through the app are written back to the live DB *and*
exported to data/seed/components_<team>.csv so they survive a rebuild and
can be committed to git.
"""
from __future__ import annotations

import csv
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SEED_DIR = DATA_DIR / "seed"
TEAMS = ["North", "Central", "East"]


def db_path(team: str) -> Path:
    return DATA_DIR / f"{team.lower()}.db"


def connect(team: str) -> sqlite3.Connection:
    """Open a connection to a team DB (building it first if missing)."""
    p = db_path(team)
    if not p.exists():
        build_all()
    conn = sqlite3.connect(p, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# --------------------------------------------------------------------------- #
#  Schema
# --------------------------------------------------------------------------- #
SCHEMA = """
CREATE TABLE clusters (
    cluster_key TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    major_city  TEXT,
    team        TEXT NOT NULL
);

CREATE TABLE price_lists (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    effective_date TEXT NOT NULL,           -- ISO yyyy-mm-dd
    reference      TEXT,
    validity       TEXT,
    note           TEXT,
    bend_extra     REAL DEFAULT 0,
    dia8_project   REAL DEFAULT 0,
    dia8_retail    REAL DEFAULT 0,
    dia10_project  REAL DEFAULT 0,
    dia10_retail   REAL DEFAULT 0,
    created_at     TEXT,
    UNIQUE(effective_date, reference)
);

CREATE TABLE prices (
    pl_id       INTEGER NOT NULL REFERENCES price_lists(id) ON DELETE CASCADE,
    cluster_key TEXT NOT NULL REFERENCES clusters(cluster_key),
    fe550       REAL,        -- JSW One 550   (basic + frt, 12-32mm)
    fe550d      REAL,        -- JSW One 550 D (12-32mm)
    PRIMARY KEY (pl_id, cluster_key)
);

CREATE TABLE components (
    cluster_key              TEXT PRIMARY KEY REFERENCES clusters(cluster_key),
    freight_to_dealer        REAL DEFAULT 0,
    cash_discount            REAL DEFAULT 0,
    distributor_margin       REAL DEFAULT 0,
    additional_price_support REAL DEFAULT 0,
    jsw_one_ecp              REAL DEFAULT 0,
    company_scheme           REAL DEFAULT 0,
    distributor_scheme       REAL DEFAULT 0,
    updated_at               TEXT
);

CREATE TABLE incentive_tiers (
    label       TEXT,
    min_pct     REAL,
    inr_per_mt  REAL,
    month       TEXT
);

CREATE TABLE incentive_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE pincodes (
    pincode     INTEGER PRIMARY KEY,
    district    TEXT,
    cluster_key TEXT REFERENCES clusters(cluster_key)
);

CREATE TABLE change_log (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ts     TEXT,
    entity TEXT,
    detail TEXT
);

CREATE INDEX idx_prices_cluster ON prices(cluster_key);
CREATE INDEX idx_pincodes_cluster ON pincodes(cluster_key);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
#  Build
# --------------------------------------------------------------------------- #
def build_all() -> None:
    """(Re)build all three team databases from the committed sources."""
    # Imported lazily so the package has no hard import-time dependency on it.
    from data.seed import source_prices as src

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load pincode -> cluster mapping grouped by team.
    pincodes_by_team: dict[str, list[tuple]] = {t: [] for t in TEAMS}
    pin_csv = SEED_DIR / "pincode_cluster.csv"
    if pin_csv.exists():
        with open(pin_csv, newline="") as fp:
            for r in csv.DictReader(fp):
                pin = (r.get("pincode") or "").strip()
                if not pin.isdigit():
                    continue
                pincodes_by_team.setdefault(r["team"], []).append(
                    (int(pin), r["district"], r["cluster_key"])
                )

    # Optional persisted component overrides per team.
    comp_overrides = _load_component_overrides()

    for team in TEAMS:
        path = db_path(team)
        if path.exists():
            path.unlink()
        conn = sqlite3.connect(path)
        conn.executescript(SCHEMA)

        team_clusters = {
            k: v for k, v in src.CLUSTERS.items() if v[2] == team
        }
        conn.executemany(
            "INSERT INTO clusters(cluster_key,name,major_city,team) VALUES (?,?,?,?)",
            [(k, v[0], v[1], v[2]) for k, v in team_clusters.items()],
        )

        # Price lists + prices.
        for pl in src.PRICE_LISTS:
            dia = pl["extras"]["dia"]
            cur = conn.execute(
                """INSERT INTO price_lists
                   (effective_date,reference,validity,note,bend_extra,
                    dia8_project,dia8_retail,dia10_project,dia10_retail,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    pl["effective_date"], pl["reference"], pl["validity"], pl["note"],
                    pl["extras"]["bend_extra"],
                    dia["8"]["project"], dia["8"]["retail"],
                    dia["10"]["project"], dia["10"]["retail"],
                    _now(),
                ),
            )
            pl_id = cur.lastrowid
            rows = [
                (pl_id, ck, pl["prices"][ck]["fe550"], pl["prices"][ck]["fe550d"])
                for ck in team_clusters
                if ck in pl["prices"]
            ]
            conn.executemany(
                "INSERT INTO prices(pl_id,cluster_key,fe550,fe550d) VALUES (?,?,?,?)",
                rows,
            )

        # Component defaults (apply persisted overrides if present).
        for ck in team_clusters:
            vals = comp_overrides.get(ck, {})
            conn.execute(
                """INSERT INTO components
                   (cluster_key,freight_to_dealer,cash_discount,distributor_margin,
                    additional_price_support,jsw_one_ecp,company_scheme,
                    distributor_scheme,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    ck,
                    vals.get("freight_to_dealer", 0),
                    vals.get("cash_discount", 0),
                    vals.get("distributor_margin", 0),
                    vals.get("additional_price_support", 0),
                    vals.get("jsw_one_ecp", 0),
                    vals.get("company_scheme", 0),
                    vals.get("distributor_scheme", 0),
                    _now(),
                ),
            )

        # Incentive scheme.
        for label, minpct, inr in src.INCENTIVE_SCHEME["tiers"]:
            conn.execute(
                "INSERT INTO incentive_tiers(label,min_pct,inr_per_mt,month) VALUES (?,?,?,?)",
                (label, minpct, inr, src.INCENTIVE_SCHEME["month"]),
            )
        si = src.INCENTIVE_SCHEME["stocking_incentive"]
        conn.execute("INSERT INTO incentive_meta(key,value) VALUES (?,?)",
                     ("stocking_incentive_inr", str(si["inr_per_mt"])))
        conn.execute("INSERT INTO incentive_meta(key,value) VALUES (?,?)",
                     ("stocking_incentive_note", si["note"]))
        conn.execute("INSERT INTO incentive_meta(key,value) VALUES (?,?)",
                     ("incentive_month", src.INCENTIVE_SCHEME["month"]))

        # Pincodes for this team.
        conn.executemany(
            "INSERT OR IGNORE INTO pincodes(pincode,district,cluster_key) VALUES (?,?,?)",
            pincodes_by_team.get(team, []),
        )

        conn.execute("INSERT INTO change_log(ts,entity,detail) VALUES (?,?,?)",
                     (_now(), "build", f"Built {team} DB from sources"))
        conn.commit()
        conn.close()

    export_price_history_csv()


def _load_component_overrides() -> dict[str, dict]:
    """Read any committed component overrides (components_<team>.csv)."""
    out: dict[str, dict] = {}
    for team in TEAMS:
        f = SEED_DIR / f"components_{team.lower()}.csv"
        if not f.exists():
            continue
        with open(f, newline="") as fp:
            for r in csv.DictReader(fp):
                ck = r.pop("cluster_key")
                out[ck] = {k: float(v or 0) for k, v in r.items()}
    return out


# --------------------------------------------------------------------------- #
#  Exports (keep git-trackable copies in sync with the live DB)
# --------------------------------------------------------------------------- #
def export_components_csv(team: str) -> None:
    conn = connect(team)
    rows = conn.execute(
        """SELECT cluster_key,freight_to_dealer,cash_discount,distributor_margin,
                  additional_price_support,jsw_one_ecp,company_scheme,distributor_scheme
           FROM components ORDER BY cluster_key"""
    ).fetchall()
    conn.close()
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    with open(SEED_DIR / f"components_{team.lower()}.csv", "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(rows[0].keys() if rows else ["cluster_key"])
        for r in rows:
            w.writerow(list(r))


def export_price_history_csv() -> None:
    """One flat CSV of the entire price history across all teams."""
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for team in TEAMS:
        conn = connect(team)
        for r in conn.execute(
            """SELECT pl.effective_date, pl.reference, c.team, c.cluster_key,
                      c.name, c.major_city, p.fe550, p.fe550d, pl.bend_extra,
                      pl.dia8_project, pl.dia8_retail, pl.dia10_project,
                      pl.dia10_retail, pl.note
               FROM prices p
               JOIN price_lists pl ON pl.id = p.pl_id
               JOIN clusters c ON c.cluster_key = p.cluster_key
               ORDER BY pl.effective_date, c.cluster_key"""
        ).fetchall():
            out.append(list(r))
        conn.close()
    with open(SEED_DIR / "price_history.csv", "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow([
            "effective_date", "reference", "team", "cluster_key", "name",
            "major_city", "fe550", "fe550d", "bend_extra", "dia8_project",
            "dia8_retail", "dia10_project", "dia10_retail", "note",
        ])
        w.writerows(out)


if __name__ == "__main__":
    build_all()
    print("Built databases:", ", ".join(str(db_path(t)) for t in TEAMS))
