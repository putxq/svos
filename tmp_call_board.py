import json
import time
import urllib.request
from urllib.error import HTTPError, URLError
from pathlib import Path

url = 'http://127.0.0.1:8000/board/decide'
payload = {
    'request': 'اريد محتوى ومبيعات لشركة تقنية',
    'context': {
        'topic': 'الذكاء الاصطناعي',
        'business_type': 'تقنية',
        'audience': 'مدراء',
        'lead_name': 'شركة الافق',
        'pain_points': ['زيادة المبيعات'],
    },
}
body = json.dumps(payload).encode('utf-8')

last_err = None
for i in range(6):
    try:
        req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=420) as r:
            data = json.loads(r.read().decode('utf-8'))
        Path('board_result.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print('ok')
        raise SystemExit(0)
    except (HTTPError, URLError, TimeoutError) as e:
        last_err = str(e)
        time.sleep(8)

print('error', last_err)
raise SystemExit(1)
