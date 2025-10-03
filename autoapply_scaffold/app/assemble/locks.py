LOCKED_FIELDS={'name','email','phone','location','linkedin'}
def enforce_locks(locked_identity, draft_identity): return locked_identity.copy()
