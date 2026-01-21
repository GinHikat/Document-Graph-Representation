import sys, os
import ast
from tqdm import tqdm

url = os.getenv('NEO4J_URI')
username = 'neo4j'
password = os.getenv('NEO4J_AUTH')

from neo4j import GraphDatabase, Result

project_root = os.path.abspath(os.path.join(os.getcwd(), "../.."))
if project_root not in sys.path:
    sys.path.append(project_root)
    
from rag_model.model.Final_pipeline.final_doc_processor import *

from shared_functions.gg_sheet_drive import *
from shared_functions.global_functions import *


driver = GraphDatabase.driver(url, auth=(username, password), keep_alive=True)

class Neo4j_retriever:
    def __init__(self):
        pass
    
    def query_neo4j(self, text, mode = 1, graph = True, chunks = None, hop = 2, namespace = "Test"):
        '''
        Retrieve list of top k contexts from Graph
        Parameter:
        text:   Input prompt
        mode:   retrieval mode
        graph: use Graph Embedding or not, if None then use Node embedding
        chunks: use chunks or not, if None then use small Node
        hop: number of steps level from original nodes in Traversal
        '''
        
        mode_dict = {
            1: "default",
            2: "traverse_embed",
            3: "traverse_exact",
            4: "exact_match",
            5: "exact_match_with_rerank",
            6: "hybrid_search"
        }
        
        query_emb = text_embedding(text, 4, phobert) # type: ignore
        
        if chunks is not None:
            additional_label = "Chunk"
        else: 
            additional_label = ""
            
        labels = ":".join(
            [lbl for lbl in [namespace, additional_label] if lbl]
        )
            
        if graph is not None:
            embedding = "embedding"
            # query_emb = query_emb[:512] # type: ignore
        else:
            embedding = 'original_embedding'
        
        chosen_mode = mode_dict[mode]
        
        if chosen_mode == 'default':
            result = driver.execute_query(
                f"""
                    WITH $emb AS queryEmbedding
                    MATCH (n:{labels})
                    WHERE n.{embedding} IS NOT NULL AND n.text IS NOT NULL
                    WITH n, gds.similarity.cosine(n.{embedding}, queryEmbedding) AS score
                    RETURN n.id AS id, n.text AS text, score
                    ORDER BY score DESC
                    LIMIT 5;
                """, # type: ignore
                {"emb": query_emb},
                result_transformer_=Result.to_df
            ) # type: ignore
        
        if chosen_mode == 'exact_match':
            result = driver.execute_query(
                f'''
                    WITH $query AS input
                    WITH split(toLower(input), " ") AS words
                    MATCH (n:{labels})
                    WHERE n.text IS NOT NULL

                    // Count how many words from input appear in n.text
                    WITH n, size([word IN words WHERE toLower(n.text) CONTAINS word]) AS match_count
                    //, gds.similarity.cosine(n.{embedding}, queryEmbedding) AS score
                    WHERE match_count > 0  // optional: only nodes with at least one match

                    RETURN n.id AS id, n.text AS text, match_count
                    ORDER BY match_count DESC
                    LIMIT 5;
                ''', # type: ignore
                {"query": text},
                result_transformer_=Result.to_df
            )# type: ignore

        if chosen_mode == 'traverse_exact':
            result = driver.execute_query(
                f"""
                    WITH $query AS input
                    WITH split(toLower(input), " ") AS words
                    MATCH (n:{labels})
                    WHERE n.text IS NOT NULL

                    // word match
                    WITH n, size([word IN words WHERE toLower(n.text) CONTAINS word]) AS match_count
                    WHERE match_count > 0
                    ORDER BY match_count DESC
                    LIMIT 5

                    WITH collect(n) AS seeds

                    UNWIND seeds AS s

                    MATCH (s)-[*1..{hop}]-(nbr)
                    WHERE nbr <> s

                    WITH s AS seed,
                        nbr
                    ORDER BY seed.id, nbr.id   // stable ordering

                    WITH seed, COLLECT(DISTINCT nbr)[0..5] AS top_neighbors

                    WITH seed,
                        // concatenated text: seed.text + “ ” + neighbor texts
                        seed.text + " " + apoc.text.join([x IN top_neighbors | x.text], " ") AS combined_text

                    RETURN seed.id AS id,
                        combined_text as text
                    LIMIT 20;

                """, # type: ignore
                {"query": text},
                result_transformer_=Result.to_df
            )# type: ignore 
            
        if chosen_mode == 'traverse_embed':
            result = driver.execute_query(
                f"""
                    WITH $emb AS queryEmbedding
                    MATCH (n:{labels})
                    WHERE n.{embedding} IS NOT NULL AND n.text IS NOT NULL
                    WITH n, gds.similarity.cosine(n.{embedding}, queryEmbedding) AS score
                    ORDER BY score DESC
                    LIMIT 5

                    WITH collect(n) AS seeds
                    UNWIND seeds AS s

                    OPTIONAL MATCH (s)-[*1..{hop}]-(nbr)
                    WHERE nbr <> s

                    WITH s AS seed,
                        COLLECT(DISTINCT nbr)[0..2] AS top_neighbors

                    WITH seed,
                        seed.text + " " +
                        apoc.text.join([x IN top_neighbors | x.text], " ") AS text

                    RETURN seed.id AS id, text
                    LIMIT 20;

                """, # type: ignore
                {"emb": query_emb},
                result_transformer_=Result.to_df
            )# type: ignore    
        
        if chosen_mode == 'exact_match_with_rerank':
            result = driver.execute_query(
                f'''
                    WITH $query AS input, $emb AS queryEmbedding
                    WITH split(toLower(input), " ") AS words, queryEmbedding

                    MATCH (n:{labels})
                    WHERE n.text IS NOT NULL AND n.embedding IS NOT NULL

                    //Count matching words
                    WITH n, size([word IN words WHERE toLower(n.text) CONTAINS word]) AS match_count, queryEmbedding
                    WHERE match_count > 0

                    //Keep top 20 by word match count
                    ORDER BY match_count DESC
                    LIMIT 20

                    //Compute cosine similarity with query embedding
                    WITH n, match_count, gds.similarity.cosine(n.{embedding}, queryEmbedding) AS sim_score

                    //Rerank by embedding similarity
                    RETURN n.id AS id, n.text AS text, match_count, sim_score
                    ORDER BY sim_score DESC
                    LIMIT 5;
                ''', # type: ignore
                {"query": text, "emb": query_emb},
                result_transformer_=Result.to_df
            )# type: ignore

        if chosen_mode == 'hybrid_search':
            result = driver.execute_query(
                f"""
            WITH
                split(toLower($query), " ") AS words,
                $emb AS queryEmbedding,
                $alpha AS alpha
                
            MATCH (n:{labels})
            WHERE n.text IS NOT NULL AND n.{embedding} IS NOT NULL

            WITH
                n,
                size([w IN words WHERE toLower(n.text) CONTAINS w]) AS lexical_score,
                gds.similarity.cosine(n.{embedding}, queryEmbedding) AS embed_score,
                alpha

            // WHERE lexical_score > 0

            WITH collect({{
                n: n,
                lex: lexical_score,
                emb: embed_score
            }}) AS rows, alpha

            WITH
                rows,
                alpha,
                reduce(m = 0, r IN rows | CASE WHEN r.lex > m THEN r.lex ELSE m END) AS max_lex

            UNWIND rows AS r

            WITH
                r.n AS n,
                (r.lex * 1.0 / max_lex) AS lex_norm,
                (r.emb + 1.0) / 2.0 AS emb_norm,   // optional: shift [-1,1] → [0,1]
                alpha

            WITH
                n,
                lex_norm,
                emb_norm,
                (alpha * lex_norm + (1 - alpha) * emb_norm) AS hybrid_score

            RETURN
                n.id   AS id,
                n.text AS text,
                hybrid_score
            ORDER BY hybrid_score DESC
            LIMIT 5

                """, # type: ignore
                {
                    "query": text,
                    "emb": query_emb,
                    "alpha": 0.5
                },
                result_transformer_=Result.to_df
            ) # type: ignore
            
        return result

    def str_to_list(self, df, col):
        df[col] = df[col].apply(
            lambda x: ast.literal_eval(x) if isinstance(x, str) else x
        )

    def batch_query(self, df, mode=1, graph=None, chunks=None, hop=2, namespace = 'Test'):
        """
        Batch Query from Neo4j and add back retrieved contexts into a column in original DataFrame
        """
        # Initialize the column first
        df['retrieved_context'] = [[] for _ in range(len(df))]

        pbar = tqdm(total=len(df), desc="Querying Neo4j", ascii=True, dynamic_ncols=True)

        for i, q in enumerate(df['question']):
            try:
                retrieved = self.query_neo4j(q, mode, graph, chunks, hop, namespace)['text'].tolist()
                df.at[df.index[i], 'retrieved_context'] = retrieved

            except Exception as e:
                print(f"\nError at row {i}: {e}")
                break
            
            pbar.update(1)
        # df['retrieved_context'] = df['retrieved_context'].apply(lambda x: x[0])
        pbar.close()
        return df

