def preflight_check(text_resume:str, jd:str)->dict:
    forbidden=['<table>','HEADER:','FOOTER:']
    flags=[f'Forbidden: {f}' for f in forbidden if f.lower() in text_resume.lower()]
    needed=[w for w in jd.split() if len(w)>5][:10]
    covered=sum(1 for w in needed if w.lower() in text_resume.lower())
    return {'pass': len(flags)==0 and covered>=max(3,len(needed)//2),'flags':flags,'keyword_needed':needed,'keyword_hits':covered}
