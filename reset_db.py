"""
Script to reset the equipment database with the new schema.
Run this if you encounter database schema errors.
"""
import os
import sqlite3

EQUIPMENT_DB = 'equipment.db'

if os.path.exists(EQUIPMENT_DB):
    print(f"Deleting existing {EQUIPMENT_DB}...")
    os.remove(EQUIPMENT_DB)
    print(f"{EQUIPMENT_DB} deleted successfully!")

print("The database will be recreated with the new schema when you restart the Flask app.")
print("Run: python app.py")

