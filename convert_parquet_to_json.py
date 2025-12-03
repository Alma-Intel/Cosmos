"""
Temporary script to convert parquet files to JSON
"""
import pandas as pd
import json
from pathlib import Path

# Base directory for gold data
GOLD_DATA_DIR = Path('tempData/handoff_package_20251202/gold')
OUTPUT_DIR = Path('tempData/handoff_package_20251202/gold_json')

# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# List of parquet files to convert
parquet_files = [
    'exploratory_cx_volumetrics_20251126.parquet',
    'exploratory_friction_heuristics_20251126.parquet',
    'exploratory_temporal_heat_20251126.parquet',
    'gold_churn_risk_monitor_20251126.parquet',
    'gold_sales_velocity_20251126.parquet',
    'gold_segmentation_matrix_20251126.parquet',
]

print("Converting parquet files to JSON...")
print("=" * 60)

for parquet_file in parquet_files:
    input_path = GOLD_DATA_DIR / parquet_file
    output_file = parquet_file.replace('.parquet', '.json')
    output_path = OUTPUT_DIR / output_file
    
    if not input_path.exists():
        print(f"[WARNING] File not found: {parquet_file}")
        continue
    
    try:
        # Read parquet file
        df = pd.read_parquet(input_path)
        
        # Convert to JSON
        # Use records orientation for easier template access
        json_data = df.to_dict(orient='records')
        
        # Replace NaN with None for JSON compatibility
        for record in json_data:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
        
        # Write to JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, default=str)
        
        print(f"[OK] Converted: {parquet_file}")
        print(f"   Rows: {len(df)}, Columns: {len(df.columns)}")
        print(f"   Output: {output_path}")
        print(f"   Columns: {', '.join(df.columns.tolist())}")
        print()
        
    except Exception as e:
        print(f"[ERROR] Error converting {parquet_file}: {e}")
        print()

print("=" * 60)
print("Conversion complete!")
print(f"JSON files saved to: {OUTPUT_DIR}")

