# Phase 1: QA Data Analysis

**Goal:** Extract candidate questions likely to benefit from graph context

---

## Data Source

**File:** `/Users/hieudinh/Documents/my-projects/GP/Document-Graph-Representation/source/data/Research_sheet - QA_new.csv`
**Records:** ~36,847

### CSV Fields
```
question_id, doc_id, doc_source, question, answer, supporting_context,
supporting_context_node, created_time, gen_method, annotation_method,
question_type, question_category, cognitive, multi_clause, negative,
multi_source, validation_score, validation_notes
```

---

## Step 1: Filter High-Potential Questions

### Filter Criteria (ranked by priority)

1. **multi_source=True**: Requires info from multiple documents - BEST for graph
2. **multi_clause=True**: Spans multiple clauses within same document
3. **question_category=compare**: Comparative questions need relationship traversal
4. **cognitive=True**: Reasoning questions benefit from broader context
5. **question_type in [how, why]**: Explanatory questions need more context

### Python Script Template
```python
import pandas as pd

df = pd.read_csv('source/data/Research_sheet - QA_new.csv')

# Priority filters
multi_source = df[df['multi_source'] == True]
multi_clause = df[df['multi_clause'] == True]
compare = df[df['question_category'] == 'compare']
cognitive = df[df['cognitive'] == True]
why_how = df[df['question_type'].isin(['why', 'how'])]

# Score each question
df['graph_potential'] = (
    df['multi_source'].astype(int) * 3 +
    df['multi_clause'].astype(int) * 2 +
    (df['question_category'] == 'compare').astype(int) * 2 +
    df['cognitive'].astype(int) * 1 +
    df['question_type'].isin(['why', 'how']).astype(int) * 1
)

candidates = df[df['graph_potential'] >= 3].sort_values('graph_potential', ascending=False)
```

---

## Step 2: Cross-Reference with Neo4j Docs

Check which `doc_id` values exist in Neo4j Test_rel_2 namespace.

### Known Available Documents (from reports)
- 82/2025/ND-CP
- 59/2020/QH14
- 67/2025/QH15

### Query to Check
```cypher
MATCH (n:Test_rel_2)
WITH split(n.id, '_')[0] as doc_id
RETURN DISTINCT doc_id ORDER BY doc_id
```

---

## Step 3: Sample Output Structure

| question_id | question (truncated) | doc_id | multi_clause | multi_source | graph_potential |
|-------------|---------------------|--------|--------------|--------------|-----------------|
| 16/2023/QH15_Q03 | Lam the nao viec... | 16/2023 | True | False | 4 |
| ... | ... | ... | ... | ... | ... |

---

## Expected Output

File: `candidates-raw.json`
```json
{
  "total_candidates": 500,
  "filters_applied": ["multi_source", "multi_clause", "compare"],
  "questions": [
    {
      "id": "16/2023/QH15_Q03",
      "question": "...",
      "graph_potential_score": 4,
      "doc_available": true
    }
  ]
}
```
