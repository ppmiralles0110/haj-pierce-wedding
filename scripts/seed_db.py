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
    "couple_name_1": "Pierce",                              # EDIT THIS
    "couple_name_2": "[Partner Name]",                      # EDIT THIS
    "wedding_date": "[Wedding Date]",                       # EDIT THIS  e.g. "December 12, 2026"
    "wedding_time": "[Wedding Time]",                       # EDIT THIS  e.g. "4:00 PM"

    # ---- Venue ----
    "venue_name": "[Venue Name]",                           # EDIT THIS
    "venue_address": "[Full Venue Address]",                # EDIT THIS
    "venue_google_maps_url": "#",                           # EDIT THIS  full Google Maps URL

    # ---- Style & Dress Code ----
    "dress_code": "[Dress Code]",                           # EDIT THIS  e.g. "Black Tie Optional"
    "theme_description": "[Theme Description]",             # EDIT THIS

    # ---- Theme Colours (CSS vars) ----
    "color_primary":   "#c9a96e",                           # Warm gold
    "color_secondary": "#e8c4b8",                           # Soft blush
    "color_accent":    "#ff6b35",                           # Bright orange

    # ---- Typography ----
    "font_heading":    "Cormorant Garamond",
    "font_subheading": "Montserrat",
    "font_body":       "Lato",

    # ---- RSVP Settings ----
    "rsvp_deadline": "[RSVP Deadline Date]",                # EDIT THIS  e.g. "November 1, 2026"
    "rsvp_open":     "true",                                # Set to "false" to close RSVP

    # ---- Content ----
    "hero_image_url":   "/static/images/placeholder.jpg",  # EDIT after uploading hero photo
    "custom_message":   "We can't wait to celebrate with you!",  # EDIT THIS
    "wedding_hashtag":  "#OurWedding2026",                  # EDIT THIS
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
