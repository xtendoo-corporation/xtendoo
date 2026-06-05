import re
with open('/opt/odoo/auto/test_barcode_output4.log', 'r') as f:
    content = f.read()
    
# Find all tracebacks
matches = re.finditer(r'(Traceback \(most recent call last\):.*?)(?=\n\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} |$)', content, re.DOTALL)
for m in matches:
    print(m.group(1))
    print("-" * 40)
