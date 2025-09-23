# Environment Switching Guide

This guide explains how to switch between different demo environments for Netquery.

## Two Demo Environments

### 🏗️ **Sample Environment** (Network Infrastructure)
- **Database**: SQLite (`data/infrastructure.db`)
- **Schema**: Auto-detected from SQLite metadata
- **Tables**: Load balancers, servers, network monitoring, SSL certificates
- **Use Case**: Network infrastructure operations demo
- **Data**: Generated sample data with realistic network metrics

### 🏢 **Production Environment** (PostgreSQL)
- **Database**: PostgreSQL (your production database)
- **Schema**: Excel-defined schema (no database introspection)
- **Tables**: Your real business tables defined in Excel
- **Use Case**: Production data with any domain (not limited to e-commerce)
- **Data**: Your actual PostgreSQL data
- **SQL Syntax**: Auto-detects PostgreSQL and uses `CURRENT_DATE + INTERVAL`, `ILIKE`, etc.

## Quick Switching

### Switch to Sample Data (Default)
```bash
python scripts/switch_environment.py sample
```

### Switch to Production Data
```bash
python scripts/switch_environment.py production
```

### Check Current Environment
```bash
python scripts/switch_environment.py status
```

## Manual Configuration

### Sample Environment Setup
1. **Switch environment**: `python scripts/switch_environment.py sample`
2. **Create sample data**: `python scripts/create_sample_data.py`
3. **Start server**: `python -m uvicorn src.api.server:app --reload`
4. **Test queries**: "Show me all load balancers", "What's the network traffic trend?"

### Production Environment Setup
1. **Switch environment**: `python scripts/switch_environment.py production`
2. **Update .env file**:
   ```bash
   DATABASE_URL=postgresql://user:pass@host:5432/database
   EXCEL_SCHEMA_PATH=/path/to/your/schema.xlsx
   ```
3. **Place your Excel file** with the schema definition
4. **Start server**: `python -m uvicorn src.api.server:app --reload`
5. **Test queries**: "Show me top customers", "What are the recent orders?"

## Environment Files

### `.env.sample` (Network Infrastructure)
```env
DATABASE_URL=sqlite:///data/infrastructure.db
DEMO_MODE=sample
EXCEL_SCHEMA_PATH=
TABLE_DESCRIPTIONS_FILE=table_descriptions.yaml
```

### `.env.production` (E-commerce with Excel Schema)
```env
DATABASE_URL=postgresql://user:password@localhost:5432/your_database
DEMO_MODE=production
EXCEL_SCHEMA_PATH=your_real_schema.xlsx
TABLE_DESCRIPTIONS_FILE=table_descriptions_ecommerce.yaml
```

## Table Description Files

### `table_descriptions.yaml` (Sample - Network)
- Load balancers
- Servers
- Network traffic
- SSL certificates
- Backend mappings

### `table_descriptions_ecommerce.yaml` (Production - E-commerce)
- Users, customers
- Orders, order items
- Products, categories
- Reviews, shopping cart
- Payments, discounts

## Key Differences

| Aspect | Sample Environment | Production Environment |
|--------|-------------------|----------------------|
| Database | SQLite | PostgreSQL |
| SQL Syntax | SQLite (`DATE('now')`) | PostgreSQL (`CURRENT_DATE + INTERVAL`) |
| Schema Source | Database introspection | Excel file |
| Tables | Network infrastructure | Your business domain |
| Data | Generated samples | Real production data |
| Queries | "Show load balancers" | Your business queries |
| Setup | Auto-generated | Manual configuration |

## Benefits of This Approach

### ✅ **Advantages**
1. **Clean separation**: No mixing of sample and real data
2. **Easy switching**: One command to switch environments
3. **Database flexibility**: SQLite development, PostgreSQL production
4. **Schema flexibility**: Database introspection vs Excel definitions
5. **SQL compatibility**: Auto-detects database type and generates correct syntax
6. **Safe testing**: Sample environment for experimentation

### 🎯 **Use Cases**
- **Sample**: Demo to network engineers, development teams
- **Production**: Demo to business users, production deployment
- **Development**: Test schema parsing vs database introspection
- **SQL Testing**: Verify PostgreSQL vs SQLite syntax compatibility

## Troubleshooting

### Environment Not Switching
```bash
# Check current status
python scripts/switch_environment.py status

# Force switch
rm .env
python scripts/switch_environment.py sample
```

### Missing Files
```bash
# Restore original files if corrupted
git checkout src/text_to_sql/table_descriptions.yaml
python scripts/switch_environment.py sample
```

### Database Connection Issues

**Sample Environment:**
- Ensure SQLite file exists: `python scripts/create_sample_data.py`
- Check file permissions in `data/` directory

**Production Environment:**
- Verify PostgreSQL connection string in `.env`
- Test database connectivity manually
- Ensure Excel schema file exists and is readable

## Advanced Usage

### Custom Environment
1. Create `.env.custom` with your settings
2. Copy to `.env` manually
3. Update table descriptions as needed

### Multiple Production Environments
1. Create `.env.production_staging`, `.env.production_live`
2. Create corresponding table description files
3. Modify switch script to handle additional environments

## Best Practices

1. **Always check status** before starting demos
2. **Test queries** after switching environments
3. **Keep Excel schema updated** with real database changes
4. **Backup configurations** before major changes
5. **Document custom setups** for team members