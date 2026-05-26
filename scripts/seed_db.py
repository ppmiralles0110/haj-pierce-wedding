#!/usr/bin/env python3
# =============================================================================
# scripts/seed_db.py — Seed the wedding_config table with default values
# =============================================================================
"""
Seed script for the wedding_config table.

Run this once after the initial deployment and database migration:
  $ python scripts/seed_db.py

All values marked "# EDIT THIS" should be updated via the admin panel
at /admin/config after deployment, or by editing this file before seeding.
"""

import sys
import os

# Ensure the app package is on the path when running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.wedding_config import WeddingConfig


# ---------------------------------------------------------------------------
# Default configuration
# All "# EDIT THIS" values must be customised before the website goes live.
# ---------------------------------------------------------------------------
DEFAULT_CONFIG: dict[str, str] = {
    # ---- Couple Details ----
    "couple_name_1": "Pierce",
    "couple_name_2": "Haj",
    "wedding_date":  "",                                    # EDIT THIS  e.g. "2026-12-12"
    "wedding_time":  "",                                    # EDIT THIS  e.g. "16:00"

    # ---- Venue ----
    "venue_name":            "",                            # EDIT THIS
    "venue_address":         "",                            # EDIT THIS
    "venue_google_maps_url": "#",                           # EDIT THIS

    # ---- Style & Dress Code ----
    "dress_code":        "Black Tie",                       # EDIT THIS
    "theme_description": "Burgundy, White & Black",

    # ---- Theme Colours (CSS vars) ----
    "color_primary":   "#800020",                           # Burgundy
    "color_secondary": "#c4536e",                           # Rose
    "color_accent":    "#5a0014",                           # Deep Burgundy

    # ---- Typography ----
    "font_heading":    "Cormorant Garamond",
    "font_subheading": "Montserrat",
    "font_body":       "Lato",

    # ---- RSVP Settings ----
    "rsvp_deadline": "",                                    # EDIT THIS  e.g. "2026-11-01"
    "rsvp_open":     "true",

    # ---- Content ----
    "hero_image_url":  "/static/images/placeholder.jpg",   # EDIT after uploading hero photo
    "custom_message":  "We can't wait to celebrate with you!",
    "wedding_hashtag": "#PierceAndHaj",
}


def seed(force: bool = False) -> None:
    """
    Populate the wedding_config table with default values.

    Args:
        force: If True, overwrite ALL existing rows.
               If False (default), only INSERT rows with missing keys.
    """
    app = create_app()
    with app.app_context():
        seeded_count = 0
        skipped_count = 0

        for key, value in DEFAULT_CONFIG.items():
            existing = WeddingConfig.query.filter_by(key=key).first()
            if existing and not force:
                print(f"  SKIP  {key!r:40s} (already set to {existing.value!r:.40})")
                skipped_count += 1
            else:
                if existing:
                    existing.value = value
                else:
                    db.session.add(WeddingConfig(key=key, value=value))
                print(f"  SEED  {key!r:40s} = {value!r:.40}")
                seeded_count += 1

        db.session.commit()
        print(
            f"\n✅  Seed complete — {seeded_count} values written, "
            f"{skipped_count} skipped."
        )
        print(
            "\n📝  Remember to edit all '# EDIT THIS' values via the admin panel "
            "at /admin/config\n"
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed wedding_config defaults.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite all existing config values with defaults.",
    )
    args = parser.parse_args()
    seed(force=args.force)
