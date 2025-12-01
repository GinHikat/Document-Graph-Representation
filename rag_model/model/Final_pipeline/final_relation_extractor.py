import re
import pandas as pd
import numpy as np
import os, sys
from underthesea import sent_tokenize
import unicodedata
from copy import deepcopy

class Extractor:
    def __init__(self, ner, re_model):
        self.ner = ner
        self.re_model = re_model
        
    check_mask = ['luật', 'thông', 'nghị', 'hiến', 'quyết', 'định', 'pháp', 'tư', 'điều', 'mục', 'phần', 'khoản', 'điểm']
    
    mapping = {'chapter': 'chương', 'clause': 'điều', 'point': 'khoản', 'subpoint': 'điểm', 'subsubpoint': 'điểm', 'subsubsubpoint': 'điểm'}

    splitting_char = re.compile(r'\s*(,|\bvà\b|\bhoặc\b)\s*', re.IGNORECASE)
    hierarchy_range = re.compile(r'(điều|khoản|điểm|chương)\s*(\d+|[a-z])\s*đến\s*\1\s*(\d+|[a-z])', re.IGNORECASE)
    number = re.compile(r'^\d+$')
    word = re.compile(r'^[a-z]$')
    
    hierarchy_word = {
        'chapter': re.compile(r'chương\s*([ivxlcdm\d]+)', re.IGNORECASE),
        'clause':  re.compile(r'điều\s*(\d+)', re.IGNORECASE),
        'point':   re.compile(r'khoản\s*(\d+)', re.IGNORECASE),
        'subpoint':re.compile(r'điểm\s*([a-z])', re.IGNORECASE),
        'subsubpoint':re.compile(r'điểm\s*([a-z]\.\d+)', re.IGNORECASE),
        'subsubsubpoint':re.compile(r'điểm\s*([a-z]\.\d+\.\d+)', re.IGNORECASE)
    }

    def final_relation_check(self, text, df):
        
        check_mask = ['luật', 'thông', 'nghị', 'hiến', 'quyết', 'định', 'pháp', 'tư', 'điều', 'mục', 'phần', 'khoản', 'điểm']
        re_result = self.re_model.predict(text)
        ner_result = self.ner.extract_document_metadata(text)

        # Safety checks
        if re_result is None or 'Span' not in re_result.columns or re_result['Span'].isna().all():
            return df

        # Get a clean span string
        span = str(re_result['Span'].iloc[0]).lower()
        span_tokens = re.findall(r'\w+', span)

        # Rule check
        if any(token in check_mask for token in span_tokens):
            meta = ner_result[['issue_date', 'title', 'document_id', 'document_type']].iloc[:1].reset_index(drop=True)
            rel = re_result.iloc[:1].reset_index(drop=True)
            combined = pd.concat([rel, meta], axis=1)
            df = pd.concat([df, combined], ignore_index=True)

        return df
    
    def extract_sentences(self, text):
        sentences = []
        buffer = ""

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            if buffer:
                buffer += " " + line
            else:
                buffer = line

            # If the current line ends with ';', sentence is complete
            if line.endswith(';'):
                sentences.append(buffer.strip())
                buffer = ""

        # Append leftover if it doesn’t end with ;
        if buffer:
            sentences.append(buffer.strip())

        # Drop everything before the first "Căn cứ"
        for i, s in enumerate(sentences):
            if "Căn cứ" in s:
                idx = s.find("Căn cứ")
                sentences[i] = s[idx:].strip()
                sentences = sentences[i:]
                break

        return sentences      
        
    def final_relation(self, text):
        check_mask = ['luật', 'thông', 'nghị', 'hiến', 'quyết', 'định', 'pháp', 'tư', 'điều', 'mục', 'phần', 'khoản', 'điểm']

        # Take only the first sentence
        first_sent = sent_tokenize(text)[0]
        sents = self.extract_sentences(first_sent)

        df = pd.DataFrame(columns=['Text', 'Self Root', 'Relation', 'Span', 'issue_date', 'title', 'document_id', 'document_type'])

        # Proper filtering loop
        for sent in sents:
            df_meta = self.ner.extract_document_metadata(sent)
                # check if any keyword in check_mask appears in the sentence
            if (any(token in sent.lower() for token in check_mask)) and ((len(df_meta['document_id'].iloc[0]) > 0) or ('này' in sent.split())):
                df = self.final_relation_check(sent, df)
            else:
                continue
        
        if df.empty:
            return df
        
        df['document_id'] = df.apply(
            lambda row: 'HP' if 'Hiến Pháp' in row['title'] else row['document_id'],
            axis=1
        )
        
        return df   
        
    def to_roman(self,num):
        val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
        roman = ""
        i = 0
        while num > 0:
            for _ in range(num // val[i]):
                roman += syms[i]
                num -= val[i]
            i += 1
        return roman

    def parse_legal_ref(self, text, root=None):
        text = unicodedata.normalize("NFC", text)
        lower_text = text.lower()

        hierarchy = ["doc", "chapter", "C", "P", "SP", "SSP", "SSSP"]
        map_type = {
            "chapter": "Chapter",
            "C": "Clause",
            "P": "Point",
            "SP": "Subpoint",
            "SSP": "Subsubpoint",
            "SSSP": "Subsubsubpoint"
        }

        # --- 1) Parse existing root ---
        existing = {key: None for key in hierarchy}
        lowest_level_index = -1

        if root:
            root = re.sub(r'(.*)_doc_\1', r'\1', root)

            for m in re.finditer(r'(chapter|C|P|SP|SSP|SSSP)_([A-Za-z0-9.]+)', root):
                existing[m.group(1)] = m.group(2)

            doc_match = re.match(r'^([^_]+)', root)
            if doc_match and not re.search(r'(chapter|C|P|SP|SSP|SSSP)_', doc_match.group(1)):
                existing["doc"] = doc_match.group(1)

            for i, k in enumerate(hierarchy):
                if existing[k] is not None:
                    lowest_level_index = i

        # --- 2) Parse from text ---
        result = {k: None for k in hierarchy}
        result["SP"], result["SSP"], result["SSSP"] = [], [], []

        if root is None:
            m = re.search(r"số\s*([A-Za-z0-9/.\-Đđ]+)", text)
            if m:
                result["doc"] = m.group(1).upper()

        if m := re.search(r"chương\s*(\d+)", lower_text):
            result["chapter"] = self.to_roman(int(m.group(1)))

        if m := re.search(r"điều\s*(\d+)", lower_text):
            result["C"] = m.group(1)

        if m := re.search(r"khoản\s*(\d+)", lower_text):
            result["P"] = m.group(1)

        # Extract điểm (points)
        for match in re.findall(r"điểm\s*([a-z](?:\.\d+)*)(?=\)|\s|,|;|$)", lower_text):
            depth = match.count(".") + 1
            key = {1: "SP", 2: "SSP", 3: "SSSP"}.get(depth, "SP")
            result[key].append(match)

        # Normalize hierarchy
        def normalize_hierarchy(result_dict):
            def split(x): return x.split(".") if x else []

            for ref in result_dict["SSSP"]:
                parts = split(ref)
                if len(parts) >= 1 and not result_dict["SP"]:
                    result_dict["SP"].append(parts[0])
                if len(parts) >= 2 and not result_dict["SSP"]:
                    result_dict["SSP"].append(".".join(parts[:2]))

            for ref in result_dict["SSP"]:
                parts = split(ref)
                if len(parts) >= 1 and not result_dict["SP"]:
                    result_dict["SP"].append(parts[0])

            return result_dict

        result = normalize_hierarchy(result)

        # --- 3) Build final ---
        final = []

        # Add existing if any
        for level in ["doc", "chapter", "C", "P", "SP", "SSP", "SSSP"]:
            if existing[level]:
                final.append(f"{level}_{existing[level]}" if level != "doc" else existing[level])

        # Add new entities
        for i, level in enumerate(hierarchy):
            if i <= lowest_level_index:
                continue
            val = result[level]
            if val:
                if level in ["SP", "SSP", "SSSP"]:
                    final.extend(f"{level}_{v}" for v in val)
                else:
                    final.append(f"{level}_{val}" if i > 0 else f"{val}")

        # Remove duplicates
        seen = set()
        final = [x for x in final if not (x in seen or seen.add(x))]

        # --- 4) Return None if nothing recognized ---
        if not final:
            return None, None  # or return (None, "NoEntity") if preferred

        # Determine node type
        last = final[-1]
        prefix = last.split("_")[0]
        node_type = map_type.get(prefix, "Document")

        return "_".join(final), node_type

    def expand_ranges(self, text):
        # Handle ranges like "Điều 5 đến Điều 10" or "khoản a đến khoản d"
        

        def repl(m):
            lvl, s, e = m.group(1).lower(), m.group(2), m.group(3) #capture same level hierarchy word and their values
            if s.isdigit() and e.isdigit():
                s, e = int(s), int(e)
                return ', '.join(f'{lvl} {i}' for i in range(s, e + 1))
            elif s.isalpha() and e.isalpha():
                return ', '.join(f'{lvl} {chr(i)}' for i in range(ord(s), ord(e) + 1))
            return m.group(0)
        return self.hierarchy_range.sub(repl, text)

    def extract_entities(self, text): 
        '''
        Extract multiple entities from a multi-entities sentence in a raw text format
        '''
        
        check = ['điều', 'khoản', 'điểm']
        tokens = text.lower().split()
        if not any(word in tokens for word in check):
            return text

        else: 
            text = text.lower().strip()
            text = self.expand_ranges(text)
            # Split with capture so we can detect separators directly
            levels = ['chapter', 'clause', 'point', 'subpoint', 'subsubpoint', 'subsubsubpoint'] if 'chương' in text else ['clause', 'point', 'subpoint', 'subsubpoint', 'subsubsubpoint']

            # Split with capture so we can detect separators directly
            tokens = self.splitting_char.split(text)
            segments = []
            for i in range(0, len(tokens), 2):
                seg = tokens[i].strip()
                sep = tokens[i+1].strip() if i+1 < len(tokens) else None
                segments.append((seg, sep))

            results, last_levels = [], {lvl: None for lvl in levels}
            last_anchor_level = None

            for seg, sep in segments:
                if not seg:
                    continue

                # detect anchors
                anchors_found = {}
                for lvl in levels:
                    matches = self.hierarchy_word[lvl].findall(seg)
                    if matches:
                        val = matches[-1]
                        if lvl in ('clause', 'point'):
                            try: val = int(val)
                            except: pass
                        anchors_found[lvl] = val

                # If segment has anchor(s)
                if anchors_found:
                    entity = deepcopy(last_levels)
                    for lvl in levels:
                        if lvl in anchors_found:
                            entity[lvl] = anchors_found[lvl]
                            # clear lower levels
                            for l in levels[levels.index(lvl)+1:]:
                                entity[l] = None
                    results.append({k: v for k, v in entity.items() if v is not None})
                    last_anchor_level = next(iter(anchors_found))
                    for lvl in levels:
                        if entity.get(lvl) is not None:
                            last_levels[lvl] = entity[lvl]

                else:
                    # bare number or letter segment
                    tokens2 = re.split(r'\s+', seg)
                    for t in tokens2:
                        if not t:
                            continue
                        if self.number.match(t):
                            assign_level = last_anchor_level or levels[0]
                            entity = deepcopy(last_levels)
                            val = int(t)
                            entity[assign_level] = val
                            for l in levels[levels.index(assign_level)+1:]:
                                entity[l] = None
                            results.append({k: v for k, v in entity.items() if v is not None})
                            last_levels[assign_level] = val
                        elif self.word.match(t): #and last_anchor_level in ['subpoint', 'subsubpoint', 'subsubsubpoint']:
                            assign_level = 'subpoint' if 'subpoint' in levels else levels[-1]
                            entity = deepcopy(last_levels)
                            entity[assign_level] = t
                            results.append({k: v for k, v in entity.items() if v is not None})
                            last_levels[assign_level] = t
                            last_anchor_level = assign_level

                # Reset context if highest-level entity ends with a splitting character
                if sep and any(lvl in anchors_found for lvl in ('chapter', 'clause')):
                    for lvl in levels:
                        last_levels[lvl] = None
                    last_anchor_level = None
            
            # Fix missing higher-level linkage (lookahead propagation)
            final_results = []
            for i, e in enumerate(results):
                # if a sub-level exists without its parent
                if 'subsubsubpoint' in e or 'subsubpoint' in e or 'subpoint' in e:
                    if 'point' not in e or 'clause' not in e:
                        for j in range(i + 1, len(results)):
                            future = results[j]
                            if 'point' in future and 'point' not in e:
                                e['point'] = future['point']
                            if 'clause' in future and 'clause' not in e:
                                e['clause'] = future['clause']
                            # stop once we’ve filled both
                            if 'clause' in e and 'point' in e:
                                break

                # if a point exists but no clause, link to next clause
                elif 'point' in e and 'clause' not in e:
                    for j in range(i + 1, len(results)):
                        future = results[j]
                        if 'clause' in future:
                            e['clause'] = future['clause']
                            break

                final_results.append(e)

            map_list = []    
            
            df_meta = self.ner.extract_document_metadata(text)
            doc_id = df_meta['document_id'].iloc[0] if df_meta['document_id'] is not None else None
            
            for pair in final_results:
                result = ''
                for key, value in pair.items():
                    if key in self.mapping:
                        temp = f'{self.mapping[key]} {str(value)}'
                        
                    result += f'{temp} '
                    
                result += f'văn bản số {doc_id}' if doc_id else ''
                        
                map_list.append(result.strip())
                
            return map_list
    
    def extract_relation_entities(self, text, root=None):
        """
        Return: self-root, relation type, list of {entity: ref_type}
        root: input root node id for 'này' (this) cases
        """
        text = text.lower().strip()
        df_relation = self.final_relation(text)
        self_root = df_relation['Self Root'].iloc[0] if not df_relation.empty else None
        relation = df_relation['Relation'].iloc[0] if not df_relation.empty else None

        entities = self.extract_entities(text)
        mapped_entities = []

        if len(entities) > 0:
            for ent in entities:
                parsed_ref, ref_type = self.parse_legal_ref(ent, root)
                mapped_entities.append({parsed_ref: ref_type})
        elif root:
            # fallback to root if no entities
            parsed_ref, ref_type = self.parse_legal_ref(text, root)
            mapped_entities.append({parsed_ref: ref_type})
        else:
            mapped_entities.append({None: None})

        return self_root, relation, mapped_entities
