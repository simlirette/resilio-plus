"""
FCÉN bootstrap script.

Usage:
    python -m scripts.load_fcen \
        --food-csv path/to/FOOD_NAME.csv \
        --nutrient-amount-csv path/to/NUTRIENT_AMOUNT.csv \
        --nutrient-name-csv path/to/NUTRIENT_NAME.csv \
        [--db-url sqlite:///path/to/db.sqlite]

Re-running is safe (idempotent upsert). Expected: ~6000 items, ~5s.
"""
import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Load FCÉN data into food_cache table.")
    parser.add_argument("--food-csv", required=True, help="Path to FOOD NAME.csv")
    parser.add_argument("--nutrient-amount-csv", required=True, help="Path to NUTRIENT AMOUNT.csv")
    parser.add_argument("--nutrient-name-csv", required=True, help="Path to NUTRIENT NAME.csv")
    parser.add_argument("--db-url", default=None, help="SQLAlchemy DB URL (default: app engine)")
    args = parser.parse_args()

    if args.db_url:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(args.db_url)
        Session = sessionmaker(engine)
    else:
        from app.db.database import engine
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(engine)

    from app.integrations.nutrition.fcen_loader import load_fcen

    with Session() as db:
        count = load_fcen(
            food_name_csv=Path(args.food_csv),
            nutrient_amount_csv=Path(args.nutrient_amount_csv),
            nutrient_name_csv=Path(args.nutrient_name_csv),
            db=db,
        )
    print(f"Loaded {count} FCÉN items.")


if __name__ == "__main__":
    main()
