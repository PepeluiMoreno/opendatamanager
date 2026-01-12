#!/usr/bin/env python3
"""
Test script for JSONL Viewer functionality
"""
import json
from pathlib import Path

# Create test JSONL files in staging directory
staging_dir = Path('./data/staging')
test_dir = staging_dir / 'test'
test_dir.mkdir(exist_ok=True)

# Sample JSONL data for RER
rer_data = [
    {
        "id": "1",
        "entidad": "IGLESIA CATÓLICA",
        "denominación": "ARQUIDIÓCESIS DE MADRID",
        "número_registro": "12345-ABC",
        "fecha_registro": "2020-01-15",
        "estado": "ACTIVO",
        "dirección": "Calle Mayor, 15, Madrid",
        "cif": "Q2800000A"
    },
    {
        "id": "2", 
        "entidad": "COMUNIDAD ISLÁMICA",
        "denominación": "MEZQUITA DE COMILLAS",
        "número_registro": "23456-DEF",
        "fecha_registro": "2021-03-20",
        "estado": "ACTIVO",
        "dirección": "Calle de los Moros, 45, Madrid",
        "cif": "G28000001"
    },
    {
        "id": "3",
        "entidad": "COMUNIDAD JUDÍA",
        "denominación": "COMUNIDAD JUDÍA DE MADRID",
        "número_registro": "34567-GHI",
        "fecha_registro": "2019-11-10", 
        "estado": "ACTIVO",
        "dirección": "Calle Balmes, 3, Madrid",
        "cif": "H28000002"
    }
]

# Create RER test file
rer_file = test_dir / 'rer_sample.jsonl'
with open(rer_file, 'w', encoding='utf-8') as f:
    for item in rer_data:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f"Created test file: {rer_file}")
print(f"Test file contains {len(rer_data)} RER records")

# Create a larger sample file for testing pagination
large_data = []
for i in range(150):
    record = {
        "id": str(i + 1),
        "entidad": f"ENTIDAD RELIGIOSA {i+1}",
        "denominación": f"DENOMINACIÓN DE PRUEBA {i+1}",
        "número_registro": f"{10000 + i:05d}-XYZ",
        "fecha_registro": f"2020-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
        "estado": "ACTIVO" if i % 10 != 0 else "INACTIVO",
        "dirección": f"Calle de Prueba {i+1}, Madrid",
        "cif": f"{'ABCDEFGH'[i % 8]}{28000000 + i:08d}"
    }
    large_data.append(record)

large_file = test_dir / 'rer_large_sample.jsonl'
with open(large_file, 'w', encoding='utf-8') as f:
    for item in large_data:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f"Created large test file: {large_file}")
print(f"Large file contains {len(large_data)} records")

# Verify files exist
print("\nTest files created:")
for file_path in test_dir.glob('*.jsonl'):
    size = file_path.stat().st_size
    print(f"  {file_path.name} ({size:,} bytes)")