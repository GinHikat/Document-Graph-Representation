# from underthesea import word_tokenize
import re
import pandas as pd

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional
from transformers import AutoModel, AutoTokenizer

import sys, os
import difflib
import math

project_root = os.path.abspath(os.path.join(os.getcwd(), "../../.."))
if project_root not in sys.path:
    sys.path.append(project_root)

from shared_functions.global_functions import *
from shared_functions.gg_sheet_drive import *

os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TRANSFORMERS_NO_FLAX"] = "1"
os.environ["TRANSFORMERS_NO_JAX"] = "1"
os.environ["TRANSFORMERS_NO_VISION"] = "1"


# Support functions 
def build_legal_mask(text):
    tokens = tokenizer.tokenize(text.lower())
    n = len(tokens)
    M = torch.zeros((n, n), dtype=torch.int)

    single = {'luật', 'pháp', 'điều', 'chương', 'khoản', 'mục'}
    anchors = {"nghị", "thông", "quyết", "hiến", "luật", "pháp"}
    followers = {"định", "quyết", "tư", "pháp", "lệnh"}

    for i, tok in enumerate(tokens):
        # mark single-word types like "luật", "pháp"
        if tok in single:
            M[i, i] = 1
        # mark legal multiword combos (anchor + follower)
        if tok in anchors and i + 1 < n:
            if tokens[i + 1] in followers:
                M[i, i] = 1
                M[i + 1, i + 1] = 1
                M[i, i + 1] = 1
                M[i + 1, i] = 1
    
    M = 0.1 + 0.9 * M #rescale so that non-legal token can still attend

    return tokens, M

class PhoBertEmbedding(nn.Module):
    def __init__(self, model_name="vinai/phobert-base", device=None, freeze=False, max_length = 256):
        super().__init__()
        
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
        self.model = AutoModel.from_pretrained(model_name).to(self.device)
        
        self.max_length = max_length
        
        if freeze:
            for p in self.model.parameters():
                p.requires_grad = False

    def encode(self, texts):
        toks = self.tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length = self.max_length)
        input_ids = toks["input_ids"].to(self.device)
        attention_mask = toks["attention_mask"].to(self.device)
        outputs = self.model(input_ids=input_ids, attention_mask=attention_mask, return_dict=True)
        # last_hidden_state: (batch, seq_len, hidden)
        return outputs.last_hidden_state, attention_mask, toks
    
    #only different by name but for Module usage
    def forward(self, texts):
        toks = self.tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length = self.max_length)
        input_ids = toks["input_ids"].to(self.device)
        attention_mask = toks["attention_mask"].to(self.device)

        with torch.set_grad_enabled(not self.model.training):
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask, return_dict=True)

        return outputs.last_hidden_state, attention_mask, toks
    
class SimpleTokenizer:
    def __init__(self):
        self.pad_token = "<pad>"
        self.cls_token = "<cls>"
        self.sep_token = "<sep>"
        self.unk_token = "<unk>"
        self.pad_token_id = 0
        self.cls_token_id = 1
        self.sep_token_id = 2
        self.unk_token_id = 3

    def tokenize(self, text):
        return text.split()

    def encode(self, text, max_length=256, padding=True, truncation=True, return_tensors=None):
        tokens = [self.cls_token] + text.split()[: max_length - 2] + [self.sep_token]
        input_ids = list(range(len(tokens)))  # dummy token ids
        attention_mask = [1] * len(input_ids)

        if padding and len(input_ids) < max_length:
            pad_len = max_length - len(input_ids)
            input_ids += [self.pad_token_id] * pad_len
            attention_mask += [0] * pad_len

        if return_tensors == "pt":
            import torch
            input_ids = torch.tensor([input_ids])
            attention_mask = torch.tensor([attention_mask])

        return {"input_ids": input_ids, "attention_mask": attention_mask}

    def __call__(self, text, **kwargs):
        return self.encode(text, **kwargs)

class RelativePositionBias(nn.Module):
    """
    biases that are added to attention logits.
    """
    def __init__(self, max_distance, n_heads):
        super().__init__()
        self.max_distance = max_distance
        self.n_heads = n_heads
        # relative distances range from -max_distance..+max_distance -> 2*max_distance+1 buckets for exmple -8->8 to 0->16
        self.rel_emb = nn.Embedding(2 * max_distance + 1, n_heads)

    def forward(self, seq_len, device=None):
        device = device or next(self.rel_emb.parameters()).device
        # compute matrix of relative distances j - i
        idxs = torch.arange(seq_len, device=device)
        rel = idxs.unsqueeze(0) - idxs.unsqueeze(1)  # (seq, seq) with relative distances
        clipped = rel.clamp(-self.max_distance, self.max_distance) + self.max_distance #clip the values to positive range
        biases = self.rel_emb(clipped).permute(2, 0, 1)  # (n_heads, seq, seq) embedding for trainable
        return biases 

class SinusoidalPositionalEncoding(nn.Module):
    def __init__(self, dim: int, max_len: int = 5000):
        super().__init__()
        self.dim = dim

        # a long enough matrix of position encodings
        position = torch.arange(max_len).unsqueeze(1) #(max_len, 1)
        div_term = torch.exp(torch.arange(0, dim, 2) * (-math.log(10000.0) / dim))

        #sine/cosine positional encodings
        pe = torch.zeros(max_len, dim)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, dim)

        # Register as buffer (not a parameter, not updated by optimizer)
        self.register_buffer("pe", pe)

    def forward(self, seq_len: int, device=None):
        """
        Returns positional encodings for a sequence of length seq_len.
        Output shape: (1, seq_len, dim)
        """
        device = device or self.pe.device
        return self.pe[:, :seq_len].to(device)

class POSTag(nn.Module):
    def __init__(self, n_postags, n_heads):
        super().__init__()
        self.n_postags = int(n_postags)   # ensure integer type
        self.n_heads = n_heads
        self.bias_table = nn.Embedding(self.n_postags * self.n_postags, n_heads)

    def forward(self, postag_ids):
        postag_ids = postag_ids.long()

        B, L = postag_ids.shape
        tag_i = postag_ids.unsqueeze(2).expand(B, L, L)
        tag_j = postag_ids.unsqueeze(1).expand(B, L, L)

        pair_index = tag_i * self.n_postags + tag_j
        pair_index = pair_index.long()  

        bias = self.bias_table(pair_index)  # [B, L, L, n_heads]
        bias = bias.permute(0, 3, 1, 2).contiguous()
        return bias
    
## Encoder

class MultiHeadAttention(nn.Module):
    def __init__(self, dim, n_heads, dropout=0.1, pre_ln=True, use_rel_pos=True):
        super().__init__()
        self.dim = dim
        self.n_heads = n_heads
        self.d_k = dim // n_heads
        self.scale = self.d_k ** 0.5
        self.pre_ln = pre_ln
        self.use_rel_pos = use_rel_pos  

        self.W_q = nn.Linear(dim, dim)
        self.W_k = nn.Linear(dim, dim)
        self.W_v = nn.Linear(dim, dim)
        self.W_o = nn.Linear(dim, dim)
        self.norm = nn.LayerNorm(dim, eps=1e-6)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        query,
        context=None,
        pos_bias=None,     # expected from RelativePositionBias
        sinusoidal_pe=None, # expected from SinusoidalPositionalEncoding
        postag_bias=None,
        mask=None,
        lex_mask=None,
        multiplicative=False,
    ):
        if context is None:
            context = query  # self-attention
        residual = query

        if self.pre_ln:
            query = self.norm(query)

        if not self.use_rel_pos and sinusoidal_pe is not None:
            seq_len = query.size(1)
            query = query + sinusoidal_pe[:, :seq_len, :].to(query.device)
            context = context + sinusoidal_pe[:, :seq_len, :].to(context.device)

        B, L, _ = query.size()
        _, S, _ = context.size()

        Q = self.W_q(query).view(B, L, self.n_heads, self.d_k).transpose(1, 2)
        K = self.W_k(context).view(B, S, self.n_heads, self.d_k).transpose(1, 2)
        V = self.W_v(context).view(B, S, self.n_heads, self.d_k).transpose(1, 2)

        attn_logits = torch.matmul(Q, K.transpose(-2, -1)) / self.scale

        if self.use_rel_pos and pos_bias is not None:
            attn_logits = attn_logits + pos_bias.unsqueeze(0)

        if postag_bias is not None:
            B2, H2, Lp, _ = postag_bias.shape
            _, H, L, S = attn_logits.shape
            if Lp != L:
                if Lp < L:
                    pad_len = L - Lp
                    postag_bias = F.pad(postag_bias, (0, pad_len, 0, pad_len), value=0.0)
                else:
                    postag_bias = postag_bias[:, :, :L, :L]
            attn_logits = attn_logits + postag_bias


        # Lexicon masking
        if lex_mask is not None:
            lex_mask = lex_mask.unsqueeze(1).unsqueeze(2)
            attn_logits = attn_logits * lex_mask if multiplicative else attn_logits + lex_mask


        # Attention masking
        if mask is not None:
            mask = mask.unsqueeze(1).unsqueeze(2)
            attn_logits = attn_logits.masked_fill(mask == 0, float('-inf'))

        attn = F.softmax(attn_logits, dim=-1)
        attn = self.dropout(attn)

        out = torch.matmul(attn, V).transpose(1, 2).contiguous().view(B, L, self.dim)
        out = self.W_o(out)
        out = self.dropout(out)
        out = out + residual
        if not self.pre_ln:
            out = self.norm(out)

        return out, attn
    
class FeedForward(nn.Module):
    def __init__(self, dim: int, hidden_dim: int, dropout: float = 0.1):
        super().__init__()
        hidden_dim = hidden_dim or 4 * dim  # default expansion that hidden dim is 4 x model_dim
        self.norm = nn.LayerNorm(dim)
        self.fc1 = nn.Linear(dim, hidden_dim)
        self.act = nn.GELU()
        self.fc2 = nn.Linear(hidden_dim, dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        # Pre-LN + MLP + Residual
        residual = x
        x = self.norm(x)
        x = self.fc1(x)
        x = self.act(x)
        x = self.dropout(x)
        x = self.fc2(x)
        x = self.dropout(x)
        return residual + x #Skip connection
    
class TransformerEncoder(nn.Module):
    def __init__(
        self,
        dim,
        n_heads,
        dropout=0.1,
        ff_hidden_dim=None,
        max_distance=256,
        pre_ln=True,
        num_postags=None,
        use_rel_pos=True,    
        max_seq_len=5000         
    ):
        super().__init__()
        self.use_rel_pos = use_rel_pos

        # Attention + Feedforward
        self.attn = MultiHeadAttention(
            dim,
            n_heads,
            dropout=dropout,
            pre_ln=pre_ln,
            use_rel_pos=use_rel_pos   # pass toggle
        )
        self.ff = FeedForward(dim, hidden_dim=ff_hidden_dim, dropout=dropout)

        # Positional representations
        if use_rel_pos:
            self.pos_module = RelativePositionBias(max_distance=max_distance, n_heads=n_heads)
        else:
            self.pos_module = SinusoidalPositionalEncoding(dim, max_len=max_seq_len)

        # Optional POS-tag bias
        self.postag_bias = POSTag(n_postags=num_postags, n_heads=n_heads) if num_postags is not None else None

    def forward(self, x, postag_ids=None, lex_mask=None):
        seq_len = x.size(1)
        device = x.device

        # Get positional representation depending on mode

        if self.use_rel_pos:
            pos_rep = self.pos_module(seq_len, device=device)  # (n_heads, L, L)
            pos_kwargs = {"pos_bias": pos_rep, "sinusoidal_pe": None}
        else:
            pos_rep = self.pos_module(seq_len, device=device)  # (1, L, dim)
            pos_kwargs = {"pos_bias": None, "sinusoidal_pe": pos_rep}


        # Compute POS-tag bias if applicable
        postag_bias = None
        if self.postag_bias is not None and postag_ids is not None:
            postag_bias = self.postag_bias(postag_ids)  # (B, n_heads, L, L)
            postag_bias = postag_bias[..., :seq_len, :seq_len]

        #  Self-Attention
        x, _ = self.attn(
            query=x,
            context=None,
            postag_bias=postag_bias,
            lex_mask=lex_mask,
            **pos_kwargs   # dynamically pass correct positional arg
        )

        #  Feed Forward

        x = self.ff(x)
        return x
    
class StackedEncoder(nn.Module):
    def __init__(self,
                 dim=768,
                 n_heads=12,
                 ff_hidden_dim=2048,
                 dropout=0.1,
                 max_distance=128,
                 pre_ln=True,
                 num_postags=None,
                 use_rel_pos = True,
                 num_layers=6):  # number of encoder blocks
        super().__init__()

        # Stack of independent TransformerEncoder blocks
        self.layers = nn.ModuleList([
            TransformerEncoder(
                dim=dim,
                n_heads=n_heads,
                dropout=dropout,
                ff_hidden_dim=ff_hidden_dim,
                max_distance=max_distance,
                pre_ln=pre_ln,
                num_postags=num_postags,
                use_rel_pos = use_rel_pos
            )
            for _ in range(num_layers)
        ])

        # Final normalization — important if using pre-LN blocks (like your TransformerEncoder)
        self.final_norm = nn.LayerNorm(dim) if pre_ln else nn.Identity()

    def forward(self, x, postag_ids=None, lex_mask=None, output_hidden_states=False):

        hidden_states = []

        for layer in self.layers:
            x = layer(x, postag_ids=postag_ids, lex_mask=lex_mask)
            if output_hidden_states:
                hidden_states.append(x)

        # Apply normalization after all layers (for pre-LN Transformer)
        x = self.final_norm(x)

        if output_hidden_states:
            return x, hidden_states
        return x
    
class CombinedEmbedding(nn.Module):
    def __init__(self, phobert=None, transformer_encoder=None, alpha=0.5, use_phobert=False, max_len=256):
        super().__init__()
        self.use_phobert = use_phobert
        self.phobert = phobert if use_phobert else None
        self.encoder = transformer_encoder
        self.alpha = nn.Parameter(torch.tensor(alpha))  # learnable interpolation factor
        self.max_len = max_len

    def forward(self, texts, input_ids=None):
        batch_size = len(texts)
        device = next(self.encoder.parameters()).device
        seq_len = self.max_len
        hidden_dim = self.encoder.input_dim if hasattr(self.encoder, "input_dim") else 768

        if self.use_phobert and self.phobert is not None:
            pho_hidden, attn_mask, toks = self.phobert.encode(texts)
            # truncate/pad pho_hidden if needed
            if pho_hidden.size(1) > seq_len:
                pho_hidden = pho_hidden[:, :seq_len, :]
                attn_mask = attn_mask[:, :seq_len]
            elif pho_hidden.size(1) < seq_len:
                pad_len = seq_len - pho_hidden.size(1)
                pho_hidden = torch.cat([pho_hidden, torch.zeros(batch_size, pad_len, hidden_dim, device=device)], dim=1)
                attn_mask = torch.cat([attn_mask, torch.zeros(batch_size, pad_len, device=device)], dim=1)
        else:
            pho_hidden = torch.zeros(batch_size, seq_len, hidden_dim, device=device)
            attn_mask = torch.ones(batch_size, seq_len, device=device)
            toks = None

        trans_hidden = self.encoder(pho_hidden, postag_ids=None, lex_mask=attn_mask)
        alpha = torch.clamp(self.alpha, 0.0, 1.0)

        if not self.use_phobert:
            return trans_hidden, attn_mask, toks

        combined = alpha * pho_hidden + (1 - alpha) * trans_hidden
        return combined, attn_mask, toks
    
## Decoder

class BiLSTMEncoder(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers=1, dropout=0.0):
        super().__init__()
        self.bilstm = nn.LSTM(input_dim, hidden_dim // 2,
                              num_layers=num_layers,
                              dropout=dropout,
                              bidirectional=True,
                              batch_first=True)
    def forward(self, x):
        output, _ = self.bilstm(x)
        return output
    
class DecoderHeads(nn.Module):
    def __init__(self, hidden_dim, num_relations):
        super().__init__()
        self.self_root = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1)
        )

        self.relation = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, num_relations)
        )

        # span for start and end indices
        self.start = nn.Linear(hidden_dim, 1)
        self.end = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        # pool once for classification
        pooled = x.mean(dim=1)  #(batch_size, hidden_dim)

        self_root_logits = self.self_root(pooled).squeeze(-1)
        relation_logits = self.relation(pooled)

        # start and end idx
        start_logits = self.start(x).squeeze(-1)
        end_logits = self.end(x).squeeze(-1)

        return self_root_logits, relation_logits, start_logits, end_logits

class DecoderBody(nn.Module):
    def __init__(self,
                 hidden_dim=768,
                 num_heads=8,
                 ffn_dim=2048,
                 dropout=0.1,
                 pre_ln=True):
        super().__init__()
        self.cross_attn = MultiHeadAttention(hidden_dim, num_heads, dropout=dropout, pre_ln=pre_ln)
        self.bilstm = BiLSTMEncoder(hidden_dim, hidden_dim)
        self.ffn = FeedForward(hidden_dim, ffn_dim)
        self.norm = nn.LayerNorm(hidden_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, decoder_state, encoder_output, mask=None):
        # Project decoder_state to match encoder_output dim if needed
        if decoder_state.size(-1) != encoder_output.size(-1):
            project_to_dim = nn.Linear(decoder_state.size(-1), encoder_output.size([-1])).to(decoder_state.device)
            decoder_state = project_to_dim(decoder_state)

        # Ensure shape [B, L, D]
        if decoder_state.dim() == 2:
            decoder_state = decoder_state.unsqueeze(-1).repeat(1, 1, encoder_output.size(-1))

        # ---- Cross-Attention ----
        cross_out, _ = self.cross_attn(
            query=decoder_state,
            context=encoder_output,
            mask=mask
        )
        x = self.norm(cross_out + decoder_state)
        x = self.dropout(x)

        # ---- BiLSTM + FFN ----
        x = self.bilstm(x)
        x = self.ffn(x)

        return x  # [B, L, D]
    
class StackedDecoder(nn.Module):
    def __init__(self,
                 hidden_dim=768,
                 num_heads=8,
                 num_relations=10,
                 ffn_dim=2048,
                 dropout=0.1,
                 pre_ln=True,
                 num_layers=6,
                 recursive=False):
        super().__init__()

        # Stack of N DecoderBody blocks (no heads inside)
        self.layers = nn.ModuleList([
            DecoderBody(
                hidden_dim=hidden_dim,
                num_heads=num_heads,
                ffn_dim=ffn_dim,
                dropout=dropout,
                pre_ln=pre_ln
            )
            for _ in range(num_layers)
        ])

        # Final normalization after stacked layers
        self.final_norm = nn.LayerNorm(hidden_dim)

        # Shared decoder head
        self.head1 = DecoderHeads(hidden_dim, num_relations)
        # self.head2 = DecoderHeadCopy(hidden_dim, num_relations)
        self.recursive = recursive

    def forward(self, decoder_state, encoder_output, mask=None):
        """
        decoder_state: [B, L, D] or [B, L]
        encoder_output: [B, L, D]
        mask: [B, L] optional
        """

        x = decoder_state

        # Sequentially pass through each DecoderBody block
        for layer in self.layers:
            x = layer(x, encoder_output, mask)

        # Final normalization
        x = self.final_norm(x)

        # Apply the shared decoder head
        # if self.recursive:
        #     return self.head2(x)
            
        return self.head1(x)
    
class Transformer(nn.Module):
    def __init__(self,
                 phobert_embedder=None,
                 encoder=None,
                 decoder=None,
                 alpha=0.5,
                 use_phobert=False):
        super().__init__()

        self.use_phobert = use_phobert
        self.embedding = phobert_embedder  
        self.encoder = encoder              # Should be StackedEncoder
        self.decoder = decoder              # Should be StackedDecoder
        self.alpha = alpha

    def forward(self, texts, postag_ids):

        combined_output, attn_mask, toks = self.embedding(texts)
        # combined_output: (B, L, D)
        # attn_mask:      (B, L)

        #multi-block encoder
        encoded_output = self.encoder(
            combined_output,
            postag_ids=postag_ids,
            lex_mask=attn_mask
        )

        decoder_output = self.decoder(
            decoder_state=encoded_output,
            encoder_output=encoded_output,
            mask=attn_mask
        )


        # if StackedDecoder returns logits directly (root, rel, start, end), unpack them here:
        if isinstance(decoder_output, tuple) and len(decoder_output) == 4:
            root_logits, relation_logits, start_logits, end_logits = decoder_output
        else:
            # if stacked decoder only returns the last hidden state
            root_logits = relation_logits = start_logits = end_logits = None

        return {
            "self_root": root_logits,
            "relation": relation_logits,
            "start_logits": start_logits,
            "end_logits": end_logits,
            "mask": attn_mask,
            "tokens": toks
        }
        
class RE:
    def __init__(self, checkpoint, device = 'cpu', use_phobert = "False", id2relation = None, 
                 encoder_layer = 1, decoder_layer = 3, max_len = 128, use_rel_pos = True, freeze_train = False):
        self.checkpoint = checkpoint
        self.device = device
        self.use_phobert = use_phobert
        self.encoder_layer = encoder_layer
        self.decoder_layer = decoder_layer
        self.id2relation = id2relation
        self.max_len = max_len
        self.use_rel_pos = use_rel_pos
        self.freeze_train = freeze_train
        
    def detokenize_phobert_tokens(self, tokens):
        """
        Merge PhoBERT subword tokens (with '@@') back into readable text.
        """
        words = []
        current = ""
        for tok in tokens:
            if tok.endswith("@@"):
                current += tok[:-2]  
            else:
                current += tok
                words.append(current)
                current = ""
        return " ".join(words)
    
    def predict(self, text):
        if self.use_phobert:
            tokenizer = AutoTokenizer.from_pretrained('vinai/phobert-base')
            phobert = PhoBertEmbedding(freeze=self.freeze_train, max_length=self.max_len)
            phobert.to(self.device)
            # print('PhoBERT enabled. Using PhoBERT')
        else:
            phobert = None
            tokenizer = SimpleTokenizer()
            # print("PhoBERT disabled. Using encoder-only embeddings.")
            
        encoder = StackedEncoder(
            dim=768,
            n_heads=8,
            ff_hidden_dim=2048,
            dropout=0.1,
            num_postags=None,
            num_layers=self.encoder_layer,
            max_distance = self.max_len,
            use_rel_pos = self.use_rel_pos
        ).to(self.device)

        decoder = StackedDecoder(
            hidden_dim=768,
            num_heads=8,
            num_relations=10,
            num_layers=self.decoder_layer,
            recursive=False
        ).to(self.device)


        embedding = CombinedEmbedding(
            phobert=phobert,
            transformer_encoder=encoder,
            alpha=0.5,
            use_phobert=self.use_phobert
        )

        model = Transformer(
            phobert_embedder=embedding,
            encoder=encoder,
            decoder=decoder,
            alpha=0.5,
            use_phobert=self.use_phobert
        )
        model.to(self.device)
        
        state_dict = torch.load(self.checkpoint, map_location=self.device)
        
        model.load_state_dict(state_dict, strict=False)
        
        tokens = tokenizer(text, 
                                padding=True, 
                                truncation=True, 
                                return_tensors="pt",
                                max_length = 256)

        # Run model forward pass
        with torch.no_grad():
            outputs = model([text], postag_ids = None)   
            
        self_root_logits = outputs["self_root"].squeeze()
        relation_logits = outputs["relation"]
        start_logits = outputs["start_logits"]
        end_logits = outputs["end_logits"]

        # Convert logits to predictions
        self_root_pred = (torch.sigmoid(self_root_logits) > 0.5).long().item()
        relation_pred_idx = torch.argmax(relation_logits, dim=1).item()
        relation_pred_label = self.id2relation[str(relation_pred_idx)]

        start_idx = torch.argmax(start_logits, dim=1).item()
        end_idx = torch.argmax(end_logits, dim=1).item()
  
        start_idx = max(start_idx + 1, 0)
        
        input_tokens = tokenizer.convert_ids_to_tokens(tokens["input_ids"][0])

        # Extract predicted span (include end_idx)
        predicted_span = input_tokens[start_idx:end_idx + 3]

        # Detokenize
        predicted_span_clean = self.detokenize_phobert_tokens(predicted_span)
                        
        return pd.DataFrame({
            "Text": [text],
            "Self Root": [self_root_pred],
            "Relation": [relation_pred_label],
            "Span": [predicted_span_clean]
        })
                    
                    
