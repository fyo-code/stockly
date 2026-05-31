# Forecast V2 Sales Export Completeness Checklist

Updated: 2026-05-29.

Purpose: track store/year sales exports while keeping each database export small enough to avoid cube crashes.

## Export Split

Use two exports per store/year when needed:

- `P1`: supplier/product-group/order-context columns.
- `P2`: remaining missing detail/status/campaign/date/lifecycle columns.
- Put `COD ARTICOL`, `MAGAZIN`, and `DATA` in both `P1` and `P2` when possible. They are common join/audit columns and are not repeated inside every missing list below.
- Apply these filters where relevant: `AN`, `GRUPA DIRECTII_LICITATII`, `CLIENT SPECIFIC`.
- Always include measures: `REDUCERE`, `CANTITATE FACTURATA`, `VALOARE FACTURATA`.

`P1` standard columns:

`COD ARTICOL`, `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `MAGAZIN`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`

`P2` is the rest of the missing columns for that store/year after removing `P1`, `COD ARTICOL`, `MAGAZIN`, and filter-only fields.

## Full Desired Column Universe

`ACTIV`, `ACTIV ONLINE`, `AN`, `CAMPANIE`, `CAMPANIE BF`, `CAMPANIE SELECTATA`, `CATEGORIE`, `CLASA`, `COD ARTICOL`, `DATA`, `DATA COMANDA`, `DENUMIRE ARTICOL`, `DIMENSIUNI`, `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID CLIENT`, `ID COMANDA`, `ID FACTURA`, `ID FURNIZOR`, `MAGAZIN`, `NECESITA MONTAJ`, `NR COMANDA`, `OUTLET`, `RAION`, `STIL`, `SUBCLASA`, `SUBSTIL`, `VECHIME IN COLECTIE`

## Store-Year Checklist

### Baneasa

- [ ] 2022 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2022 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `CATEGORIE`, `CLASA`, `DENUMIRE ARTICOL`, `DIMENSIUNI`, `ID CLIENT`, `ID COMANDA`, `ID FACTURA`, `OUTLET`, `RAION`, `SUBCLASA`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `new_baneasa_22.csv`.

- [ ] 2023 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2023 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `CATEGORIE`, `CLASA`, `DENUMIRE ARTICOL`, `DIMENSIUNI`, `ID CLIENT`, `ID COMANDA`, `ID FACTURA`, `OUTLET`, `RAION`, `SUBCLASA`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `new_baneasa_23.csv`.

- [ ] 2024 P1
  - Export columns: `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2024 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DIMENSIUNI`, `ID CLIENT`, `ID FACTURA`, `OUTLET`, `RAION`, `SUBCLASA`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `bane 24.csv`, `new_baneasa_24.csv`.

- [ ] 2025 P1
  - Export columns: `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2025 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DIMENSIUNI`, `ID CLIENT`, `ID FACTURA`, `OUTLET`, `RAION`, `SUBCLASA`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `bane 25.csv`, `new_baneasa_25.csv`.

### Brasov

- [ ] 2022 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2022 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `brasov 22 full.csv`.

- [ ] 2023 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2023 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `brasov 23 full.csv`.

- [ ] 2024 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2024 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `brasov 24 full.csv`.

- [ ] 2025 P1
  - Export columns: `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2025 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE`, `CAMPANIE BF`, `CAMPANIE SELECTATA`, `CLASA`, `DATA`, `DIMENSIUNI`, `ID FACTURA`, `OUTLET`, `RAION`, `SUBCLASA`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `bras 25.csv`.
  - Related columns already present: `ID FURNIZOR` related present: `FURNIZOR`, `FURNIZOR EXT`.

### Constanta

- [ ] 2022 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2022 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `cons 22 full.csv`.

- [ ] 2023 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2023 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `cons 23 full.csv`.

- [ ] 2024 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2024 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `cons 24 full.csv`.

- [ ] 2025 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2025 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `cons 25 full.csv`.

### Iasi

- [ ] 2022 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2022 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `iasi 22 full.csv`.

- [ ] 2023 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2023 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `iasi 23 full.csv`.

- [ ] 2024 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2024 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `iasi 24 full.csv`.

- [ ] 2025 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2025 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `iasi 25 full.csv`.

### Militari

- [ ] 2022 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2022 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `ID CLIENT`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `mil 22.csv`.
  - Related columns already present: `FURNIZOR` related present: `ID FURNIZOR`; `FURNIZOR EXT` related present: `ID FURNIZOR`; `GRUPA` related present: `GRUPA_PRODUSE`; `GRUPA MEDIU VANZARE` related present: `GRUPA_PRODUSE`.

- [ ] 2023 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2023 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `ID CLIENT`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `mil 23.csv`.
  - Related columns already present: `FURNIZOR` related present: `ID FURNIZOR`; `FURNIZOR EXT` related present: `ID FURNIZOR`; `GRUPA` related present: `GRUPA_PRODUSE`; `GRUPA MEDIU VANZARE` related present: `GRUPA_PRODUSE`.

- [ ] 2024 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2024 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `ID CLIENT`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `mil 24.csv`.
  - Related columns already present: `FURNIZOR` related present: `ID FURNIZOR`; `FURNIZOR EXT` related present: `ID FURNIZOR`; `GRUPA` related present: `GRUPA_PRODUSE`; `GRUPA MEDIU VANZARE` related present: `GRUPA_PRODUSE`.

- [ ] 2025 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2025 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `ID CLIENT`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `mil 25 mdetailed.csv`.
  - Related columns already present: `FURNIZOR` related present: `ID FURNIZOR`; `FURNIZOR EXT` related present: `ID FURNIZOR`; `GRUPA` related present: `GRUPA_PRODUSE`; `GRUPA MEDIU VANZARE` related present: `GRUPA_PRODUSE`.

### Oradea

- [ ] 2022 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2022 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `oradea 22 23 full.csv`.

- [ ] 2023 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2023 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `oradea 22 23 full.csv`.

- [ ] 2024 P1
  - Export columns: `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2024 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE`, `CAMPANIE BF`, `CAMPANIE SELECTATA`, `CLASA`, `DATA`, `DENUMIRE ARTICOL`, `DIMENSIUNI`, `OUTLET`, `SUBCLASA`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `oradea_24.csv`.

- [ ] 2025 P1
  - Export columns: `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2025 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE`, `CAMPANIE BF`, `CAMPANIE SELECTATA`, `CLASA`, `DATA`, `DENUMIRE ARTICOL`, `DIMENSIUNI`, `OUTLET`, `SUBCLASA`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `oradea_25.csv`.

### Pantelemon

- [ ] 2022 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2022 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `pante 22 full.csv`.

- [ ] 2023 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2023 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `pante 23 full.csv`.

- [ ] 2024 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2024 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `pante 24 full.csv`.

- [ ] 2025 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2025 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `pante 25 full.csv`.

### Pipera

- [ ] 2022 P1
  - Export columns: `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2022 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `pip 22 more detailed.csv`, `pip 22.csv`.
  - Related columns already present: `STIL` related present: `SUBSTIL`.

- [ ] 2023 P1
  - Export columns: `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2023 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DIMENSIUNI`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `23 pip more detail+date.csv`, `pip 23.csv`.
  - Related columns already present: `STIL` related present: `SUBSTIL`.

- [ ] 2024 P1
  - Export columns: `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2024 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DIMENSIUNI`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `24 pip more detail.csv`, `pip 24.csv`.
  - Related columns already present: `STIL` related present: `SUBSTIL`.

- [ ] 2025 P1
  - Export columns: `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2025 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DIMENSIUNI`, `RAION`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `25 pip more detail.csv`, `pipera_25.csv`.
  - Related columns already present: `GRUPA MEDIU VANZARE` related present: `GRUPA`; `GRUPA_PRODUSE` related present: `GRUPA`; `STIL` related present: `SUBSTIL`.

### Ploiesti

- [ ] 2022 P1
  - Export columns: `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2022 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE`, `CAMPANIE BF`, `CAMPANIE SELECTATA`, `DATA`, `DENUMIRE ARTICOL`, `DIMENSIUNI`, `OUTLET`, `RAION`, `SUBCLASA`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `ploiesti_22_23.csv`.

- [ ] 2023 P1
  - Export columns: `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2023 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE`, `CAMPANIE BF`, `CAMPANIE SELECTATA`, `DATA`, `DENUMIRE ARTICOL`, `DIMENSIUNI`, `OUTLET`, `RAION`, `SUBCLASA`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `ploiesti_22_23.csv`.

- [ ] 2025 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2025 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `ploiesti 25 full.csv`.

### Sibiu

- [ ] 2022 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2022 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `sibiu 22 full.csv`.

- [ ] 2023 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2023 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `sibiu 23 full.csv`.

- [ ] 2024 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2024 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `sib 24 full.csv`.

- [ ] 2025 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2025 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `sib 25 full.csv`.

### Timisoara

- [ ] 2022 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2022 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `tim 22-25 full.csv`.

- [ ] 2023 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2023 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `tim 22-25 full.csv`.

- [ ] 2024 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2024 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `tim 22-25 full.csv`.

- [ ] 2025 P1
  - Export columns: `FURNIZOR`, `FURNIZOR EXT`, `GRUPA`, `GRUPA MEDIU VANZARE`, `GRUPA_PRODUSE`, `ID FURNIZOR`, `NECESITA MONTAJ`, `NR COMANDA`, `STIL`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
- [ ] 2025 P2
  - Export columns: `ACTIV`, `ACTIV ONLINE`, `CAMPANIE SELECTATA`, `DATA`, `DIMENSIUNI`, `OUTLET`, `SUBSTIL`, `VECHIME IN COLECTIE`.
  - Also include in this part: `COD ARTICOL`, `MAGAZIN`, `DATA`.
  - Existing file(s): `tim 22-25 full.csv`.

## Missing Store/Year Watchlist

- [ ] Ploiesti 2024 P1: no current sales CSV found. Export a full detailed 2024 file using the same P1 split.
- [ ] Ploiesti 2024 P2: no current sales CSV found. Export a full detailed 2024 file using the same P2 split.
- [ ] Craiova P1/P2: no current sales CSV found. Export available years if Craiova had sales during 2022-2025.

## Practical Export Priority

- Highest impact first: Baneasa 2022-2025, Pipera 2022-2025, Militari 2022-2025, Ploiesti 2024, and any Craiova sales history.
- Use physical-product rows only.
- Services can be exported separately later if they share order/invoice IDs, but they should not be mixed into the product demand target.
