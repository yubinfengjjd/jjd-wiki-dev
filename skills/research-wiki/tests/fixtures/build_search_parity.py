"""Build deterministic synthetic Python/JS rank parity corpus (no source/data writes)."""
import json,sys
from collections import Counter
from pathlib import Path
SKILL=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(SKILL))
from rwiki.search import _document,rank_export,ALIASES,QUERY_ALIASES,STOPWORDS,RANKING,INDEX_VERSION

def main():
    seeds=[
      ("differential-expression","差异表达分析","## 用途\n明确分组后比较差异表达基因，DE FindMarkers。\n## 不适用\n细胞级 p 值不能替代样本级推断。","method"),
      ("cell-annotation","细胞类型注释","## 输入\n参考表达与 marker 标签。\n## 注意\nSingleR 需要合适 reference。","method"),
      ("coexpression","基因共表达","## 原理\nCoexpression prediction approximation co-expression network。","method"),
      ("precision-recall","精确率召回率","## 原理\nPR precision recall 用于不平衡分类模型。","method"),
      ("volcano","差异基因火山图","## 适用\nvolcano 图展示差异表达效应量。","template"),
      ("annotation-scenario","细胞注释场景","## 什么时候用\n细胞注释 marker 参考标签。","scenario"),
      ("equal-a","Equal","## 正文\nidentical term","interface"),
      ("equal-b","Equal","## 正文\nidentical term","interface"),
      ("phrase-a-reversed","Order probe","## 原理\nbeta alpha","method"),
      ("phrase-z-ordered","Order probe","## 原理\nalpha beta","method"),
      ("phrase-substring","Order probe","## 原理\nunalpha betaextra alpha separately beta","method"),
    ]
    documents=[]
    for identity,title,body,kind in seeds:
        record={"id":identity,"kind":kind,"level":"L2" if kind=="template" else "note","title":title,
                "summary":"","usable":identity=="precision-recall","run":"none","status":"draft",
                "asset_availability":"available","evidence_state":"fixture_only"}
        documents.append(_document(record,body))
    df=Counter();lengths=[]
    for doc in documents:
        for section in doc["sections"]:
            df.update(section["tf"].keys());lengths.append(section["length"])
    index={"schema_version":1,"tokenizer":{"version":2,"aliases":QUERY_ALIASES,"alias_scope":"query","stopwords":STOPWORDS,"cjk_ngrams":[2],"english_pattern":"[a-z0-9]+"},
           "ranking":RANKING,"documents":documents,"statistics":{"document_count":len(lengths),"average_length":sum(lengths)/len(lengths),"df":dict(df)},
           "coverage":{"scope":"knowledge","evidence":"synthetic_fixture","source_available":False},"index":{"version":INDEX_VERSION}}
    inputs=[("差异表达",{}),("我想给细胞做注释",{}),("判断每个细胞属于什么类型",{}),("PR",{}),("coexpression",{}),
            ("volcano",{"kind":"template"}),("参考标签",{"limit":2}),("identical term",{}),("不存在词zzzz",{}),("PR",{"runnable":True}),("",{}),
            ('"alpha beta"',{}),("alpha beta",{}),('“细胞类型”',{}),('"alpha beta" "precision recall"',{}),('"alpha beta"',{"scope":"source"})]
    cases=[{"query":q,"options":o,"results":rank_export(index,q,**o)} for q,o in inputs]
    target=Path(__file__).with_name("search-parity.json")
    target.write_text(json.dumps({"index":index,"cases":cases},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(str(target),len(cases),"cases")
if __name__=="__main__":main()
