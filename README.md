# Document-Graph-Representation

```bash
git clone https://github.com/GinHikat/Document-Graph-Representation.git

cd Document-Graph-Representation

pip install -r requirement.txt
```

Note that the requirement.txt may miss several libraries, fill them later if missing dependencies occurs. For further work with Pytorch models, torch-related libraries need to be installed later

Also, the files .env, ggsheet_credentials.json and neo4j_credentials.txt will be provided earlier if asked.

I. About the Github file structure

1. rag_model

1.1. Cypher: Working with Neo4j 
+ Install "Neo4j for VS Code" and "Neo4j Viz" extensions in VScode
+ for_neo4j.ipynb: For sample connection to Neo4j and Query via Python code
+ test_viz.cypher: cypher query to direct query to Neo4j, may require connecting to the AuraDB first

1.2. model
+ Modular Pipeline for Autoprocessing document

+ Test code is in test_pipeline.ipynb

+ Retrieval codebase in retrieval_pipeline

2. shared_functions

- gg_sheet_drive.py: Working with gg_sheet and gg_drive, read description in the file

- global functions.py: Working with S3, Neo4j, MySQL (unavailable) and file format conversion

- supabase.py: Working with supabase Relationdb, not necessary now

3. source

3.1. data: Training dataset for RE and NER models

3.2. document: Legal document as corpus

II. Working file for each task

- For working with document corpus: Read the rag_mode/test_google_drive.ipynb

- For working with retrieval pipeline: rag_model/retrieval_pipeline

- For the document autoprocessing into Graphdb: rag_model/model/test_pipeline.ipynb

III. Some additional Notes

1. When use text_embedding() from rag_model.model.Final_pipeline.final_doc_processor.py

List of embedding model and their respective id

```python
models = {
        0: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        1: "sentence-transformers/distiluse-base-multilingual-cased-v2",
        2: "sentence-transformers/all-mpnet-base-v2",
        3: 'sentence-transformers/all-MiniLM-L12-v2',
        4: "vinai/phobert-base",
        5: "BAAI/bge-m3" (only for retrieval evaluation)
    }
```

If use phobert-base then call PhoBERTEmbedding first

```python
from rag_model.model.Final_pipeline.final_doc_processor import *

phobert = PhoBERTEmbedding()

text = 'sample text'

embedding = text_embedding(text, 4, phobert)
```

If not use phobert-base then no need to call phobert parameter

```python
from rag_model.model.Final_pipeline.final_doc_processor import *

phobert = PhoBERTEmbedding()

text = 'sample text'

embedding = text_embedding(text, 1)
```

For the evaluation functions, call

```python
from shared_functions.eval import *

eval = Evaluator()

#if only embedding or jaccard
result = eval.evaluate_embedding(referenced_context = , retrieved_context = , embedding_threshold = )
result = eval.evaluate_jaccard(referenced_context = , retrieved_context = , jaccard_threshold = )

#if combined result
result = eval.combined_evaluator(referenced_context = , retrieved_context = , embedding_threshold = , jaccard_threshold = , scaling_factor = )

#if ragas, pass the whole dataframe instead of single entity, dataframe should contain question/user_input, answer/reference, retrieved_contexts
#rename input columns if needed
eval.ragas(df)
```

For the Graph Retrieval, call
```python
from shared_functions.batch_retrieval_neo4j import *

neo4j_retriever = Neo4j_retriever()

#if input is the whole dataframe with a lot of question
mode = {
        1: "default",
        2: "traverse_embed",
        3: "traverse_exact",
        4: "pagerank_embed",
        5: "pagerank_exact",
        6: "exact_match",
        7: "exact_match_with_rerank"
    }

graph = {1 if "use graph embedding", 0 if "use raw text embedding"}
chunks = {1 if "use only chunk nodes", 0 if "use all availabale nodes"}
hop = "Number of hops from original seed in traversal

#expect df has a 'question' column
df = neo4j_retriever.batch_query(df, mode = , graph = , chunks = , hop = )

# if input is one single sentence
df = neo4j_retriever.query_neo4j(text:str = , mode = , graph = , chunks = , hop = )
```
