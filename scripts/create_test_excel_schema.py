#!/usr/bin/env python3
"""
Create a test Excel file with schema definitions matching the expected format.
This creates a realistic e-commerce schema with many junction tables and foreign keys.
"""
import pandas as pd
from pathlib import Path

def create_test_excel_schema(output_path: str = "test_schema.xlsx"):
    """Create a test Excel file with table_schema and mapping tabs."""

    # Tab 1: table_schema - table and column definitions
    # Simulating an e-commerce database with many junction tables
    table_schema_data = [
        # Users table
        ("users", "id"),
        ("users", "username"),
        ("users", "email"),
        ("users", "created_date"),

        # Customers table
        ("customers", "id"),
        ("customers", "user_id"),
        ("customers", "first_name"),
        ("customers", "last_name"),
        ("customers", "phone"),

        # Products table
        ("products", "id"),
        ("products", "product_name"),
        ("products", "category_id"),
        ("products", "price"),
        ("products", "stock_quantity"),

        # Categories table
        ("categories", "id"),
        ("categories", "category_name"),
        ("categories", "parent_category_id"),

        # Orders table
        ("orders", "id"),
        ("orders", "customer_id"),
        ("orders", "order_date"),
        ("orders", "total_amount"),
        ("orders", "status"),
        ("orders", "shipping_address_id"),

        # Order Items junction table (many-to-many: orders <-> products)
        ("order_items", "id"),
        ("order_items", "order_id"),
        ("order_items", "product_id"),
        ("order_items", "quantity"),
        ("order_items", "unit_price"),

        # Addresses table
        ("addresses", "id"),
        ("addresses", "customer_id"),
        ("addresses", "street"),
        ("addresses", "city"),
        ("addresses", "state"),
        ("addresses", "zip_code"),

        # Reviews table
        ("reviews", "id"),
        ("reviews", "product_id"),
        ("reviews", "customer_id"),
        ("reviews", "rating"),
        ("reviews", "review_text"),
        ("reviews", "review_date"),

        # Shopping Cart junction table
        ("shopping_cart", "id"),
        ("shopping_cart", "customer_id"),
        ("shopping_cart", "product_id"),
        ("shopping_cart", "quantity"),
        ("shopping_cart", "added_date"),

        # Wishlist junction table
        ("wishlist", "id"),
        ("wishlist", "customer_id"),
        ("wishlist", "product_id"),
        ("wishlist", "added_date"),

        # Product Tags junction table (many-to-many: products <-> tags)
        ("product_tags", "id"),
        ("product_tags", "product_id"),
        ("product_tags", "tag_id"),

        # Tags table
        ("tags", "id"),
        ("tags", "tag_name"),

        # Suppliers table
        ("suppliers", "id"),
        ("suppliers", "supplier_name"),
        ("suppliers", "contact_email"),

        # Product Suppliers junction table (many-to-many)
        ("product_suppliers", "id"),
        ("product_suppliers", "product_id"),
        ("product_suppliers", "supplier_id"),
        ("product_suppliers", "supply_price"),

        # Inventory Log
        ("inventory_log", "id"),
        ("inventory_log", "product_id"),
        ("inventory_log", "quantity_change"),
        ("inventory_log", "log_date"),
        ("inventory_log", "reason"),

        # Payments table
        ("payments", "id"),
        ("payments", "order_id"),
        ("payments", "payment_method_id"),
        ("payments", "amount"),
        ("payments", "payment_date"),
        ("payments", "status"),

        # Payment Methods table
        ("payment_methods", "id"),
        ("payment_methods", "customer_id"),
        ("payment_methods", "method_type"),
        ("payment_methods", "card_last_four"),

        # Discounts table
        ("discounts", "id"),
        ("discounts", "discount_code"),
        ("discounts", "discount_percentage"),
        ("discounts", "valid_from"),
        ("discounts", "valid_to"),

        # Order Discounts junction table
        ("order_discounts", "id"),
        ("order_discounts", "order_id"),
        ("order_discounts", "discount_id"),

        # Customer Sessions
        ("customer_sessions", "id"),
        ("customer_sessions", "customer_id"),
        ("customer_sessions", "session_start"),
        ("customer_sessions", "session_end"),
        ("customer_sessions", "ip_address"),
    ]

    # Tab 2: mapping - table relationships
    mapping_data = [
        # User relationships
        ("users", "id", "customers", "user_id"),

        # Customer relationships
        ("customers", "id", "orders", "customer_id"),
        ("customers", "id", "addresses", "customer_id"),
        ("customers", "id", "reviews", "customer_id"),
        ("customers", "id", "shopping_cart", "customer_id"),
        ("customers", "id", "wishlist", "customer_id"),
        ("customers", "id", "payment_methods", "customer_id"),
        ("customers", "id", "customer_sessions", "customer_id"),

        # Product relationships
        ("products", "id", "order_items", "product_id"),
        ("products", "id", "reviews", "product_id"),
        ("products", "id", "shopping_cart", "product_id"),
        ("products", "id", "wishlist", "product_id"),
        ("products", "id", "product_tags", "product_id"),
        ("products", "id", "product_suppliers", "product_id"),
        ("products", "id", "inventory_log", "product_id"),
        ("categories", "id", "products", "category_id"),

        # Order relationships
        ("orders", "id", "order_items", "order_id"),
        ("orders", "id", "payments", "order_id"),
        ("orders", "id", "order_discounts", "order_id"),
        ("addresses", "id", "orders", "shipping_address_id"),

        # Tag relationships
        ("tags", "id", "product_tags", "tag_id"),

        # Supplier relationships
        ("suppliers", "id", "product_suppliers", "supplier_id"),

        # Payment relationships
        ("payment_methods", "id", "payments", "payment_method_id"),

        # Discount relationships
        ("discounts", "id", "order_discounts", "discount_id"),

        # Self-referencing (categories hierarchy)
        ("categories", "id", "categories", "parent_category_id"),
    ]

    # Create DataFrames
    df_schema = pd.DataFrame(table_schema_data, columns=['table_name', 'column_name'])
    df_mapping = pd.DataFrame(mapping_data, columns=['table_a', 'column_a', 'table_b', 'column_b'])

    # Write to Excel with two sheets
    output_file = Path(output_path)
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_schema.to_excel(writer, sheet_name='table_schema', index=False)
        df_mapping.to_excel(writer, sheet_name='mapping', index=False)

    print(f"✅ Created test Excel file: {output_file}")
    print(f"   - {len(set(df_schema['table_name']))} tables")
    print(f"   - {len(df_schema)} total columns")
    print(f"   - {len(df_mapping)} relationships")

    # Print summary
    print("\n📊 Tables created:")
    for table in sorted(set(df_schema['table_name'])):
        col_count = len(df_schema[df_schema['table_name'] == table])
        print(f"   - {table}: {col_count} columns")

    return str(output_file)


if __name__ == "__main__":
    import sys

    # Allow custom output path
    output_path = sys.argv[1] if len(sys.argv) > 1 else "test_schema.xlsx"
    create_test_excel_schema(output_path)