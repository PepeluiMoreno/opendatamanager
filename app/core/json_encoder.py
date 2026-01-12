"""
Custom JSON encoder para manejar objetos SQLAlchemy y otros tipos complejos
"""
import json
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID


class OpenDataManagerEncoder(json.JSONEncoder):
    """Custom JSON encoder that can handle SQLAlchemy objects and other complex types"""
    
    def default(self, o):
        # Handle SQLAlchemy model instances
        if hasattr(o, '__tablename__') and hasattr(o, 'to_dict'):
            return o.to_dict()
        
        # Handle SQLAlchemy model instances without to_dict method
        if hasattr(o, '__tablename__'):
            # Build dict from columns
            result = {}
            for column in o.__table__.columns:
                value = getattr(o, column.name)
                if value is not None:
                    result[column.name] = value
            return result
        
        # Handle datetime objects
        if isinstance(o, datetime):
            return o.isoformat()
        
        if isinstance(o, date):
            return o.isoformat()
        
        if isinstance(o, time):
            return o.isoformat()
        
        # Handle UUID objects
        if isinstance(o, UUID):
            return str(o)
        
        # Handle Decimal objects
        if isinstance(o, Decimal):
            return float(o)
        
        # Handle sets (convert to list)
        if isinstance(o, set):
            return list(o)
        
        # Handle bytes (decode as utf-8)
        if isinstance(o, bytes):
            try:
                return o.decode('utf-8')
            except UnicodeDecodeError:
                return str(o)
        
        # Handle objects with __dict__
        if hasattr(o, '__dict__'):
            return vars(o)
        
        # Fall back to parent class
        return super().default(o)