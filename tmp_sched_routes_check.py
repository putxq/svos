from main import app
routes = [r.path for r in app.routes if hasattr(r, 'path') and 'scheduler' in r.path]
print(f'Scheduler routes: {len(routes)}')
for r in sorted(set(routes)):
    count = routes.count(r)
    dup = ' [DUPLICATE]' if count > 1 else ''
    print(f' {r}{dup}')
