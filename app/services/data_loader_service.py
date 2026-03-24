import json
import os
from datetime import datetime
from typing import Dict, List, Any

from sqlalchemy.orm import Session
from sqlalchemy import text, create_engine, MetaData, Table, Column, String, Integer, DateTime, JSONB
from sqlalchemy.dialects.postgresql import insert

from app.models import Dataset, Resource
from app.database import DATABASE_URL
import uuid

class DataLoaderService:
    """Service for loading normalized data into the PostgreSQL database."""

    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.metadata = MetaData()
        self.metadata.reflect(bind=self.engine)

    def load_data(
        self,
        session: Session,
        dataset: Dataset,
        normalized_data: List[Dict[str, Any]],
        load_mode: str = "upsert"
    ) -> int:
        """
        Loads normalized data into the database.

        Args:
            session: SQLAlchemy session.
            dataset: The Dataset object associated with the data.
            normalized_data: A list of dictionaries, where each dictionary is a record.
            load_mode: 'upsert' to update existing records or insert new ones, 'replace' to delete all existing data and insert new ones.

        Returns:
            The number of records loaded.
        """
        if not normalized_data:
            print("  [LOAD] No data to load.")
            return 0

        table_name = f"core.{dataset.resource.name.lower().replace(' ', '_')}"
        print(f"  [LOAD] Loading data into table: {table_name} with mode: {load_mode}")

        # Ensure table exists and matches schema
        self._ensure_table_schema(session, table_name, dataset.schema_json)

        if load_mode == "replace":
            self._replace_data(session, table_name)
        
        loaded_count = self._upsert_data(session, table_name, normalized_data)
        session.commit()
        print(f"  [LOAD] Loaded {loaded_count} records into {table_name}.")
        return loaded_count

    def _ensure_table_schema(self, session: Session, table_name: str, schema_json: Dict):
        """
        Ensures the target table exists and its schema matches the dataset's schema.
        Creates the table if it doesn't exist, or alters it if necessary.
        """
        schema_name, simple_table_name = table_name.split('.')
        
        # Reflect metadata to check for table existence
        self.metadata.reflect(bind=self.engine, schema=schema_name)

        if simple_table_name not in self.metadata.tables:
            print(f"  [LOAD] Table {table_name} does not exist. Creating it...")
            columns = [
                Column('id', String, primary_key=True),
                Column('created_at', DateTime, default=datetime.utcnow),
                Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
                Column('data', JSONB) # Store the entire record as JSONB
            ]
            # Add columns based on schema_json if needed, for now, we'll store everything in JSONB
            # For a more robust solution, we would dynamically create columns based on schema_json types
            # and map data accordingly.
            new_table = Table(simple_table_name, self.metadata, *columns, schema=schema_name)
            self.metadata.create_all(self.engine)
            print(f"  [LOAD] Table {table_name} created.")
        else:
            print(f"  [LOAD] Table {table_name} already exists. Skipping creation.")
            # TODO: Implement schema alteration if schema_json dictates changes
            # For now, we assume schema is compatible or data is stored in JSONB

    def _replace_data(self, session: Session, table_name: str):
        """
        Deletes all existing data from the table.
        """
        print(f"  [LOAD] Deleting all existing data from {table_name}...")
        session.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY;"))
        print(f"  [LOAD] All data deleted from {table_name}.")

    def _upsert_data(self, session: Session, table_name: str, data: List[Dict[str, Any]]) -> int:
        """
        Performs an upsert operation (insert or update) for the given data.
        """
        schema_name, simple_table_name = table_name.split('.')
        target_table = Table(simple_table_name, self.metadata, schema=schema_name, autoload_with=self.engine)

        loaded_count = 0
        for record in data:
            # Assuming 'id' is present in each record for upserting
            record_id = record.get('id') or str(uuid.uuid4()) # Generate UUID if no ID is present
            
            insert_stmt = insert(target_table).values(
                id=record_id,
                data=record
            )
            on_conflict_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['id'],
                set_=dict(data=record, updated_at=datetime.utcnow())
            )
            session.execute(on_conflict_stmt)
            loaded_count += 1
        return loaded_count


# Helper function for staging data (writing to JSONL)
def stage_data(data: List[Dict[str, Any]], staging_path: str, execution_id: str):
    """
    Writes data to a JSONL file in the staging directory.
    """
    os.makedirs(staging_path, exist_ok=True)
    file_path = os.path.join(staging_path, f"{execution_id}.jsonl")
    with open(file_path, "w", encoding="utf-8") as f:
        for record in data:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  [STAGE] Data staged to {file_path}")
    return file_path
