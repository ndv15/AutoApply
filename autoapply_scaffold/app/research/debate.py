def debate_and_merge(refs):
    def score(r): return 0.4*r['credibility']+0.4*r['topicality']+0.2*r['recency']
    return sorted(refs,key=score,reverse=True)[:6]
