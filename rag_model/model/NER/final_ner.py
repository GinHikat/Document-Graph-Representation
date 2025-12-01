import torch
import torch.nn as nn
from torchcrf import CRF
import json
import re
import pandas as pd
import unicodedata
from underthesea import sent_tokenize

class MaskedAttention(nn.Module):
    def __init__(self, hidden_dim):
        super().__init__()
        self.attn = nn.Linear(hidden_dim, 1)

    def forward(self, lstm_out, mask):
        scores = self.attn(lstm_out).squeeze(-1)
        scores = scores.masked_fill(mask == 0, -1e9)
        attn_weights = torch.softmax(scores, dim=1).unsqueeze(-1)
        context = torch.sum(lstm_out * attn_weights, dim=1, keepdim=True)
        return lstm_out + context.expand_as(lstm_out)

class BiLSTM_CRF(nn.Module):
    def __init__(self, vocab_size, tagset_size, embedding_dim=128, hidden_dim=256,
                 num_layers=2, dropout=0.25, pad_idx=0):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=pad_idx)
        self.embedding_dropout = nn.Dropout(dropout)

        self.bilstm = nn.LSTM(
            embedding_dim,
            hidden_dim // 2,
            num_layers=num_layers,
            bidirectional=True,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )

        self.layer_norm = nn.LayerNorm(hidden_dim)
        self.attention = MaskedAttention(hidden_dim)
        self.hidden_fc = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        self.fc = nn.Linear(hidden_dim, tagset_size)
        self.crf = CRF(tagset_size, batch_first=True)

    def forward(self, x, tags=None, mask=None):
        if mask is None:
            mask = (x != self.embedding.padding_idx).type(torch.bool)
        mask[:, 0] = 1

        embeddings = self.embedding(x)
        embeddings = self.embedding_dropout(embeddings)

        lstm_out, _ = self.bilstm(embeddings)
        lstm_out = self.layer_norm(lstm_out)
        lstm_out = self.attention(lstm_out, mask)
        lstm_out = self.hidden_fc(lstm_out)
        emissions = self.fc(lstm_out)

        if tags is not None:
            log_likelihood = self.crf(emissions, tags, mask=mask)
            return -log_likelihood.mean()
        else:
            return self.crf.decode(emissions, mask=mask)

class NER:
    def __init__(self, model_path, token2idx_path, label2idx_path, annotator, device="cpu"):
        """
        Initialize and load model + dictionaries.
        """
        self.device = torch.device(device)
        
        self.annotator = annotator
    
        with open(token2idx_path, "r", encoding="utf-8") as f:
            self.token2idx = json.load(f)
        with open(label2idx_path, "r", encoding="utf-8") as f:
            self.label2idx = json.load(f)
        self.idx2label = {v: k for k, v in self.label2idx.items()}

        self.model = BiLSTM_CRF(
            vocab_size=len(self.token2idx),
            tagset_size=len(self.label2idx),
            embedding_dim=128,
            hidden_dim=256,
            num_layers=2,
            dropout=0.3,
            pad_idx=self.token2idx["<PAD>"]
        ).to(self.device)

        # Load trained weights
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()

    #  Tokenization & Prediction 
    def _tokenize(self, text):
        return re.findall(r"\w+|[^\w\s]", text.lower(), re.UNICODE)

    def _prepare_input(self, tokens):
        X = [self.token2idx.get(tok, self.token2idx["<UNK>"]) for tok in tokens]
        X_tensor = torch.tensor([X], dtype=torch.long).to(self.device)
        mask = (X_tensor != self.token2idx["<PAD>"]).to(torch.bool)
        return X_tensor, mask

    def predict(self, sentence):
        tokens = self._tokenize(sentence)
        X_tensor, mask = self._prepare_input(tokens)
        with torch.no_grad():
            preds = self.model(X_tensor, mask=mask)[0]
            preds = preds[:len(tokens)]
        labels = [self.idx2label[p] for p in preds]
        return tokens, labels

    #  Utility / Cleaning Helpers 
    @staticmethod
    def merge_entities(tokens, labels):
        entities, current_tokens, current_type = [], [], None
        for tok, lbl in zip(tokens, labels):
            if lbl.startswith("B-"):
                if current_tokens:
                    entities.append((" ".join(current_tokens), current_type))
                current_tokens = [tok]
                current_type = lbl[2:]
            elif lbl.startswith("I-") and current_tokens:
                current_tokens.append(tok)
            else:
                if current_tokens:
                    entities.append((" ".join(current_tokens), current_type))
                    current_tokens, current_type = [], None
        if current_tokens:
            entities.append((" ".join(current_tokens), current_type))
        return entities

    @staticmethod
    def normalize_text(text):
        if not text:
            return None
        text = re.sub(r"\s+", " ", text.strip())
        text = text.replace("–", "-").replace("_", " ")
        text = re.sub(r"[-–—,:;.\s]+$", "", text)
        return text

    @staticmethod
    def merge_fragmented(text):
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

    @staticmethod
    def normalize_date(text):
        if not text:
            return None
        text = text.strip().lower().replace("–", "-").replace("_", " ")
        match_vn = re.search(r"ngày\s*(\d{1,2})\D+tháng\s*(\d{1,2})\D+năm\s*(\d{2,4})", text)
        if match_vn:
            d, m, y = match_vn.groups()
            if len(y) == 2:
                y = "20" + y
            return f"{d.zfill(2)}/{m.zfill(2)}/{y}"
        match_num = re.search(r"(\d{1,2})[^\d]+(\d{1,2})(?:[^\d]+(\d{2,4}))?", text)
        if match_num:
            d, m, y = match_num.groups()
            if y:
                if len(y) == 2:
                    y = "20" + y
                return f"{d.zfill(2)}/{m.zfill(2)}/{y}"
            return f"{d.zfill(2)}/{m.zfill(2)}"
        return re.sub(r"\s+", " ", text.strip())

    @staticmethod
    def extract_abbreviation(text):
        def remove_accents(s):
            return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
        parts = remove_accents(text).strip().split()
        return ''.join(p[0].upper() for p in parts if p)

    @staticmethod
    def clean_document_id(id_str):
        if not isinstance(id_str, str):
            return id_str
        id_str = id_str.lower().strip()
        replacements = {
            r'cpu\b': 'cp', r'qhu\b': 'qh', r'bnvu\b': 'bnv',
            r'bkhu\b': 'bkh', r'ttu\b': 'tt', r'nhnnvn': 'nhnn', r'bkhvcn': 'bkhcn'
        }
        for pattern, repl in replacements.items():
            id_str = re.sub(pattern, repl, id_str)
        return id_str

    @staticmethod
    def to_upper_alnum(text):
        if not isinstance(text, str):
            return text
        return re.sub(r'[a-zA-ZÀ-ỹ]', lambda m: m.group(0).upper(), text)

    #  METADATA EXTRACTION 
    def extract_document_metadata(self, text):

        raw_text = text.strip()
        if not raw_text:
            return pd.DataFrame([{}])

        sentences = sent_tokenize(raw_text)
        if not sentences:
            return pd.DataFrame([{}])

        first_sentence, last_sentence = sentences[0], sentences[-1]

        # Predict NER on first sentence
        tokens, labels = self.predict(first_sentence)
        entities = self.merge_entities(tokens, labels)

        # Predict NER on last sentence
        last_tokens, last_labels = self.predict(last_sentence)
        last_entities = self.merge_entities(last_tokens, last_labels)

        metadata = {
            "issuer_department": None,
            "issue_date": None,
            "title": None,
            "location": None,
            "document_id": None,
            "issuer": None,
            "document_type": None,
        }

        # Extract from first sentence
        seen_loc = 0
        for text_, etype in entities:
            if etype == "DEP" and metadata["issuer_department"] is None:
                metadata["issuer_department"] = self.normalize_text(text_)
            elif etype == "DAT" and metadata["issue_date"] is None:
                metadata["issue_date"] = self.normalize_date(text_)
            elif etype == "LOC":
                seen_loc += 1
                if seen_loc == 2 and metadata["location"] is None:
                    metadata["location"] = self.normalize_text(text_)
            elif etype == "DOCID" and metadata["document_id"] is None:
                docid_candidate = re.sub(r"\s+", "", self.normalize_text(text_))
                tokens_in_text = first_sentence.split()
                expanded_docid = None
                for tok in tokens_in_text:
                    tok_clean = re.sub(r"[^\w/\-]", "", tok)
                    if "-" in tok_clean and docid_candidate.lower() in tok_clean.lower():
                        expanded_docid = tok_clean
                        break
                metadata["document_id"] = (
                    re.sub(r"\s+", "", self.normalize_text(expanded_docid))
                    if expanded_docid else docid_candidate
                )

        # Auto-fill missing year in issue_date
        if metadata.get("issue_date") and metadata.get("document_id"):
            date_str = metadata["issue_date"]
            if date_str.count("/") == 1:
                try:
                    year_part = metadata["document_id"].split("/")[1]
                    metadata["issue_date"] = f"{date_str}/{year_part}"
                except Exception:
                    pass

        # Default location to Hà Nội
        if not metadata["location"]:
            metadata["location"] = "Hà Nội"

        # Title & Document Type Extraction
        title_keywords = ["luật", "nghị quyết", "nghị định", "thông tư",
                        "quyết định", "chỉ thị", "hướng dẫn", 'hiến pháp']

        # Mark all title_keywords as B-TIT
        for i, tok in enumerate(tokens):
            if tok.lower() in [kw.split()[0] for kw in title_keywords]:
                labels[i] = "B-TIT"

        # Find first B-TIT token
        first_b_tit_idx = next((i for i, lbl in enumerate(labels) if lbl == "B-TIT"), None)

        if first_b_tit_idx is not None:
            # Get the token that starts the title
            title_start_token = tokens[first_b_tit_idx]

            # Find the start of this token in the raw text
            start_idx = first_sentence.lower().find(title_start_token.lower())
            if start_idx == -1:
                start_idx = 0 

            can_idx = first_sentence.lower().find("căn", start_idx)
            end_idx = can_idx if can_idx != -1 else len(first_sentence)

            expanded_title = first_sentence[start_idx:end_idx].replace("\n", " ").strip()
            metadata["title"] = expanded_title

            # Determine document_type
            for kw in title_keywords:
                if expanded_title.lower().startswith(kw):
                    metadata["document_type"] = kw.capitalize()
                    break

        # Handle second "Luật" occurrence
        if (metadata.get("document_type") or "").lower() == "luật":
            luat_indices = [i for i, t in enumerate(tokens) if t.lower() == "luật"]
            if len(luat_indices) >= 2:
                start_idx = luat_indices[1]
                end_idx = start_idx
                for k in range(start_idx + 1, len(tokens)):
                    if labels[k].endswith("TIT"):
                        end_idx = k
                    else:
                        if (end_idx - start_idx + 1) < 5:
                            end_idx = min(start_idx + 4, len(tokens) - 1)
                        break
                metadata["title"] = self.normalize_text(" ".join(tokens[start_idx:end_idx + 1]))

        # Ensure title starts with document_type
        if metadata["title"] and metadata["document_type"]:
            title_lower = metadata["title"].lower()
            doc_type_lower = metadata["document_type"].lower()
            if not title_lower.startswith(doc_type_lower):
                metadata["title"] = f"{metadata['document_type']} {metadata['title']}"

        # Extract issuer using VnCoreNLP
        try:
            if self.annotator:
                annotated = self.annotator.annotate(last_sentence)
                persons, current_name = [], []
                for sent in annotated["sentences"]:
                    for word_info in sent:
                        label = word_info.get("nerLabel")
                        token = word_info.get("form", "").replace("_", " ")
                        if label == "B-PER":
                            if current_name:
                                persons.append(" ".join(current_name))
                            current_name = [token]
                        elif label == "I-PER" and current_name:
                            current_name.append(token)
                        else:
                            if current_name:
                                persons.append(" ".join(current_name))
                                current_name = []
                if current_name:
                    persons.append(" ".join(current_name))

                if persons:
                    metadata["issuer"] = self.normalize_text(persons[-1])
                else:
                    metadata["issuer"] = "UNKNOWN"

                if len(metadata["issuer"].split()) == 1:
                    metadata["issuer"] = "UNKNOWN"
            else: metadata["issuer"] = "UNKNOWN"

        except Exception as e:
            print(f"[WARN] VnCoreNLP extraction failed: {e}")
            metadata["issuer"] = "UNKNOWN"

        # Final formatting
        df = pd.DataFrame([metadata])
        for col in metadata.keys():
            df[col] = df[col].fillna("")

        ids = df["document_id"].astype(str).str.strip()
        mask = ids.str.split("/").str[-1].apply(lambda x: len(x) <= 2)
        issuer = (
            df["issuer_department"]
            .astype(str).str.strip()
            .apply(self.extract_abbreviation)
            .str.lower()
        )
        df.loc[mask & (issuer != ""), "document_id"] = ids[mask] + "-" + issuer[mask]

        df["document_id"] = df["document_id"].apply(self.clean_document_id)
        df["document_id"] = df["document_id"].apply(self.to_upper_alnum)
        
        #final check of document_id to truncate duplicated end
        parts = df['document_id'].iloc[0].split('/')
        last_part = parts[-1]
        
        hyphen_split = last_part.split('-')
        
        # If all entities equal and there was at least one '-'
        if len(hyphen_split) > 1 and len(set(hyphen_split)) == 1:
            last_part = hyphen_split[0]  # remove the repeated suffix
        
        # Reconstruct document_id
        df['document_id'] = '/'.join(parts[:-1] + [last_part])
        
        df = df.map(lambda x: self.merge_fragmented(x) if isinstance(x, str) else x)

        title_cols = ["issuer_department", "title", "location", "issuer", "document_type"]
        df[title_cols] = df[title_cols].apply(lambda col: col.apply(lambda x: x.title() if isinstance(x, str) else x))
        df = df.map(lambda x: x.rstrip(';, .') if isinstance(x, str) else x)
        
        df.loc[df['document_type'] == 'Hiến pháp', 'document_id'] = 'HP'
        
        #Final add of amending document
        if "sửa đổi" in df['title'].iloc[0].lower():
            df['amend'] = True
        else:
            df['amend'] = False

        return df
