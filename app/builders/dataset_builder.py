"""
Dataset Builder - Generates complete dataset packages.
Creates versioned packages with data, schema, models, and metadata.
"""
import os
import json
import shutil
import hashlib
from uuid import uuid4
from datetime import datetime
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models import Resource, ResourceExecution, Dataset
from app.utils.schema_inference import infer_schema
from app.utils.versioning import compute_next_version


class DatasetBuilder:
    """Builds complete dataset packages with versioning"""

    def build(
        self,
        session: Session,
        resource: Resource,
        execution: ResourceExecution,
        data: List[Dict]
    ) -> Dataset:
        """
        Build complete dataset package.

        Creates a versioned package containing:
        - data.jsonl: The actual data
        - schema.json: Inferred JSON Schema
        - models.py: Generated SQLAlchemy models
        - metadata.json: Package metadata

        Args:
            session: SQLAlchemy session
            resource: Resource being processed
            execution: ResourceExecution record
            data: List of data records

        Returns:
            Dataset record
        """
        print(f"  [3/4] dataset - Generating package for {resource.name}...")

        # 1. Infer schema from data
        schema_json = infer_schema(data)

        # 2. Get latest dataset for versioning
        latest_dataset = (
            session.query(Dataset)
            .filter(Dataset.resource_id == resource.id)
            .order_by(
                Dataset.major_version.desc(),
                Dataset.minor_version.desc(),
                Dataset.patch_version.desc()
            )
            .first()
        )

        # 3. Compute version
        major, minor, patch = compute_next_version(latest_dataset, schema_json)
        version_str = f"{major}.{minor}.{patch}"

        print(f"    Version: {version_str}")

        # 4. Create dataset directory
        dataset_id = str(uuid4())
        dataset_dir = f"data/datasets/{resource.id}/{dataset_id}"
        os.makedirs(dataset_dir, exist_ok=True)

        # 5. Copy staged data to dataset
        if os.path.exists(execution.staging_path):
            shutil.copy(execution.staging_path, f"{dataset_dir}/data.jsonl")
        else:
            # If staging file doesn't exist, write data directly
            with open(f"{dataset_dir}/data.jsonl", 'w', encoding='utf-8') as f:
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')

        # 6. Write schema
        with open(f"{dataset_dir}/schema.json", 'w', encoding='utf-8') as f:
            json.dump(schema_json, f, indent=2, ensure_ascii=False)

        # 7. Generate models
        models_code = self._generate_models(resource, schema_json)
        with open(f"{dataset_dir}/models.py", 'w', encoding='utf-8') as f:
            f.write(models_code)

        # 8. Compute checksum
        checksum = self._compute_checksum(f"{dataset_dir}/data.jsonl")

        # 9. Write metadata
        metadata = {
            "dataset_id": dataset_id,
            "resource_id": str(resource.id),
            "resource_name": resource.name,
            "execution_id": str(execution.id),
            "version": version_str,
            "created_at": datetime.utcnow().isoformat(),
            "record_count": len(data),
            "checksum": checksum
        }
        with open(f"{dataset_dir}/metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # 10. Create Dataset record
        dataset = Dataset(
            id=dataset_id,
            resource_id=resource.id,
            execution_id=execution.id,
            major_version=major,
            minor_version=minor,
            patch_version=patch,
            schema_json=schema_json,
            data_path=f"{dataset_dir}/data.jsonl",
            record_count=len(data),
            checksum=checksum,
            created_at=datetime.utcnow()
        )

        print(f"    Dataset generated: {dataset_dir}")

        return dataset

    def _compute_checksum(self, filepath: str) -> str:
        """Compute SHA256 checksum of file"""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _generate_models(self, resource: Resource, schema_json: Dict) -> str:
        """
        Generate SQLAlchemy models from schema.

        Args:
            resource: Resource being processed
            schema_json: Inferred JSON Schema

        Returns:
            Python code as string
        """
        table_name = resource.target_table
        class_name = self._to_pascal_case(table_name)

        code = f'''"""
Auto-generated models for: {resource.name}
Generated: {datetime.utcnow().isoformat()}
Version: Auto-generated from dataset
DO NOT EDIT MANUALLY - Download new version from OpenDataManager
"""
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class {class_name}(Base):
    """
    Dataset: {resource.name}
    Publisher: {resource.publisher}
    """
    __tablename__ = "{table_name}"
    __table_args__ = {{"schema": "core"}}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
'''

        # Add columns from schema
        for field_name, field_spec in schema_json.get("properties", {}).items():
            sql_type = self._map_json_type_to_sqlalchemy(field_spec.get("type", "string"))
            nullable = field_name not in schema_json.get("required", [])
            code += f'    {field_name} = Column({sql_type}, nullable={nullable})\n'

        return code

    def _to_pascal_case(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase"""
        return ''.join(word.capitalize() for word in snake_str.split('_'))

    def _map_json_type_to_sqlalchemy(self, json_type: str) -> str:
        """Map JSON Schema type to SQLAlchemy type"""
        mapping = {
            "string": "String(255)",
            "integer": "Integer",
            "number": "Float",
            "boolean": "Boolean",
            "array": "JSONB",
            "object": "JSONB"
        }
        return mapping.get(json_type, "Text")
