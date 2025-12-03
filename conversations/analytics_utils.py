"""
Utility functions for loading analytics data from JSON files
"""
import json
from pathlib import Path
from django.conf import settings
import os


# Base directory for gold JSON data
GOLD_DATA_DIR = Path(__file__).resolve().parent.parent / 'tempData' / 'handoff_package_20251202' / 'gold_json'


def load_json_file(filename):
    """
    Load a JSON file from the gold data directory
    
    Args:
        filename: Name of the JSON file (e.g., 'gold_churn_risk_monitor_20251126.json')
    
    Returns:
        List of dictionaries or None if file not found
    """
    file_path = GOLD_DATA_DIR / filename
    
    if not file_path.exists():
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return None


def get_cx_volumetrics():
    """Load CX volumetrics data"""
    return load_json_file('exploratory_cx_volumetrics_20251126.json')


def get_friction_heuristics():
    """Load friction heuristics data"""
    return load_json_file('exploratory_friction_heuristics_20251126.json')


def get_temporal_heat():
    """Load temporal heatmap data"""
    return load_json_file('exploratory_temporal_heat_20251126.json')


def get_churn_risk_monitor():
    """Load churn risk monitor data"""
    return load_json_file('gold_churn_risk_monitor_20251126.json')


def get_sales_velocity():
    """Load sales velocity data"""
    return load_json_file('gold_sales_velocity_20251126.json')


def get_segmentation_matrix():
    """Load segmentation matrix data"""
    return load_json_file('gold_segmentation_matrix_20251126.json')


def get_data_slice(data, max_rows=None):
    """
    Get a slice of data for template rendering
    
    Args:
        data: List of dictionaries
        max_rows: Maximum number of rows to return (None for all)
    
    Returns:
        List of dictionaries
    """
    if data is None or len(data) == 0:
        return []
    
    # Limit rows if specified
    if max_rows:
        return data[:max_rows]
    
    return data


def get_summary_stats(data):
    """
    Get summary statistics for a data list
    
    Returns:
        Dictionary with summary statistics
    """
    if data is None or len(data) == 0:
        return {
            'row_count': 0,
            'column_count': 0,
            'columns': []
        }
    
    # Get columns from first record
    columns = list(data[0].keys()) if data else []
    
    return {
        'row_count': len(data),
        'column_count': len(columns),
        'columns': columns
    }

