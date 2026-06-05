import logging
env.user.company_id.nomenclature_id = env.ref("barcodes_gs1_nomenclature.default_gs1_nomenclature")
barcode = "]C1011529000000000010LOT123\x1D305"
nomenclature = env.user.company_id.nomenclature_id
res = nomenclature.parse_barcode(barcode)
print(f"RES1: {res}")
barcode2 = "011529000000000010LOT123\x1D305"
res2 = nomenclature.parse_barcode(barcode2)
print(f"RES2: {res2}")
