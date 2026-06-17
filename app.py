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


GST_RATE = 0.18  # TMT steel GST


def reset_quote():
    """Clear the per-quote inputs (components, incentives, qty, GST, mix)."""
    for k in list(st.session_state.keys()):
        if (k.startswith(("comp_", "tli_", "stk_", "mix_"))
                or k in ("ach", "qty_calc", "gst_calc")):
            del st.session_state[k]


def comp_control(label: str, kind: str, default, key: str, step: float = 50.0):
    """Render a component control and return its ₹/MT value.

    kind = "always"      -> value box, always shown
           "yesno"       -> Yes/No gate; value box only when Yes
           "applicable"  -> Applicable/Not Applicable gate; value box only when on
    """
    if kind == "always":
        return st.number_input(f"{label} (₹/MT)", value=float(default or 0),
                               step=step, format="%.0f", key=f"{key}_v")
    on_lab, off_lab = (("Applicable", "Not Applicable") if kind == "applicable"
                       else ("Yes", "No"))
    c1, c2 = st.columns([1.1, 1])
    choice = c1.radio(label, [off_lab, on_lab], horizontal=True, index=0,
                      key=f"{key}_t")
    if choice == on_lab:
        return c2.number_input("₹/MT", value=float(default or 0), step=step,
                               format="%.0f", key=f"{key}_v")
    return 0.0


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
    # Live result card pinned at the top (filled in after we compute below).
    result = st.container(border=True)

    # ---------- Step 1 — Location & product ----------
    with st.expander("📍  Step 1 — Location & product", expanded=True):
        cluster_key, cluster_name = select_state_cluster(team, "calc")

        pls = q.get_price_lists(team)
        if not pls:
            st.error("No price list available for this zone.")
            return
        if ROLE == "admin":
            pl_labels = {f"{p['effective_date']}  ({p['reference']})": p for p in pls}
            pl = pl_labels[st.selectbox("Price list (effective date)",
                                        list(pl_labels.keys()))]
        else:
            pl = pls[0]
            st.caption(f"📅 Current price list: **{pl['effective_date']}** · {pl['reference']}")
        if pl.get("note"):
            st.caption(f"📌 {pl['note']}")

        c1, c2 = st.columns(2)
        product = c1.selectbox("Product", list(calc.PRODUCTS.keys()), key="p_product")
        dia = c2.selectbox("Diameter (mm)", calc.DIAS, index=2, key="p_dia")
        segment = st.radio("Segment", [s.capitalize() for s in calc.SEGMENTS],
                           horizontal=True, key="p_segment").lower()

    price_row = q.get_price(team, pl["id"], cluster_key)
    if price_row is None or price_row.get(calc.PRODUCTS[product]) is None:
        with result:
            st.error(f"No **{product}** price published for {cluster_name} "
                     f"in this price list. Try the other product.")
        return

    # ---------- Step 2 — Components (toggle-gated) ----------
    defaults = q.get_components(team, cluster_key)
    values = {}
    with st.expander("➕  Step 2 — Price components", expanded=False):
        st.caption("Switch on what applies, then enter the ₹/MT value.")
        bend_val = comp_control("Bending (+)", "yesno", pl["bend_extra"], "comp_bending")
        for field, label, sign, toggle in calc.COMPONENTS:
            sgn = " (+)" if sign > 0 else " (−)"
            values[field] = comp_control(label + sgn, toggle,
                                         defaults.get(field, 0) or 0, f"comp_{field}")
    ecp = values.get("jsw_one_ecp", 0) or 0
    btype = "Bend" if bend_val else "Straight"

    b = calc.base_price(pl, price_row, product, dia, segment, "Straight", ecp=ecp)
    n = calc.net_price(b["base"], values)
    sub_total = n["net"] + bend_val
    n_components = sum(1 for ln in n["lines"] if ln["value"]) + (1 if bend_val else 0)

    # ---------- Step 3 — Incentives ----------
    inc = q.get_incentive(team)
    tli, tier, stock_val = 0.0, None, 0.0
    with st.expander("🎯  Step 3 — Incentives (deducted)", expanded=False):
        if st.radio("Target-linked incentive (−)", ["No", "Yes"], horizontal=True,
                    index=0, key="tli_t") == "Yes":
            ach = st.slider("Target achievement %", 0, 130, 100, step=5, key="ach")
            tier = calc.incentive_for(ach, inc["tiers"])
            tli = float(tier["inr_per_mt"]) if tier else 0.0
            st.caption(f"Slab: {tier['label'] if tier else 'below lowest slab'} "
                       f"→ {rupee(tli)}/MT")
        if st.radio("Stocking incentive (−)", ["No", "Yes"], horizontal=True,
                    index=0, key="stk_t") == "Yes":
            stock_val = st.number_input(
                "Stocking incentive ₹/MT",
                value=float(inc["meta"].get("stocking_incentive_inr") or 0),
                step=50.0, format="%.0f", key="stk_v")

    incentive_applied = tli + stock_val
    landed = sub_total - incentive_applied

    # ---------- Order options ----------
    o1, o2 = st.columns([1.2, 1])
    qty = o1.number_input("Quantity (MT)", value=1.0, min_value=0.0, step=1.0,
                          key="qty_calc")
    show_gst = o2.toggle("Show incl. 18% GST", key="gst_calc")
    mult = (1 + GST_RATE) if show_gst else 1.0
    gst_note = " (incl. GST)" if show_gst else ""

    # ---------- Live result card (rendered at the very top) ----------
    with result:
        st.markdown(f"#### 🧾 {cluster_name}")
        st.caption(f"{product} · {dia} mm · {btype} · {segment.capitalize()}  |  "
                   f"PL {pl['effective_date']}")
        m1, m2 = st.columns(2)
        m1.metric(f"Net Landed / MT{gst_note}", rupee(landed * mult),
                  delta=(f"−{rupee(incentive_applied)} incentive"
                         if incentive_applied else None), delta_color="inverse")
        m2.metric(f"Order total · {qty:g} MT", rupee(landed * qty * mult))
        st.caption(
            f"Sub-total {rupee(sub_total * mult)}/MT "
            f"· {n_components} component(s) applied"
            + (f" · incentives −{rupee(incentive_applied)}" if incentive_applied else "")
        )

    # ---------- Details ----------
    with st.expander("🧮 Base price build-up"):
        dia_label = f"Dia extra ({dia} mm, {segment})"
        if b["dia_waived"]:
            dia_label += " — waived (ECP applied)"
        st.dataframe(
            pd.DataFrame(
                [("List price (12-32 mm)", b["list_price"]),
                 (dia_label, b["dia_extra"]),
                 ("PL base (12-32 mm + dia)", b["base"])],
                columns=["Item", "Rs/MT"],
            ).style.format({"Rs/MT": "{:,.0f}"}),
            hide_index=True, use_container_width=True)

    with st.expander("📋 Full break-up"):
        rows = [("PL base (list + dia)", b["base"])]
        if bend_val:
            rows.append(("Bending (+)", bend_val))
        rows += [(f"{ln['label']} ({'+' if ln['sign'] > 0 else '−'})", ln["effect"])
                 for ln in n["lines"] if ln["value"]]
        rows.append(("Sub-total / MT", sub_total))
        if tli:
            rows.append((f"Target-linked incentive (−) [{tier['label']}]", -tli))
        if stock_val:
            rows.append(("Stocking incentive (−)", -stock_val))
        rows.append(("NET LANDED TO DEALER / MT", landed))
        if show_gst:
            rows.append(("NET LANDED incl. 18% GST / MT", landed * mult))
        st.dataframe(
            pd.DataFrame(rows, columns=["Component", "Rs/MT"])
            .style.format({"Rs/MT": "{:,.0f}"}),
            hide_index=True, use_container_width=True)

    with st.expander("📤 Share this quote"):
        quote = (
            "JSW One TMT — Price Quote\n"
            f"Zone / Cluster : {team} / {cluster_name}\n"
            f"Product        : {product}, {dia} mm, {btype}, {segment.capitalize()}\n"
            f"Price list     : {pl['effective_date']} ({pl['reference']})\n"
            f"Net Landed/MT  : {rupee(landed * mult)}{gst_note}\n"
            f"Quantity       : {qty:g} MT\n"
            f"Order total    : {rupee(landed * qty * mult)}{gst_note}\n"
        )
        st.code(quote, language="text")
        st.download_button("⬇️ Download quote (.txt)", quote.encode(),
                           file_name=f"jsw_quote_{cluster_key.lower()}.txt",
                           mime="text/plain")

    with st.expander("⚖️ Blended rate (diameter mix)"):
        st.caption("Enter the % share of each diameter in the order.")
        bc = st.columns(3)
        mix = {
            "8":     bc[0].number_input("8 mm %", 0.0, step=5.0, key="mix_8"),
            "10":    bc[1].number_input("10 mm %", 0.0, step=5.0, key="mix_10"),
            "12-32": bc[2].number_input("12-32 mm %", value=100.0, step=5.0, key="mix_12"),
        }
        br = calc.blended_rate(pl, price_row, product, segment, btype, mix, ecp=ecp)
        if br:
            st.metric("Blended base / MT", rupee(br["blended"]))
            st.caption(", ".join(f"{p['dia']}mm: {p['weight_pct']:.0f}%"
                                 for p in br["parts"]))

    st.button("↺ Reset components & incentives", on_click=reset_quote,
              use_container_width=True)


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
