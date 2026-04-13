#!/usr/bin/env python3
"""Generate the synthetic food-delivery demo dataset.

Emits four CSVs under `data/` that mirror the shape of the legacy Toyota
dataset (dimension tables + one fact table aggregated at month grain):

    data/DIM_CITY.csv        city_id, city_name, country, region
    data/DIM_DISH.csv        dish_id, dish_name, cuisine, category,
                             base_price_eur, calories, allergens
    data/DIM_RESTAURANT.csv  restaurant_id, restaurant_name, city_id,
                             cuisine_type, avg_rating
    data/FACT_ORDERS.csv     dish_id, restaurant_id, city_id, year, month,
                             orders_count, revenue_eur, avg_rating,
                             avg_delivery_minutes

The generator is **deterministic** — fixed random seed — so a clean clone
always produces identical data. Run it from the repo root:

    uv run python scripts/generate_demo_orders.py

The resulting CSVs are consumed by `scripts/structured_data_ingestion_pipeline.py`
which loads them into SQLite for the agent's SQL tools to query.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import random
from typing import List

# ── Determinism ──────────────────────────────────────────────────────────
# A fixed seed makes every run produce byte-identical CSVs. Changing this
# is the only way to get a different synthetic dataset; reviewers can diff
# two runs without noise.
SEED = 20260413


@dataclass(frozen=True)
class City:
    city_id: int
    city_name: str
    country: str
    region: str


@dataclass(frozen=True)
class Dish:
    dish_id: int
    dish_name: str
    cuisine: str
    category: str  # starter | main | dessert | drink
    base_price_eur: float
    calories: int
    allergens: str  # comma-separated


@dataclass(frozen=True)
class Restaurant:
    restaurant_id: int
    restaurant_name: str
    city_id: int
    cuisine_type: str
    avg_rating: float


# ── Master data (all hand-picked so eval questions have predictable answers) ──

CITIES: List[City] = [
    City(1, "Berlin", "Germany", "Western Europe"),
    City(2, "Munich", "Germany", "Western Europe"),
    City(3, "Milan", "Italy", "Southern Europe"),
    City(4, "Rome", "Italy", "Southern Europe"),
    City(5, "Paris", "France", "Western Europe"),
    City(6, "Amsterdam", "Netherlands", "Western Europe"),
    City(7, "Brussels", "Belgium", "Western Europe"),
    City(8, "Madrid", "Spain", "Southern Europe"),
    City(9, "Lisbon", "Portugal", "Southern Europe"),
    City(10, "Vienna", "Austria", "Central Europe"),
]

# Allergens are plain comma-joined strings so the menu PDF and the SQL
# results stay aligned (a reviewer can grep for "Margherita" in both and
# see the same allergen list).
DISHES: List[Dish] = [
    # Italian
    Dish(1, "Margherita Pizza", "Italian", "main", 9.50, 680, "gluten, dairy"),
    Dish(2, "Pepperoni Pizza", "Italian", "main", 11.00, 820, "gluten, dairy"),
    Dish(3, "Spaghetti Carbonara", "Italian", "main", 11.50, 820, "gluten, dairy, eggs"),
    Dish(4, "Lasagna Bolognese", "Italian", "main", 12.00, 910, "gluten, dairy, eggs"),
    Dish(5, "Tiramisu", "Italian", "dessert", 5.50, 420, "gluten, dairy, eggs"),
    # Japanese
    Dish(6, "Salmon Nigiri (6 pcs)", "Japanese", "main", 14.00, 560, "fish, soy"),
    Dish(7, "Tuna Sashimi (8 pcs)", "Japanese", "main", 16.50, 320, "fish, soy"),
    Dish(8, "Ramen Shoyu", "Japanese", "main", 12.50, 720, "gluten, soy, eggs, sesame"),
    Dish(9, "Chicken Katsu Curry", "Japanese", "main", 13.00, 880, "gluten, eggs, soy"),
    Dish(10, "Miso Soup", "Japanese", "starter", 3.50, 90, "soy"),
    # Indian
    Dish(11, "Chicken Tikka Masala", "Indian", "main", 12.00, 780, "dairy, nuts"),
    Dish(12, "Paneer Butter Masala", "Indian", "main", 11.50, 720, "dairy, nuts"),
    Dish(13, "Lamb Biryani", "Indian", "main", 13.50, 850, "dairy, nuts"),
    Dish(14, "Vegetable Samosas (4 pcs)", "Indian", "starter", 5.00, 380, "gluten"),
    Dish(15, "Mango Lassi", "Indian", "drink", 4.00, 240, "dairy"),
    # Mexican
    Dish(16, "Beef Burrito", "Mexican", "main", 10.50, 780, "gluten, dairy"),
    Dish(17, "Chicken Quesadilla", "Mexican", "main", 9.50, 680, "gluten, dairy"),
    Dish(18, "Guacamole & Nachos", "Mexican", "starter", 6.00, 520, "dairy"),
    Dish(19, "Veggie Tacos (3 pcs)", "Mexican", "main", 9.00, 540, "gluten"),
    # American
    Dish(20, "Classic Cheeseburger", "American", "main", 11.00, 900, "gluten, dairy, sesame"),
    Dish(21, "BBQ Chicken Wings (8 pcs)", "American", "starter", 8.50, 620, "gluten"),
    Dish(22, "Caesar Salad", "American", "starter", 7.50, 420, "dairy, eggs, gluten, fish"),
    Dish(23, "New York Cheesecake", "American", "dessert", 5.50, 460, "gluten, dairy, eggs"),
    # Vegan / other
    Dish(24, "Falafel Wrap", "Middle Eastern", "main", 8.50, 560, "gluten, sesame"),
    Dish(25, "Hummus Plate", "Middle Eastern", "starter", 6.50, 380, "sesame"),
    Dish(26, "Pad Thai", "Thai", "main", 11.00, 720, "peanuts, eggs, fish, soy"),
    Dish(27, "Green Thai Curry", "Thai", "main", 11.50, 680, "fish, peanuts"),
    Dish(28, "Greek Salad", "Greek", "starter", 7.00, 340, "dairy"),
    Dish(29, "Moussaka", "Greek", "main", 11.50, 820, "gluten, dairy, eggs"),
    Dish(30, "Espresso", "Italian", "drink", 2.50, 5, ""),
]

# 20 restaurants across the 10 cities (2 per city on average).
# cuisine_type aligns with one of the cuisine labels on DISHES so each
# restaurant can plausibly carry dishes of that cuisine.
RESTAURANTS: List[Restaurant] = [
    Restaurant(1, "Trattoria Marco", 3, "Italian", 4.6),
    Restaurant(2, "La Piazza", 4, "Italian", 4.4),
    Restaurant(3, "Pasta Fresca", 1, "Italian", 4.5),
    Restaurant(4, "Sushi Zen", 6, "Japanese", 4.7),
    Restaurant(5, "Tokyo Kitchen", 5, "Japanese", 4.3),
    Restaurant(6, "Ramen Ichiban", 1, "Japanese", 4.5),
    Restaurant(7, "Bombay House", 2, "Indian", 4.4),
    Restaurant(8, "Taj Palace", 8, "Indian", 4.6),
    Restaurant(9, "Spice Garden", 6, "Indian", 4.2),
    Restaurant(10, "El Sombrero", 5, "Mexican", 4.3),
    Restaurant(11, "Casa Mexicana", 8, "Mexican", 4.5),
    Restaurant(12, "Burger Avenue", 1, "American", 4.2),
    Restaurant(13, "Liberty Grill", 10, "American", 4.4),
    Restaurant(14, "Smoke & Bones BBQ", 2, "American", 4.6),
    Restaurant(15, "Beirut Corner", 7, "Middle Eastern", 4.3),
    Restaurant(16, "Falafel King", 9, "Middle Eastern", 4.1),
    Restaurant(17, "Bangkok Garden", 7, "Thai", 4.5),
    Restaurant(18, "Thai Orchid", 4, "Thai", 4.2),
    Restaurant(19, "Athens Taverna", 9, "Greek", 4.5),
    Restaurant(20, "Zorba's Kitchen", 10, "Greek", 4.3),
]


# ── Fact table generation ────────────────────────────────────────────────


def _dishes_for_restaurant(restaurant: Restaurant, rng: random.Random) -> List[Dish]:
    """Pick 8–12 dishes matching the restaurant's cuisine (+ a few drinks/desserts).

    The matching is strict (`dish.cuisine == restaurant.cuisine_type`) so
    the menu book can list each dish under exactly one restaurant family,
    making the KB→SQL cross-references consistent in eval questions.
    """
    cuisine_matches = [d for d in DISHES if d.cuisine == restaurant.cuisine_type]
    # Every restaurant also carries Espresso (universal drink).
    universal = [d for d in DISHES if d.cuisine == "Italian" and d.category == "drink"]
    pool = cuisine_matches + [d for d in universal if d not in cuisine_matches]
    target = min(len(pool), rng.randint(8, 12))
    return sorted(rng.sample(pool, target), key=lambda d: d.dish_id)


def _months() -> List[tuple[int, int]]:
    """Jan 2024 → Jun 2025 inclusive — 18 months."""
    out: List[tuple[int, int]] = []
    for year in (2024, 2025):
        for month in range(1, 13):
            if year == 2025 and month > 6:
                break
            out.append((year, month))
    return out


def generate_fact_orders() -> List[dict]:
    """Produce the fact_orders rows deterministically.

    For every (restaurant, dish_on_menu, month) combination we emit one
    row capturing monthly aggregates: count, revenue, average rating, and
    average delivery time. The base price per dish is perturbed by a
    per-restaurant multiplier so two restaurants serving the same dish
    don't come out identical.
    """
    rng = random.Random(SEED)
    rows: List[dict] = []

    for restaurant in RESTAURANTS:
        restaurant_dishes = _dishes_for_restaurant(restaurant, rng)
        # Each restaurant gets a price multiplier so premium spots cost more.
        price_mult = round(rng.uniform(0.9, 1.25), 2)
        # Each restaurant has a "popularity" baseline that shapes order counts.
        popularity = rng.randint(40, 140)

        for dish in restaurant_dishes:
            # Some dishes are hero items for a restaurant.
            is_hero = rng.random() < 0.25
            hero_boost = rng.uniform(1.5, 2.5) if is_hero else 1.0

            for year, month in _months():
                # Monthly seasonality: summer bumps cold dishes, winter bumps hot ones.
                is_summer = month in (6, 7, 8)
                is_winter = month in (11, 12, 1, 2)
                seasonal = 1.0
                if dish.category == "drink" and is_summer:
                    seasonal = 1.3
                if dish.cuisine in ("Thai", "Japanese", "Indian") and is_winter:
                    seasonal = 1.15

                orders_count = max(
                    1,
                    int(popularity * hero_boost * seasonal * rng.uniform(0.7, 1.3)),
                )
                unit_price = round(dish.base_price_eur * price_mult, 2)
                revenue_eur = round(orders_count * unit_price, 2)
                # Rating drifts around restaurant's baseline, bounded to [3.6, 5.0].
                avg_rating = round(
                    max(3.6, min(5.0, restaurant.avg_rating + rng.uniform(-0.4, 0.2))),
                    2,
                )
                # Delivery time 18–55 minutes, hero dishes slightly faster.
                base_dt = rng.randint(22, 50)
                avg_delivery_minutes = max(15, base_dt - (5 if is_hero else 0))

                rows.append(
                    {
                        "dish_id": dish.dish_id,
                        "restaurant_id": restaurant.restaurant_id,
                        "city_id": restaurant.city_id,
                        "year": year,
                        "month": month,
                        "orders_count": orders_count,
                        "revenue_eur": revenue_eur,
                        "avg_rating": avg_rating,
                        "avg_delivery_minutes": avg_delivery_minutes,
                    }
                )

    return rows


# ── CSV writers ──────────────────────────────────────────────────────────


def _write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    data_dir = Path("data")

    _write_csv(
        data_dir / "DIM_CITY.csv",
        [
            {
                "city_id": c.city_id,
                "city_name": c.city_name,
                "country": c.country,
                "region": c.region,
            }
            for c in CITIES
        ],
        ["city_id", "city_name", "country", "region"],
    )

    _write_csv(
        data_dir / "DIM_DISH.csv",
        [
            {
                "dish_id": d.dish_id,
                "dish_name": d.dish_name,
                "cuisine": d.cuisine,
                "category": d.category,
                "base_price_eur": d.base_price_eur,
                "calories": d.calories,
                "allergens": d.allergens,
            }
            for d in DISHES
        ],
        [
            "dish_id",
            "dish_name",
            "cuisine",
            "category",
            "base_price_eur",
            "calories",
            "allergens",
        ],
    )

    _write_csv(
        data_dir / "DIM_RESTAURANT.csv",
        [
            {
                "restaurant_id": r.restaurant_id,
                "restaurant_name": r.restaurant_name,
                "city_id": r.city_id,
                "cuisine_type": r.cuisine_type,
                "avg_rating": r.avg_rating,
            }
            for r in RESTAURANTS
        ],
        ["restaurant_id", "restaurant_name", "city_id", "cuisine_type", "avg_rating"],
    )

    fact_rows = generate_fact_orders()
    _write_csv(
        data_dir / "FACT_ORDERS.csv",
        fact_rows,
        [
            "dish_id",
            "restaurant_id",
            "city_id",
            "year",
            "month",
            "orders_count",
            "revenue_eur",
            "avg_rating",
            "avg_delivery_minutes",
        ],
    )

    print(f"✓ Wrote {len(CITIES)} cities to {data_dir / 'DIM_CITY.csv'}")
    print(f"✓ Wrote {len(DISHES)} dishes to {data_dir / 'DIM_DISH.csv'}")
    print(f"✓ Wrote {len(RESTAURANTS)} restaurants to {data_dir / 'DIM_RESTAURANT.csv'}")
    print(f"✓ Wrote {len(fact_rows):,} fact_orders rows to {data_dir / 'FACT_ORDERS.csv'}")
    print("\nNext: run `make ingest-sql` to load these CSVs into SQLite.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
