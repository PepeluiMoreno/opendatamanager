#!/usr/bin/env python
"""
Script to run Alembic migrations to HEAD.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic.config import Config
from alembic import command

def run_migrations():
    """Run all pending migrations"""
    alembic_cfg = Config("alembic.ini")

    print("Running migrations to HEAD...")
    command.upgrade(alembic_cfg, "head")
    print("✅ Migrations completed successfully!")

if __name__ == "__main__":
    run_migrations()
