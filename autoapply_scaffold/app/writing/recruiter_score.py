def score_human_readability(summary:str, bullets:list)->int:
    score=100; words=len(summary.split())
    if words>220: score-=10
    if words<120: score-=6
    quantified=sum(1 for b in bullets if any(ch.isdigit() for ch in b))
    if quantified<2: score-=10
    if bullets:
        avg=sum(len(b.split()) for b in bullets)/len(bullets)
        if avg>22: score-=6
    return max(0,score)
