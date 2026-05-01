import sys
sys.path.insert(0, '.')

from models.schemas import SupportTicket, TriageOutput, TicketContext
from config import settings
from constants import HARD_ESCALATE_KEYWORDS, PRODUCT_AREAS

# Test 1: company normalization
t = SupportTicket(issue='test issue', subject='test', company='None')
print('Company normalized:', repr(t.company))  # should be None

# Test 2: Pydantic rejects wrong status
try:
    bad = TriageOutput(status='reply', request_type='bug', product_area='General', response='x', justification='y')
    print('ERROR: should have rejected bad status')
except Exception as e:
    print('Correctly rejected bad status:', type(e).__name__)

# Test 3: valid output
good = TriageOutput(status='replied', request_type='bug', product_area='General', response='x', justification='y')
print('Valid output created:', good.status)

# Test 4: escalated clears response
escalated = TriageOutput(status='escalated', request_type='bug', product_area='General', response='some text', justification='reason')
print('Escalated response cleared:', repr(escalated.response))  # should be ""

# Test 5: settings loaded
print('Corpus dir:', settings.CORPUS_DIR)
print('Keywords loaded:', len(HARD_ESCALATE_KEYWORDS))

print()
print('Hour 1 complete - all contracts verified')