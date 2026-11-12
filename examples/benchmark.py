"""Small constructed regression scenarios, not real-world model evaluations."""
import json
from context_budget.core import Passage, select, sha

def p(name,text): return Passage(name,1,1,text,sha(text))

scenarios = [
    ('duplicate-heavy',
     [p(f'copy-{i}.md','solar battery tariff overview solar battery tariff') for i in range(6)] +
     [p('battery.md','battery capacity measured in kWh determines storage duration'),
      p('tariff.md','tariff varies by hour compare electricity prices before charging')],
     'solar battery tariff', 28, {'battery.md','tariff.md'}),
    ('focused-query', [p('battery.md','battery capacity is measured in kWh'),p('unrelated.md','poetry and music')],
     'battery capacity', 12, {'battery.md'}),
    ('synonym-gap', [p('transport.md','Public transport electrification reduces fossil fuel consumption')],
     'bus decarbonisation',20,{'transport.md'}),
    ('budget-too-small',[p('long.md','battery capacity measured in kWh determines storage duration')],
     'battery',2,{'long.md'})
]
results=[]
for name, passages, query, budget, gold in scenarios:
    row={'scenario':name,'budget_words':budget,'gold_sources':sorted(gold)}
    for method in ('bm25','coverage'):
        r=select(passages,query,budget,method)
        selected={x['source'] for x in r['passages']}
        row[method]={'gold_source_recall':len(gold & selected)/len(gold), 'words':r['used_words'], 'selected':sorted(selected)}
    results.append(row)
print(json.dumps({'disclaimer':'Constructed tiny regression fixtures, no Claude/model comparison or general performance claim. Gold-source recall checks retrieval only, not answer correctness.', 'results':results},indent=2))
