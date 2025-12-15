import numpy as np
import pandas as pd
import os, sys
from typing import List
import dotenv
dotenv.load_dotenv()
from tqdm import tqdm

project_root = os.path.abspath(os.path.join(os.getcwd(), "../.."))
if project_root not in sys.path:
    sys.path.append(project_root)
    
from rag_model.model.Final_pipeline.final_doc_processor import *
from rag_model.model.RE.final_re import *

class Evaluator:
    def __init__(self, embedding_as_judge = 5):
        self.embedding_as_judge = embedding_as_judge
        if self.embedding_as_judge == 4:
            self.phobert = PhoBertEmbedding()
        else:
            self.phobert = None
     
    def cosine(self, a, b):
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def jaccard(self, a, b): 
        A = set(a.lower().split()) 
        B = set(b.lower().split()) 
        return len(A & B) / len(A | B) if len(A | B) > 0 else 0

    def evaluate_embedding(self, referenced_context: List[str], retrieved_context: List[str], embedding_threshold=0.6):
        """
        Calculate Precision, Recall, F1-Score, and MRR for embedding-based retrieval.
        """
        referenced_set = list(set(referenced_context))
        retrieved_set  = list(set(retrieved_context))

        tp = 0 
        for ref in referenced_set:
            max_sim = -1
            for ret in retrieved_set:
                ref_emb = text_embedding(ref, self.embedding_as_judge, self.phobert)
                ret_emb = text_embedding(ret, self.embedding_as_judge, self.phobert)
                sim_score = self.cosine(ref_emb, ret_emb)
                if sim_score > max_sim:
                    max_sim = sim_score
            if max_sim >= embedding_threshold:
                tp += 1

        precision = tp / len(retrieved_set) if len(retrieved_set) > 0 else 0
        recall    = tp / len(referenced_set) if len(referenced_set) > 0 else 0
        f1_score  = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0

        reciprocal_rank = 0.0
        for rank, ret in enumerate(retrieved_set, start=1):
            max_sim = max(
                self.cosine(text_embedding(ref, self.embedding_as_judge), text_embedding(ret, self.embedding_as_judge))
                for ref in referenced_set
            )
            if max_sim >= embedding_threshold:
                reciprocal_rank = 1 / rank
                break  # only first relevant item counts

        return {
            'Precision': precision,
            'Recall': recall,
            'F1-Score': f1_score,
            'MRR': reciprocal_rank
        }

    def evaluate_jaccard(self, referenced_context: List[str], retrieved_context: List[str], jaccard_threshold=0.3):
        """
        Calculate Precision, Recall, F1-Score, and MRR using Jaccard similarity.
        """
        referenced_set = list(set(referenced_context))
        retrieved_set  = list(set(retrieved_context))

        used = set()   # retrieved indices already matched
        tp = 0

        for ref in referenced_set:
            best_match = None
            best_score = 0

            for i, ret in enumerate(retrieved_set):
                if i in used:
                    continue

                score = self.jaccard(ref, ret)
                if score > best_score:
                    best_score = score
                    best_match = i

            if best_score >= jaccard_threshold:
                tp += 1
                used.add(best_match)

        precision = tp / len(retrieved_set) if len(retrieved_set) > 0 else 0
        recall    = tp / len(referenced_set) if len(referenced_set) > 0 else 0
        f1_score  = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0

        reciprocal_rank = 0.0
        for rank, ret in enumerate(retrieved_set, start=1):
            max_score = max(self.jaccard(ref, ret) for ref in referenced_set)
            if max_score >= jaccard_threshold:
                reciprocal_rank = 1 / rank
                break  # only first relevant item counts

        return {
            'Precision': precision,
            'Recall': recall,
            'F1-Score': f1_score,
            'MRR': reciprocal_rank
        }

    def combined_evaluation(self, referenced_context: List[str], retrieved_context: List[str], embedding_threshold = 0.6, jaccard_threshold = 0.3, scaling_factor=0.5):
        '''
        Get the final combined result from the embedding and jaccard evaluations.
        
        tunable scaling_factor to adjust the weight of each evaluation method.
        final = scaling * embedding + (1 - scaling) * jaccard
        
        Output: dict{"Precision", "Recall", "F1-Score", "MRR"}
        '''
        embedding_results = self.evaluate_embedding(referenced_context, retrieved_context, embedding_threshold)
        jaccard_results = self.evaluate_jaccard(referenced_context, retrieved_context, jaccard_threshold)

        combined = {}
        combined.keys = embedding_results.keys() # type: ignore
        for key in combined.keys():
            combined[key] = embedding_results[key] * scaling_factor + jaccard_results[key] * (1-scaling_factor)
            
        return combined
    
    def ragas(self, df: pd.DataFrame):
        
        #Only import if the function is called to prevent overhead
        from langchain_community.llms import HuggingFacePipeline
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
        from langchain_community.embeddings import HuggingFaceBgeEmbeddings
        from ragas import evaluate
        from ragas.metrics import (
            ContextPrecision,
            LLMContextRecall
        )
        from datasets import Dataset

        metrics = [
            LLMContextRecall(),
            ContextPrecision()
        ]
        
        model_id = "Qwen/Qwen3-4B"
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(model_id)
        pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=512)
        llm = HuggingFacePipeline(pipeline=pipe)
    
        embeddings = HuggingFaceBgeEmbeddings(
            model_name="BAAI/bge-m3",
            model_kwargs={"device": "cuda"}, 
            encode_kwargs={"normalize_embeddings": True}
        )
        
        hf_ds = Dataset.from_pandas(df)
        results = evaluate(hf_ds, metrics=metrics, llm=llm, embeddings=embeddings)
        
        print(results)
        