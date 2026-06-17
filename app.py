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
#  Navigation (separate section, in the sidebar) + Zone filter (in the page)
# --------------------------------------------------------------------------- #
screens = ["🧮 Calculator"]
if ROLE == "admin":
    screens += ["📈 Past Price Lists"]

with st.sidebar:
    st.markdown("### Menu")
    page = st.radio("Go to", screens, label_visibility="collapsed")
    st.divider()
    st.markdown(f"**Signed in as:** {ROLE.capitalize()}")
    if st.button("Log out"):
        st.session_state.pop("role", None)
        st.rerun()

team = st.selectbox("Zone", TEAMS, key="team")


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
    if not pls:
        st.error("No price list available for this zone.")
        return

    if ROLE == "admin":
        # Admins may compute on any (incl. past) price list.
        pl_labels = {f"{p['effective_date']}  ({p['reference']})": p for p in pls}
        pl_label = st.selectbox("Price List (effective date)", list(pl_labels.keys()))
        pl = pl_labels[pl_label]
    else:
        # Sales team always uses the current (latest) price list only.
        pl = pls[0]
        st.markdown(f"**Price List (current):** {pl['effective_date']}  ·  {pl['reference']}")
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
    if price_row is None or price_row.get(calc.PRODUCTS[product]) is None:
        st.error(f"No **{product}** price published for {cluster_name} in this list.")
        return

    # --- Components (defaults from DB, editable live) — read first so the
    #     ECP rule (ECP set => 8/10 mm dia differential = 0) can apply. ---
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
    ecp = values.get("jsw_one_ecp", 0) or 0

    b = calc.base_price(pl, price_row, product, dia, segment, btype, ecp=ecp)

    with st.container(border=True):
        st.markdown("**Base price build-up**")
        dia_label = f"Dia extra ({dia} mm, {segment})"
        if b["dia_waived"]:
            dia_label += " — waived (ECP applied)"
        st.write(
            pd.DataFrame(
                [
                    ("List price (12-32 mm)", b["list_price"]),
                    (dia_label, b["dia_extra"]),
                    (f"Bend extra ({btype})", b["bend_extra"]),
                    ("Base price", b["base"]),
                ],
                columns=["Item", "Rs/MT"],
            ).style.format({"Rs/MT": "{:,.0f}"}).hide(axis="index")
        )

    n = calc.net_price(b["base"], values)

    # --- Sub-total before incentives ---
    st.metric("Sub-total / MT (before incentives)", rupee(n["net"]))

    # --- Incentives (deducted to reach Net Landed to Dealer) ---
    st.markdown("**🎯 Incentives (deducted)**")
    inc = q.get_incentive(team)
    ic1, ic2 = st.columns([2, 1])
    ach = ic1.slider("Target achievement %", 0, 130, 100, step=5)
    tier = calc.incentive_for(ach, inc["tiers"])
    tli = float(tier["inr_per_mt"]) if tier else 0.0
    ic2.metric("Target-linked / MT", rupee(tli), tier["label"] if tier else "no slab")

    apply_tli = st.checkbox("Apply target-linked incentive", value=True)
    stock_inr = float(inc["meta"].get("stocking_incentive_inr") or 0)
    apply_stock = False
    if stock_inr:
        apply_stock = st.checkbox(
            f"Apply stocking incentive (₹{stock_inr:,.0f}/MT)", value=True,
            help=inc["meta"].get("stocking_incentive_note", ""),
        )

    incentive_applied = (tli if apply_tli else 0.0) + (stock_inr if apply_stock else 0.0)
    landed = n["net"] - incentive_applied

    # --- Net landed to dealer ---
    qty = st.number_input("Quantity (MT)", value=1.0, min_value=0.0, step=1.0)
    st.divider()
    l1, l2 = st.columns(2)
    l1.metric("Net Landed to Dealer / MT", rupee(landed),
              f"−{rupee(incentive_applied)} incentive" if incentive_applied else None)
    l2.metric(f"Total ({qty:g} MT)", rupee(landed * qty))

    with st.expander("🧾 Full break-up"):
        rows = [("PL + Bending (base)", b["base"])]
        rows += [(f"{ln['label']} ({'+' if ln['sign']>0 else '−'})", ln["effect"])
                 for ln in n["lines"]]
        rows.append(("Sub-total / MT", n["net"]))
        if apply_tli and tli:
            rows.append((f"Target-linked incentive (−) [{tier['label']}]", -tli))
        if apply_stock and stock_inr:
            rows.append(("Stocking incentive (−)", -stock_inr))
        rows.append(("NET LANDED TO DEALER / MT", landed))
        st.dataframe(
            pd.DataFrame(rows, columns=["Component", "Rs/MT"])
            .style.format({"Rs/MT": "{:,.0f}"}),
            hide_index=True, use_container_width=True,
        )
        st.caption("Incentive slabs: " + " · ".join(
            f"{t['label']} → ₹{t['inr_per_mt']:,.0f}" for t in inc["tiers"]))

    # --- Blended rate ---
    with st.expander("⚖️ Blended rate (diameter mix)"):
        st.caption("Enter the % share of each diameter in the order.")
        bc = st.columns(3)
        mix = {
            "8":     bc[0].number_input("8 mm %", value=0.0, min_value=0.0, step=5.0),
            "10":    bc[1].number_input("10 mm %", value=0.0, min_value=0.0, step=5.0),
            "12-32": bc[2].number_input("12-32 mm %", value=100.0, min_value=0.0, step=5.0),
        }
        br = calc.blended_rate(pl, price_row, product, segment, btype, mix, ecp=ecp)
        if br:
            st.metric("Blended base / MT", rupee(br["blended"]))
            st.caption(", ".join(f"{p['dia']}mm: {p['weight_pct']:.0f}%" for p in br["parts"]))


# --------------------------------------------------------------------------- #
#  PRICE HISTORY
# --------------------------------------------------------------------------- #
def page_history():
    if ROLE != "admin":
        st.error("Past price lists are visible to Admins only.")
        return
    st.caption("Past price lists (Admin only) — all dated changes per cluster.")
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
# Price lists & schemes are maintained in data/seed/source_prices.py (updates
# are provided to the maintainer, not edited in the app), so there is no in-app
# admin/editing screen — the DB is rebuilt from source on deploy.
# --------------------------------------------------------------------------- #
if page == "🧮 Calculator":
    page_calculator()
else:
    page_history()

st.caption("JSW One Distribution Ltd · Private Brands · prices exclude GST.")
