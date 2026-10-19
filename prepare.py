import csv, json, hashlib, base64
from pathlib import Path
from decimal import Decimal
from datetime import date
import openpyxl

root = Path(__file__).parent
source = root / 'base-porsche.xlsx'
sheet = openpyxl.load_workbook(source, data_only=True)['Sanitized']
values = list(sheet.values)
rows = []
for values_row in values[1:]:
    r = dict(zip(values[0], values_row))
    if r['sale_id'] is None:
        continue
    raw_date = str(r['SaleDateSanitized'])
    try:
        sale_date = date.fromisoformat(raw_date).isoformat()
    except ValueError:
        sale_date = None
    rows.append(dict(id=int(r['sale_id']), date=sale_date,
        model=str(r['PorscheModelSanitized']).strip(),
        year=int(r['ModelYearSanitized']),
        cents=int(Decimal(str(r['SalesPriceSanitized']))*100),
        payment=str(r['PayMethodSanitized']).strip(),
        city=str(r['CitySanitized']).strip(), state=str(r['StateSanitized']).strip(),
        status=str(r['DeliveryStatusSanitized']).strip()))
assert len(rows) == 100 and len({r['id'] for r in rows}) == 100
assert all(r['cents'] > 0 and 1900 < r['year'] < 2100 for r in rows)
(root/'data.json').write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
with (root/'base-sanitizada.csv').open('w',encoding='utf-8-sig',newline='') as f:
    out=csv.writer(f,delimiter=';')
    out.writerow(['id','data_venda','modelo','ano_modelo','preco_usd','pagamento','cidade','estado','status'])
    for r in rows:
        out.writerow([r['id'],r['date'] or '',r['model'],r['year'],str(Decimal(r['cents'])/100),r['payment'],r['city'],r['state'],r['status']])
active=[r for r in rows if r['status']!='Cancelled']
audit=dict(records=len(rows),invalid_dates=sum(r['date'] is None for r in rows),
    total_cents=sum(r['cents'] for r in rows),active_records=len(active),
    active_cents=sum(r['cents'] for r in active),sha256=hashlib.sha256(source.read_bytes()).hexdigest())
(root/'audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
template=(root/'dashboard.template.html').read_text(encoding='utf-8')
for token, filename, mime in [('__HERO__','porsche-header.webp','image/webp'),('__LOGO__','porsche-wordmark.svg','image/svg+xml')]:
    template=template.replace(token,'data:'+mime+';base64,'+base64.b64encode((root/'assets'/filename).read_bytes()).decode())
(root/'index.html').write_text(template.replace('__DATA__',json.dumps(rows,ensure_ascii=False)),encoding='utf-8')
print(json.dumps(audit,indent=2))
