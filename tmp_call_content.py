import json
import urllib.request
from pathlib import Path

url = 'http://127.0.0.1:8000/assembly/content'
payload = {
    'topic': 'فوائد الذكاء الاصطناعي للشركات',
    'business': 'شركة استشارات',
    'audience': 'رجال الأعمال السعوديين',
}
req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req, timeout=240) as r:
    data = json.loads(r.read().decode('utf-8'))
Path('content_result.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('ok')
