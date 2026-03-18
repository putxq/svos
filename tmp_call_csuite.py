import json
import urllib.request
from pathlib import Path

url = 'http://127.0.0.1:8000/csuite/run_all'
payload = {
  'business_context': 'شركة تقنية ناشئة في الرياض',
  'current_operations': 'يدوية جزئياً',
  'bottlenecks': ['بطء التوصيل', 'ضعف التسويق'],
  'current_tech': 'Excel وواتساب فقط',
  'tech_goals': ['أتمتة العمليات', 'تطبيق جوال'],
  'business_type': 'تجارة إلكترونية'
}
req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type':'application/json'})
with urllib.request.urlopen(req, timeout=480) as r:
    data = json.loads(r.read().decode('utf-8'))
Path('csuite_result.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('ok')
