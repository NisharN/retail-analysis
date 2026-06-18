# Missing Winners Analysis System

> *"Are my branches readily stocking my popular products?"*

A retail analytics tool for category managers. Given chain-wide sales data across multiple shops, it identifies products that sell well across the chain but are missing or underperforming in a specific shop — ranked by lost revenue opportunity and surfaced in a filterable dashboard.

---

## What it does

- **Missing Winners** — top-selling (Class A/B) products that a selected shop has never stocked or has zero sales for
- **Underperforming** — products the shop stocks but sells below the chain average threshold
- **Gap Score** — `(ChainAvg - ShopSales) / ChainAvg`, showing how far behind each product is
- **Potential Lost Revenue** — estimated recoverable revenue per product if the shop matched chain average
- **Export** — download results as Excel or PDF report

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Backend | FastAPI + Uvicorn |
| Data | Pandas + NumPy (in-memory; no database required) |
| Export | openpyxl / XlsxWriter (Excel), ReportLab (PDF) |

---

## Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- The source Excel dataset (`data/testdata1.xlsx`) — place it in the `data/` folder before starting

---

## Getting Started

### 1. Clone the repository

```bash
git clone <repo-url>
cd missing-winners-claude-setup
```

### 2. Start the backend

```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --reload
```

The backend runs on **http://localhost:8000**.

> **Note:** On first start, loading the 521k-row Excel dataset takes ~25–30 seconds. The frontend polls the health endpoint automatically and will show a loading state until ready.

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on **http://localhost:5173**.

---

## Project Structure

```
missing-winners-claude-setup/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── pipeline.py          # Data cleaning & ABC classification
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── export.py            # Excel & PDF export logic
│   │   └── routers/
│   │       ├── gaps.py          # Gap detection endpoint
│   │       ├── dimensions.py    # Shops & departments lookup
│   │       ├── summary.py       # Dataset summary & KPIs
│   │       ├── upload.py        # Dataset upload & reload
│   │       └── health.py        # Health check
│   ├── tests/                   # Pytest test suite
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.tsx              # Root component & tab routing
│       ├── api.ts               # API client
│       ├── types.ts             # Shared TypeScript types
│       └── components/
│           ├── FilterPanel.tsx  # Shop/dept/ABC filter controls
│           ├── KPISection.tsx   # Summary KPI cards
│           ├── GapsTable.tsx    # Sortable, paginated results table
│           ├── CleaningSummary.tsx
│           └── FileUploader.tsx
├── data/
│   └── testdata1.xlsx           # Source dataset (not committed)
├── docs/
│   └── spec.md                  # Original product specification
├── .claude/                     # Claude Code commands & skills
└── CLAUDE.md                    # Validated project memory (overrides spec)
```

---

## How Gap Detection Works

1. **Data cleaning** — removes duplicates, flags returns (`QtySold < 0 OR SaleValue < 0`), drops admin rows (`DUMMY` articles, `GROUP INCOME/EXPENSE` department)
2. **ABC classification** — products ranked by total chain revenue; A = top 70%, B = next 20%, C = remainder
3. **Chain averages** — per-product average sale value across all shops that have *any* sales row for it
4. **Gap detection** — for a selected shop:
   - *Missing Winner*: Class A/B product with no sales row (or zero sales) in that shop, selling in ≥ N other shops
   - *Underperforming*: product with `ShopSaleValue < threshold × ChainAvgSaleValue`
5. **Ranking** — results sorted by `PotentialLostRevenue` descending

---

## Data Notes

Source file: `data/testdata1.xlsx`, sheet `testdata1` — 521,102 rows, 5 columns:

| Column | Notes |
|---|---|
| `ShopCode` | 74 active shops (codes 102–197; 6 codes only appear in admin rows and are excluded) |
| `DepartmentName` | 39 departments after cleaning |
| `ArticleCode` | 69,993 unique products after cleaning |
| `QtySold` | Can be negative (returns) |
| `SaleValue` | Can be negative (returns); currency unspecified — displayed with generic `¤` symbol |

---

## Running Tests

```bash
cd backend
pytest
```

---

## Uploading a New Dataset

Navigate to the **Upload New Dataset** tab in the UI and upload a replacement `.xlsx` file in the same column format. The backend will re-run the full cleaning and classification pipeline automatically.

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Backend readiness & dataset load status |
| `/dimensions/shops` | GET | List of available shop codes |
| `/dimensions/departments` | GET | List of available departments |
| `/summary` | GET | Dataset summary & ABC distribution |
| `/gaps` | GET | Run gap analysis with filters |
| `/export/excel` | GET | Download results as Excel |
| `/export/pdf` | GET | Download results as PDF |
| `/upload` | POST | Upload replacement dataset |

Interactive API docs available at **http://localhost:8000/docs** when the backend is running.
