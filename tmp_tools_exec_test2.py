from tool_registry import build_registry

registry = build_registry()

print('Test 1: CMO sends WhatsApp')
r = registry.execute('whatsapp', 'CMO', 'send', to='+966500000000', body='Test from SVOS')
print('Status:', r.get('status'))

print('Test 2: CFO sends WhatsApp')
r = registry.execute('whatsapp', 'CFO', 'send', to='+966500000000', body='Test')
print('Status:', r.get('status'))

print('Test 3: CMO generates landing page')
r = registry.execute('landing_page', 'CMO', 'generate', title='SVOS', headline='Build Your Digital Company', sub_headline='AI-Powered Sovereign System', features=['24/7 Agents','Smart Governance','Auto Execution'], lang='en')
print('Status:', r.get('status'))
print('filepath:', r.get('filepath'))

print('Test 4: CMO posts Twitter')
r = registry.execute('social_post', 'CMO', 'post', content='SVOS is building the future of autonomous digital companies', platform='twitter')
print('Status:', r.get('status'))
