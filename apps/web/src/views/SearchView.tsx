import { FormEvent, useEffect, useRef, useState } from 'react';
import { api, SearchResponse, SearchResult } from '../api';
import { latestSearch, parseSearchQuery, searchHref, searchParams, searchResultHref } from '../search';

const KINDS = [['', '全部类型'], ['method', '方法'], ['template', '模板'], ['recipe', '配方'],
  ['scenario', '场景'], ['source', '来源'], ['interface', '接口'], ['chart-type', '图型'], ['project', '课题'], ['layout', '图样'], ['item', '来源条目']];
const AVAILABILITY = {available: '资料已在本机', not_downloaded: '未下载', missing: '资料缺失'};
const EVIDENCE: Record<string, string> = {current: '已核对当前证据', unknown: '尚未核对', unverified: '未验证',
  not_downloaded: '资料未下载，尚未核对', not_run: '未运行', pass: '运行通过', none: '未记录', export_snapshot: '导出时快照'};
const COVERAGE_LABELS: Record<string, string> = {pages: '知识页面', catalog_items: '来源目录条目', source_files: '已下载来源文件',
  not_downloaded: '未下载来源', unreadable: '无法读取', excluded: '已排除'};

export function SearchResults({results, onDownload, downloading}: {
  results: SearchResult[]; onDownload: (result: SearchResult) => void; downloading: string;
}) {
  return <ol className="global-search-results">{results.map(result => {
    const href = searchResultHref(result.source_scope ? {...result, match_section: ''} : result);
    return <li key={`${result.kind}:${result.id}`} className="sheet search-result">
      <div className="panel-row"><h2>{href ? <a href={href}>{result.title}</a> : result.title}</h2>
        <span className="small muted">{result.source_scope ? '来源文件' : KINDS.find(([kind]) => kind === result.kind)?.[1] ?? result.kind}</span></div>
      <p className="small muted search-result-path">{result.id}{(result.source_path || result.file_path || result.page) && ` · ${result.source_path || result.file_path || result.page}`}</p>
      {result.match_section && <p className="small search-match-section">{result.source_scope ? '命中文件' : '命中章节'}：{result.match_section}</p>}
      {result.source_scope && <p className="small muted">标题链接打开所属知识页；命中文件路径见上方。</p>}
      <p className="search-snippet">{result.snippet || result.summary}</p>
      <p className="small muted">{(result.why ?? []).join('；')}</p>
      <div className="search-result-facts small">
        <span>{AVAILABILITY[result.asset_availability] ?? '资料状态未知'}</span>
        <span>运行证据：{EVIDENCE[result.evidence_state] || EVIDENCE[result.run] || '尚未核对'}</span>
        <span>{result.usable ? '可进入复用流程' : '使用前需核对前提与证据'}</span>
        {result.asset_availability === 'not_downloaded' && result.kind === 'item' &&
          <span>获取来源并复用：<code>rwiki use {result.id} --project &lt;课题目录&gt;</code></span>}
        {result.asset_availability === 'not_downloaded' && result.kind !== 'item' && <button type="button" className="small" disabled={!!downloading}
          onClick={() => onDownload(result)}>{downloading === result.id ? '正在下载…' : '下载资料'}</button>}
      </div>
    </li>;
  })}</ol>;
}

export function SearchView({query = ''}: {query?: string}) {
  const selection = parseSearchQuery(query);
  const [text, setText] = useState(selection.q);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [revision, setRevision] = useState(0);
  const [downloading, setDownloading] = useState('');
  const request = useRef(latestSearch<SearchResponse>());
  useEffect(() => { setText(selection.q); }, [selection.q]);
  useEffect(() => {
    setError(''); setResponse(null);
    if (!selection.q.trim()) { request.current.cancel(); setLoading(false); return; }
    setLoading(true);
    void request.current(signal => api.search(searchParams(selection), signal), result => {
      setResponse(result); setLoading(false);
    }, failure => { setError(failure.message); setLoading(false); });
    return () => request.current.cancel();
  }, [query, revision]);
  const submit = (event: FormEvent) => { event.preventDefault(); location.hash = searchHref({...selection, q: text.trim()}); };
  const download = async (result: SearchResult) => {
    setDownloading(result.id); setError('');
    try { await api.fetchAsset(result.asset_id || result.id); setRevision(value => value + 1); }
    catch (failure) { setError(`资料下载失败：${(failure as Error).message}`); }
    finally { setDownloading(''); }
  };
  return <section className="global-search">
    <header className="hero slim"><div className="hero-text"><h1>全库搜索</h1>
      <p className="lede">搜索方法、代码说明、图样与来源正文，直接查看命中章节。</p></div></header>
    <form className="global-search-form sheet" onSubmit={submit}>
      <div className="global-search-query"><input type="search" name="q" value={text} onChange={event => setText(event.target.value)}
        placeholder="例如：差异表达、DEG、空间自相关、ggplot2" aria-label="全库搜索关键词" />
        <button type="submit">搜索</button></div>
      <div className="global-search-controls">
        <label>类型 <select value={selection.kind} onChange={event => {location.hash = searchHref({...selection, q: text, kind: event.target.value});}}>
          {KINDS.map(([kind, label]) => <option key={kind} value={kind}>{label}</option>)}</select></label>
        <label>范围 <select value={selection.scope} onChange={event => {location.hash = searchHref({...selection, q: text, scope: event.target.value as 'knowledge' | 'source'});}}>
          <option value="knowledge">知识条目</option><option value="source">来源全文</option></select></label>
        <label><input type="checkbox" checked={selection.runnable} onChange={event => {location.hash = searchHref({...selection, q: text, runnable: event.target.checked});}} /> 仅含可运行证据</label>
      </div>
    </form>
    {!selection.q.trim() && <p className="notice">输入课题问题、方法名或代码关键词开始搜索。也可继续按<a href="#/methods">方法分类</a>或<a href="#/sources">来源目录</a>浏览。</p>}
    {loading && <p className="notice" role="status">正在搜索…</p>}
    {error && <p className="notice error" role="alert">{error} <button onClick={() => setRevision(value => value + 1)}>重试</button></p>}
    {response && <><p className="small muted" role="status">找到 {response.results.length} 条结果{response.results.length === 20 ? '（最多显示 20 条，请缩小查询范围）' : ''}。运行证据与资料下载状态分别显示。</p>
      {response.results.length ? <SearchResults results={response.results} onDownload={result => void download(result)} downloading={downloading} />
        : <p className="notice">没有找到匹配条目。尝试中英文方法名、缩短关键词，或切换到来源全文。</p>}
      <details className="search-coverage"><summary>查看搜索覆盖范围</summary>
        <p className="small">{Object.entries(COVERAGE_LABELS).filter(([key]) => typeof response.coverage[key] === 'number')
          .map(([key, label]) => `${label}：${response.coverage[key]}`).join('；') || `当前范围：${selection.scope === 'source' ? '已下载来源全文' : '知识条目与来源目录'}`}</p>
        <p className="small">{selection.scope === 'source' ? '搜索本机已下载的代码与说明文件。数据、缓存、运行输出和日志不进入搜索。' : '搜索知识正文与目录说明；来源代码需切换到“来源全文”。'}</p>
      </details></>}
  </section>;
}
