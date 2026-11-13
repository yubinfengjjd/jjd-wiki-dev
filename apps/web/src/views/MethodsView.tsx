import { useEffect, useState } from 'react';
import { InterfaceMeta, isItem, MethodMeta, PageSummary } from '../api';
import type { AppData } from '../App';
import { MethodCard, TypeMark } from '../components';
import { pageLink } from '../nav';
import { methodFigures } from '../figureModels';
import { filterAnalysisMethods, matchesMethodQuery, methodBrowseKind, methodSelectionHref, normalizeMethodSelection, parseMethodQuery, purposeOptionsFor, verifiedImplementations } from '../methods';
import { MethodCodeCard } from './MethodCodeCard';

export function MethodsView({ data, query = '' }: { data: AppData; query?: string }) {
  const byPath = new Map(data.pages.map((p) => [p.path, p]));
  const allMethods = data.pages.filter((p): p is PageSummary<MethodMeta> => p.meta.type === 'method' && p.meta.status !== 'archived');
  const analysis = allMethods.filter(p => p.meta.method_kind === 'analysis');
  const auxiliary = allMethods.filter(p => p.meta.method_kind !== 'analysis');
  const kind = methodBrowseKind(query);
  const interfaces = data.pages.filter((p): p is PageSummary<InterfaceMeta> => p.meta.type === 'interface');
  const selection = normalizeMethodSelection(parseMethodQuery(query), data.taxonomy);
  const [search, setSearch] = useState(selection.q);
  // The input is controlled by the URL selection, so clearing the query also
  // clears the visible text after a hash change or a browser back/forward.
  useEffect(() => { setSearch(selection.q); }, [selection.q]);
  const methods = kind === 'workflow' || kind === 'technical' ? [] : filterAnalysisMethods(data.pages, data.taxonomy, { ...selection, q: search });
  const auxiliaryShown = auxiliary.filter(p => (kind === 'all' || p.meta.method_kind === kind)
    && (!selection.domain || p.meta.tags.includes(selection.domain))
    && !selection.purpose && matchesMethodQuery(p.meta, search));
  const purposeOptions = purposeOptionsFor(data.taxonomy, selection.domain);
  const title = (path: string) => byPath.get(path)?.meta.title ?? path;
  const live = (paths: string[]) => paths.filter((path) => {
    const meta = byPath.get(path)?.meta;
    return meta !== undefined && (!isItem(meta) || meta.status !== 'archived');
  });
  const href = (next: typeof selection, nextKind = kind) => {
    const base = methodSelectionHref(next);
    return base + (base.includes('?') ? '&' : '?') + `kind=${nextKind}`;
  };
  const select = (changes: Partial<typeof selection>) =>
    href(normalizeMethodSelection({ ...selection, ...changes }, data.taxonomy));

  return (
    <section className="methods">
      <header className="hero slim">
        <div className="hero-text">
          <h1>方法库</h1>
          <p className="lede">
            方法理论、组合流程和代码复用入口在这里统一检索。分析家族保持语义去重；具体实现的验证状态与笔记确认分别展示。
          </p>
          <dl className="census">
            <div><dt>分析家族</dt><dd>{data.taxonomy.total}</dd></div>
            <div><dt>笔记已确认</dt><dd>{analysis.filter(m => m.meta.status === 'ready').length}</dd></div>
            <div><dt>含已验证实现</dt><dd>{analysis.filter(m => verifiedImplementations(m.meta, m.implementation_status).length > 0).length}</dd></div>
            <div><dt>流程与技术资料</dt><dd>{auxiliary.length}</dd></div>
          </dl>
        </div>
      </header>

      <nav className="taxonomy" aria-label="资料类型">
        {([['all', '全部条目'], ['analysis', '分析理论'], ['workflow', '组合流程'], ['technical', '代码与技术资料']] as const).map(([value, label]) =>
          <a key={value} href={href({domain: '', purpose: '', q: search}, value)} className={kind === value ? 'active' : ''} aria-current={kind === value ? 'page' : undefined}>
            {label} {value === 'all' ? allMethods.length : allMethods.filter(p => p.meta.method_kind === value).length}
          </a>)}
      </nav>

      {kind === 'analysis' && <nav className="taxonomy taxonomy-domains" aria-label="研究领域">
        <span className="taxonomy-label">领域</span>
        <a href={select({ domain: '', purpose: '' })} className={!selection.domain ? 'active' : ''} aria-current={!selection.domain ? 'page' : undefined}>全部 {data.taxonomy.total}</a>
        {data.taxonomy.domains.map(domain => (
          <a key={domain.value} href={select({ domain: domain.value })} className={selection.domain === domain.value ? 'active' : ''} aria-current={selection.domain === domain.value ? 'page' : undefined}>
            {domain.value} {domain.count}
          </a>
        ))}
      </nav>}

      {kind === 'analysis' && purposeOptions.length > 0 && (
        <nav className="taxonomy taxonomy-purposes" aria-label="分析用途">
          <span className="taxonomy-label">用途</span>
          <a href={select({ purpose: '' })} className={!selection.purpose ? 'active' : ''} aria-current={!selection.purpose ? 'page' : undefined}>全部</a>
          {purposeOptions.map(purpose => (
            <a key={purpose.value} href={select({ purpose: purpose.value })} className={selection.purpose === purpose.value ? 'active' : ''} aria-current={selection.purpose === purpose.value ? 'page' : undefined}>
              {purpose.value} {purpose.count}
            </a>
          ))}
        </nav>
      )}

      <form className="method-search" action="#/methods" onSubmit={(event) => {
        event.preventDefault();
        location.hash = href({ ...selection, q: search.trim() });
      }}>
        <input name="q" value={search} onChange={(event) => setSearch(event.target.value)}
               placeholder="搜索方法、用途或关键词" aria-label="搜索方法" />
        <button type="submit">搜索</button>
        {selection.q && <a href={href({ ...selection, q: '' })}>清除</a>}
      </form>

      {methods.length === 0 && auxiliaryShown.length === 0 ? (
        <p className="notice">
          没有匹配的方法。分类与搜索只缩小发现范围；可以返回全部，或在上方换一个领域/用途。
          {' '}<a href={href({ domain: '', purpose: '', q: '' }, 'all')}>查看全部</a>
        </p>
      ) : methods.length > 0 && (
        <>
          <p className="muted small taxonomy-result">显示 {methods.length} / {data.taxonomy.total} 个分析家族；同一页面即使属于多个领域或用途也只计一次。</p>
          <div className="grid">
            {methods.map((m, i) => (
              <MethodCard
                key={m.path}
                path={m.path}
                meta={m.meta}
                number={i + 1}
                outputs={data.flow.outputs(m.path).map((path) => ({ path, title: title(path) }))}
                figures={methodFigures(m.path, data.pages, data.graph, data.flow)}
                implementationStatus={m.implementation_status}
              />
            ))}
          </div>
        </>
      )}

      {auxiliaryShown.length > 0 && <section className="method-auxiliary">
        <h2>流程与代码资料 · {auxiliaryShown.length}</h2>
        <p className="muted small">保留资料分类与来源；同一实现的多份项目副本不重复计为分析家族。验证范围见各入口。</p>
        <div className="source-grid">{auxiliaryShown.map(page => <MethodCodeCard key={page.path} page={page} pages={data.pages} />)}</div>
      </section>}

      <details className="method-details method-interfaces">
        <summary>数据接口 {interfaces.length}</summary>
        <p className="muted small">
          方法与图之间的内部执行约定。外部数据不必改名为 <code>&lt;接口&gt;.csv</code>：用 <code>render --bindings</code> 显式映射文件和列；固定文件名只保留为标准输入的兼容入口。
        </p>
        <ul className="links interface-links">
          {interfaces.map((p) => (
            <li key={p.path}>
              <TypeMark type="interface" />
              <a {...pageLink(p.path)}>{p.meta.title}</a>
              <code>{p.meta.slug}.csv</code>
              <span className="muted small"> · {live(data.flow.inputs(p.path)).map((m) => title(m)).join('、') || '暂无产出方法'}</span>
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}
