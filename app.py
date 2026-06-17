"""
JSW One TMT — Price Calculator (mobile-friendly) for North / Central / East sales teams.

Run:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from pricing import calc
from pricing import queries as q
from pricing.database import TEAMS

st.set_page_config(page_title="JSW One TMT Price Calculator",
                   page_icon="🧱", layout="centered")

# JSW One brand styling — compact & mobile friendly.
JSW_BLUE = "#0A4DA2"
JSW_DARK = "#06306A"
st.markdown(
    f"""
    <style>
      .block-container {{padding-top: 1rem; padding-bottom: 3rem; max-width: 760px;}}
      div[data-testid="stMetricValue"] {{font-size: 1.7rem; color: {JSW_BLUE};}}
      .stNumberInput input {{font-size: 1rem;}}
      .jsw-header {{
          background: linear-gradient(90deg, {JSW_DARK} 0%, {JSW_BLUE} 100%);
          color: #fff; padding: 14px 18px; border-radius: 12px;
          margin-bottom: 14px; display:flex; align-items:center; gap:12px;
      }}
      .jsw-header .logo {{
          background:#fff; color:{JSW_BLUE}; font-weight:800; font-size:1.05rem;
          padding:6px 10px; border-radius:8px; letter-spacing:.3px;
      }}
      .jsw-header .title {{font-size:1.15rem; font-weight:700; line-height:1.2;}}
      .jsw-header .sub {{font-size:.78rem; opacity:.85;}}
      .stButton button[kind="primary"] {{background:{JSW_BLUE}; border:0;}}
    </style>
    """,
    unsafe_allow_html=True,
)


def brand_header(subtitle: str = "TMT Price Calculator"):
    st.markdown(
        f"""
        <div class="jsw-header">
          <span class="logo">JSW One</span>
          <div>
            <div class="title">{subtitle}</div>
            <div class="sub">Private Brands · Domestic Sales · prices exclude GST</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
#  Authentication  (Sales: 1111  ·  Admin: 9999)
# --------------------------------------------------------------------------- #
def _passwords() -> dict:
    # Defaults can be overridden via .streamlit/secrets.toml ([passwords] section).
    pw = {"1111": "sales", "9999": "admin"}
    try:
        sec = st.secrets.get("passwords", {})
        if sec.get("sales"):
            pw = {str(sec["sales"]): "sales", str(sec.get("admin", "9999")): "admin"}
    except Exception:
        pass
    return pw


def login_gate():
    if st.session_state.get("role"):
        return
    brand_header("TMT Price Calculator")
    st.subheader("🔒 Sign in")
    pw = st.text_input("Password", type="password",
                       placeholder="Sales or Admin password")
    if st.button("Sign in", type="primary"):
        role = _passwords().get(pw.strip())
        if role:
            st.session_state.role = role
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.caption("Sales team and Admins have separate passwords.")
    st.stop()


login_gate()
ROLE = st.session_state.role
brand_header("TMT Price Calculator")

# --------------------------------------------------------------------------- #
#  Team + page selector
# --------------------------------------------------------------------------- #
screens = ["🧮 Calculator", "📈 Price History"]
if ROLE == "admin":
    screens.append("⚙️ Admin")

top = st.columns([1, 1])
team = top[0].selectbox("Zone", TEAMS, key="team")
page = top[1].selectbox("Screen", screens)

with st.sidebar:
    st.markdown(f"**Signed in as:** {ROLE.capitalize()}")
    if st.button("Log out"):
        st.session_state.pop("role", None)
        st.rerun()


def rupee(x) -> str:
    return "—" if x is None else f"₹{x:,.0f}"


def select_state_cluster(team: str, key: str) -> tuple[str, str]:
    """State + Cluster dropdowns (State narrows the cluster list). Returns
    (cluster_key, cluster_name)."""
    states = q.get_states(team)
    c1, c2 = st.columns(2)
    state = c1.selectbox("State", states, key=f"{key}_state")
    clusters = q.get_clusters(team, state)
    cl_names = {c["name"]: c["cluster_key"] for c in clusters}
    cluster_name = c2.selectbox("Cluster / City", list(cl_names.keys()),
                                key=f"{key}_cluster")
    return cl_names[cluster_name], cluster_name


# --------------------------------------------------------------------------- #
#  CALCULATOR
# --------------------------------------------------------------------------- #
def page_calculator():
    # --- Location: Zone (top) -> State -> Cluster ---
    cluster_key, cluster_name = select_state_cluster(team, "calc")

    pls = q.get_price_lists(team)
    pl_labels = {f"{p['effective_date']}  ({p['reference']})": p for p in pls}
    pl_label = st.selectbox("Price List (effective date)", list(pl_labels.keys()))
    pl = pl_labels[pl_label]
    if pl.get("note"):
        st.caption(f"📌 {pl['note']}")

    # --- Product config ---
    c1, c2 = st.columns(2)
    product = c1.selectbox("Product", list(calc.PRODUCTS.keys()))
    btype = c2.selectbox("Type", calc.TYPES)
    c3, c4 = st.columns(2)
    dia = c3.selectbox("Diameter (mm)", calc.DIAS, index=2)
    segment = c4.selectbox("Segment", [s.capitalize() for s in calc.SEGMENTS]).lower()

    price_row = q.get_price(team, pl["id"], cluster_key)
    b = calc.base_price(pl, price_row, product, dia, segment, btype)

    if not b["available"]:
        st.error(f"No **{product}** price published for {cluster_name} in this list.")
        return

    with st.container(border=True):
        st.markdown("**Base price build-up**")
        st.write(
            pd.DataFrame(
                [
                    ("List price (12-32 mm)", b["list_price"]),
                    (f"Dia extra ({dia} mm, {segment})", b["dia_extra"]),
                    (f"Bend extra ({btype})", b["bend_extra"]),
                    ("Base price", b["base"]),
                ],
                columns=["Item", "Rs/MT"],
            ).style.format({"Rs/MT": "{:,.0f}"}).hide(axis="index")
        )

    # --- Components (defaults from DB, editable live) ---
    st.markdown("**Components** (defaults shown — edit for this quote)")
    defaults = q.get_components(team, cluster_key)
    values = {}
    cols = st.columns(2)
    for i, (field, label, sign) in enumerate(calc.COMPONENTS):
        suffix = "  (+)" if sign > 0 else "  (−)"
        values[field] = cols[i % 2].number_input(
            label + suffix, value=float(defaults.get(field, 0) or 0),
            step=50.0, format="%.0f", key=f"comp_{field}",
        )

    n = calc.net_price(b["base"], values)

    # --- Net price ---
    qty = st.number_input("Quantity (MT)", value=1.0, min_value=0.0, step=1.0)
    m1, m2 = st.columns(2)
    m1.metric("Net Price / MT", rupee(n["net"]))
    m2.metric(f"Total ({qty:g} MT)", rupee(n["net"] * qty))

    with st.expander("🧾 Full break-up"):
        rows = [("Base price", b["base"])]
        rows += [(f"{ln['label']} ({'+' if ln['sign']>0 else '−'})", ln["effect"])
                 for ln in n["lines"]]
        rows.append(("NET PRICE / MT", n["net"]))
        st.dataframe(
            pd.DataFrame(rows, columns=["Component", "Rs/MT"])
            .style.format({"Rs/MT": "{:,.0f}"}),
            hide_index=True, use_container_width=True,
        )

    # --- Blended rate ---
    with st.expander("⚖️ Blended rate (diameter mix)"):
        st.caption("Enter the % share of each diameter in the order.")
        bc = st.columns(3)
        mix = {
            "8":     bc[0].number_input("8 mm %", value=0.0, min_value=0.0, step=5.0),
            "10":    bc[1].number_input("10 mm %", value=0.0, min_value=0.0, step=5.0),
            "12-32": bc[2].number_input("12-32 mm %", value=100.0, min_value=0.0, step=5.0),
        }
        br = calc.blended_rate(pl, price_row, product, segment, btype, mix)
        if br:
            st.metric("Blended base / MT", rupee(br["blended"]))
            st.caption(", ".join(f"{p['dia']}mm: {p['weight_pct']:.0f}%" for p in br["parts"]))

    # --- Incentive ---
    with st.expander("🎯 Target-linked incentive"):
        inc = q.get_incentive(team)
        ach = st.slider("Target achievement %", 0, 130, 100, step=5)
        tier = calc.incentive_for(ach, inc["tiers"])
        if tier:
            st.metric("Incentive / MT", rupee(tier["inr_per_mt"]), tier["label"])
        else:
            st.info("Below the lowest slab — no incentive.")
        st.dataframe(
            pd.DataFrame(inc["tiers"]).rename(
                columns={"label": "Slab", "min_pct": "Min %", "inr_per_mt": "Rs/MT"}
            ), hide_index=True, use_container_width=True,
        )
        if inc["meta"].get("stocking_incentive_inr"):
            st.caption(f"➕ Stocking incentive: ₹{inc['meta']['stocking_incentive_inr']}/MT — "
                       f"{inc['meta'].get('stocking_incentive_note','')}")


# --------------------------------------------------------------------------- #
#  PRICE HISTORY
# --------------------------------------------------------------------------- #
def page_history():
    cluster_key, cluster_name = select_state_cluster(team, "hist")
    hist = q.get_cluster_price_history(team, cluster_key)
    if not hist:
        st.info("No history.")
        return
    df = pd.DataFrame(hist)
    show = df.rename(columns={
        "effective_date": "Date", "reference": "Reference",
        "fe550": "JSW One 550", "fe550d": "JSW One 550 D", "note": "Note",
    })
    st.dataframe(
        show[["Date", "JSW One 550", "JSW One 550 D", "Reference", "Note"]]
        .style.format({"JSW One 550": "{:,.0f}", "JSW One 550 D": "{:,.0f}"}),
        hide_index=True, use_container_width=True,
    )
    chart = df[["effective_date", "fe550", "fe550d"]].set_index("effective_date")
    chart.columns = ["JSW One 550", "JSW One 550 D"]
    st.line_chart(chart.sort_index())


# --------------------------------------------------------------------------- #
#  ADMIN
# --------------------------------------------------------------------------- #
def page_admin():
    if ROLE != "admin":
        st.error("Admins only.")
        return
    st.warning("Admin screen — changes update the live database and the committed CSVs.")
    clusters = q.get_clusters(team)
    tab1, tab2, tab3 = st.tabs(["Component defaults", "Add new Price List", "Line-item template"])

    # ---- edit component defaults ----
    with tab1:
        cluster_key, cluster_name = select_state_cluster(team, "adm")
        cur = q.get_components(team, cluster_key)
        vals = {}
        for field, label, sign in calc.COMPONENTS:
            vals[field] = st.number_input(
                label, value=float(cur.get(field, 0) or 0), step=50.0,
                format="%.0f", key=f"adm_{field}",
            )
        if st.button("💾 Save defaults", type="primary"):
            q.save_components(team, cluster_key, vals)
            st.success(f"Saved defaults for {cluster_name}.")

    # ---- add a new price list ----
    with tab2:
        st.caption("Fill this whenever prices change. Pre-filled from the latest list.")
        latest = q.get_latest_pl(team)
        m1, m2 = st.columns(2)
        eff = m1.date_input("Effective date")
        ref = m2.text_input("Reference", value="JODL/ TMT / ")
        validity = st.text_input("Validity", value=latest["validity"] if latest else "")
        note = st.text_area("Note / scheme", value="Bend extra Rs 600/MT.")
        e = st.columns(5)
        bend = e[0].number_input("Bend extra", value=float(latest["bend_extra"]) if latest else 600.0, step=50.0)
        d8p = e[1].number_input("8mm proj", value=float(latest["dia8_project"]) if latest else 2500.0, step=50.0)
        d8r = e[2].number_input("8mm retail", value=float(latest["dia8_retail"]) if latest else 3500.0, step=50.0)
        d10p = e[3].number_input("10mm proj", value=float(latest["dia10_project"]) if latest else 1000.0, step=50.0)
        d10r = e[4].number_input("10mm retail", value=float(latest["dia10_retail"]) if latest else 2250.0, step=50.0)

        # Per-cluster grid prefilled from latest list.
        grid = []
        for c in clusters:
            pr = q.get_price(team, latest["id"], c["cluster_key"]) if latest else {}
            grid.append({"cluster_key": c["cluster_key"], "Cluster": c["name"],
                         "JSW One 550": (pr or {}).get("fe550"),
                         "JSW One 550 D": (pr or {}).get("fe550d")})
        edited = st.data_editor(
            pd.DataFrame(grid), hide_index=True, use_container_width=True,
            disabled=["cluster_key", "Cluster"], key="pl_grid",
        )
        if st.button("➕ Publish new price list", type="primary"):
            prices = {
                r["cluster_key"]: {"fe550": r["JSW One 550"], "fe550d": r["JSW One 550 D"]}
                for _, r in edited.iterrows()
            }
            meta = {"effective_date": str(eff), "reference": ref, "validity": validity,
                    "note": note, "bend_extra": bend, "dia8_project": d8p,
                    "dia8_retail": d8r, "dia10_project": d10p, "dia10_retail": d10r}
            q.add_price_list(team, meta, prices)
            st.success(f"Published price list effective {eff}. History updated.")

    # ---- downloadable line-item template ----
    with tab3:
        st.caption("The exact line-item format to provide on every price/scheme change.")
        tmpl = pd.DataFrame([
            {"cluster_key": c["cluster_key"], "Cluster": c["name"],
             "Major city": c["major_city"], "JSW One 550 (Rs/MT)": "",
             "JSW One 550 D (Rs/MT)": ""}
            for c in clusters
        ])
        st.dataframe(tmpl, hide_index=True, use_container_width=True)
        st.download_button(
            "⬇️ Download CSV template",
            tmpl.to_csv(index=False).encode(),
            file_name=f"price_list_template_{team.lower()}.csv",
            mime="text/csv",
        )
        st.markdown(
            "**Header fields to send each time:** Effective date · Reference · "
            "Validity · Bend extra · 8/10 mm extras (project & retail) · Note/scheme."
        )


# --------------------------------------------------------------------------- #
if page == "🧮 Calculator":
    page_calculator()
elif page == "📈 Price History":
    page_history()
else:
    page_admin()

st.caption("JSW One Distribution Ltd · Private Brands · prices exclude GST.")
