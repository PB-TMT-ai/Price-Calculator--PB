"""Read/write helpers used by the Streamlit app."""
from __future__ import annotations

from datetime import datetime, timezone

from .database import connect, export_components_csv, export_price_history_csv


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_clusters(team: str, state: str | None = None) -> list[dict]:
    conn = connect(team)
    if state:
        rows = conn.execute(
            "SELECT cluster_key, name, major_city, state FROM clusters "
            "WHERE state = ? ORDER BY name", (state,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT cluster_key, name, major_city, state FROM clusters ORDER BY name"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_states(team: str) -> list[str]:
    conn = connect(team)
    rows = conn.execute(
        "SELECT DISTINCT state FROM clusters WHERE state IS NOT NULL ORDER BY state"
    ).fetchall()
    conn.close()
    return [r["state"] for r in rows]


def get_price_lists(team: str) -> list[dict]:
    """All price lists for a team, newest first."""
    conn = connect(team)
    rows = conn.execute(
        """SELECT id, effective_date, reference, validity, note, bend_extra,
                  dia8_project, dia8_retail, dia10_project, dia10_retail
           FROM price_lists ORDER BY effective_date DESC, id DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_pl(team: str, on_date: str | None = None) -> dict | None:
    """Latest price list effective on/before `on_date` (default: most recent)."""
    conn = connect(team)
    if on_date:
        row = conn.execute(
            """SELECT * FROM price_lists WHERE effective_date <= ?
               ORDER BY effective_date DESC, id DESC LIMIT 1""",
            (on_date,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM price_lists ORDER BY effective_date DESC, id DESC LIMIT 1"
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_price(team: str, pl_id: int, cluster_key: str) -> dict | None:
    conn = connect(team)
    row = conn.execute(
        "SELECT fe550, fe550d FROM prices WHERE pl_id=? AND cluster_key=?",
        (pl_id, cluster_key),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_cluster_price_history(team: str, cluster_key: str) -> list[dict]:
    conn = connect(team)
    rows = conn.execute(
        """SELECT pl.effective_date, pl.reference, p.fe550, p.fe550d, pl.note
           FROM prices p JOIN price_lists pl ON pl.id = p.pl_id
           WHERE p.cluster_key = ?
           ORDER BY pl.effective_date DESC""",
        (cluster_key,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_components(team: str, cluster_key: str) -> dict:
    conn = connect(team)
    row = conn.execute(
        "SELECT * FROM components WHERE cluster_key=?", (cluster_key,)
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def save_components(team: str, cluster_key: str, values: dict) -> None:
    conn = connect(team)
    conn.execute(
        """UPDATE components SET
             freight_to_dealer=?, cash_discount=?, quantity_discount=?,
             distributor_margin=?, additional_price_support=?, jsw_one_ecp=?,
             company_scheme=?, distributor_scheme=?, updated_at=?
           WHERE cluster_key=?""",
        (
            values.get("freight_to_dealer", 0),
            values.get("cash_discount", 0),
            values.get("quantity_discount", 0),
            values.get("distributor_margin", 0),
            values.get("additional_price_support", 0),
            values.get("jsw_one_ecp", 0),
            values.get("company_scheme", 0),
            values.get("distributor_scheme", 0),
            _now(), cluster_key,
        ),
    )
    conn.execute(
        "INSERT INTO change_log(ts,entity,detail) VALUES (?,?,?)",
        (_now(), "components", f"{cluster_key} updated"),
    )
    conn.commit()
    conn.close()
    export_components_csv(team)


def get_incentive(team: str) -> dict:
    conn = connect(team)
    tiers = conn.execute(
        "SELECT label, min_pct, inr_per_mt FROM incentive_tiers ORDER BY min_pct"
    ).fetchall()
    meta = dict(
        (r["key"], r["value"])
        for r in conn.execute("SELECT key, value FROM incentive_meta").fetchall()
    )
    conn.close()
    return {"tiers": [dict(t) for t in tiers], "meta": meta}


def resolve_pincode(team: str, pincode: int) -> dict | None:
    conn = connect(team)
    row = conn.execute(
        """SELECT p.pincode, p.district, p.cluster_key, c.name, c.major_city
           FROM pincodes p JOIN clusters c ON c.cluster_key = p.cluster_key
           WHERE p.pincode = ?""",
        (pincode,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def find_team_for_pincode(pincode: int) -> str | None:
    """Search all teams for a pincode (used by the global pincode lookup)."""
    from .database import TEAMS
    for team in TEAMS:
        if resolve_pincode(team, pincode):
            return team
    return None


def add_price_list(team: str, meta: dict, prices: dict[str, dict]) -> int:
    """Insert a new price list + its per-cluster prices. Returns the new pl id.

    meta keys: effective_date, reference, validity, note, bend_extra,
               dia8_project, dia8_retail, dia10_project, dia10_retail
    prices: {cluster_key: {"fe550": x, "fe550d": y}}
    """
    conn = connect(team)
    cur = conn.execute(
        """INSERT INTO price_lists
           (effective_date,reference,validity,note,bend_extra,dia8_project,
            dia8_retail,dia10_project,dia10_retail,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            meta["effective_date"], meta.get("reference"), meta.get("validity"),
            meta.get("note"), meta.get("bend_extra", 600),
            meta.get("dia8_project", 2500), meta.get("dia8_retail", 3500),
            meta.get("dia10_project", 1000), meta.get("dia10_retail", 2250),
            _now(),
        ),
    )
    pl_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO prices(pl_id,cluster_key,fe550,fe550d) VALUES (?,?,?,?)",
        [(pl_id, ck, v.get("fe550"), v.get("fe550d")) for ck, v in prices.items()],
    )
    conn.execute(
        "INSERT INTO change_log(ts,entity,detail) VALUES (?,?,?)",
        (_now(), "price_list", f"Added {meta['effective_date']} {meta.get('reference','')}"),
    )
    conn.commit()
    conn.close()
    export_price_history_csv()
    return pl_id
