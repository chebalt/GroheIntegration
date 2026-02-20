# Test CSV Fixtures

Real product data batch (de/DE market) copied from `NEO/data_input/`.

**Locale:** `de_DE` (language=`de`, market=`DE`)

| File | Type | Records |
|---|---|---|
| `1_product_data.csv` | Products (core) | real data |
| `2_product_content.csv` | Product content (localized) | real data |
| `4_included_not_included.csv` | What's in the box | real data |
| `5_tag.csv` | Product-tag associations | real data |
| `6_warranty.csv` | Warranty info | real data |
| `7_spare_part.csv` | Spare parts | real data |
| `8_filter.csv` | Product filter attributes | real data |
| `9_product_data_specification.csv` | Specifications | real data |
| `10_flow_diagram.csv` | Flow diagrams | real data |
| `A_product_category_index.csv` | Category reference | real data |
| `B_product_feature_index.csv` | Feature reference | real data |
| `C_tag_index.csv` | Tag reference | real data |
| `D_award_index.csv` | Award reference | real data |
| `E_finish_index.csv` | Finish reference | real data |
| `F_filter_index.csv` | Where-to-buy filters | real data |
| `G_price_range_index.csv` | Price range symbols | real data |
| `H_product_data_specification_index.csv` | Spec index | real data |

## Updating fixtures

When the data format changes (new fields, renamed columns), update these files
from the latest `NEO/data_input/` batch:

```bash
cp ../../../data_input/*.csv .
```
