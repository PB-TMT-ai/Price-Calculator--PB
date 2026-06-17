"""
JSW One TMT — Price Calculator (mobile-friendly) for the zonal sales teams.

Run:  streamlit run app.py
"""
from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

from pricing import calc
from pricing import queries as q
from pricing.database import TEAMS

st.set_page_config(page_title="JSW One TMT Price Calculator",
                   page_icon="🧱", layout="centered")

# JSW One brand styling — colourful, card-based & mobile friendly.
JSW_BLUE = "#0A4DA2"
JSW_DARK = "#06306A"
JSW_SKY = "#EAF1FB"
JSW_GREY = "#F4F6FA"
JSW_LINE = "#D7E0EC"
st.markdown(
    f"""
    <style>
      .stApp {{ background: {JSW_GREY}; }}
      .block-container {{padding-top: 3.2rem; padding-bottom: 3rem; max-width: 780px;}}

      /* Header banner */
      .jsw-header {{
          background: linear-gradient(90deg, {JSW_DARK} 0%, {JSW_BLUE} 100%);
          color: #fff; padding: 14px 18px; border-radius: 14px;
          margin-bottom: 16px; display:flex; align-items:center; gap:12px;
          box-shadow: 0 4px 14px rgba(10,77,162,.25);
      }}
      .jsw-header .logo {{
          background:#fff; color:{JSW_BLUE}; font-weight:800; font-size:1.05rem;
          padding:6px 10px; border-radius:8px; letter-spacing:.3px;
      }}
      .jsw-header .title {{font-size:1.15rem; font-weight:700; line-height:1.35; padding-top:2px;}}
      .jsw-header .sub {{font-size:.78rem; opacity:.9;}}

      /* Expanders as cards with a blue accent strip */
      details[data-testid="stExpander"] {{
          background:#fff; border:1px solid {JSW_LINE}; border-left:5px solid {JSW_BLUE};
          border-radius:12px; margin-bottom:12px;
          box-shadow:0 1px 4px rgba(16,42,76,.06);
      }}
      details[data-testid="stExpander"] summary {{
          font-weight:700; color:{JSW_DARK}; padding:10px 12px;
      }}
      details[data-testid="stExpander"] summary:hover {{ color:{JSW_BLUE}; }}

      /* Inputs */
      div[data-testid="stSelectbox"] label, div[data-testid="stNumberInput"] label,
      div[data-testid="stRadio"] label, div[data-testid="stTextInput"] label {{
          font-weight:600; color:{JSW_DARK};
      }}
      .stNumberInput input {{font-size: 1rem;}}

      /* Result / metric cards */
      div[data-testid="stMetricValue"] {{font-size: 1.8rem; color: {JSW_BLUE}; font-weight:800;}}
      div[data-testid="stVerticalBlockBorderWrapper"] {{
          background: linear-gradient(180deg, {JSW_SKY} 0%, #fff 60%);
          border-radius:14px;
      }}

      /* Buttons */
      .stButton button[kind="primary"] {{background:{JSW_BLUE}; border:0; font-weight:700;}}
      .stButton button {{ border-radius:10px; }}
      .stDownloadButton button {{ border-radius:10px; border:1px solid {JSW_BLUE}; color:{JSW_BLUE}; font-weight:600; }}

      /* Sidebar */
      section[data-testid="stSidebar"] {{ background:#fff; border-right:1px solid {JSW_LINE}; }}
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

team = st.selectbox("Select Zone", TEAMS, index=None,
                    placeholder="Select Zone", key="team")
if team is None:
    st.info("👆 Select a Zone to begin.")
    st.stop()


def rupee(x) -> str:
    return "—" if x is None else f"₹{x:,.0f}"


GST_RATE = 0.18  # TMT steel GST


def reset_quote():
    """Clear the per-quote inputs (components, incentives, GST view)."""
    for k in list(st.session_state.keys()):
        if (k.startswith(("comp_", "tli_", "stk_", "mix_"))
                or k in ("ach", "gst_calc")):
            del st.session_state[k]


def _font(size: int, bold: bool = False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for path in (f"/usr/share/fonts/truetype/dejavu/{name}", name):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def quote_image(fields: dict) -> bytes:
    """Render a shareable JSW One quote card as PNG bytes."""
    W, pad, header_h, line_h = 760, 30, 90, 50
    rows = list(fields.items())
    H = header_h + pad + len(rows) * line_h + pad
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, header_h], fill=(10, 77, 162))
    d.text((pad, 20), "JSW One", font=_font(36, True), fill="white")
    d.text((pad, 60), "TMT Price Quote", font=_font(18), fill=(214, 226, 245))
    kf, vf, big = _font(21), _font(21, True), _font(30, True)
    y = header_h + pad
    for k, v in rows:
        v = str(v).replace("₹", "Rs ")
        big_row = (k == "Net Landed / MT")
        d.text((pad, y), k, font=kf, fill=(90, 100, 115))
        d.text((W - pad, y - (5 if big_row else 0)), v,
               font=(big if big_row else vf),
               fill=((10, 77, 162) if big_row else (26, 37, 51)), anchor="ra")
        y += line_h
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


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


def select_state_cluster(team: str, key: str) -> tuple[str | None, str | None]:
    """State + Cluster dropdowns. Returns (None, None) until a State is chosen."""
    states = q.get_states(team)
    c1, c2 = st.columns(2)
    state = c1.selectbox("Select State", states, index=None,
                         placeholder="Select State", key=f"{key}_state")
    if state is None:
        return None, None
    clusters = q.get_clusters(team, state)
    cl_names = {c["name"]: c["cluster_key"] for c in clusters}
    cluster_name = c2.selectbox("Cluster / City", list(cl_names.keys()),
                                key=f"{key}_cluster")
    return cl_names[cluster_name], cluster_name


# --------------------------------------------------------------------------- #
#  CALCULATOR
# --------------------------------------------------------------------------- #
def page_calculator():
    # ---------- Step 1 — Location & product ----------
    with st.expander("📍  Step 1 — Location & product", expanded=True):
        cluster_key, cluster_name = select_state_cluster(team, "calc")
        if cluster_key is None:
            st.info("Select a State to load prices.")
            return

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
        segment = "retail"   # Retail only

        # --- Ship From / Ship To (dropdowns) ---
        s1, s2 = st.columns(2)
        ship_from = s1.selectbox("Ship From", ["Plant", "Warehouse"],
                                 key="ship_from")
        if ship_from == "Plant":
            ship_to = s2.selectbox("Ship To",
                                   ["Warehouse", "Dealer Shop", "Dealer Site",
                                    "Distributor Site"], key="ship_to")
        else:
            ship_to = "Dealer"   # warehouse ships onward to dealer
            s2.caption("From Warehouse → secondary freight applies.")

    # Secondary freight (Freight to Dealer) applies only when shipping from a
    # warehouse. Stocking incentive applies only on Plant → Warehouse moves.
    secondary_freight = (ship_from == "Warehouse")
    stocking_ok = (ship_from == "Plant" and ship_to == "Warehouse")

    price_row = q.get_price(team, pl["id"], cluster_key)
    if price_row is None or price_row.get(calc.PRODUCTS[product]) is None:
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
            if field == "freight_to_dealer" and not secondary_freight:
                values[field] = 0.0   # secondary freight N/A when shipping from Plant
                continue
            sgn = " (+)" if sign > 0 else " (−)"
            values[field] = comp_control(label + sgn, toggle,
                                         defaults.get(field, 0) or 0, f"comp_{field}")
        if not secondary_freight:
            st.caption("ℹ️ Freight to Dealer (secondary) not applicable when "
                       "shipping from Plant.")
    ecp = values.get("jsw_one_ecp", 0) or 0
    btype = "Bend" if bend_val else "Straight"

    b = calc.base_price(pl, price_row, product, dia, segment, "Straight", ecp=ecp)
    n = calc.net_price(b["base"], values)
    sub_total = n["net"] + bend_val
    n_components = sum(1 for ln in n["lines"] if ln["value"]) + (1 if bend_val else 0)

    # ---------- Step 3 — Incentives (not applicable when shipping from Warehouse) ----------
    inc = q.get_incentive(team)
    tli, tier, stock_val = 0.0, None, 0.0
    with st.expander("🎯  Step 3 — Incentives (deducted)", expanded=False):
        if ship_from == "Warehouse":
            st.caption("ℹ️ Incentives are not applicable when shipping from Warehouse.")
        else:
            if st.radio("Target-linked incentive (−)", ["No", "Yes"], horizontal=True,
                        index=0, key="tli_t") == "Yes":
                ach = st.number_input("Enter target achievement %", min_value=0.0,
                                      value=100.0, step=1.0, format="%.0f", key="ach")
                tier = calc.incentive_for(ach, inc["tiers"])
                tli = float(tier["inr_per_mt"]) if tier else 0.0
                st.caption(f"Slab: {tier['label'] if tier else 'below lowest slab'} "
                           f"→ {rupee(tli)}/MT")
            if stocking_ok:
                if st.radio("Stocking incentive (−)", ["No", "Yes"], horizontal=True,
                            index=0, key="stk_t") == "Yes":
                    stock_val = st.number_input(
                        "Stocking incentive ₹/MT",
                        value=float(inc["meta"].get("stocking_incentive_inr") or 0),
                        step=50.0, format="%.0f", key="stk_v")
            else:
                st.caption("ℹ️ Stocking incentive applies only on Plant → Warehouse.")

    incentive_applied = tli + stock_val
    landed = sub_total - incentive_applied

    # ---------- Output options ----------
    show_gst = st.toggle("Show incl. 18% GST", key="gst_calc")
    mult = (1 + GST_RATE) if show_gst else 1.0
    gst_note = " (incl. GST)" if show_gst else ""

    ship_label = f"{ship_from} → {ship_to}" if ship_from == "Plant" else "Warehouse"

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
            f"Product        : {product}, {dia} mm, {btype}, Retail\n"
            f"Ship           : {ship_label}\n"
            f"Price list     : {pl['effective_date']} ({pl['reference']})\n"
            f"Net Landed/MT  : {rupee(landed * mult)}{gst_note}\n"
        )
        st.code(quote, language="text")
        st.download_button("⬇️ Download quote (.txt)", quote.encode(),
                           file_name=f"jsw_quote_{cluster_key.lower()}.txt",
                           mime="text/plain")

        # Shareable image of the quote (e.g. for WhatsApp), shown below.
        img = quote_image({
            "Cluster": cluster_name,
            "Product": f"{product}, {dia} mm, {btype}, Retail",
            "Ship": ship_label,
            "Price list": pl["effective_date"],
            "Net Landed / MT": f"{rupee(landed * mult)}{gst_note}",
        })
        st.image(img, caption="Quote image (download to share)")
        st.download_button("⬇️ Download quote image (.png)", img,
                           file_name=f"jsw_quote_{cluster_key.lower()}.png",
                           mime="image/png")

    # ---------- Result card (after the quote) ----------
    with st.container(border=True):
        st.markdown(f"#### 🧾 {cluster_name}")
        st.caption(f"{product} · {dia} mm · {btype} · Retail  |  Ship: {ship_label}  |  "
                   f"PL {pl['effective_date']}")
        st.metric(f"Net Landed / MT{gst_note}", rupee(landed * mult),
                  delta=(f"−{rupee(incentive_applied)} incentive"
                         if incentive_applied else None), delta_color="inverse")
        st.caption(
            f"Sub-total {rupee(sub_total * mult)}/MT "
            f"· {n_components} component(s) applied"
            + (f" · incentives −{rupee(incentive_applied)}" if incentive_applied else "")
        )

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
    if cluster_key is None:
        st.info("Select a State to view its price history.")
        return
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
