import { useCallback, useEffect, useState } from 'react';
import { api, imageOf, isItem, LayoutMeta, PageDetail, pageCache, PageSummary, TYPE_LABEL, wikiFile } from '../api';
import type { AppData } from '../App';
import { FigureImage, TypeMark } from '../components';
import { figureLabel, isWholeSource, methodFigures, templateSourceNote } from '../figureModels';
import { renderBody, userBlock } from '../markdown';
import { pageLink } from '../nav';
import { Chain } from './Chain';
import { ItemActions, LayoutImages, MethodSource, NoteEditor, TagsEditor } from './ItemPanel';
import { CodeButton } from '../CodeViewer';
import { RelationList } from '../RelationList';
import { adaptableTemplateRelations } from '../relations';
import { MethodOverview } from './MethodOverview';

// The viewer shows the figure, so the page's own leading image embed (kept for Obsidian) is dropped here.
const LEAD_EMBED = /^!\[\[[^\]]+\.png\]\]\n/m;

export function PageView({ path, data }: { path: string; data: AppData }) {
  // A page opened from a card was prefetched, so it paints in the transition's first frame.
  const [page, setPage] = useState<PageDetail | null>(() => pageCache.get(path) ?? null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.page(path).then(setPage, (e: Error) => setError(e.message));
  }, [path]);

  const run = useCallback(
    async (action: () => Promise<PageDetail>) => {
      setBusy(true);
      setError('');
      try {
        const next = await action();
        pageCache.set(path, next);
        setPage(next);
        await data.reload();
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setBusy(false);
      }
    },
    [data, path],
  );

  if (!page) return error ? <p className="notice error">{error}</p> : null;

  const { meta } = page;
  if (isWholeSource(meta)) return <p className="notice">整图来源已归档并隐藏。请从图库选择单 panel 图样或可调用模板；完整原图保留在画廊作溯源。</p>;
  const item = isItem(meta) ? meta : null;
  const html = renderBody(page.body.replace(LEAD_EMBED, ''), data.env, { dropUser: item !== null, dropFacts: meta.type === 'method' });
  const byPath = new Map(data.pages.map((p) => [p.path, p]));
  const pagesOf = (paths: string[]) => paths.flatMap((p) => byPath.get(p) ?? []);
  const { flow } = data;
  const structuralTemplates = meta.type === 'method' ? pagesOf(flow.figuresOf(path)) : [];
  const adaptableTemplates = meta.type === 'method'
    ? adaptableTemplateRelations(page.relations ?? [])
    : [];
  const adaptablePages = pagesOf(adaptableTemplates.map((relation) => relation.figure));
  const chainDetail = (target: string) => {
    if (!target.startsWith('templates/')) return '';
    const titles = flow.inputs(target)
      .filter((source) => source.startsWith('interfaces/'))
      .map((source) => byPath.get(source)?.meta.title ?? source);
    return titles.length ? `读取：${titles.join('、')}` : '';
  };

  return (
    <article className={item ? 'page with-side' : 'page'}>
      <div className="page-main sheet">
        <p className="crumb">
          <a href={meta.type === 'method' || meta.type === 'interface' ? '#/methods' : '#/gallery'}>
            {meta.type === 'method' || meta.type === 'interface' ? '方法库' : '图库'}
          </a>{' '}
          / {meta.type === 'template' ? '单 panel 图样 / 可调用模板' : meta.type === 'layout' ? figureLabel(meta) : TYPE_LABEL[meta.type]}
        </p>
        <div className="page-title-row"><h1>{meta.title}</h1>{item && <CodeButton meta={item} />}</div>
        {error && <p className="notice error" role="alert">{error}</p>}

        {meta.type === 'layout' && <LayoutImages page={page} meta={meta} />}
        {meta.type === 'template' && <figure className="viewer"><div className="plate"><FigureImage key={imageOf(meta)} meta={meta} /></div></figure>}
        {meta.type === 'layout' && <PanelSet meta={meta} pages={pagesOf(meta.templates)} />}

        {meta.type === 'method' && <MethodOverview meta={meta} body={page.body} figures={methodFigures(path, data.pages.map((p) => p.path === path ? page : p), data.graph, flow)} pages={data.pages} hiddenSources={data.env.hiddenSources} />}
        {meta.type === 'method' && <details className="method-details"><summary>查看接口结构匹配与完整关联证据</summary>
          <Chain
            title="接口结构匹配"
            hint="结构匹配只看模板是否消费方法声明的输出；仍需另行核对含义、每行单位、量纲与方法前提。"
            self={path}
            columns={[
              { label: '分析方法', pages: pagesOf([path]) },
              { label: '输出的数据接口', pages: pagesOf(flow.outputs(path)) },
              { label: '结构匹配的模板', pages: structuralTemplates,
                empty: adaptableTemplates.length ? '暂无；见下方“语义关联的模板（需适配）”' : '暂无' },
            ]}
            detailOf={chainDetail}
          />
          {adaptableTemplates.length > 0 && (
            <Chain
              title="语义关联的模板（需适配）"
              hint="这些模板的输入接口不在方法声明输出中；需要先按关系中的适配动作准备表，不能当作结构直连。"
              self={path}
              columns={[
                { label: '分析方法', pages: pagesOf([path]) },
                { label: '输出的数据接口', pages: pagesOf(flow.outputs(path)) },
                { label: '语义关联的模板（需适配）', pages: adaptablePages },
              ]}
              detailOf={chainDetail}
            />
          )}
          <RelationList relations={page.relations ?? []} self={path} pages={data.pages} />
        </details>}
        {item && meta.type !== 'method' && <RelationList relations={page.relations ?? []} self={path} pages={data.pages} />}
        {meta.type === 'template' && (
          <section className="reuse-note">
            <p>{templateSourceNote(meta, data.pages, data.env.hiddenSources)}</p>
            <strong>换数据与任意 n 复用</strong>
            <p>n 由实际数据决定，agent 根据课题编排尺寸、标签、配色和间距；原图组数不构成函数上限。</p>
            <p className="small muted">{page.reuse?.sizing_declared
              ? page.reuse.profile === 'unbound' ? '此模板的尺寸策略尚待绑定具体数据表与列，使用前需适配验证。' : '此模板已声明尺寸策略；仍需按实际数据验证图型与排版。'
              : '此历史模板尚未声明新的尺寸策略；使用前需由 agent 按函数化契约适配并验证。'}</p>
            <a href={wikiFile('AGENTS.md')} target="_blank" rel="noreferrer">查看当前知识库维护规则</a>
          </section>
        )}
        {meta.type === 'template' && (
          <Chain
            title="接口结构匹配"
            hint="已声明的接口说明表结构；这种匹配不代表方法与图的科学含义、单位及前提已核实。"
            self={path}
            columns={[
              { label: '结构匹配的分析方法', pages: pagesOf(flow.methodsFor(path)) },
              { label: '读取的数据接口', pages: pagesOf(flow.inputs(path)) },
              { label: '这张图', pages: pagesOf([path]) },
            ]}
            detailOf={chainDetail}
          />
        )}
        {meta.type === 'interface' && (
          <Chain
            title="谁写它，谁读它"
            hint={`文件名约定为 ${meta.slug}.csv；接口结构匹配仍需核对当前课题的含义、单位和前提。`}
            self={path}
            columns={[
              { label: '产出方法', pages: pagesOf(flow.inputs(path)) },
              { label: '数据接口', pages: pagesOf([path]) },
              { label: '读取它的图与方法', pages: pagesOf(flow.outputs(path)) },
            ]}
          />
        )}

        <div className="prose" dangerouslySetInnerHTML={{ __html: html }} />

      </div>

      {item && (
        <aside className="page-side sheet">
          <ItemActions meta={item} workflow={page.workflow} run={run} busy={busy} onDeleted={async () => { await data.reload(); location.hash = '#/queue'; }} />
          {/* Keys remount the editors when the saved value changes; prefixed so two empty values never collide. */}
          <TagsEditor key={`tags:${item.tags.join('|')}`} meta={item} run={run} busy={busy} />
          <NoteEditor key={`note:${userBlock(page.body)}`} meta={item} note={userBlock(page.body)} run={run} busy={busy} />
          {item.type === 'method' && <MethodSource meta={item} />}
          {page.gallery && (
            <div className="panel small">
              <h3>来源</h3>
              <dl className="facts">
                <dt>帖子</dt>
                <dd>{page.gallery.post.url ? <a href={page.gallery.post.url} target="_blank" rel="noreferrer">{page.gallery.post.title ?? page.gallery.post.url}</a> : page.gallery.post.title ?? '—'}</dd>
                <dt>数据</dt>
                <dd>{page.gallery.data_provenance}</dd>
                <dt>代码</dt>
                <dd>{page.gallery.code_provenance}</dd>
                <dt>画廊版本</dt>
                <dd>v{page.gallery.version}</dd>
              </dl>
            </div>
          )}
          <Backlinks page={{ ...page, backlinks: page.backlinks.filter((b) => data.env.titles.has(b.path)) }} />
        </aside>
      )}
      {!item && (
        <aside className="page-side sheet">
          <Backlinks page={{ ...page, backlinks: page.backlinks.filter((b) => data.env.titles.has(b.path)) }} />
        </aside>
      )}
    </article>
  );
}

function Backlinks({ page }: { page: PageDetail }) {
  return (
    <div className="panel small">
      <h3>反向链接</h3>
      {page.backlinks.length === 0 ? (
        <p className="muted">暂无</p>
      ) : (
        <ul className="links">
          {page.backlinks.map((b) => (
            <li key={b.path}>
              <TypeMark type={b.type} />
              <a {...pageLink(b.path)} title={TYPE_LABEL[b.type]}>{b.title}</a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** The single-figure templates a layout was split into, with the panel letters each one draws. */
function PanelSet({ meta, pages }: { meta: LayoutMeta; pages: PageSummary[] }) {
  if (pages.length === 0) return null;
  return (
    <section className="panel-set">
      <h2>拆成的单图模板</h2>
      <div className="panel-set-grid">
        {pages.map((p) => (
          <a key={p.path} className="panel-set-item" {...pageLink(p.path)}>
            <span className="plate">
              <FigureImage key={imageOf(p.meta)} meta={p.meta} />
            </span>
            <span className="letters">{(meta.template_panels[p.path.replace(/^templates\/|\.md$/g, '')] ?? []).join(' · ')}</span>
            <span>{p.meta.title}</span>
          </a>
        ))}
      </div>
    </section>
  );
}

