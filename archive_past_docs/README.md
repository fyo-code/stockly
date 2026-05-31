# Supply Chain Decision Engine — Quick Start

## First Time Setup

### Read before touching any code
1. `docs/PROJECT_CONTEXT.md` — business context, Mobexpert, the problem
2. `docs/MVP_SPEC.md` — exact features, calculations, data requirements
3. `docs/AGENT_RULES.md` — how to work on this project

### Backend
```bash
cd backend
pip install fastapi uvicorn pandas numpy sqlalchemy psycopg2-binary python-dotenv anthropic openpyxl
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Database
PostgreSQL required. Create database `supply_chain_dev`.
Connection string in `.env`: `DATABASE_URL=postgresql://user:password@localhost/supply_chain_dev`

---

## Build Order

Start here, work down:

- [ ] Generate synthetic data (`data_samples/generate.py`)
- [ ] Build data ingestion pipeline (`backend/data/ingest.py`)
- [ ] Build demand engine (`backend/engines/demand.py`)
- [ ] Build dead stock engine (`backend/engines/dead_stock.py`)
- [ ] Build supplier engine (`backend/engines/supplier.py`)
- [ ] Build scenario engine (`backend/engines/scenario.py`)
- [ ] Build API routes (`backend/api/routes.py`)
- [ ] Build frontend dashboard (`frontend/app/`)
- [ ] Add Claude API reasoning layer (`backend/agents/`)

---

## Data Files

Drop Pentaho CSV exports into `data_samples/` when they arrive.
Required format documented in `docs/MVP_SPEC.md` under "Synthetic Data Requirements".

---

## Key Constraint

Do NOT overlap with V's internal Mobexpert tool.
V's tool handles: reorder triggers, lead time calculation, basic demand from last year.
This product handles: everything V's tool cannot.
See `docs/PROJECT_CONTEXT.md` for full details.
