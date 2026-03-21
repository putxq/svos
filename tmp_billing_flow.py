from billing.plans import list_plans
from billing.checkout import get_provider
from billing.subscriptions import get_subscription_manager

plans = list_plans()
print(f'Plans available: {len(plans)}')
for p in plans:
    print(f"  {p['id']:15s} USD {p['price_usd']:>6} / SAR {p['price_sar']:>6}")

print()
provider = get_provider('international')
checkout = provider.create_checkout_session('professional', 'test@svos.ai', 'https://svos.ai/success', 'https://svos.ai/cancel')
print(f"Checkout: {checkout['status']} | Plan: {checkout['plan']} | Amount: USD {checkout.get('amount_usd', '?')}")

print()
mgr = get_subscription_manager()
result = mgr.provision('cust_001', 'professional', 'test@svos.ai', payment_ref='dry_run_123')
print(f"Provisioned: {result['status']}")

print()
checks = [
    ('cust_001', 'cycle'),
    ('cust_001', 'tool:whatsapp'),
    ('cust_001', 'tool:landing_page'),
]
for cid, res in checks:
    r = mgr.check_limit(cid, res)
    print(f"  {res:20s} -> allowed={r['allowed']}")

print()
mgr.record_usage('cust_001', 'cycle')
mgr.record_usage('cust_001', 'cycle')
sub = mgr.get_subscription('cust_001')
usage = sub['subscription']['usage_today']
limits = sub['subscription']['limits']
print(f"Usage: {usage['cycles']}/{limits['cycles_per_day']} cycles today")

r = mgr.check_limit('cust_001', 'cycle')
print(f"Cycle check after 2 uses: allowed={r['allowed']} (limit={r['limit']})")
print()
print('BILLING SYSTEM OPERATIONAL')
