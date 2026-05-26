#!/usr/bin/env python3
# =============================================================================
# scripts/export_rsvp.py — Export all RSVPs to a CSV file
# =============================================================================
"""
Standalone RSVP export script.

Usage:
  $ python scripts/export_rsvp.py                     # writes rsvp_export.csv
  $ python scripts/export_rsvp.py --output guests.csv
  $ python scripts/export_rsvp.py --status attending
"""

import csv
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def export_rsvp(output_path: str = "rsvp_export.csv", status: Optional[str] = None) -> None:
    """
    Export guest RSVP data to a CSV file.

    Args:
        output_path: Path to write the CSV file.
        status: Optional filter — one of 'attending', 'not_attending', 'pending'.
    """
    from app import create_app
    from app.models.guest import Guest

    app = create_app()
    with app.app_context():
        query = Guest.query.order_by(Guest.name.asc())
        if status:
            query = query.filter_by(rsvp_status=status)

        guests = query.all()

        fieldnames = [
            "name", "email", "rsvp_status", "meal_preference",
            "plus_one", "plus_one_name", "table_number",
            "special_requests", "rsvp_submitted_at", "created_at",
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for g in guests:
                writer.writerow({
                    "name": g.name or "",
                    "email": g.email,
                    "rsvp_status": g.rsvp_status,
                    "meal_preference": g.meal_preference or "",
                    "plus_one": "Yes" if g.plus_one else "No",
                    "plus_one_name": g.plus_one_name or "",
                    "table_number": g.table_number or "",
                    "special_requests": g.special_requests or "",
                    "rsvp_submitted_at": (
                        g.rsvp_submitted_at.isoformat() if g.rsvp_submitted_at else ""
                    ),
                    "created_at": g.created_at.isoformat(),
                })

        print(f"✅  Exported {len(guests)} guest(s) to {output_path!r}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Export RSVP data to CSV.")
    parser.add_argument("--output", default="rsvp_export.csv", help="Output CSV path.")
    parser.add_argument(
        "--status",
        choices=["attending", "not_attending", "pending"],
        help="Filter by RSVP status.",
    )
    args = parser.parse_args()
    export_rsvp(output_path=args.output, status=args.status)
