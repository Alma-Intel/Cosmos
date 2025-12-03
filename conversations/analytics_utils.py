"""
Utility functions for loading analytics data from parquet files
"""
import pandas as pd
from pathlib import Path
from django.conf import settings
import os


# Base directory for gold data
GOLD_DATA_DIR = Path(__file__).resolve().parent.parent / 'tempData' / 'handoff_package_20251202' / 'gold'


def load_parquet_file(filename):
    """
    Load a parquet file from the gold data directory
    
    Args:
        filename: Name of the parquet file (e.g., 'gold_churn_risk_monitor_20251126.parquet')
    
    Returns:
        pandas DataFrame or None if file not found
    """
    file_path = GOLD_DATA_DIR / filename
    
    if not file_path.exists():
        return None
    
    try:
        df = pd.read_parquet(file_path)
        return df
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return None


def get_cx_volumetrics():
    """Load CX volumetrics data"""
    return load_parquet_file('exploratory_cx_volumetrics_20251126.parquet')


def get_friction_heuristics():
    """Load friction heuristics data"""
    return load_parquet_file('exploratory_friction_heuristics_20251126.parquet')


def get_temporal_heat():
    """Load temporal heatmap data"""
    return load_parquet_file('exploratory_temporal_heat_20251126.parquet')


def get_churn_risk_monitor():
    """Load churn risk monitor data"""
    return load_parquet_file('gold_churn_risk_monitor_20251126.parquet')


def get_sales_velocity():
    """Load sales velocity data"""
    return load_parquet_file('gold_sales_velocity_20251126.parquet')


def get_segmentation_matrix():
    """Load segmentation matrix data"""
    return load_parquet_file('gold_segmentation_matrix_20251126.parquet')


def dataframe_to_dict_list(df, max_rows=None):
    """
    Convert pandas DataFrame to list of dictionaries for template rendering
    
    Args:
        df: pandas DataFrame
        max_rows: Maximum number of rows to return (None for all)
    
    Returns:
        List of dictionaries, each representing a row
    """
    if df is None or df.empty:
        return []
    
    # Limit rows if specified
    if max_rows:
        df = df.head(max_rows)
    
    # Convert to dict, handling NaN values
    records = df.to_dict('records')
    
    # Replace NaN with None for better template handling
    for record in records:
        for key, value in record.items():
            if pd.isna(value):
                record[key] = None
    
    return records


def get_summary_stats(df):
    """
    Get summary statistics for a DataFrame
    
    Returns:
        Dictionary with summary statistics
    """
    if df is None or df.empty:
        return {
            'row_count': 0,
            'column_count': 0,
            'columns': []
        }
    
    return {
        'row_count': len(df),
        'column_count': len(df.columns),
        'columns': list(df.columns),
        'numeric_summary': df.describe().to_dict() if len(df.select_dtypes(include=['number']).columns) > 0 else None
    }

