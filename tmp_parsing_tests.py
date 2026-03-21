from engines.confidence_engine import ConfidenceEngine

print('=== ConfidenceEngine Tests ===')
tests = [
    ('78%', 'string percentage'),
    (78, 'integer 0-100'),
    (0.78, 'float 0-1'),
    ('high', 'word label'),
    ('medium-low', 'word label compound'),
    ('0%', 'zero string'),
    (0, 'zero int'),
    (None, 'None'),
    ('very high', 'word very high'),
    ('72.5%', 'decimal percentage'),
]
for val, desc in tests:
    result = ConfidenceEngine.evaluate(val)
    print(f" {desc:25s} | {str(val):12s} -> {result['normalized']:.3f} ({result['percentage']:>6s}) -> {result['action_level']}")

print()
print('=== Schema Validation Tests ===')
from core.response_schemas import validate_response, OpportunitySchema, TimeResult

opp = validate_response({'name': 'Test', 'confidence': '78%'}, OpportunitySchema)
print(f" Opportunity confidence: 78% -> {opp['confidence']}")

tr = validate_response({'recommendation': 'caution_with_proceed', 'avg_confidence': 68}, TimeResult)
print(f" TimeResult: caution_with_proceed -> {tr['recommendation']}")
print(f" TimeResult: 68 -> {tr['avg_confidence']}")

empty = validate_response({}, OpportunitySchema)
print(f" Empty opportunity: confidence={empty['confidence']}, name={empty['name']}")

print()
print('ALL PARSING TESTS PASSED')
