# Forecast V2 Data Dictionary And Business Rules

Updated: 2026-05-31.

Purpose: living source of truth for Forecast V2 data meanings, business semantics, column interpretations, export rules, and modeling-safe assumptions. A new chat should be able to read this file and understand what the sales/stock/campaign data means without guessing.

This file is the business-semantics reference. `forecast_data/csv_spec.md` remains the older technical ingestion spec, but this file should win when there is a conflict in business meaning.

## Related Files

- `forecast_data/csv_spec.md`: older technical CSV ingestion specification.
- `active_docs/FORECAST_V2_SALES_EXPORT_COMPLETENESS_CHECKLIST.md`: sales export checklist by store/year, including P1/P2 export splits.
- `active_docs/FORECAST_V2_CURRENT_HANDOFF.md`: current model status and next-step handoff.
- `active_docs/ITER5AA_V2_PHASE8G_BUSINESS_SEMANTICS_AUDIT.md`: business-semantics audit that corrected stock interpretation.
- `active_docs/ITER5AB_V2_PHASE8G_M_HYGIENE_SEMANTICS.md`: discount/returns/stock-language cleanup report.

## Current Forecast Target

- Forecast V2 focuses on physical product demand, especially high-revenue Top 1000 SKUs.
- The old engine is irrelevant for current decisions.
- Delivery, installation, packaging, transport, and other service rows should not be mixed into the main physical-product demand target.
- Service rows can become context later if they share `ID COMANDA` or `ID FACTURA` with physical product rows. For example, installation or delivery services may help identify custom, bulky, delayed, or high-friction orders, but they are not demand units for the product forecast.
- The current demand target is gross positive product units. Returns are not the same thing as no demand.

## Transaction Grain

Each sales CSV row is normally one line item for one SKU inside one customer order/invoice.

Important interpretation:

- `COD ARTICOL` is the SKU/product code.
- A single customer order can contain multiple SKU rows.
- `ID COMANDA` groups all SKU rows bought together in one purchase/order/cart.
- `ID FACTURA` groups rows on the same invoice/check when available.
- If `CANTITATE FACTURATA` is greater than `1`, that row represents multiple units of the same SKU in the same transaction line.
- Approximate unit price can be derived as `VALOARE FACTURATA / CANTITATE FACTURATA` when quantity is positive and non-zero.

Modeling implication:

- Weekly SKU demand should aggregate positive physical-product units.
- `ID COMANDA` should be preserved for future basket/order features, such as products bought together, bulky multi-line orders, high-value orders, or service-attached orders.
- Row-level unit price, price bucket, and bulk quantity behavior should be treated as useful pricing/order-context signals, not only as aggregated revenue totals.

## Quantity, Revenue, Discounts, Returns

### `CANTITATE FACTURATA`

Meaning: quantity sold or returned for the SKU line.

Rules:

- Positive quantity means sold units.
- Negative quantity means returned units.
- Zero quantity should be flagged because it may represent accounting/no-sale rows rather than true demand.

Demand calculation:

```text
gross_units = max(quantity, 0)
returned_units = abs(quantity) if quantity < 0 else 0
net_units = gross_units - returned_units
```

Official demand target:

- Use gross positive units for demand.
- Keep returns separately as diagnostics/context.

### `VALOARE FACTURATA`

Meaning: final line value paid by the customer.

Important caveat:

- `VALOARE FACTURATA` is not always negative on returns, so return detection should use `CANTITATE FACTURATA` sign first.
- Use value as revenue/price context, but do not rely only on value sign to identify returns.
- Confirmed by Fyo on 2026-05-31: this is the final amount the customer paid to the store for the line. It includes discounts and VAT.

Revenue calculations should be explicit and auditable:

```text
gross_revenue = max(value, 0)
returned_revenue = value tied to returned rows when available/reliable
net_revenue = gross_revenue - returned_revenue
```

Payment caveat:

- The sales CSVs provided do not expose first/second payment split details. For custom orders, deposits vs final payments are not separately reflected in the current raw CSV exports; treat the row as the total recorded payment/value for that sale line.

### `REDUCERE` / `Reducere %`

Meaning: discount on the SKU sale row.

Rules:

- Keep it as a real demand signal.
- Sanitize impossible/non-finite values such as `Infinity`, `-Infinity`, malformed values, and impossible percentage ranges.
- Do not blindly trust extreme values until audited.
- `-0.0` / `0` means no discount.

Modeling implication:

- Discount depth can separate normal demand from campaign/promotion-driven demand.
- Historical discount behavior is one of the strongest current-data levers for high-revenue SKUs.

## Date Semantics

### `DATA COMANDA`

Meaning: the date when the actual order was placed by the client.

This is the preferred demand timing field because it represents the demand decision moment.

Examples:

- A customer orders a custom couch today. `DATA COMANDA` is today.
- The couch may be produced and delivered much later.

Rules:

- Use `DATA COMANDA` as the canonical sale/demand date when present.
- Filename year and `AN` must not override the actual parsed order date.
- If a row appears in a 2025 file but `DATA COMANDA` is in 2024, the demand belongs to 2024 for backtesting.

### `DATA`

Meaning: invoice/check date. Usually this is when the invoice was generated, often when the product is delivered to the client and/or fully paid.

This is not always the same as the demand decision date.

Examples:

- Custom order: client orders on `DATA COMANDA`, factory produces for one or two months, then `DATA` appears when delivered/finally invoiced.
- Normal order: gap between `DATA COMANDA` and `DATA` may be only a few days, a week, or around ten days.

Rules:

- Use `DATA` as fallback only when `DATA COMANDA` is missing/null.
- Preserve `sale_date_source` so fallback rows are auditable.
- Preserve `invoice_lag_days = DATA - DATA COMANDA` when both dates exist.
- Large lag is a useful signal for custom, made-to-order, delivery-friction, bulky, or delayed-fulfillment behavior.

Important current-data opportunity:

- Forecast V2 already stores `DATA`, `DATA COMANDA`, `used_invoice_date_fallback`, and `invoice_lag_days`.
- The underused part is not ingestion. The underused part is modeling: invoice lag and fallback-date behavior have not yet been fully used as product-route features.

### `AN`

Meaning: year/export/filter metadata.

Rules:

- Useful for database export filters and audit.
- Not the modeling date.
- `DATA COMANDA` and `DATA` are enough for timing, but `AN` is still useful as a sanity check when exports are split by year.

## Store, Channel, Outlet, And Area

### `MAGAZIN`

Meaning: store/entity identifier.

Rules:

- Include it whenever possible, even if the filename already says the store/year.
- Explicit `MAGAZIN` makes ingestion safer, prevents accidental file naming mistakes, and helps merge P1/P2 exports.

### `GRUPA MEDIU VANZARE`

Meaning: sale medium/channel/context.

Known values:

- `OFFLINE`: bought physically in the normal store.
- `ONLINE`: bought from the site.
- `OUTLET`: bought physically in the outlet area.

Important business meaning:

- Outlet is physical retail, but commercially different from normal store sales.
- Bigger hyperstores often have outlet areas next to them, so one store umbrella can contain normal offline and outlet demand.

Modeling implication:

- This should become a major route/context feature.
- Normal store, online, and outlet demand should not be blindly blended if their behavior differs.

### `RAION`

Meaning: product area/department/gamma where the SKU belongs or where the SKU sale is attributed.

Rules:

- It is not the checkout location.
- Usually it means the physical place/department of the store associated with the product.
- Exception: `ONLINE` in `RAION` clearly means online sale context.
- Preserve raw values and compare with `GRUPA MEDIU VANZARE` for consistency.

Modeling implication:

- Useful for store layout/product-area behavior.
- Should be treated as product/store context, not just channel.

### `OUTLET`

Meaning: outlet-related flag/dimension when present.

Rule:

- Keep as raw context and reconcile with `GRUPA MEDIU VANZARE = OUTLET`.

## Stock And Availability Semantics

Critical business correction:

- Stock is not sellability for Mobexpert.
- A SKU can be sold even if it is not currently in store stock, supplier stock, or warehouse stock.
- As long as the SKU is active/orderable/listed, it can be sold.

Rules:

- Do not use stock as a hard availability gate.
- Store/supplier/warehouse stock is fulfillment context, not a can-sell indicator.
- Use terms like `stock_position` or `fulfillment_context`, not "availability" or "sellability", unless the signal is truly active/orderable/listed status.

Modeling implication:

- Stock can still matter for delivery speed, outlet clearance, display context, and fulfillment friction.
- But stock absence must not be interpreted as "zero possible demand".

## Product Listing / Active Status

### `ACTIV`

Meaning: whether the SKU is active.

Known values:

- `D`: yes / `Da` / active.
- `Nu`: no / not active.

High-value unresolved point:

- Need to confirm whether this is current status at export time or status as of the sale row/date.

Modeling-safe rule:

- If `ACTIV` is historical-as-of sale date, it can be used directly for backtests and zero-sales interpretation.
- If `ACTIV` is only current export-time status, it is dangerous for historical backtests because it leaks future/current state into past windows. In that case it should be used mainly for current forecast filtering/diagnostics, not historical training labels.

### `ACTIV ONLINE`

Meaning: whether the SKU exists/is active on the website.

Known values:

- `Da`: active/available online.
- `Nu`: not active/not available online.

Business meaning:

- Some SKUs are store-only.
- Some SKUs may not yet be sold or visible online.

Modeling implication:

- This is likely one of the most important missing sellability/listing signals, especially for online/offline route separation.
- Same leakage caution applies: confirm whether it is historical-as-of row date or current status at export time.

## Product Descriptive Fields

These columns describe what the product is. They should be preserved raw, normalized carefully, and used for product similarity/transfer learning. Do not impose generic outside taxonomy too aggressively; learn Mobexpert's taxonomy from the data.

### `CATEGORIE`

Meaning: broad product category/group, a bird-view product direction.

Examples:

- `MOBILIER OFFICE`
- `CANAPELE SI FOTOLII`
- `MOBILIER DE CASA - BUCATARII`

Important interpretation:

- This is Mobexpert's internal categorization, not a universal retail taxonomy.
- Categories can be business-specific and should be interpreted from observed values.
- A home couch is not necessarily under a broad "home" bucket if Mobexpert categorizes it under `CANAPELE SI FOTOLII`.

### `CLASA`

Meaning: more specific product class than `CATEGORIE`.

Example:

- `CATEGORIE = MOBILIER OFFICE`
- `CLASA = MOBILIER DE BIROU OPERATIONAL`

Use:

- Strong product-descriptive feature.
- Useful for hierarchy rollups and transfer learning between similar SKUs.

### `SUBCLASA`

Meaning: finer hierarchy below `CLASA`, when present.

Use:

- High-value grouping for sparse SKUs and product-family behavior.

### `GRUPA` / `GRUPA_PRODUSE`

Meaning: additional product grouping dimensions.

Use:

- Preserve raw.
- Compare with `CATEGORIE`, `CLASA`, and `SUBCLASA`.
- Useful when some stores/years have incomplete hierarchy columns.

### `STIL` And `SUBSTIL`

Meaning: internal style/gamma/type attributes for furniture/decor products.

Current understanding:

- `STIL` and `SUBSTIL` are similar product style descriptors.
- User is not yet sure why both exist or how exactly they differ.
- Values may be internal style/gamma names rather than obvious external categories.

Use:

- Product-descriptive features.
- Useful for similarity, product families, and style-specific demand patterns.
- Preserve both separately until their relationship is audited.

### `DENUMIRE ARTICOL`

Meaning: detailed product name/description for the SKU.

Business meaning:

- Often contains the exact product type, dimensions, material, color, finish, collection/family, or other identifying text.
- Dimensions can appear here, but `DIMENSIUNI` is preferred when available for size-specific features.
- Even when dimensions are separate, `DENUMIRE ARTICOL` remains valuable for identifying product type/material/family and repeated naming patterns.

Current V2 usage:

- Not ignored.
- V2 ingestion stores product name.
- V2 extracts dimensions from the name when `DIMENSIUNI` is missing.
- Hierarchy normalization can infer category from product name in some cases.

Underused opportunity:

- The engine has not yet deeply used `DENUMIRE ARTICOL` for material/type/style tokenization, product-family clustering, top-mover analysis, SKU forecastability analysis, or product-name similarity transfer.
- User's suspicion here is mostly correct: the field is captured, but underutilized as a modeling signal.

Future feature ideas:

- Product type tokens: `saltea`, `pat`, `canapea`, `fotoliu`, `masa`, `scaun`, `comoda`, etc.
- Material/finish/color tokens when reliable.
- Collection/family prefixes.
- Dimension/size bucket fallback.
- Name-similarity groups for new or sparse SKUs.
- Analysis of which product-name families are easier/harder to forecast.

### `DIMENSIUNI`

Meaning: physical dimensions/sizes of the product.

Use:

- Prefer this over dimensions embedded in `DENUMIRE ARTICOL`.
- Can drive size buckets, bulky-item behavior, installation likelihood, delivery lag, and product similarity.

### `NECESITA MONTAJ`

Meaning: whether the product needs installation/assembly.

Examples:

- Bed may need installation.
- Plate/decoration item does not.

Current caveat:

- Exact short codes such as `NMU` and `NMD` are not yet confirmed.

Use:

- Product/friction feature.
- Likely useful for delivery lag, custom/order behavior, service attachment, and forecastability.

### `VECHIME IN COLECTIE`

Meaning: age of the SKU/item in the collection.

Business meaning:

- Likely approximates how old the item/SKU is since it started being produced/sold.
- Good lifecycle/freshness signal.

Modeling-safe rule:

- If this is historical-as-of the sale row, it is high-value for backtests.
- If it is current/snapshot only, it cannot be used directly as a historical feature without leakage.

Use:

- Newness/maturity/decline features.
- Cold-start behavior.
- Lifecycle phase routing.

## Supplier And Product Source

Useful fields:

- `FURNIZOR`
- `FURNIZOR EXT`
- `ID FURNIZOR`
- `TIP FURNIZOR` if available later

Use:

- Supplier/product-source context.
- Helpful for lead-time, product family, replenishment, and supplier-specific sales behavior.
- Preserve raw and normalized versions.

## Campaigns

### `CAMPANIE`

Meaning: campaign / product program / campaign-like label.

Caution:

- It may mix true temporary campaigns with product/program labels.
- Do not assume every value is a real promo timing event.

Rule:

- Preserve raw.
- Derive cautious flags only after auditing values.

### `CAMPANIE BF`

Meaning: stronger Black Friday campaign/timing signal when present.

Use:

- Can include Black Friday year and duration, such as a campaign name with dates.
- Better BF signal than generic `CAMPANIE` when populated.

### `CAMPANIE SELECTATA` / `COD IN CAMPANIE`

Meaning: campaign-selection/membership context when available.

Use:

- Potentially helps distinguish actual campaign assignment from generic product labels.
- Preserve raw and audit coverage.

Modeling rule:

- Campaign features must be guarded. Previous broad BF/global lifts improved some aggregate score but hurt stability.
- Future campaign membership and planned discounts remain a higher-ceiling data need.

## Current Preferred Sales Export Columns

The current checklist requests these displayed/safety columns when available:

`ACTIV`, `ACTIV ONLINE`, `AN`, `CAMPANIE`, `CAMPANIE BF`, `CAMPANIE SELECTATA`, `CATEGORIE`, `CLASA`, `COD ARTICOL`, `DATA`, `DATA COMANDA`, `DENUMIRE ARTICOL`, `DIMENSIUNI`, `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID CLIENT`, `ID COMANDA`, `ID FACTURA`, `ID FURNIZOR`, `MAGAZIN`, `NECESITA MONTAJ`, `NR COMANDA`, `OUTLET`, `RAION`, `STIL`, `SUBCLASA`, `SUBSTIL`, `VECHIME IN COLECTIE`.

Always also include measures:

`REDUCERE`, `CANTITATE FACTURATA`, `VALOARE FACTURATA`.

Filter context:

- `CLIENT SPECIFIC` can be applied in filters and does not need to be displayed unless useful.
- `GRUPA DIRECTII_LICITATII` can be applied in filters and does not need to be displayed unless useful.
- `AN` can be used as a filter. It is still useful as a displayed audit column if the database can handle it, but not required for modeling timing if `DATA` and `DATA COMANDA` are exported.

P1/P2 export split:

- Because the cube can crash with too many columns, store/year exports may be split into P1 and P2.
- Include `COD ARTICOL`, `MAGAZIN`, and `DATA` in both P1 and P2 to make merging safer.
- Measures should be included as needed to preserve row identity and validate joins.

Standard P1 columns:

`COD ARTICOL`, `DATA`, `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `MAGAZIN`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.

Standard P2 columns:

The remaining needed columns for that store/year after removing the P1 fields and repeated safety columns. Common P2 fields include:

`ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `CATEGORIE`, `CLASA`, `DATA COMANDA`, `DENUMIRE ARTICOL`, `DIMENSIUNI`, `ID CLIENT`, `ID COMANDA`, `ID FACTURA`, `OUTLET`, `RAION`, `SUBCLASA`, `SUBSTIL`, `VECHIME IN COLECTIE`.

## Honest Underutilization Assessment

Short answer: the user is mostly right, with nuance.

The engine did not completely ignore the richer fields:

- `DENUMIRE ARTICOL` is stored in V2 raw rows.
- Dimensions are extracted from `DENUMIRE ARTICOL` when `DIMENSIUNI` is missing.
- Product name can be used by the hierarchy normalizer to infer category in limited cases.
- `DATA` is already used as a fallback when `DATA COMANDA` is missing.
- V2 stores `sale_date_source`, `used_invoice_date_fallback`, and `invoice_lag_days`.
- V2 has rolling average unit price features derived from revenue/units.

But these fields are still underutilized in the official forecasting logic:

- `DENUMIRE ARTICOL`: captured, but not deeply tokenized into material/type/family/style features, not used enough for product similarity, and not yet used for forecastability or top-mover pattern analysis.
- `DATA` vs `DATA COMANDA`: fallback exists, but invoice lag and custom/order-delay behavior are not yet treated as serious product-route signals.
- `GRUPA MEDIU VANZARE`: newly requested and not yet a core route feature. This is likely a major missing channel split between normal offline, online, and outlet demand.
- `ACTIV` / `ACTIV ONLINE`: high-value listing/sellability fields, but not yet usable until exported and clarified as historical-as-of or current snapshot.
- `VECHIME IN COLECTIE`: known valuable lifecycle signal, but current availability has been mostly snapshot-like, so it has not been safe for historical backtests.
- `NECESITA MONTAJ`: useful friction/custom/bulky-product signal, not yet implemented because code meanings are not confirmed and full coverage is missing.
- `STIL` / `SUBSTIL` / richer taxonomy: useful descriptive features, but not yet fully exploited for transfer learning.
- `ID COMANDA`: preserved as order context, but not yet used enough for basket/co-purchase, service-attached order, multi-SKU order, or high-value order features.
- Row-level unit price from `VALOARE FACTURATA / CANTITATE FACTURATA`: approximate price is available, but the model mostly uses aggregated average unit price rather than richer price buckets, quantity-per-line behavior, and discount-adjusted price history.

Practical conclusion:

- The next real improvement wave should not just add random features.
- It should ingest the richer store/year exports, audit coverage/meaning, then build route/product/lifecycle features around these exact underused signals.

## Recommended Analyses After New Exports Arrive

Run these before promoting new model changes:

- Product text audit: coverage and top tokens from `DENUMIRE ARTICOL`, material/type/collection extraction, and forecastability by product-name family.
- Channel route audit: compare `GRUPA MEDIU VANZARE`, `RAION`, `OUTLET`, and store to split normal offline vs online vs outlet behavior.
- Active/listing audit: coverage and behavior of `ACTIV` and `ACTIV ONLINE`; confirm whether fields are historical or current-snapshot.
- Date-lag audit: distribution of `DATA - DATA COMANDA`, by product type/category/store/channel, and relation to forecast errors.
- Lifecycle audit: coverage and predictive value of `VECHIME IN COLECTIE`, if historical-safe.
- Montage/friction audit: decode `NECESITA MONTAJ`, then test against invoice lag, returns, service rows, and forecastability.
- Order/basket audit: use `ID COMANDA` to identify multi-line orders, service-attached orders, and co-purchase patterns.
- Discount/price audit: derive row-level unit price and discount-adjusted price history; detect impossible or extreme values.

## Open Questions For Fyo

1. Is `ACTIV` historical as of the sale row/date, or is it current active status at the time of export?
2. Is `ACTIV ONLINE` historical as of the sale row/date, or current website status at export time?
3. Is `VECHIME IN COLECTIE` historical as of the sale row/date, or current age at export time?
4. What exactly do `NECESITA MONTAJ` values like `NMU`, `NMD`, and any other codes mean?
5. What is the practical difference between `STIL` and `SUBSTIL`, if anyone in the business knows?
6. Can the same SKU have different `GRUPA MEDIU VANZARE` values across transactions, or is it a fixed SKU attribute? Current assumption: it is transaction/channel context.
7. Should `RAION = ONLINE` always match `GRUPA MEDIU VANZARE = ONLINE`, or can they disagree?
8. Does `DATA` always mean invoice/delivery/final payment, or can an invoice be generated before actual delivery?
9. Are `ID COMANDA` and `ID FACTURA` globally unique across stores/years, or only unique inside a store/year/entity?
