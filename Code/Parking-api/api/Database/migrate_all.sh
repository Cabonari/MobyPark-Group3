#!/usr/bin/env bash

# open the Database folder in bash and enter command: bash migrate_all.sh 
set -e

echo "Creating tables..."
python create_tables.py

echo "Migrating users..."
python migrate_users.py

echo "Migrating parking lots..."
python migrate_parkinglots.py

echo "Migrating vehicles..."
python migrate_vehicles.py

echo "Migrating payments ..."
python migrate_payments.py

echo "All migrations completed successfully."
