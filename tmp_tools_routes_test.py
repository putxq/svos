from main import app
routes = [r.path for r in app.routes if hasattr(r, 'path')]
tool_routes = [r for r in routes if '/tools' in r]
print(f'Total routes: {len(routes)}')
print(f'Tool routes: {len(tool_routes)}')
for r in tool_routes:
    print(r)
