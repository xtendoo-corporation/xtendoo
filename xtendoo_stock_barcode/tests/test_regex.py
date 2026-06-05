import re
rule_pattern = r'(10)([!"%-/0-9:-?A-Z_a-z]{0,20})'
separator_group = r'\x1d?'
barcode = '10LOT123\x1d305'
match = re.search('^' + rule_pattern + separator_group, barcode)
print('Match:', match)
if match:
    print('Groups:', match.groups())
    print('End:', match.end())
    print('Remaining:', barcode[match.end():])
