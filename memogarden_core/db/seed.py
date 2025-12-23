"""Seed database with sample transaction data for development."""

import asyncio
import aiosqlite
from datetime import date, timedelta
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from memogarden_core.config import settings
from memogarden_core.database import create_entity, init_db


async def seed_transactions():
    """Create sample transactions for development."""

    # Initialize database first (only if not already initialized)
    db_path = Path(settings.database_path)
    if not db_path.exists() or db_path.stat().st_size == 0:
        await init_db()
        print("✅ Database initialized with schema")

    db_path = Path(settings.database_path)
    async with aiosqlite.connect(str(db_path)) as db:

        # Sample transactions (last 30 days)
        today = date.today()

        transactions = [
            # Recent transactions
            {
                "description": "Coffee at Starbucks",
                "amount": 6.50,
                "transaction_date": (today - timedelta(days=1)).isoformat(),
                "account": "Personal",
                "category": "Food",
                "notes": "Morning coffee before work"
            },
            {
                "description": "Grocery shopping",
                "amount": 123.45,
                "transaction_date": (today - timedelta(days=2)).isoformat(),
                "account": "Household",
                "category": "Food",
                "notes": "Weekly groceries at FairPrice"
            },
            {
                "description": "Taxi to airport",
                "amount": 28.00,
                "transaction_date": (today - timedelta(days=3)).isoformat(),
                "account": "Personal",
                "category": "Transport",
                "notes": None
            },
            {
                "description": "Netflix subscription",
                "amount": 16.98,
                "transaction_date": (today - timedelta(days=5)).isoformat(),
                "account": "Household",
                "category": "Entertainment",
                "notes": "Monthly subscription"
            },
            {
                "description": "Lunch at hawker center",
                "amount": 5.00,
                "transaction_date": (today - timedelta(days=6)).isoformat(),
                "account": "Personal",
                "category": "Food",
                "notes": None
            },
            {
                "description": "Electricity bill",
                "amount": 82.50,
                "transaction_date": (today - timedelta(days=7)).isoformat(),
                "account": "Household",
                "category": "Utilities",
                "notes": "SP Group monthly bill"
            },
            {
                "description": "Bookstore purchase",
                "amount": 34.90,
                "transaction_date": (today - timedelta(days=10)).isoformat(),
                "account": "Personal",
                "category": "Shopping",
                "notes": "Two technical books"
            },
            {
                "description": "Doctor consultation",
                "amount": 45.00,
                "transaction_date": (today - timedelta(days=12)).isoformat(),
                "account": "Personal",
                "category": "Healthcare",
                "notes": "Annual checkup"
            },
            {
                "description": "MRT card top-up",
                "amount": 50.00,
                "transaction_date": (today - timedelta(days=14)).isoformat(),
                "account": "Personal",
                "category": "Transport",
                "notes": None
            },
            {
                "description": "Internet bill",
                "amount": 49.90,
                "transaction_date": (today - timedelta(days=15)).isoformat(),
                "account": "Household",
                "category": "Utilities",
                "notes": "Singtel fiber broadband"
            },
            {
                "description": "Restaurant dinner",
                "amount": 78.50,
                "transaction_date": (today - timedelta(days=18)).isoformat(),
                "account": "Personal",
                "category": "Food",
                "notes": "Dinner with friends"
            },
            {
                "description": "Clothing purchase",
                "amount": 89.00,
                "transaction_date": (today - timedelta(days=20)).isoformat(),
                "account": "Personal",
                "category": "Shopping",
                "notes": "Uniqlo sale"
            },
            {
                "description": "Movie tickets",
                "amount": 24.00,
                "transaction_date": (today - timedelta(days=22)).isoformat(),
                "account": "Personal",
                "category": "Entertainment",
                "notes": "Weekend movie"
            },
            {
                "description": "Pharmacy",
                "amount": 18.50,
                "transaction_date": (today - timedelta(days=25)).isoformat(),
                "account": "Personal",
                "category": "Healthcare",
                "notes": "Vitamins and supplements"
            },
            {
                "description": "Grab ride",
                "amount": 12.30,
                "transaction_date": (today - timedelta(days=28)).isoformat(),
                "account": "Personal",
                "category": "Transport",
                "notes": None
            },
        ]

        # Insert transactions using entity registry pattern
        for txn_data in transactions:
            # Step 1: Create entity in registry
            entity_id = await create_entity(db, 'transactions')

            # Step 2: Insert transaction data
            await db.execute(
                """INSERT INTO transactions
                   (id, description, amount, currency, transaction_date, account, category, author, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entity_id,
                    txn_data["description"],
                    txn_data["amount"],
                    "SGD",  # Default currency
                    txn_data["transaction_date"],
                    txn_data["account"],
                    txn_data["category"],
                    "seed-script",  # Author
                    txn_data["notes"]
                )
            )

        await db.commit()
        print(f"✅ Seeded {len(transactions)} transactions successfully!")

        # Display summary
        cursor = await db.execute(
            """SELECT COUNT(*) as count, account, category
               FROM transactions
               GROUP BY account, category
               ORDER BY account, category"""
        )
        rows = await cursor.fetchall()

        print("\n📊 Transaction Summary:")
        for row in rows:
            print(f"  {row[1]} / {row[2]}: {row[0]} transactions")


async def main():
    """Main entry point."""
    try:
        await seed_transactions()
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
