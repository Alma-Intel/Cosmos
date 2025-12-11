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

def get_clients_analysis():
    """Load clients analysis data from the newest JSON file"""
    file_path = GOLD_DATA_DIR / 'clients_analysis_20251211_055217.json'
    
    if not file_path.exists():
        return None, None, None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Return clients array, metadata, and global_analyses
        return data.get('clients', []), data.get('metadata', {}), data.get('global_analyses', {})
    except Exception as e:
        print(f"Error loading clients_analysis_20251211_055217.json: {e}")
        return None, None, None


def transform_clients_for_time_window(clients, time_window='last_6_months'):
    """
    Transform client data to show metrics from a specific time window.
    
    Args:
        clients: List of client dictionaries with time_windows
        time_window: One of 'last_week', 'last_month', 'last_3_months', 'last_6_months', 'last_year'
    
    Returns:
        List of transformed client dictionaries with flattened time window metrics
    """
    if not clients:
        return []
    
    transformed = []
    for client in clients:
        # Get basic client info
        transformed_client = {
            'client_name': client.get('client_name', ''),
            'legal_name': client.get('legal_name', ''),
            'cnpj': client.get('cnpj', ''),
            'total_interactions': client.get('total_interactions', 0),
        }
        
        # Get time window data
        time_windows = client.get('time_windows', {})
        window_data = time_windows.get(time_window, {})
        
        if window_data:
            # Flatten time window metrics
            transformed_client.update({
                'interactions': window_data.get('interactions', 0),
                'sentiment': window_data.get('sentiment'),
                'trend': window_data.get('trend'),
                'topics': window_data.get('topics', []),
                'days_since_last_interaction': window_data.get('days_since_last_interaction'),
                'risk_level': window_data.get('risk_level'),
                'date_range_start': window_data.get('date_range', {}).get('start'),
                'date_range_end': window_data.get('date_range', {}).get('end'),
                'window_name': window_data.get('window_name', time_window),
                'window_label': window_data.get('window_label', time_window.replace('_', ' ').title()),
            })
        else:
            # If no data for this window, set defaults
            transformed_client.update({
                'interactions': 0,
                'sentiment': None,
                'trend': None,
                'topics': [],
                'days_since_last_interaction': None,
                'risk_level': None,
                'date_range_start': None,
                'date_range_end': None,
                'window_name': time_window,
                'window_label': time_window.replace('_', ' ').title(),
            })
        
        transformed.append(transformed_client)
    
    return transformed


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

