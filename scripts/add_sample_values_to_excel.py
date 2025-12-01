"""
Script to add sample_values column to the sample Excel schema.
This demonstrates how sample_values can be specified in the Excel file.
"""
import pandas as pd

# Read the existing Excel file
excel_path = 'schema_files/sample_schema.xlsx'

# Read both sheets
table_schema_df = pd.read_excel(excel_path, sheet_name='table_schema')
mapping_df = pd.read_excel(excel_path, sheet_name='mapping')

# Add sample_values column if it doesn't exist
if 'sample_values' not in table_schema_df.columns:
    table_schema_df['sample_values'] = ''

# Define sample values for specific columns based on the schema
# These are examples that make sense for a load balancer schema
sample_values_map = {
    ('load_balancers', 'status'): 'active, inactive, maintenance',
    ('load_balancers', 'datacenter'): 'us-west-2, us-east-1, eu-central-1',
    ('virtual_ips', 'protocol'): 'HTTP, HTTPS, TCP',
    ('wide_ips', 'status'): 'active, inactive',
    ('wide_ips', 'load_balancing_method'): 'round_robin, weighted, geolocation',
    ('backend_servers', 'health_status'): 'healthy, unhealthy, draining',
    ('backend_servers', 'datacenter'): 'us-west-2, us-east-1, eu-central-1',
}

# Apply sample values to the DataFrame
for idx, row in table_schema_df.iterrows():
    table_name = row['table_name']
    column_name = row['column_name']
    key = (table_name, column_name)

    if key in sample_values_map:
        table_schema_df.at[idx, 'sample_values'] = sample_values_map[key]

# Save back to Excel with both sheets
with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
    table_schema_df.to_excel(writer, sheet_name='table_schema', index=False)
    mapping_df.to_excel(writer, sheet_name='mapping', index=False)

print(f"✅ Added sample_values column to {excel_path}")
print(f"\nColumns with sample values:")
for key, values in sample_values_map.items():
    print(f"  - {key[0]}.{key[1]}: {values}")
