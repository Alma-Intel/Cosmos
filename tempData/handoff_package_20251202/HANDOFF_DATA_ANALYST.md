# Data Analyst Handoff: Avipam Ploomes CRM Analytics

**Date:** December 2, 2025  
**Prepared by:** Data Engineering Team  
**For:** Data Analyst / BI Developer

---

## 📋 Executive Summary

We've built a **Bronze → Silver → Gold** data pipeline for Avipam's Ploomes CRM data, focused on **Customer Experience (CX) Friction Analysis**. The pipeline now includes **noise filtering** to remove system-generated records that were diluting our metrics.

### Key Finding: 35% of Interaction Data Was Noise!

| Category | Count | % |
|----------|------:|--:|
| Read Receipts (Lida:/Read:) | 883 | 0.5% |
| Delivery Receipts (Entregue:) | 443 | 0.2% |
| **Mass Emails (4+ recipients)** | **67,563** | **34.6%** |
| **Total Noise Removed** | **68,889** | **35.3%** |
| **Valid Human Interactions** | **126,345** | **64.7%** |

---

## 📁 Data Files Available

### Gold Layer (Ready for Power BI)
Located in: `data/gold/`

| File | Records | Description |
|------|--------:|-------------|
| `exploratory_cx_volumetrics_20251126.parquet` | 249 | Manager-Client pairs with interaction velocity, neediness ratio, load metrics |
| `exploratory_friction_heuristics_20251126.parquet` | 10,808 | Individual interactions flagged with urgency/failure/escalation scores |
| `exploratory_temporal_heat_20251126.parquet` | 168 | Heatmap data (DayOfWeek × Hour) for volume and friction patterns |
| `gold_churn_risk_monitor_20251126.parquet` | 265 | Churn risk scores by client |
| `gold_sales_velocity_20251126.parquet` | 10 | Sales pipeline velocity metrics |
| `gold_segmentation_matrix_20251126.parquet` | 5 | Client segmentation matrix |

### Silver Layer (Cleansed Data)
Located in: `data/silver/`

| File | Records | Description |
|------|--------:|-------------|
| `contacts_20251125.parquet` | 3,521 | Company contacts (TypeId=2) |
| `deals_20251125.parquet` | 1,445 | Deals/opportunities |
| `interaction_records_20251126.parquet` | 195,234 | All interactions with email fields for filtering |

### Bronze Layer (Raw Data)
Located in: `data/bronze/`
- `interaction_records_20251125.jsonl` (285MB) - Raw interaction logs
- `contacts_20251125.jsonl` - Raw contacts
- `deals_20251125.jsonl` - Raw deals
- `metadata/` - Lookup tables (fields, users, stages, interaction_types)

---

## 🔧 What We Built

### 1. Noise Filtering System
The Gold layer now automatically filters out:

```
✗ Read Receipts     → EmailSubject starts with "Lida:" or "Read:"
✗ Delivery Receipts → EmailSubject starts with "Entregue:" or "Delivered:"
                      OR Title="E-mail recebido." + Content contains "sua mensagem foi entregue"
✗ Mass Emails       → EmailRecipients has >3 semicolons (4+ recipients = blast)
```

This is implemented in `gold/exploratory_aggregator.py` → `_filter_system_noise()` method.

### 2. Three Exploratory Tables

#### Table A: `exploratory_cx_volumetrics`
- **Grain:** One row per Manager-Client pair
- **Metrics:**
  - `total_interactions` - Count of valid interactions
  - `interaction_velocity` - Interactions per week
  - `manager_load` - Avg interactions per client for this manager
  - `neediness_ratio` - Interactions ÷ Deal Value (high = needy client)
  - `long_thread_count` - Email threads with 3+ back-and-forths

#### Table B: `exploratory_friction_heuristics`
- **Grain:** One row per Friction Interaction
- **Flags (0/1):**
  - `urgency_score` - Contains: urgente, prioridade, asap, pra ontem, grave, emergência
  - `failure_score` - Contains: erro, problema, falha, não funciona, reclamação, defeito
  - `escalation_score` - Contains: gerente, diretor, supervisor, advogado, presidente, ceo

#### Table C: `exploratory_temporal_heat`
- **Grain:** One row per (DayOfWeek, Hour) slot (168 total = 7 days × 24 hours)
- **Metrics:**
  - `interaction_count` - Volume at this time slot
  - `friction_count` - Friction interactions at this time slot
  - `friday_afternoon_friction_count` - Friday 2PM+ friction (syndrome detection)

---

## 🚨 Open Issue: "Silent Clients"

**Problem:** Many clients show zero interactions despite being active customers.

**Root Cause (Discovered):** 
- Our `contacts` table only contains **Companies** (TypeId=2)
- But interactions are often linked to **People** (TypeId=1) within those companies
- We need to fetch `People` from the API and map them to their parent `Company`

**Diagnostic Results:**
```
Total Interactions:           195,234
Linked to Known Companies:     44,117 (22.6%)
Linked to Unknown (People):   151,117 (77.4%)  ← THIS IS THE PROBLEM
```

**Solution Required:** 
1. Fetch `People` endpoint from Ploomes API
2. Map `Person.CompanyId` → `Company.Id`
3. Re-join interactions via this mapping

---

## 🎯 Suggested Next Steps

### Immediate (Power BI)
1. Connect Power BI to the Gold parquet files
2. Build dashboards:
   - **Friction Heatmap:** `temporal_heat` → Matrix visual (Day × Hour)
   - **Top Needy Clients:** `cx_volumetrics` sorted by `neediness_ratio`
   - **Urgency Timeline:** `friction_heuristics` → Line chart by date with urgency_score

### Data Pipeline
1. Add `People` ingestion to fix "Silent Clients"
2. Consider adding more noise patterns as discovered
3. Add incremental loading (currently full refresh)

### Analysis Ideas
- Which managers handle the most friction?
- Is there a correlation between `neediness_ratio` and churn risk?
- Do Friday afternoon friction spikes predict Monday escalations?

---

## 🔑 How to Run

```powershell
# Re-run Silver transformation (if bronze data changes)
python run_silver.py

# Re-run Gold exploratory aggregation
python run_gold_exploratory.py

# Run noise diagnostic on bronze data
python diagnostic_check.py
```

---

## 📂 Key Files Reference

| File | Purpose |
|------|---------|
| `gold/exploratory_aggregator.py` | Creates the 3 exploratory tables with noise filtering |
| `gold/data_loader.py` | Loads Silver parquet files |
| `silver/transformer.py` | Transforms Bronze JSONL → Silver Parquet |
| `diagnostic_check.py` | Analyzes People vs Companies linkage issue |
| `run_gold_exploratory.py` | Main script to regenerate Gold layer |

---

## ❓ Questions?

Contact the data engineering team for:
- API access to Ploomes for additional endpoints
- Schema changes or new field requirements
- Performance optimization for larger datasets

