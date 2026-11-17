"""Load quarter-acre land prices and construction cost factors by 3-digit ZIP area.

Safe to re-run: every row is upserted on prefix.

    python -m app.load_land
"""
import csv
from decimal import Decimal
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from .db import SessionLocal
from .models import ZipLandValue

SOURCE = "FHFA residential land prices v4.0 (June 2024), 2022 values, quarter-acre lot"
CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "costs_by_zip3.csv"


def _blank(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _index_bps(raw: str | None) -> int | None:
    text = (raw or "").strip()
    if not text:
        return None
    return int(round(Decimal(text) * 10000))


def load_land(path: Path = CSV_PATH) -> int:
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        for rec in csv.DictReader(f):
            prefix = rec["prefix"].strip()
            if prefix.isdigit():
                prefix = prefix.zfill(3)
            rows.append(
                {
                    "prefix": prefix,
                    "state": rec["state"].strip(),
                    "land_cents": int(rec["land_quarter_acre_usd"]) * 100,
                    "basis": rec["land_basis"].strip(),
                    "source": SOURCE,
                    "construction_index_bps": _index_bps(rec["construction_factor"]),
                    "factor_basis": _blank(rec["factor_basis"]),
                    "area_type": _blank(rec["area_type"]),
                }
            )
    stmt = insert(ZipLandValue).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[ZipLandValue.prefix],
        set_={
            "state": stmt.excluded.state,
            "land_cents": stmt.excluded.land_cents,
            "basis": stmt.excluded.basis,
            "source": stmt.excluded.source,
            "construction_index_bps": stmt.excluded.construction_index_bps,
            "factor_basis": stmt.excluded.factor_basis,
            "area_type": stmt.excluded.area_type,
        },
    )
    with SessionLocal() as db:
        db.execute(stmt)
        db.commit()
    return len(rows)


if __name__ == "__main__":
    print(load_land())
