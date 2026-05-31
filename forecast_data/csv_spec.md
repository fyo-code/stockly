# Dataset Specification: Mobexpert Sales Data

Updated: 2026-05-10

## 1. Context

The dataset is transactional sales data from Mobexpert stores. Each row is a line item for one SKU within one customer order or invoice.

The current rebuild uses multi-store data. Older notes saying `MAGAZIN` is redundant are obsolete.

## 2. Core Columns

| Column | Meaning | Notes |
|---|---|---|
| `DATA COMANDA` | Sale/order date | Source of truth for timing. Use this date for training, scoring, and backtests, not the filename year. |
| `MAGAZIN` | Store legal/entity name | Source of truth for store identity. Normalize to canonical IDs such as `constanta`, `pipera`, `baneasa`. |
| `COD ARTICOL` | SKU code | Main product identifier. |
| `DENUMIRE ARTICOL` | Product name/description | Most detailed product text. Preserve raw and use for feature engineering, including dimensions and product type extraction. |
| `CATEGORIE` | Broad product category | Preserve raw; also normalize for model features. |
| `CLASA` | Product class | More detailed hierarchy than category. Preserve raw. |
| `SUBCLASA` | Product subclass | Available in many full files. Preserve raw; useful for fine-grained product grouping. |
| `GRUPA` / `GRUPA DIRECTII_LICITATII` | Product grouping | Available in some non-full files. Preserve raw as hierarchy metadata. |
| `RAION` | Mixed sales channel / area / department flag | Can mean `ONLINE`, `VANZARI DIRECTE`, `OUTLET`, or product-area labels such as `DECORATIUNI`. Preserve raw and derive channel flags. |
| `ID COMANDA` | Order/cart ID | Multiple lines can belong to the same order. |
| `ID FACTURA` | Invoice ID | Available in richer files. Use for transaction-line dedupe when present. |
| `ID CLIENT` | Client ID | Useful for optional basket/client aggregation; not required for first forecast model. |
| `FURNIZOR` | Supplier | Preserve when present. |
| `FURNIZOR EXT` | External supplier / factory | Preserve when present. |
| `ID FURNIZOR` | Supplier ID | Preserve when present. |
| `VALOARE FACTURATA` | Line value | Negative value means refund/return. |
| `CANTITATE FACTURATA` | Line quantity | Negative quantity means refund/return. |
| `Reducere %` | Discount percentage | Negative values mean discount off. Parse `discount_pct = abs(value)`, so `-0.2` means 20% discount and `-0.0` means no discount. |
| `CAMPANIE` | Campaign / product program / campaign-like label | Active on the sale row, but may mix true temporary campaigns with permanent/product-line labels. Preserve raw; derive cautiously. |
| `CAMPANIE BF` | Black Friday campaign label and timing | Authoritative Black Friday sale/campaign flag when present. Usually includes year and duration, e.g. `BF 2025 [03-23 NOIEMBRIE]`. |
| `AN` | Export/year field | Use only as metadata. Do not use it as sale timing if it conflicts with `DATA COMANDA`. |
| `CLIENT SPECIFIC`, `NR CLIENTI`, `NR COMANDA` | Extra order/client metadata | Preserve when present; lower priority for v2 forecasting. |

## 3. Store Normalization

Normalize `MAGAZIN` into stable store IDs:

| Raw `MAGAZIN` | Canonical store ID |
|---|---|
| `M & D RETAIL CONSTANTA SRL` | `constanta` |
| `M & D RETAIL BRASOV SRL` | `brasov` |
| `M & D RETAIL PIPERA SRL` | `pipera` |
| `M & D RETAIL PANTELIMON SRL` | `pantelemon` |
| `MOBEXPERT BANEASA SRL` | `baneasa` |
| `M & D RETAIL SIBIU SRL` | `sibiu` |
| `M & D RETAIL ORADEA SRL` | `oradea` |
| `M & D RETAIL PLOIESTI SRL` | `ploiesti` |
| `M & D RETAIL IASI SRL` | `iasi` |
| `M & D RETAIL TIM SRL` | `timisoara` |

Store type metadata:

- `hyperstore`: Constanta, Brasov, Pipera, Pantelemon, Baneasa, Sibiu
- `hybrid`: Iasi
- `smaller_store`: Oradea, Ploiesti, Timisoara

## 4. Business Logic And Processing Rules

### Rule 1: Sale Date

Use `DATA COMANDA` as the real sale date. Filename year and `AN` are export metadata only.

If a row is inside a 2025 file but `DATA COMANDA` is in 2024, the row belongs to 2024 for forecasting.

### Rule 2: Returns / Refunds

Negative `VALOARE FACTURATA` or negative `CANTITATE FACTURATA` signifies a refund/return.

For demand:

```text
gross_units = max(quantity, 0)
returned_units = abs(quantity) if quantity < 0 else 0
net_units = gross_units - returned_units
```

For revenue:

```text
gross_revenue = max(value, 0)
returned_revenue = abs(value) if value < 0 else 0
net_revenue = gross_revenue - returned_revenue
```

Keep returns as separate fields. Do not simply drop them, because return behavior is part of real demand quality.

### Rule 3: Non-Physical Rows

Filter service/non-product rows from product demand analysis when category/class/product text indicates:

- transport
- livrare
- montaj
- servicii
- pure discount/accounting rows with no physical SKU demand

Do not filter `OUTLET`, `ONLINE`, or real discounted product sales. They are valid demand rows.

### Rule 4: Campaign Fields

`CAMPANIE` is active on the sale row, but its meaning is mixed:

- Some values are temporary campaigns, e.g. Black Friday or named promotions.
- Some values are product/program labels, e.g. `FABRO` / `FABRICAT IN ROMANIA`.
- Some values encode product logic, e.g. `PATSPRING` means bed spring.

Modeling rule:

- Preserve raw `CAMPANIE`.
- Derive broad flags such as `is_bf_like_campaign`, `is_fabricat_in_romania`, `is_product_program_label`, and `campaign_name_raw`.
- Do not assume all `CAMPANIE` values are temporary promo timing.

`CAMPANIE BF` is the actual Black Friday campaign marker for the current data year when present. It can include the duration of that year's Black Friday campaign. Use it as the stronger BF signal than generic `CAMPANIE` values like `BF 2021 promotii`.

Important example:

- A row in a 2025 file can have `CAMPANIE = BF 2021 promotii`; this likely means the item was assigned to that older campaign/product label, not that the sale happened during Black Friday 2025.
- A row with `CAMPANIE BF = BF 2025 [03-23 NOIEMBRIE]` means the item was part of the actual Black Friday 2025 campaign window.

Optional feature signal rule:

- Missing optional columns or blank optional values must not be interpreted as "no signal".
- For campaign/BF, hierarchy, dimensions, supplier, and similar optional metadata, keep a signal source whenever possible:
  - `observed`: direct value exists in the row/file, e.g. `CAMPANIE BF`.
  - `inferred`: derived from reliable patterns such as known BF windows, calendar Black Friday timing, discount spikes, same-SKU behavior in richer stores, or repeated cross-store campaign patterns.
  - `unknown`: no reliable direct or inferred evidence.
- Lower-detail Baneasa/Pipera-style rows can use inferred signals, but the inferred source must remain visible to audits and model features.

### Rule 5: Discount

Parse `Reducere %` as absolute discount depth:

```text
discount_pct = abs(Reducere %)
```

Examples:

- `-0.2` -> 20% discount
- `-0.65` -> 65% discount
- `-0.0` -> no discount

### Rule 6: Product Text And Dimensions

`DENUMIRE ARTICOL` should be used for feature engineering.

Useful derived features include:

- product type keywords, e.g. saltea, pat, canapea, comoda, masa, scaun
- material/color/style tokens where reliable
- dimensions, e.g. `160x200`, `43.5x48.5x56.5cm`
- size bucket, e.g. single/double mattress, small/medium/large furniture
- variant families derived from repeated name prefixes

Keep raw text, extracted dimensions, and extracted tokens. The first v2 model can start with conservative parsed features; deeper text modeling can be added after the base scorecard works.

### Rule 7: Missing Values

Treat exact `#null`, empty strings, and impossible values as missing.

Do not globally treat numeric `0` as missing. Some zeros are meaningful:

- `Reducere % = -0.0` means no discount.
- zero quantity/value product rows often mean non-sale/accounting rows and should be filtered or flagged.
- zero sales in an explicitly generated weekly demand table means no observed sales, not missing data.

### Rule 8: Late-Arriving Data

The importer must support adding files later, such as a missing store/year export. Track source filename and use transaction-line deduplication so re-ingestion does not double-count old rows.
