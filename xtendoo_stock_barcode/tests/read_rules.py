import re
rules = env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature').rule_ids
for r in rules:
    if r.type == 'lot' or r.gs1_content_type == 'lot' or r.name == 'Lot':
        print(f"LOT Rule: {r.name}, Pattern: {r.pattern}")
