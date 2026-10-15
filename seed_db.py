"""Build inventory.db: a small auto-parts inventory with sample data.

Usage:
    python seed_db.py            # creates/overwrites inventory.db next to this file
    python seed_db.py my.db      # custom path
"""
import random
import sqlite3
import sys
from pathlib import Path

DEFAULT_PATH = Path(__file__).with_name("inventory.db")

SCHEMA = """
CREATE TABLE suppliers (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL,
    city  TEXT NOT NULL
);

CREATE TABLE vehicles (
    id        INTEGER PRIMARY KEY,
    make      TEXT NOT NULL,
    model     TEXT NOT NULL,
    year_from INTEGER NOT NULL,
    year_to   INTEGER NOT NULL
);

CREATE TABLE parts (
    id          INTEGER PRIMARY KEY,
    sku         TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    oem_number  TEXT NOT NULL,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    price_inr   INTEGER NOT NULL,
    condition   TEXT NOT NULL CHECK (condition IN ('New', 'Refurbished'))
);

CREATE TABLE fitment (
    part_id    INTEGER NOT NULL REFERENCES parts(id),
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(id),
    PRIMARY KEY (part_id, vehicle_id)
);

CREATE TABLE stock (
    part_id      INTEGER PRIMARY KEY REFERENCES parts(id),
    quantity     INTEGER NOT NULL,
    bin_location TEXT NOT NULL
);
"""

SUPPLIERS = [
    ("Bosch India", "Bengaluru"),
    ("Minda Industries", "Gurugram"),
    ("Denso India", "Noida"),
    ("Exide Auto", "Kolkata"),
    ("Gabriel India", "Pune"),
    ("Valeo India", "Chennai"),
]

# make, model, year_from, year_to
VEHICLES = [
    ("Maruti Suzuki", "Swift", 2012, 2023),
    ("Maruti Suzuki", "Baleno", 2015, 2024),
    ("Hyundai", "i20", 2014, 2024),
    ("Hyundai", "Creta", 2015, 2024),
    ("Honda", "City", 2010, 2022),
    ("Tata", "Nexon", 2017, 2024),
    ("Mahindra", "XUV700", 2021, 2024),
    ("Toyota", "Innova", 2009, 2022),
]

# name, category, min price (INR), max price (INR)
PART_TYPES = [
    ("Brake Pad Set", "Brakes", 1200, 3800),
    ("Brake Disc", "Brakes", 1800, 5200),
    ("Oil Filter", "Filters", 150, 600),
    ("Air Filter", "Filters", 250, 900),
    ("Cabin Filter", "Filters", 300, 1100),
    ("Spark Plug", "Ignition", 180, 750),
    ("Battery 12V", "Electrical", 4200, 9500),
    ("Headlight Assembly", "Lighting", 2500, 9000),
    ("Shock Absorber", "Suspension", 1600, 5400),
    ("Clutch Plate", "Transmission", 2200, 6800),
    ("Radiator", "Cooling", 3500, 9800),
    ("Alternator", "Electrical", 5500, 14000),
]

VARIANTS_PER_PART_TYPE = 3


def build(path: Path) -> None:
    rng = random.Random(42)  # fixed seed: same data every run
    if path.exists():
        path.unlink()

    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO suppliers (name, city) VALUES (?, ?)", SUPPLIERS)
    conn.executemany(
        "INSERT INTO vehicles (make, model, year_from, year_to) VALUES (?, ?, ?, ?)",
        VEHICLES,
    )

    part_id = 0
    for name, category, low, high in PART_TYPES:
        for _ in range(VARIANTS_PER_PART_TYPE):
            part_id += 1
            supplier_id = rng.randint(1, len(SUPPLIERS))
            condition = rng.choices(["New", "Refurbished"], weights=[3, 1])[0]
            price = round(rng.randint(low, high), -1)
            if condition == "Refurbished":
                price = int(round(price * 0.6, -1))

            conn.execute(
                "INSERT INTO parts (id, sku, name, category, oem_number, supplier_id, price_inr, condition) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    part_id,
                    f"SKU-{part_id:04d}",
                    name,
                    category,
                    f"OEM-{rng.randint(100000, 999999)}",
                    supplier_id,
                    price,
                    condition,
                ),
            )

            fits = rng.sample(range(1, len(VEHICLES) + 1), rng.randint(1, 3))
            conn.executemany(
                "INSERT INTO fitment (part_id, vehicle_id) VALUES (?, ?)",
                [(part_id, vehicle_id) for vehicle_id in fits],
            )

            conn.execute(
                "INSERT INTO stock (part_id, quantity, bin_location) VALUES (?, ?, ?)",
                (
                    part_id,
                    rng.choice([0, 0, 3, 5, 8, 12, 20, 35, 60]),
                    f"{rng.choice('ABCDEF')}-{rng.randint(1, 20):02d}",
                ),
            )

    conn.commit()
    for table in ("suppliers", "vehicles", "parts", "fitment", "stock"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table:10} {count:4} rows")
    conn.close()
    print(f"\nCreated {path}")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH)
