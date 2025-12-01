import sys, os
    
os.environ["TRANSFORMERS_NO_TF"] = "1"

from copy import deepcopy
import pandas as pd
import json 
from collections import OrderedDict
from underthesea import sent_tokenize
import re
import unicodedata
from collections import OrderedDict

from shared_functions.gg_sheet_drive import *
from shared_functions.global_functions import *

project_root = os.path.abspath(os.path.join(os.getcwd(), ".."))
if project_root not in sys.path:
    sys.path.append(project_root)
    
class Doc_processor:
    def __init__(self, ner, re_model, final_re):
        self.ner = ner
        self.re_model = re_model
        self.final_re = final_re
    
    def normalize_unicode(self, s: str) -> str:
        s = unicodedata.normalize("NFKC", s)
        s = s.replace("\u00A0", " ").replace("\u202F", " ").replace("\u200B", "")
        return s.strip()

    def parse_legal_text(self, text: str):
        # Normalize each line and rebuild
        clean_lines = [self.normalize_unicode(line) for line in text.splitlines()]
        clean_text = "\n".join(clean_lines)

        chapter_pattern = r"(?i)^\s*chương\s+([IVXLCDM\d]+)\b"
        clause_pattern = r"^\s*Điều\s+(\d+)\b"
        point_pattern = r"^\s*(\d+)\."
        subpoint_pattern = r"^\s*([a-z])\)"
        subsubpoint_pattern = r"^\s*([a-z])\.(\d+)\)"
        subsubsubpoint_pattern = r"^\s*([a-z])\.(\d+)\.(\d+)\)"

        # Detect if document has chapters
        has_chapter = any(re.match(chapter_pattern, line) for line in clean_lines)

        structure = OrderedDict()
        if has_chapter:
            structure["chapters"] = OrderedDict()
        else:
            structure["clauses"] = []

        current_chapter = None
        current_clause = None
        current_point = None
        current_subpoint = None
        current_subsubpoint = None
        current_subsubsubpoint = None

        for line in clean_lines:
            if not line:
                continue

            # Chapter
            mch = re.match(chapter_pattern, line)
            if mch and has_chapter:
                chap_key = f"chapter {mch.group(1)}"
                structure["chapters"][chap_key] = {
                    "title": line,
                    "text": "",
                    "clauses": []
                }
                current_chapter = chap_key
                current_clause = current_point = current_subpoint = current_subsubpoint = current_subsubsubpoint = None
                continue

            # Clause (Điều)
            mcl = re.match(clause_pattern, line)
            if mcl:
                clause_entry = {"clause": mcl.group(1), "text": line, "points": []}
                if has_chapter:
                    if current_chapter is None:
                        current_chapter = "no_chapter"
                        structure["chapters"].setdefault(current_chapter, {"title": "", "text": "", "clauses": []})
                    structure["chapters"][current_chapter]["clauses"].append(clause_entry)
                else:
                    structure["clauses"].append(clause_entry)
                current_clause = clause_entry
                current_point = current_subpoint = current_subsubpoint = current_subsubsubpoint = None
                continue

            # Point (1.)
            mp = re.match(point_pattern, line)
            if mp and current_clause is not None:
                current_point = {"point": mp.group(1), "text": line, "subpoints": []}
                current_clause["points"].append(current_point)
                current_subpoint = current_subsubpoint = current_subsubsubpoint = None
                continue

            # Subpoint (a))
            ms = re.match(subpoint_pattern, line)
            if ms and current_point is not None:
                current_subpoint = {"subpoint": ms.group(1), "text": line, "subsubpoints": []}
                current_point["subpoints"].append(current_subpoint)
                current_subsubpoint = current_subsubsubpoint = None
                continue

            # SubSubpoint (a.1))
            mss = re.match(subsubpoint_pattern, line)
            if mss and current_subpoint is not None:
                tag = f"{mss.group(1)}.{mss.group(2)}"
                current_subsubpoint = {"subsubpoint": tag, "text": line, "subsubsubpoints": []}
                current_subpoint["subsubpoints"].append(current_subsubpoint)
                current_subsubsubpoint = None
                continue

            # SubSubSubpoint (a.1.1))
            msss = re.match(subsubsubpoint_pattern, line)
            if msss and current_subsubpoint is not None:
                tag = f"{msss.group(1)}.{msss.group(2)}.{msss.group(3)}"
                current_subsubsubpoint = {"subsubsubpoint": tag, "text": line}
                current_subsubpoint["subsubsubpoints"].append(current_subsubsubpoint)
                continue

            # Continuation of content
            if current_subsubsubpoint is not None:
                current_subsubsubpoint["text"] += "\n" + line
            elif current_subsubpoint is not None:
                current_subsubpoint["text"] += "\n" + line
            elif current_subpoint is not None:
                current_subpoint["text"] += "\n" + line
            elif current_point is not None:
                current_point["text"] += "\n" + line
            elif current_clause is not None:
                current_clause["text"] += "\n" + line
            elif has_chapter and current_chapter is not None:
                prev = structure["chapters"][current_chapter]["text"]
                structure["chapters"][current_chapter]["text"] = (prev + "\n" + line) if prev else line

        return structure
    
    def merge_fragmented(self, text):
        if not isinstance(text, str):
            return text
        vowels = "aeiouyàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựýỳỷỹỵ"
        vowel_start = re.compile(rf"^[{vowels}]", re.IGNORECASE)
        exclude_words = {"án", "anh"}
        parts = text.split()
        if len(parts) < 2:
            return text
        merged = [parts[0]]
        for token in parts[1:]:
            token_lower = token.lower()
            if vowel_start.match(token_lower) and token_lower not in exclude_words:
                merged[-1] += token
            else:
                merged.append(token)
        return " ".join(merged)
    
    def saving_neo4j(self, text, namespace="Test"):
    # Extract metadata
        df_meta = self.ner.extract_document_metadata(text)
        meta_row = df_meta.iloc[0]
        df_relation = self.final_re.final_relation(text)
        
        self_check = {'luật': 'doc1', 'định': 'doc2', 'tư': 'doc3', 'quyết': 'doc4', 'chương': 'chapter', 'điều': 'clause', 'mục': 'point'}

        metadata = {
            "law_id": meta_row["document_id"],
            "title": meta_row["title"],
            "issuer": meta_row["issuer"],
            "issue_date": meta_row["issue_date"],
            "location": meta_row["location"],
            "issuer_department": meta_row["issuer_department"],
            "document_type": meta_row["document_type"],
            "amendment_history": "None",
            "jurisdiction_scope": "National",
        }

        # Document type
        doc_type_label = metadata["document_type"].replace(" ", "_").capitalize()
        # Namespace
        ns_label = re.sub(r"\W+", "_", namespace)

        # central document node
        dml_ddl_neo4j(
            f"""
            MERGE (l:`{doc_type_label}`:`{ns_label}` {{id: $law_id}})
            SET l += $meta
            """,
            law_id=metadata["law_id"],
            meta=metadata,
        )
        
        #Connect reference node
        for i in range(len(df_relation)):
            
            doc_type = df_relation.iloc[i,7].replace(" ", "_").capitalize()
            
            if ((len(df_relation.iloc[i,6].split('/')) or df_relation.iloc[i, 6] == 'HP') > 1) and (df_relation.iloc[i,7]):
                
                dml_ddl_neo4j(
                f"""
                MERGE (l:`{doc_type}`:`{ns_label}` {{id: $law_id}})
                WITH l
                MATCH (r: `{doc_type_label}`:`{ns_label}` {{id: $law_id2}})
                MERGE (r)-[:`{df_relation.iloc[i,2]}`]->(l)
                """,
                law_id=df_relation.iloc[i,6],
                law_id2=metadata['law_id']
            )
                if (df_relation.iloc[i,4]):  
                    dml_ddl_neo4j(
                        f"""
                        MATCH (l:`{doc_type}`:`{ns_label}` {{id: $law_id}})
                        SET l.issue_date = $issue_date
                        """,
                        law_id=df_relation.iloc[i,6],
                        issue_date=str(df_relation.iloc[i,4])
                    )
                    
            #if id not available, use date
            if df_relation.iloc[i,4]:
                dml_ddl_neo4j(
                f"""
                MERGE (l:`{doc_type}`:`{ns_label}` {{issue_date: $issue_date}})
                WITH l
                MATCH (r: `{doc_type_label}`:`{ns_label}` {{id: $law_id2}})
                MERGE (r)-[:`{df_relation.iloc[i,2]}`]->(l)
                """,
                issue_date=str(df_relation.iloc[i,4]),
                law_id2=metadata['law_id']
            )
                
        # Parse structure
        parsed = self.parse_legal_text(text)

        # Extract text
        def get_text(node, *keys):
            for k in keys:
                if isinstance(node, dict) and k in node and node[k]:
                    return node[k]
            if isinstance(node, str):
                return node
            return ""

        # If HAS chapters 
        if "chapters" in parsed:
            for chapter_key, chapter_obj in parsed["chapters"].items():
                chapter_id = f"{metadata['law_id']}_{chapter_key.replace(' ', '_')}"
                chapter_title = get_text(chapter_obj, "title")
                chapter_text = get_text(chapter_obj, "text")
                re_text = None
                re_temp = None
                relation = None
                second_entity = []
                            
                dml_ddl_neo4j(
                    f"""
                    MERGE (ch:Chapter:{ns_label} {{id: $id}})
                    SET ch.title = $title, ch.text = $text
                    WITH ch
                    MATCH (l:{ns_label} {{law_id: $law_id}})
                    MERGE (l)-[:HAS_CHAPTER]->(ch)
                    """,
                    id=chapter_id,
                    title=chapter_title,
                    text=chapter_text,
                    law_id=metadata["law_id"],
                )
                        
                #Extract relation
                chapter_text = re.sub(r'^(?:Chương|Điều)\s*\d*\s*|^[a-z](?:\.\d+)*\)', '', chapter_text, flags=re.IGNORECASE)
                re_text = sent_tokenize(chapter_text)
                # re_text[0] = re_text[0].split(chapter_id.split('_')[-1], 1)[1].strip()
                for sentence in re_text:
                    root = None
                    re_temp = self.final_re.final_relation(sentence)

                    if len(re_temp['document_id']) > 0:
                        _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)

                    if 'này' in sentence.split():
                        words = sentence.split()
                        root = None
                        ref = None
                        for i, token in enumerate(words):
                            if token == "này" and i > 0:
                                prev_word = words[i-1]
                                if prev_word.lower() in self_check.keys():
                                    text_type = self_check[prev_word.lower()]
                                    match text_type:
                                        case "doc1":
                                            root = metadata["law_id"]
                                            ref = "Luật"
                                        case "doc2":
                                            root = metadata["law_id"]
                                            ref = "Nghị_định"
                                        case "doc3":
                                            root = metadata["law_id"]
                                            ref = "Thông_tư"
                                        case "doc4":
                                            root = metadata["law_id"]
                                            ref = "Nghị_quyết"
                                        case "chapter":
                                            root = chapter_id
                                        case "clause":
                                            root = clause_id
                                        case "point":
                                            root = point_id
                                    if root is not None:
                                        _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)
                                    else:
                                        second_entity = []   
                                            
                    if not second_entity or not relation:
                        continue               
                    for entity in second_entity or []:
                        if (list(entity.keys())[0] == None) or list(entity.values())[0] is None:
                                            continue
                        label = list(entity.keys())[0]       
                        ref_type = ref if list(entity.values())[0] == 'Document' else list(entity.values())[0]

                        dml_ddl_neo4j(
                            f"""
                            MERGE (l:`{ref_type}`:`{ns_label}` {{id: $law_id}})
                            WITH l
                            MATCH (r:Chapter:`{ns_label}` {{id: $law_id2}})
                            MERGE (r)-[:`{relation}`]->(l)
                            """,
                            law_id=label,
                            law_id2=chapter_id
                        )

                # Handle Clauses inside the Chapter
                for cl in chapter_obj.get("clauses", []):
                    clause_id = f"{chapter_id}_C_{cl.get('clause', '?')}"
                    clause_text = get_text(cl, "text")
                    root = None
                    ref = None
                    second_entity = []

                    dml_ddl_neo4j(
                        f"""
                        MERGE (c:Clause:{ns_label} {{id: $id}})
                        SET c.text = $text
                        WITH c
                        MATCH (ch:Chapter:{ns_label} {{id: $chapter_id}})
                        MERGE (ch)-[:HAS_CLAUSE]->(c)
                        """,
                        id=clause_id,
                        text=clause_text,
                        chapter_id=chapter_id,
                    )
                    
                    #Extract relation
                    clause_text = re.sub(r'^(?:Chương|Điều)\s*\d*\s*|^[a-z](?:\.\d+)*\)', '', clause_text, flags=re.IGNORECASE)
                    re_text = sent_tokenize(clause_text)
                    for sentence in re_text:
                        root = None
                        re_temp = self.final_re.final_relation(sentence)

                        if len(re_temp['document_id']) > 0:
                            _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)

                        if 'này' in sentence.split():
                            words = sentence.split()
                            root = None
                            ref = None
                            for i, token in enumerate(words):
                                if token == "này" and i > 0:
                                    prev_word = words[i-1]
                                    if prev_word.lower() in self_check.keys():
                                        text_type = self_check[prev_word.lower()]
                                        match text_type:
                                            case "doc1":
                                                root = metadata["law_id"]
                                                ref = "Luật"
                                            case "doc2":
                                                root = metadata["law_id"]
                                                ref = "Nghị_định"
                                            case "doc3":
                                                root = metadata["law_id"]
                                                ref = "Thông_tư"
                                            case "doc4":
                                                root = metadata["law_id"]
                                                ref = "Nghị_quyết"
                                            case "chapter":
                                                root = chapter_id
                                            case "clause":
                                                root = clause_id
                                            case "point":
                                                root = point_id
                                        if root is not None:
                                            _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)
                                        else:
                                            second_entity = []        
                        if not second_entity or not relation:
                            continue                           
                        for entity in second_entity or []:
                            if (list(entity.keys())[0] == None) or list(entity.values())[0] is None:
                                            continue
                            label = list(entity.keys())[0]       
                            ref_type = ref if list(entity.values())[0] == 'Document' else list(entity.values())[0]

                            dml_ddl_neo4j(
                                f"""
                                MERGE (l:`{ref_type}`:`{ns_label}` {{id: $law_id}})
                                WITH l
                                MATCH (r:Clause:`{ns_label}` {{id: $law_id2}})
                                MERGE (r)-[:`{relation}`]->(l)
                                """,
                                law_id=label,
                                law_id2=clause_id
                            )

                    # Handle Points (1.)
                    for point in cl.get("points", []):
                        point_id = f"{clause_id}_P_{point.get('point', '?')}"
                        point_text = get_text(point, "text")
                        root = None
                        ref = None
                        second_entity = []
                
                        dml_ddl_neo4j(
                            f"""
                            MERGE (p:Point:{ns_label} {{id: $id}})
                            SET p.text = $text
                            WITH p
                            MATCH (c:Clause:{ns_label} {{id: $clause_id}})
                            MERGE (c)-[:HAS_POINT]->(p)
                            """,
                            id=point_id,
                            text=point_text,
                            clause_id=clause_id,
                        )
                        
                        #Extract relation
                        re_text = sent_tokenize(point_text)
                        for sentence in re_text:
                            root = None
                            re_temp = self.final_re.final_relation(sentence)

                            if len(re_temp['document_id']) > 0:
                                _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)

                            if 'này' in sentence.split():
                                words = sentence.split()
                                root = None
                                ref = None
                                for i, token in enumerate(words):
                                    if token == "này" and i > 0:
                                        prev_word = words[i-1]
                                        if prev_word.lower() in self_check.keys():
                                            text_type = self_check[prev_word.lower()]
                                            match text_type:
                                                case "doc1":
                                                    root = metadata["law_id"]
                                                    ref = "Luật"
                                                case "doc2":
                                                    root = metadata["law_id"]
                                                    ref = "Nghị_định"
                                                case "doc3":
                                                    root = metadata["law_id"]
                                                    ref = "Thông_tư"
                                                case "doc4":
                                                    root = metadata["law_id"]
                                                    ref = "Nghị_quyết"
                                                case "chapter":
                                                    root = chapter_id
                                                case "clause":
                                                    root = clause_id
                                                case "point":
                                                    root = point_id
                                            if root is not None:
                                                _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)
                                            else:
                                                second_entity = []        
                            if not second_entity or not relation:
                                continue                             
                            for entity in second_entity or []:
                                if (list(entity.keys())[0] == None) or list(entity.values())[0] is None:
                                            continue
                                label = list(entity.keys())[0]       
                                ref_type = ref if list(entity.values())[0] == 'Document' else list(entity.values())[0]

                                dml_ddl_neo4j(
                                    f"""
                                    MERGE (l:`{ref_type}`:`{ns_label}` {{id: $law_id}})
                                    WITH l
                                    MATCH (r:Point:`{ns_label}` {{id: $law_id2}})
                                    MERGE (r)-[:`{relation}`]->(l)
                                    """,
                                    law_id=label,
                                    law_id2=point_id
                                )

                        # Handle Subpoints (a))
                        for subpoint in point.get("subpoints", []):
                            subpoint_id = f"{point_id}_SP_{subpoint.get('subpoint', '?')}"
                            subpoint_text = get_text(subpoint, "text")
                            root = None
                            ref = None
                            second_entity = []
                        
                            dml_ddl_neo4j(
                                f"""
                                MERGE (sp:Subpoint:{ns_label} {{id: $id}})
                                SET sp.text = $text
                                WITH sp
                                MATCH (p:Point:{ns_label} {{id: $point_id}})
                                MERGE (p)-[:HAS_SUBPOINT]->(sp)
                                """,
                                id=subpoint_id,
                                text=subpoint_text,
                                point_id=point_id,
                            )
                            
                            #Extract relation
                            re_text = sent_tokenize(subpoint_text)
                            for sentence in re_text:
                                root = None
                                re_temp = self.final_re.final_relation(sentence)

                                if len(re_temp['document_id']) > 0:
                                    _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)

                                if 'này' in sentence.split():
                                    words = sentence.split()
                                    root = None
                                    ref = None
                                    for i, token in enumerate(words):
                                        if token == "này" and i > 0:
                                            prev_word = words[i-1]
                                            if prev_word.lower() in self_check.keys():
                                                text_type = self_check[prev_word.lower()]
                                                match text_type:
                                                    case "doc1":
                                                        root = metadata["law_id"]
                                                        ref = "Luật"
                                                    case "doc2":
                                                        root = metadata["law_id"]
                                                        ref = "Nghị_định"
                                                    case "doc3":
                                                        root = metadata["law_id"]
                                                        ref = "Thông_tư"
                                                    case "doc4":
                                                        root = metadata["law_id"]
                                                        ref = "Nghị_quyết"
                                                    case "chapter":
                                                        root = chapter_id
                                                    case "clause":
                                                        root = clause_id
                                                    case "point":
                                                        root = point_id
                                                if root is not None:
                                                    _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)
                                                else:
                                                    second_entity = []        
                                if not second_entity or not relation:
                                    continue                              
                                for entity in second_entity or []:
                                    if (list(entity.keys())[0] == None) or list(entity.values())[0] is None:
                                            continue
                                    label = list(entity.keys())[0]       
                                    ref_type = ref if list(entity.values())[0] == 'Document' else list(entity.values())[0]

                                    dml_ddl_neo4j(
                                        f"""
                                        MERGE (l:`{ref_type}`:`{ns_label}` {{id: $law_id}})
                                        WITH l
                                        MATCH (r:Subpoint:`{ns_label}` {{id: $law_id2}})
                                        MERGE (r)-[:`{relation}`]->(l)
                                        """,
                                        law_id=label,
                                        law_id2=subpoint_id
                                    )
                                
                            # Handle SubSubpoints (a.1))
                            for ssp in subpoint.get("subsubpoints", []):
                                ssp_id = f"{subpoint_id}_SSP_{ssp.get('subsubpoint', '?')}"
                                ssp_text = get_text(ssp, "text")
                                root = None
                                ref = None
                                second_entity = []
                                
                                dml_ddl_neo4j(
                                    f"""
                                    MERGE (ssp:Subsubpoint:{ns_label} {{id: $id}})
                                    SET ssp.text = $text
                                    WITH ssp
                                    MATCH (sp:Subpoint:{ns_label} {{id: $subpoint_id}})
                                    MERGE (sp)-[:HAS_SUBSUBPOINT]->(ssp)
                                    """,
                                    id=ssp_id,
                                    text=ssp_text,
                                    subpoint_id=subpoint_id,
                                )
                                
                                #Extract relation
                                re_text = sent_tokenize(ssp_text)
                                for sentence in re_text:
                                    root = None
                                    re_temp = self.final_re.final_relation(sentence)

                                    if len(re_temp['document_id']) > 0:
                                        _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)

                                    if 'này' in sentence.split():
                                        words = sentence.split()
                                        root = None
                                        ref = None
                                        for i, token in enumerate(words):
                                            if token == "này" and i > 0:
                                                prev_word = words[i-1]
                                                if prev_word.lower() in self_check.keys():
                                                    text_type = self_check[prev_word.lower()]
                                                    match text_type:
                                                        case "doc1":
                                                            root = metadata["law_id"]
                                                            ref = "Luật"
                                                        case "doc2":
                                                            root = metadata["law_id"]
                                                            ref = "Nghị_định"
                                                        case "doc3":
                                                            root = metadata["law_id"]
                                                            ref = "Thông_tư"
                                                        case "doc4":
                                                            root = metadata["law_id"]
                                                            ref = "Nghị_quyết"
                                                        case "chapter":
                                                            root = chapter_id
                                                        case "clause":
                                                            root = clause_id
                                                        case "point":
                                                            root = point_id
                                                    if root is not None:
                                                        _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)
                                                    else:
                                                        second_entity = []        
                                    if not second_entity or not relation:
                                        continue                               
                                    for entity in second_entity or []:
                                        if (list(entity.keys())[0] == None) or list(entity.values())[0] is None:
                                            continue
                                        label = list(entity.keys())[0]       
                                        ref_type = ref if list(entity.values())[0] == 'Document' else list(entity.values())[0]

                                        dml_ddl_neo4j(
                                            f"""
                                            MERGE (l:`{ref_type}`:`{ns_label}` {{id: $law_id}})
                                            WITH l
                                            MATCH (r:Subsubpoint:`{ns_label}` {{id: $law_id2}})
                                            MERGE (r)-[:`{relation}`]->(l)
                                            """,
                                            law_id=label,
                                            law_id2=ssp_id
                                        )

                                # Handle SubSubSubpoints (a.1.1))
                                for sssp in ssp.get("subsubsubpoints", []):
                                    sssp_id = f"{ssp_id}_SSSP_{sssp.get('subsubsubpoint', '?')}"
                                    sssp_text = get_text(sssp, "text")
                                    root = None
                                    ref = None
                                    second_entity = []
                                    
                                    dml_ddl_neo4j(
                                        f"""
                                        MERGE (sssp:Subsubsubpoint:{ns_label} {{id: $id}})
                                        SET sssp.text = $text
                                        WITH sssp
                                        MATCH (ssp:Subsubpoint:{ns_label} {{id: $ssp_id}})
                                        MERGE (ssp)-[:HAS_SUBSUBSUBPOINT]->(sssp)
                                        """,
                                        id=sssp_id,
                                        text=sssp_text,
                                        ssp_id=ssp_id,
                                    )
                                    
                                    #Extract relation
                                    re_text = sent_tokenize(sssp_text)
                                    for sentence in re_text:
                                        root = None
                                        re_temp = self.final_re.final_relation(sentence)

                                        if len(re_temp['document_id']) > 0:
                                            _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)

                                        if 'này' in sentence.split():
                                            words = sentence.split()
                                            root = None
                                            ref = None
                                            for i, token in enumerate(words):
                                                if token == "này" and i > 0:
                                                    prev_word = words[i-1]
                                                    if prev_word.lower() in self_check.keys():
                                                        text_type = self_check[prev_word.lower()]
                                                        match text_type:
                                                            case "doc1":
                                                                root = metadata["law_id"]
                                                                ref = "Luật"
                                                            case "doc2":
                                                                root = metadata["law_id"]
                                                                ref = "Nghị_định"
                                                            case "doc3":
                                                                root = metadata["law_id"]
                                                                ref = "Thông_tư"
                                                            case "doc4":
                                                                root = metadata["law_id"]
                                                                ref = "Nghị_quyết"
                                                            case "chapter":
                                                                root = chapter_id
                                                            case "clause":
                                                                root = clause_id
                                                            case "point":
                                                                root = point_id
                                                        if root is not None:
                                                            _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)
                                                        else:
                                                            second_entity = []        
                                        if not second_entity or not relation:
                                            continue                                
                                        for entity in second_entity or []:
                                            if (list(entity.keys())[0] == None) or list(entity.values())[0] is None:
                                                continue
                                            label = list(entity.keys())[0]       
                                            ref_type = ref if list(entity.values())[0] == 'Document' else list(entity.values())[0]

                                            dml_ddl_neo4j(
                                                f"""
                                                MERGE (l:`{ref_type}`:`{ns_label}` {{id: $law_id}})
                                                WITH l
                                                MATCH (r:Subsubsubpoint:`{ns_label}` {{id: $law_id2}})
                                                MERGE (r)-[:`{relation}`]->(l)
                                                """,
                                                law_id=label,
                                                law_id2=sssp_id
                                            )

        # If WITHOUT chapters (only clauses)
        elif "clauses" in parsed:
            for cl in parsed["clauses"]:
                clause_id = f"{metadata['law_id']}_C_{cl.get('clause', '?')}"
                clause_text = get_text(cl, "text")
                re_text = None
                re_temp = None
                relation = None
                second_entity = []
                
                dml_ddl_neo4j(
                    f"""
                    MERGE (c:Clause:{ns_label} {{id: $id}})
                    SET c.text = $text
                    WITH c
                    MATCH (l:{ns_label} {{id: $law_id}})
                    MERGE (l)-[:HAS_CLAUSE]->(c)
                    """,
                    id=clause_id,
                    text=clause_text,
                    law_id=metadata["law_id"],
                )

                #Extract relation
                clause_text = re.sub(r'^(?:Chương|Điều)\s*\d*\s*|^[a-z](?:\.\d+)*\)', '', clause_text, flags=re.IGNORECASE)
                re_text = sent_tokenize(clause_text)
                for sentence in re_text:
                    root = None
                    re_temp = self.final_re.final_relation(sentence)

                    if len(re_temp['document_id']) > 0:
                        _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)

                    if 'này' in sentence.split():
                        words = sentence.split()
                        root = None
                        ref = None
                        for i, token in enumerate(words):
                            if token == "này" and i > 0:
                                prev_word = words[i-1]
                                if prev_word.lower() in self_check.keys():
                                    text_type = self_check[prev_word.lower()]
                                    match text_type:
                                        case "doc1":
                                            root = metadata["law_id"]
                                            ref = "Luật"
                                        case "doc2":
                                            root = metadata["law_id"]
                                            ref = "Nghị_định"
                                        case "doc3":
                                            root = metadata["law_id"]
                                            ref = "Thông_tư"
                                        case "doc4":
                                            root = metadata["law_id"]
                                            ref = "Nghị_quyết"
                                        case "chapter":
                                            root = chapter_id
                                        case "clause":
                                            root = clause_id
                                        case "point":
                                            root = point_id
                                    if root is not None:
                                        _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)
                                    else:
                                        second_entity = []        
                    if not second_entity or not relation:
                        continue                                
                    for entity in second_entity or []:
                        if (list(entity.keys())[0] == None) or list(entity.values())[0] is None:
                            continue
                        label = list(entity.keys())[0]       
                        ref_type = ref if list(entity.values())[0] == 'Document' else list(entity.values())[0]

                        dml_ddl_neo4j(
                            f"""
                            MERGE (l:`{ref_type}`:`{ns_label}` {{id: $law_id}})
                            WITH l
                            MATCH (r:Clause:`{ns_label}` {{id: $law_id2}})
                            MERGE (r)-[:`{relation}`]->(l)
                            """,
                            law_id=label,
                            law_id2=clause_id
                        )
                    
                #Handle Point
                for point in cl.get("points", []):
                    point_id = f"{clause_id}_P_{point.get('point', '?')}"
                    point_text = get_text(point, "text")
                    
                    root = None
                    ref = None
                    second_entity = []

                    dml_ddl_neo4j(
                        f"""
                        MERGE (p:Point:{ns_label} {{id: $id}})
                        SET p.text = $text
                        WITH p
                        MATCH (c:Clause:{ns_label} {{id: $clause_id}})
                        MERGE (c)-[:HAS_POINT]->(p)
                        """,
                        id=point_id,
                        text=point_text,
                        clause_id=clause_id,
                    )
                    
                    #Extract relation
                    re_text = sent_tokenize(point_text)
                    for sentence in re_text:
                        root = None
                        re_temp = self.final_re.final_relation(sentence)

                        if len(re_temp['document_id']) > 0:
                            _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)

                        if 'này' in sentence.split():
                            words = sentence.split()
                            root = None
                            ref = None
                            for i, token in enumerate(words):
                                if token == "này" and i > 0:
                                    prev_word = words[i-1]
                                    if prev_word.lower() in self_check.keys():
                                        text_type = self_check[prev_word.lower()]
                                        match text_type:
                                            case "doc1":
                                                root = metadata["law_id"]
                                                ref = "Luật"
                                            case "doc2":
                                                root = metadata["law_id"]
                                                ref = "Nghị_định"
                                            case "doc3":
                                                root = metadata["law_id"]
                                                ref = "Thông_tư"
                                            case "doc4":
                                                root = metadata["law_id"]
                                                ref = "Nghị_quyết"
                                            case "chapter":
                                                root = chapter_id
                                            case "clause":
                                                root = clause_id
                                            case "point":
                                                root = point_id
                                        if root is not None:
                                            _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)
                                        else:
                                            second_entity = []        
                        if not second_entity or not relation:
                            continue                               
                        for entity in second_entity or []:
                            if (list(entity.keys())[0] == None) or list(entity.values())[0] is None:
                                continue
                            label = list(entity.keys())[0]       
                            ref_type = ref if list(entity.values())[0] == 'Document' else list(entity.values())[0]

                            dml_ddl_neo4j(
                                f"""
                                MERGE (l:`{ref_type}`:`{ns_label}` {{id: $law_id}})
                                WITH l
                                MATCH (r:Point:`{ns_label}` {{id: $law_id2}})
                                MERGE (r)-[:`{relation}`]->(l)
                                """,
                                law_id=label,
                                law_id2=point_id
                            )
                    
                    #Handle Subpoint
                    for subpoint in point.get("subpoints", []):
                        subpoint_id = f"{point_id}_SP_{subpoint.get('subpoint', '?')}"
                        subpoint_text = get_text(subpoint, "text")
                        
                        root = None
                        ref = None
                        second_entity = []
                        
                        dml_ddl_neo4j(
                            f"""
                            MERGE (sp:Subpoint:{ns_label} {{id: $id}})
                            SET sp.text = $text
                            WITH sp
                            MATCH (p:Point:{ns_label} {{id: $point_id}})
                            MERGE (p)-[:HAS_SUBPOINT]->(sp)
                            """,
                            id=subpoint_id,
                            text=subpoint_text,
                            point_id=point_id,
                        )
                        
                        #Extract relation
                        re_text = sent_tokenize(subpoint_text)
                        for sentence in re_text:
                            root = None
                            re_temp = self.final_re.final_relation(sentence)

                            if len(re_temp['document_id']) > 0:
                                _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)

                            if 'này' in sentence.split():
                                words = sentence.split()
                                root = None
                                ref = None
                                for i, token in enumerate(words):
                                    if token == "này" and i > 0:
                                        prev_word = words[i-1]
                                        if prev_word.lower() in self_check.keys():
                                            text_type = self_check[prev_word.lower()]
                                            match text_type:
                                                case "doc1":
                                                    root = metadata["law_id"]
                                                    ref = "Luật"
                                                case "doc2":
                                                    root = metadata["law_id"]
                                                    ref = "Nghị_định"
                                                case "doc3":
                                                    root = metadata["law_id"]
                                                    ref = "Thông_tư"
                                                case "doc4":
                                                    root = metadata["law_id"]
                                                    ref = "Nghị_quyết"
                                                case "chapter":
                                                    root = chapter_id
                                                case "clause":
                                                    root = clause_id
                                                case "point":
                                                    root = point_id
                                            if root is not None:
                                                _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)
                                            else:
                                                second_entity = []        
                            if not second_entity or not relation:
                                        continue                            
                            for entity in second_entity or []:
                                if (list(entity.keys())[0] == None) or list(entity.values())[0] is None:
                                    continue
                                label = list(entity.keys())[0]       
                                ref_type = ref if list(entity.values())[0] == 'Document' else list(entity.values())[0]

                                dml_ddl_neo4j(
                                    f"""
                                    MERGE (l:`{ref_type}`:`{ns_label}` {{id: $law_id}})
                                    WITH l
                                    MATCH (r:Subpoint:`{ns_label}` {{id: $law_id2}})
                                    MERGE (r)-[:`{relation}`]->(l)
                                    """,
                                    law_id=label,
                                    law_id2=subpoint_id
                                )
                        
                        # Handle SubSubpoints (a.1))
                        for ssp in subpoint.get("subsubpoints", []):
                            ssp_id = f"{subpoint_id}_SSP_{ssp.get('subsubpoint', '?')}"
                            ssp_text = get_text(ssp, "text")
                            
                            root = None
                            ref = None
                            second_entity = []

                            dml_ddl_neo4j(
                                f"""
                                MERGE (ssp:Subsubpoint:{ns_label} {{id: $id}})
                                SET ssp.text = $text
                                WITH ssp
                                MATCH (sp:Subpoint:{ns_label} {{id: $subpoint_id}})
                                MERGE (sp)-[:HAS_SUBSUBPOINT]->(ssp)
                                """,
                                id=ssp_id,
                                text=ssp_text,
                                subpoint_id=subpoint_id,
                            )
                            
                            #Extract relation
                            re_text = sent_tokenize(ssp_text)
                            for sentence in re_text:
                                root = None
                                re_temp = self.final_re.final_relation(sentence)

                                if len(re_temp['document_id']) > 0:
                                    _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)

                                if 'này' in sentence.split():
                                    words = sentence.split()
                                    root = None
                                    ref = None
                                    for i, token in enumerate(words):
                                        if token == "này" and i > 0:
                                            prev_word = words[i-1]
                                            if prev_word.lower() in self_check.keys():
                                                text_type = self_check[prev_word.lower()]
                                                match text_type:
                                                    case "doc1":
                                                        root = metadata["law_id"]
                                                        ref = "Luật"
                                                    case "doc2":
                                                        root = metadata["law_id"]
                                                        ref = "Nghị_định"
                                                    case "doc3":
                                                        root = metadata["law_id"]
                                                        ref = "Thông_tư"
                                                    case "doc4":
                                                        root = metadata["law_id"]
                                                        ref = "Nghị_quyết"
                                                    case "chapter":
                                                        root = chapter_id
                                                    case "clause":
                                                        root = clause_id
                                                    case "point":
                                                        root = point_id
                                                if root is not None:
                                                    _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)
                                                else:
                                                    second_entity = []        
                                if not second_entity or not relation:
                                        continue                              
                                for entity in second_entity or []:
                                    if (list(entity.keys())[0] == None) or list(entity.values())[0] is None:
                                        continue
                                    label = list(entity.keys())[0]       
                                    ref_type = ref if list(entity.values())[0] == 'Document' else list(entity.values())[0]
                                    
                                    dml_ddl_neo4j(
                                        f"""
                                        MERGE (l:`{ref_type}`:`{ns_label}` {{id: $law_id}})
                                        WITH l
                                        MATCH (r:Subsubpoint:`{ns_label}` {{id: $law_id2}})
                                        MERGE (r)-[:`{relation}`]->(l)
                                        """,
                                        law_id=label,
                                        law_id2=ssp_id
                                    )

                            # Handle SubSubSubpoints (a.1.1))
                            for sssp in ssp.get("subsubsubpoints", []):
                                sssp_id = f"{ssp_id}_SSSP_{sssp.get('subsubsubpoint', '?')}"
                                sssp_text = get_text(sssp, "text")
                                
                                root = None
                                ref = None
                                second_entity = []

                                dml_ddl_neo4j(
                                    f"""
                                    MERGE (sssp:Subsubsubpoint:{ns_label} {{id: $id}})
                                    SET sssp.text = $text
                                    WITH sssp
                                    MATCH (ssp:Subsubpoint:{ns_label} {{id: $ssp_id}})
                                    MERGE (ssp)-[:HAS_SUBSUBSUBPOINT]->(sssp)
                                    """,
                                    id=sssp_id,
                                    text=sssp_text,
                                    ssp_id=ssp_id,
                                )
                                
                                #Extract relation
                                re_text = sent_tokenize(sssp_text)
                                for sentence in re_text:
                                    root = None
                                    re_temp = self.final_re.final_relation(sentence)

                                    if len(re_temp['document_id']) > 0:
                                        _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)

                                    if 'này' in sentence.split():
                                        words = sentence.split()
                                        root = None
                                        ref = None
                                        for i, token in enumerate(words):
                                            if token == "này" and i > 0:
                                                prev_word = words[i-1]
                                                if prev_word.lower() in self_check.keys():
                                                    text_type = self_check[prev_word.lower()]
                                                    match text_type:
                                                        case "doc1":
                                                            root = metadata["law_id"]
                                                            ref = "Luật"
                                                        case "doc2":
                                                            root = metadata["law_id"]
                                                            ref = "Nghị_định"
                                                        case "doc3":
                                                            root = metadata["law_id"]
                                                            ref = "Thông_tư"
                                                        case "doc4":
                                                            root = metadata["law_id"]
                                                            ref = "Nghị_quyết"
                                                        case "chapter":
                                                            root = chapter_id
                                                        case "clause":
                                                            root = clause_id
                                                        case "point":
                                                            root = point_id
                                                    if root is not None:
                                                        _, relation, second_entity = self.final_re.extract_relation_entities(sentence, root)
                                                    else:
                                                        second_entity = []        
                                    if not second_entity or not relation:
                                        continue                          
                                    for entity in second_entity or []:
                                        if (list(entity.keys())[0] == None) or list(entity.values())[0] is None:
                                            continue
                                        label = list(entity.keys())[0]       
                                        ref_type = ref if list(entity.values())[0] == "Document" else list(entity.values())[0] 

                                        dml_ddl_neo4j(
                                            f"""
                                            MERGE (l:`{ref_type}`:`{ns_label}` {{id: $law_id}})
                                            WITH l
                                            MATCH (r:Subsubsubpoint:`{ns_label}` {{id: $law_id2}})
                                            MERGE (r)-[:`{relation}`]->(l)
                                            """,
                                            law_id=label,
                                            law_id2=sssp_id
                                        )

        # Cleanup temporary "no_chapter" node
        dml_ddl_neo4j(
            f"""
            MATCH (ch:Chapter:{ns_label})
            WHERE ch.id ENDS WITH "_no_chapter"
            DETACH DELETE ch
            """
        )