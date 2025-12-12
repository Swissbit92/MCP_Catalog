#!/usr/bin/env python3
"""
Direct MongoDB exploration using pymongo.
"""

try:
    from pymongo import MongoClient
    from pymongo.server_api import ServerApi
except ImportError:
    print("Installing pymongo...")
    import subprocess
    subprocess.check_call(["pip", "install", "pymongo"])
    from pymongo import MongoClient
    from pymongo.server_api import ServerApi

import json
from datetime import datetime

MONGODB_URI = "***REMOVED***"

def main():
    print("MongoDB Crypto Cluster Exploration (Direct)")
    print("="*60)

    try:
        # Connect to MongoDB
        print("\nConnecting to MongoDB cluster...")
        client = MongoClient(MONGODB_URI, server_api=ServerApi('1'), serverSelectionTimeoutMS=10000)

        # Test connection
        client.admin.command('ping')
        print("[OK] Connected successfully!")

        # List all databases
        print("\n1. Available databases:")
        db_list = client.list_database_names()
        for db_name in db_list:
            print(f"   - {db_name}")

        # Focus on btc_data database
        db = client['btc_data']
        print("\n2. Collections in 'btc_data' database:")
        collections = db.list_collection_names()
        for coll_name in collections:
            print(f"   - {coll_name}")

        # Explore each collection
        print("\n3. Exploring collections:")
        for coll_name in collections:
            print(f"\n{'='*60}")
            print(f"Collection: {coll_name}")
            print(f"{'='*60}")

            collection = db[coll_name]

            # Get count
            count = collection.count_documents({})
            print(f"Document count: {count:,}")

            if count > 0:
                # Get a sample document
                sample = collection.find_one()
                print(f"\nSample document:")
                print(json.dumps(sample, indent=2, default=str))

                # Get schema by looking at first document fields
                print(f"\nFields in collection:")
                if sample:
                    for field, value in sample.items():
                        field_type = type(value).__name__
                        print(f"   - {field}: {field_type}")

                # Get date range if there's a timestamp field
                timestamp_fields = ['timestamp', 'date', 'time', 'created_at', 'updated_at', 'datetime']
                for ts_field in timestamp_fields:
                    if ts_field in sample:
                        print(f"\nDate range for '{ts_field}':")
                        oldest = collection.find_one(sort=[(ts_field, 1)])
                        newest = collection.find_one(sort=[(ts_field, -1)])
                        if oldest and newest:
                            print(f"   Oldest: {oldest.get(ts_field)}")
                            print(f"   Newest: {newest.get(ts_field)}")
                        break

                # Get a few recent documents
                print(f"\nLast 3 documents:")
                recent_docs = list(collection.find().sort("_id", -1).limit(3))
                for i, doc in enumerate(recent_docs, 1):
                    print(f"\n   Document {i}:")
                    print("   " + json.dumps(doc, indent=6, default=str).replace("\n", "\n   "))

            print()

        client.close()
        print("\n[OK] Exploration complete!")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
