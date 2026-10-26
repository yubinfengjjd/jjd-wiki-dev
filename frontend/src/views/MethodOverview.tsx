import { ImplementationStatus, InterfaceMeta, MethodMeta, PageSummary, effectiveStatus, imageOf, wikiFile } from '../api';
import { StatusBadge, FigureImage } from '../components';
import { MethodFigure, methodDisplayFigures, methodFigureStatusLabel, templateSourceNote } from '../figureModels';
import { pageLink } from '../nav';
import { COMPATIBILITY_LABEL, verificationLabel } from '../relations';
import { IMPLEMENTATION_LABEL, conditionFacts, entryKindLabel, methodKindLabel, packageFacts, portabilityLabel, runtimeModeLabel } from '../methods';

interface Props {
  meta: MethodMeta;
  purposeHtml?: string;
  implementationStatus?: ImplementationStatus[];
  figures: MethodFigure[];
  pages: PageSummary[];
  hiddenSources?: Set<string>;
}

/** Analysis only: purpose first, one data contract, then implementation evidence and figures. */
export function MethodOverview({ meta, purposeHtml, implementationStatus = [], figures, pages, hiddenSources }: Props) {
  const shown = methodDisplayFigures(figures);
  const interfaces = (slugs: string[]) => slugs.map((slug) => {
    const path = `interfaces/${slug}.md`;
    return <a key={path} {...pageLink(path)}>{pages.find((p) => p.path === path)?.meta.title ?? slug}</a>;
  });
  const contractSlugs = [...new Set([...meta.inputs, ...meta.outputs])];
  const definitions = contractSlugs.flatMap((slug) => {
    const found = pages.find((page) => page.path === `interfaces/${slug}.md`)?.meta;
    return found?.type === 'interface' ? [found as InterfaceMeta] : [];
  });
  const optionalFields = definitions.flatMap((definition) => Object.entries(definition.columns)
    .filter(([, column]) => column.required === false)
    .map(([name]) => `${definition.slug}.${name}`));
  return <section className="method-overview">
    <p className="method-kind muted small">{methodKindLabel(meta)}</p>
    {purposeHtml && <section className="method-purpose">
      <h2>研究问题与用途</h2>
      <div className="prose" dangerouslySetInnerHTML={{ __html: purposeHtml }} />
    </section>}
    <div className="method-data-grid">
      <div><h2>输入对象</h2><p className="small">{meta.data_contract?.input || '见正文输入说明；标准接口不能代替模型、数据粒度与科学前提。'}</p>{meta.inputs.length > 0 && <div className="small"><b>读取接口</b>{interfaces(meta.inputs)}</div>}</div>
      <div><h2>输出对象</h2><p className="small">{meta.data_contract?.output || '见正文输出说明，尚未提供对象契约。'}</p>{meta.outputs.length > 0 && <div className="small"><b>整理为接口</b>{interfaces(meta.outputs)}</div>}</div>
    </div>
    <details className="method-details method-input-contract">
      <summary>内部表格式与可选字段</summary>
      <p className="small">
        外部数据不必改名或改列名：用 <code>wiki.py render &lt;模板&gt; --data &lt;数据目录&gt; --bindings &lt;bindings.json&gt;</code>
        显式对应内部字段与作者列。不给 bindings 时仍读取标准 <code>&lt;接口&gt;.csv</code>；那只是执行约定，不是对原表的要求。
      </p>
      <ol className="small">
        <li>先核对数据语义、行单位、配对关系与量纲；字段名相同不代表这些已确认。</li>
        <li>在 bindings 的 <code>columns</code> 写“内部字段 → 作者列”；只做字段映射和无聚合的长宽整理。</li>
        <li>运行后查看输出目录的映射报告：源文件哈希、映射、缺失可选项和检查结果。</li>
        <li>bindings 不验证单位，也不自动做 0–1 / 0–100 换算；不明单位先停下来核对。</li>
      </ol>
      {optionalFields.length > 0 && <p className="small"><b>实现允许缺省的可选字段：</b>{optionalFields.join('、')}（只有核心确实按缺省分支处理时才会列在这里）。</p>}
      {definitions.length === 0 ? <p className="muted small">本方法未声明内部接口；对象语义以“输入对象/输出对象”为准。</p> : definitions.map((definition) => (
        <section key={definition.slug} className="input-definition">
          <h3><a {...pageLink(`interfaces/${definition.slug}.md`)}>{definition.title}</a> <code>{definition.slug}.csv</code></h3>
          <table className="input-columns">
            <thead><tr><th>字段</th><th>类型</th><th>必需</th><th>含义</th></tr></thead>
            <tbody>{Object.entries(definition.columns).map(([name, column]) => (
              <tr key={name}><td><code>{name}</code></td><td>{column.type}</td><td>{column.required === false ? '可选' : '必需'}</td><td>{column.description}</td></tr>
            ))}</tbody>
          </table>
        </section>
      ))}
    </details>
    <h2>具体实现与验证范围</h2>
    <p className="muted small">笔记确认与运行验证分别记录。验证仅覆盖所列分支、环境和检查范围；课题中仍需核对科学前提。</p>
    {meta.implementations?.length ? <div className="method-implementation-scroll"><table className="method-implementations">
      <thead><tr><th>实现</th><th>入口</th><th>必要依赖（清单）</th><th>运行方式</th><th>验证与范围</th></tr></thead>
      <tbody>{meta.implementations.map(implementation => {
        const status = implementationStatus.find(s => s.id === implementation.id);
        const runtime = status?.runtime;
        const state = status?.state ?? 'not_run';
        const optional = Object.entries(runtime?.optional_packages ?? {}).flatMap(([language, packages]) =>
          Object.entries(packages).map(([name, purpose]) => `${language}:${name}（${purpose}）`));
        return <tr key={implementation.id}>
          <td><strong>{implementation.title}</strong><span className="muted small">{implementation.language}</span></td>
          <td><details><summary className="small">入口</summary><code>{implementation.entrypoint}</code></details></td>
          <td>{runtime?.declared ? (packageFacts(runtime) || '未声明') : (implementation.dependencies?.join('、') || '未声明额外依赖')}</td>
          <td>
            <strong className={`runtime-mode runtime-${runtime?.mode ?? 'unknown'}`}>{runtimeModeLabel(runtime)}</strong>
            <p className={`small portability portability-${runtime?.portability?.state ?? 'unknown'}`}>{portabilityLabel(runtime)}</p>
            <details>
              <summary className="small">复制清单、可选依赖与证据</summary>
              <p className="small">复制：{runtime?.files?.length ? runtime.files.join('、') : '未声明清单'}</p>
              {entryKindLabel(runtime) && <p className="small">入口类型：{entryKindLabel(runtime)}</p>}
              {!!runtime?.resources?.length && <p className="small">资源：{runtime.resources.map((resource) => `${resource.path}（${resource.role}）`).join('、')}</p>}
              {!!conditionFacts(runtime).length && <p className="small">运行条件（仅声明）：{conditionFacts(runtime).join('；')}</p>}
              {optional.length > 0 && <p className="small">可选：{optional.join('、')}</p>}
              {runtime?.portability?.evidence && <p className="small"><a href={wikiFile(`methods/${meta.id}/${runtime.portability.evidence}`)} target="_blank" rel="noreferrer">查看独立性证据</a></p>}
              {!!runtime?.portability?.issues?.length && <p className="small error-text">{runtime.portability.issues.join('；')}</p>}
            </details>
          </td>
          <td><strong className={`implementation-state implementation-${state}`}>{IMPLEMENTATION_LABEL[state] ?? '未运行'}</strong>
            <details><summary className="small">范围与证据</summary><p className="small">{status?.scope || '未获得当前代码的有效验证范围。'}</p>
              {implementation.verification && <a className="small" href={wikiFile(`methods/${meta.id}/${implementation.verification}`)} target="_blank" rel="noreferrer">查看算法验证收据</a>}</details></td>
        </tr>;
      })}</tbody>
    </table></div> : <p className="notice small">尚未登记具体实现；可阅读方法判断，暂无已验证实现。</p>}
    <h2>可以怎样画</h2>
    <p className="muted small">同一图样只展示一次，优先提供函数模板；来源保留在图样或模板详情中。兼容关系与运行验证分别说明。</p>
    {shown.length === 0 ? <p className="muted">暂无有依据的关联图样；方法判断见正文。</p> : <div className="method-figure-grid">
      {shown.map((f) => <article key={f.path} className="method-visual">
        <a className="method-figure-link" {...pageLink(f.path)}>
          <span className="plate"><FigureImage key={imageOf(f.meta)} meta={f.meta} /></span>
          <strong>{f.meta.title}</strong>
        </a>
        <div className="method-visual-badges"><StatusBadge status={effectiveStatus(f.meta)} label={methodFigureStatusLabel(f)} />
          <span className={`compatibility compatibility-${f.semantic?.compatibility ?? 'candidate'}`}>{f.semantic ? COMPATIBILITY_LABEL[f.semantic.compatibility] : f.relation === 'reference' ? '参考图样' : '仅结构匹配'}</span></div>
        {f.semantic && <><p className="small">{f.semantic.reason}</p>{f.semantic.compatibility === 'adaptable' && <p className="small adaptation-note"><b>使用前需准备：</b>{f.semantic.adaptation}</p>}<p className="muted small">分析到绘图：{verificationLabel(f.semantic.verification)}</p></>}
        {f.meta.type === 'template' && <p className="muted small source-note">{templateSourceNote(f.meta, pages, hiddenSources)}</p>}
        {!!f.sourceLinks?.length && <p className="small source-note">来源：{f.sourceLinks.map((s, i) => <a key={s.path} {...pageLink(s.path)} title={s.title}>{i ? ' · ' : ''}图样 {i + 1}</a>)}</p>}
      </article>)}
    </div>}
    <p className="small"><a href={wikiFile(`methods/${meta.id}.md`)} target="_blank" rel="noreferrer">查看完整 Wiki 记录与来源元数据</a></p>
  </section>;
}
