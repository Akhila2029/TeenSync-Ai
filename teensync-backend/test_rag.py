import sys
sys.path.insert(0, '.')
from app.services.rag_service import initialize_rag, retrieve_context, get_rag_status

print('Building RAG index...')
initialize_rag()

print()
status = get_rag_status()
print('Status:', status)

print()
print('Test 1: anxiety query')
results = retrieve_context('I feel anxious and overwhelmed', top_k=3)
for r in results:
    print(f'  - {r["source"]} (topic: {r["topic"]}, score: {r["score"]:.4f})')

print()
print('Test 2: sleep query')
results2 = retrieve_context("I can't sleep and feel exhausted", top_k=3)
for r in results2:
    print(f'  - {r["source"]} (topic: {r["topic"]}, score: {r["score"]:.4f})')

print()
print('RAG pipeline test complete!')
