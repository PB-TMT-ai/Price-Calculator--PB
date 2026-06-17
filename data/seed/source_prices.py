"""
Canonical source of all Price List (PL) data, transcribed from the official
JSW One Distribution Ltd. TMT Annexure-1 PDFs.

This is the single editable source of truth for historical + current prices.
`build_db.py` reads this to (re)generate the per-team SQLite databases and the
CSV exports under data/seed/.

Price columns
-------------
fe550   : "Basic price + Frt: Gr. FE-550 12-32 mm" (Major city)  -> Product "JSW One 550"
fe550d  : "Fe 550D"  (by State/cluster)                           -> Product "JSW One 550 D"
A value of None means the PDF left that cell blank for that cluster.

All prices are Rs/MT, excluding GST, for 12-32 mm straight bars (the base).
Dia extras, bend extra and per-list notes live in PRICE_LISTS[*]["extras"].
"""

# Cluster master: key -> (display name, major_city, team/zone, state)
CLUSTERS = {
    # ---- North ----
    "SRINAGAR":        ("Kashmir (Srinagar)",            "Srinagar",   "North",  "Jammu & Kashmir"),
    "JAMMU":           ("Jammu",                          "Jammu",      "North",  "Jammu & Kashmir"),
    "CHANDIGARH":      ("Chandigarh",                     "Chandigarh", "North",  "Chandigarh"),
    "HIMACHAL_PRADESH":("Himachal Pradesh (Shimla)",      "Shimla",     "North",  "Himachal Pradesh"),
    "UTTARAKHAND":     ("Uttarakhand (Dehradun)",         "Dehradun",   "North",  "Uttarakhand"),
    "PUNJAB":          ("Punjab (Ludhiana)",              "Ludhiana",   "North",  "Punjab"),
    "DELHI":           ("Delhi (New Delhi)",              "New Delhi",  "North",  "Delhi"),
    "HARYANA":         ("Haryana (Faridabad)",            "Faridabad",  "North",  "Haryana"),
    "RAJASTHAN":       ("Rajasthan (Jaipur)",             "Jaipur",     "North",  "Rajasthan"),
    "UTTAR_PRADESH":   ("Uttar Pradesh (Ghaziabad/Kanpur)","Ghaziabad", "North", "Uttar Pradesh"),
    # ---- Central ----
    "CHHATTISGARH":    ("Chhattisgarh (Raipur)",          "Raipur",     "Central","Chhattisgarh"),
    "MADHYA_PRADESH":  ("Madhya Pradesh (Indore)",        "Indore",     "Central","Madhya Pradesh"),
    "GUJARAT":         ("Gujarat (Ahmedabad)",            "Ahmedabad",  "Central","Gujarat"),
    "MAHARASHTRA":     ("Maharashtra (Vidharbha)",        "Vidharbha",  "Central","Maharashtra"),
    # ---- East ----
    "ODISHA_CC":       ("Odisha Central+Coastal (Bhubaneshwar)","Bhubaneshwar","East","Odisha"),
    "ODISHA_WEST":     ("Odisha West",                    "Odisha West","East",   "Odisha"),
    "JHARKHAND":       ("Jharkhand (Ranchi)",             "Ranchi",     "East",   "Jharkhand"),
    "BIHAR":           ("Bihar (Patna)",                  "Patna",      "East",   "Bihar"),
    "SILIGURI_GRP":    ("Siliguri/Jalpaiguri/Cooch Behar","Siliguri",   "East",   "West Bengal"),
    "WEST_BENGAL":     ("West Bengal (Durgapur)",         "Durgapur",   "East",   "West Bengal"),
}

# Each price list: effective_date (ISO), reference, validity, notes,
# extras (dia/bend add-ons), and per-cluster {fe550, fe550d}.
PRICE_LISTS = [
    {
        "effective_date": "2026-05-01",
        "reference": "JODL/ TMT / May/ 2026-27/M1",
        "validity": "1st May'26 to 31st May'26",
        "note": "Bend extra Rs 600/MT.",
        "extras": {
            "bend_extra": 600,
            "dia": {  # mm: {"project": +x, "retail": +y}
                "8":  {"project": 2500, "retail": 3500},
                "10": {"project": 1000, "retail": 2250},
                "12-32": {"project": 0, "retail": 0},
            },
        },
        "prices": {
            "SRINAGAR":        {"fe550": 60400, "fe550d": 61900},
            "JAMMU":           {"fe550": 59900, "fe550d": 61400},
            "CHANDIGARH":      {"fe550": 58650, "fe550d": 59650},
            "HIMACHAL_PRADESH":{"fe550": 58900, "fe550d": 60400},
            "UTTARAKHAND":     {"fe550": 58400, "fe550d": 59900},
            "PUNJAB":          {"fe550": 58900, "fe550d": 59900},
            "DELHI":           {"fe550": 58400, "fe550d": 59400},
            "HARYANA":         {"fe550": 58400, "fe550d": 59400},
            "RAJASTHAN":       {"fe550": 58400, "fe550d": 59400},
            "UTTAR_PRADESH":   {"fe550": 58400, "fe550d": 59400},
            "CHHATTISGARH":    {"fe550": 57650, "fe550d": 58150},
            "MADHYA_PRADESH":  {"fe550": 56650, "fe550d": 58150},
            "GUJARAT":         {"fe550": 57650, "fe550d": 58650},
            "MAHARASHTRA":     {"fe550": 57150, "fe550d": None},
            "ODISHA_CC":       {"fe550": 57350, "fe550d": None},
            "ODISHA_WEST":     {"fe550": 56650, "fe550d": None},
            "JHARKHAND":       {"fe550": 57650, "fe550d": 58650},
            "BIHAR":           {"fe550": 57650, "fe550d": 58650},
            "SILIGURI_GRP":    {"fe550": 58150, "fe550d": 59150},
            "WEST_BENGAL":     {"fe550": 57650, "fe550d": 58650},
        },
    },
    {
        "effective_date": "2026-06-01",
        "reference": "JODL/ TMT / Jun/ 2026-27/M1",
        "validity": "1st Jun'26 to 30th Jun'26",
        "note": "Bend extra Rs 600/MT and Early commitment rebate of Rs 500 PMT on orders from 1st June'26 to 4th June'26.",
        "extras": {
            "bend_extra": 600,
            "dia": {
                "8":  {"project": 2500, "retail": 3500},
                "10": {"project": 1000, "retail": 2250},
                "12-32": {"project": 0, "retail": 0},
            },
        },
        "prices": {
            "SRINAGAR":        {"fe550": 57000, "fe550d": 58500},
            "JAMMU":           {"fe550": 56500, "fe550d": 58000},
            "CHANDIGARH":      {"fe550": 55250, "fe550d": 56250},
            "HIMACHAL_PRADESH":{"fe550": 55500, "fe550d": 57000},
            "UTTARAKHAND":     {"fe550": 55000, "fe550d": 56500},
            "PUNJAB":          {"fe550": 55500, "fe550d": 56500},
            "DELHI":           {"fe550": 55000, "fe550d": 56000},
            "HARYANA":         {"fe550": 55000, "fe550d": 56000},
            "RAJASTHAN":       {"fe550": 55000, "fe550d": 56000},
            "UTTAR_PRADESH":   {"fe550": 55000, "fe550d": 56000},
            "CHHATTISGARH":    {"fe550": 54250, "fe550d": 54750},
            "MADHYA_PRADESH":  {"fe550": 53250, "fe550d": 54750},
            "GUJARAT":         {"fe550": 54250, "fe550d": 55250},
            "MAHARASHTRA":     {"fe550": 53750, "fe550d": None},
            "ODISHA_CC":       {"fe550": 53950, "fe550d": None},
            "ODISHA_WEST":     {"fe550": 53250, "fe550d": None},
            "JHARKHAND":       {"fe550": 54250, "fe550d": 55250},
            "BIHAR":           {"fe550": 54250, "fe550d": 55250},
            "SILIGURI_GRP":    {"fe550": 54750, "fe550d": 55750},
            "WEST_BENGAL":     {"fe550": 54250, "fe550d": 55250},
        },
    },
    {
        "effective_date": "2026-06-09",
        "reference": "JODL/ TMT / Jun/ 2026-27/M3",
        "validity": "1st Jun'26 to 30th Jun'26",
        "note": "Bend extra Rs 600/MT and Early commitment rebate of Rs 500 PMT on orders from 1st June'26 to 10th June'26.",
        "extras": {
            "bend_extra": 600,
            "dia": {
                "8":  {"project": 2500, "retail": 3500},
                "10": {"project": 1000, "retail": 2250},
                "12-32": {"project": 0, "retail": 0},
            },
        },
        "prices": {
            "SRINAGAR":        {"fe550": 56000, "fe550d": 57500},
            "JAMMU":           {"fe550": 55500, "fe550d": 57000},
            "CHANDIGARH":      {"fe550": 54250, "fe550d": 55250},
            "HIMACHAL_PRADESH":{"fe550": 54500, "fe550d": 56000},
            "UTTARAKHAND":     {"fe550": 54000, "fe550d": 55500},
            "PUNJAB":          {"fe550": 54500, "fe550d": 55500},
            "DELHI":           {"fe550": 54000, "fe550d": 55000},
            "HARYANA":         {"fe550": 54000, "fe550d": 55000},
            "RAJASTHAN":       {"fe550": 54000, "fe550d": 55000},
            "UTTAR_PRADESH":   {"fe550": 54000, "fe550d": 55000},
            "CHHATTISGARH":    {"fe550": 53250, "fe550d": 53750},
            "MADHYA_PRADESH":  {"fe550": 52250, "fe550d": 53750},
            "GUJARAT":         {"fe550": 53250, "fe550d": 54250},
            "MAHARASHTRA":     {"fe550": 52750, "fe550d": None},
            "ODISHA_CC":       {"fe550": 52950, "fe550d": None},
            "ODISHA_WEST":     {"fe550": 52250, "fe550d": None},
            "JHARKHAND":       {"fe550": 53250, "fe550d": 54250},
            "BIHAR":           {"fe550": 53250, "fe550d": 54250},
            "SILIGURI_GRP":    {"fe550": 53750, "fe550d": 54750},
            "WEST_BENGAL":     {"fe550": 53250, "fe550d": 54250},
        },
    },
    {
        "effective_date": "2026-06-15",
        "reference": "JODL/ TMT / Jun/ 2026-27/M4",
        "validity": "1st Jun'26 to 30th Jun'26",
        "note": "Bend extra Rs 600/MT and Stocking support of Rs 500 PMT from 15th Jun'26.",
        "extras": {
            "bend_extra": 600,
            "dia": {
                "8":  {"project": 2500, "retail": 3500},
                "10": {"project": 1000, "retail": 2250},
                "12-32": {"project": 0, "retail": 0},
            },
        },
        "prices": {
            "SRINAGAR":        {"fe550": 55250, "fe550d": 56750},
            "JAMMU":           {"fe550": 54750, "fe550d": 56250},
            "CHANDIGARH":      {"fe550": 53500, "fe550d": 54500},
            "HIMACHAL_PRADESH":{"fe550": 53750, "fe550d": 55250},
            "UTTARAKHAND":     {"fe550": 53250, "fe550d": 54750},
            "PUNJAB":          {"fe550": 53750, "fe550d": 54750},
            "DELHI":           {"fe550": 53250, "fe550d": 54250},
            "HARYANA":         {"fe550": 53250, "fe550d": 54250},
            "RAJASTHAN":       {"fe550": 53250, "fe550d": 54250},
            "UTTAR_PRADESH":   {"fe550": 53250, "fe550d": 54250},
            "CHHATTISGARH":    {"fe550": 52500, "fe550d": 53000},
            "MADHYA_PRADESH":  {"fe550": 51500, "fe550d": 53000},
            "GUJARAT":         {"fe550": 52500, "fe550d": 53500},
            "MAHARASHTRA":     {"fe550": 52000, "fe550d": None},
            "ODISHA_CC":       {"fe550": 52200, "fe550d": None},
            "ODISHA_WEST":     {"fe550": 51500, "fe550d": None},
            "JHARKHAND":       {"fe550": 52500, "fe550d": 53500},
            "BIHAR":           {"fe550": 52500, "fe550d": 53500},
            "SILIGURI_GRP":    {"fe550": 53000, "fe550d": 54000},
            "WEST_BENGAL":     {"fe550": 52500, "fe550d": 53500},
        },
    },
]

# Target-linked incentive scheme (June'26 scheme sheet). achievement -> INR/MT.
INCENTIVE_SCHEME = {
    "month": "2026-06",
    "tiers": [          # (label, min_pct, inr_per_mt)
        (">= 70%",  70, 300),
        (">= 90%",  90, 450),
        (">= 100%", 100, 600),
        (">= 110%", 110, 800),
    ],
    "stocking_incentive": {
        "inr_per_mt": 500,
        "note": "Stocking incentive (warehouse sales), from June 15th onwards.",
    },
}

# Default per-cluster component values (Rs/MT). Editable by admins; the
# salesperson can also override any of these live for a single quote.
# sign convention used by the calculator: see pricing/calc.py COMPONENTS.
# Seeded at 0 because the source PDFs do not carry these figures yet.
# Must match the field keys in pricing/calc.py COMPONENTS (drives the DB columns).
COMPONENT_FIELDS = [
    "distributor_margin",
    "admin_manpower",
    "handling",
    "cash_discount",
    "quantity_discount",
    "dealer_annual_schemes",
    "contractor_loyalty",
    "jsw_one_ecp",
    "shortage",
    "freight_to_dealer",
    "additional_price_support",
    "operational_scheme",
]
