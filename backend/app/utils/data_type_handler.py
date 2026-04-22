"""
Data Type Handler - 100% Database-Driven

Handles type conversions for database columns, especially JSONB columns
that should be numeric but are stored as JSON.
"""

from typing import Optional, Any


class DataTypeHandler:
    """
    Handle various data types from database columns gracefully.
    Converts JSONB, strings, and other types to numeric values.
    """
    
    @staticmethod
    def get_numeric_value(obj: Any, attribute_name: str) -> Optional[float]:
        """
        Get numeric value from object attribute, handling JSONB and type mismatches.
        
        Args:
            obj: Database model instance (e.g., FinancialsPnL row)
            attribute_name: Column name to extract
            
        Returns:
            Float value or None if cannot convert
        """
        if obj is None:
            return None
        
        try:
            value = getattr(obj, attribute_name, None)
            
            if value is None:
                return None
            
            # If it's already a number, return it
            if isinstance(value, (int, float)):
                return float(value)
            
            # If it's a string, try to parse it
            if isinstance(value, str):
                # Handle empty strings
                if not value.strip():
                    return None
                try:
                    return float(value)
                except ValueError:
                    return None
            
            # If it's JSONB (dict), try to extract numeric value
            if isinstance(value, dict):
                # Strategy 1: If dict has 'value' key, use that
                if 'value' in value:
                    return DataTypeHandler._to_float(value['value'])
                
                # Strategy 2: If dict has 'amount' key, use that
                if 'amount' in value:
                    return DataTypeHandler._to_float(value['amount'])
                
                # Strategy 3: If dict has single numeric value, use it
                numeric_values = [v for v in value.values() if isinstance(v, (int, float))]
                if len(numeric_values) == 1:
                    return float(numeric_values[0])
                
                # Strategy 4: Try common keys
                for key in ['number', 'num', 'val', 'numeric']:
                    if key in value:
                        return DataTypeHandler._to_float(value[key])
            
            # If it's a list, try first numeric element
            if isinstance(value, list) and len(value) > 0:
                return DataTypeHandler._to_float(value[0])
            
            # Can't convert
            return None
        
        except (ValueError, TypeError, AttributeError):
            return None
    
    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        """Internal helper to convert any value to float"""
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                return None
        
        return None
    
    @staticmethod
    def safe_getattr(obj: Any, attribute_name: str, default: Any = None) -> Any:
        """
        Safely get attribute from object, returning default if not found.
        
        Args:
            obj: Object to get attribute from
            attribute_name: Name of attribute
            default: Default value if attribute not found
            
        Returns:
            Attribute value or default
        """
        try:
            return getattr(obj, attribute_name, default)
        except AttributeError:
            return default
