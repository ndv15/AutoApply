import hashlib,re
def normalize_whitespace(s:str)->str: return re.sub(r'\s+',' ', s).strip()
def hash_key(*parts:str)->str:
    h=hashlib.sha256()
    for p in parts: h.update((p or '').encode()); h.update(b'|')
    return h.hexdigest()[:16]
