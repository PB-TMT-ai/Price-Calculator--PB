#!/usr/bin/env python3
"""Rebuild the North/Central/East databases from data/seed/.

Usage:  python build_db.py
"""
from pricing.database import build_all, export_components_csv, TEAMS, db_path

if __name__ == "__main__":
    build_all()
    for t in TEAMS:
        export_components_csv(t)
    print("Built:", ", ".join(str(db_path(t)) for t in TEAMS))
