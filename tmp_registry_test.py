from tool_registry import build_registry
r = build_registry()
print(f"Registry: {len(r._tools)} tools loaded")
for n, i in r.list_all().items():
    print(f" - {n}: roles={i['allowed_roles']}")
