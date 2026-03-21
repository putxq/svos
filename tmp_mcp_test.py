from infrastructure.mcp_server import build_mcp_server
server = build_mcp_server()
tools = server.list_tools()
print(f"MCP tools registered: {len(tools)}")
for t in tools:
    print(f" {t['name']}: {t['description'][:60]}")
resp = server.handle_request({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'})
print(f"Initialize: {resp['result']['serverInfo']['name']}")
resp = server.handle_request({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})
print(f"tools/list: {len(resp['result']['tools'])} tools")
