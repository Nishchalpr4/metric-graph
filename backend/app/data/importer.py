"""
CSV Data Importer

Imports metric time-series data from CSV files into the database.

CSV Format:
  metric_name,period,segment,value
  orders,Q1 2022,Food Delivery,85.0
  aov,Q1 2022,Food Delivery,295.0
  ...
"""

import logging
from io import StringIO
import csv
from sqlalchemy.orm import Session
from ..models.db_models import TimeSeriesData

log = logging.getLogger(__name__)


def import_metrics_from_csv(file_content: str, db: Session, clear_existing: bool = False) -> dict:
    """
    Import metric data from CSV string into time_series_data table.
    
    Args:
        file_content: CSV file content as string
        db: SQLAlchemy database session
        clear_existing: If True, delete existing data before import
    
    Returns:
        Summary dict with row counts
    """
    
    if clear_existing:
        db.query(TimeSeriesData).delete()
        db.commit()
        log.info("Cleared existing time-series data")
    
    reader = csv.DictReader(StringIO(file_content))
    rows_inserted = 0
    errors = []
    
    for idx, row in enumerate(reader, start=2):  # Start at 2 (skip header)
        try:
            metric_name = row.get('metric_name', '').strip()
            period = row.get('period', '').strip()
            segment = row.get('segment', '').strip()
            value_str = row.get('value', '').strip()
            
            if not all([metric_name, period, segment, value_str]):
                errors.append(f"Row {idx}: Missing required fields")
                continue
            
            value = float(value_str)
            
            # Check if entry already exists
            existing = db.query(TimeSeriesData).filter(
                TimeSeriesData.metric_name == metric_name,
                TimeSeriesData.period == period,
                TimeSeriesData.segment == segment,
            ).first()
            
            if existing:
                existing.value = value
                log.debug(f"Updated {metric_name} for {period} / {segment}")
            else:
                ts = TimeSeriesData(
                    metric_name=metric_name,
                    period=period,
                    segment=segment,
                    value=value,
                    is_computed=False,
                )
                db.add(ts)
                log.debug(f"Added {metric_name} for {period} / {segment}")
            
            rows_inserted += 1
        
        except ValueError as e:
            errors.append(f"Row {idx}: Invalid value '{value_str}' - {str(e)}")
        except Exception as e:
            errors.append(f"Row {idx}: {str(e)}")
    
    db.commit()
    
    summary = {
        "status": "success",
        "rows_inserted": rows_inserted,
        "errors": errors,
        "error_count": len(errors),
    }
    
    log.info(f"CSV import complete: {rows_inserted} rows inserted, {len(errors)} errors")
    return summary
