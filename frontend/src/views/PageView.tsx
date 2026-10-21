import { useCallback, useEffect, useState } from 'react';
import { api, imageOf, isItem, LayoutMeta, PageDetail, pageCache, PageSummary, TYPE_LABEL } from '../api';
import type { AppData } from '../App';
import { TypeMark } from '../components';
import { renderBody, userBlock } from '../markdown';
import { pageLink } from '../nav';
import { Chain } from './Chain';
import { CodeFiles, ItemActions, LayoutImages, MethodSource, NoteEditor, SingleImage, TagsEditor } from './ItemPanel';

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
  const item = isItem(meta) ? meta : null;
  const html = renderBody(page.body.replace(LEAD_EMBED, ''), data.env, { dropUser: item !== null });
  const byPath = new Map(data.pages.map((p) => [p.path, p]));
  const pagesOf = (paths: string[]) => paths.flatMap((p) => byPath.get(p) ?? []);
  const { flow } = data;

  return (
    <article className={item ? 'page with-side' : 'page'}>
      <div className="page-main sheet">
        <p className="crumb">
          <a href={meta.type === 'method' || meta.type === 'interface' ? '#/methods' : '#/gallery'}>
            {meta.type === 'method' || meta.type === 'interface' ? '方法库' : '图库'}
          </a>{' '}
          / {TYPE_LABEL[meta.type]}
        </p>
        <h1>{meta.title}</h1>
        {error && <p className="notice error" role="alert">{error}</p>}

        {meta.type === 'layout' && <LayoutImages page={page} meta={meta} />}
        {meta.type === 'template' && <SingleImage src={imageOf(meta)!} alt="模板回放" />}
        {meta.type === 'layout' && <PanelSet meta={meta} pages={pagesOf(meta.templates)} />}

        {meta.type === 'method' && (
          <Chain
            title="分析 → 出图"
            hint="这个方法写出的表，以及能直接读这些表出图的模板。"
            self={path}
            columns={[
              { label: '分析方法', pages: pagesOf([path]) },
              { label: '输出的数据接口', pages: pagesOf(flow.outputs(path)) },
              { label: '可接的图', pages: pagesOf(flow.figuresOf(path)) },
            ]}
          />
        )}
        {meta.type === 'template' && (
          <Chain
            title="分析 → 出图"
            hint="这张图读哪些表，以及能产出这些表的分析方法。"
            self={path}
            columns={[
              { label: '可接的分析方法', pages: pagesOf(flow.methodsFor(path)) },
              { label: '读取的数据接口', pages: pagesOf(flow.inputs(path)) },
              { label: '这张图', pages: pagesOf([path]) },
            ]}
          />
        )}
        {meta.type === 'interface' && (
          <Chain
            title="谁写它，谁读它"
            hint={`文件名固定为 ${meta.slug}.csv，方法的输出目录可以直接交给读取它的模板。`}
            self={path}
            columns={[
              { label: '产出方法', pages: pagesOf(flow.inputs(path)) },
              { label: '数据接口', pages: pagesOf([path]) },
              { label: '读取它的图与方法', pages: pagesOf(flow.outputs(path)) },
            ]}
          />
        )}

        <div className="prose" dangerouslySetInnerHTML={{ __html: html }} />

        {meta.type === 'method' && <CodeFiles meta={meta} files={codeFilesOf(page.body)} />}
      </div>

      {item && (
        <aside className="page-side sheet">
          <ItemActions meta={item} run={run} busy={busy} />
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
          <Backlinks page={page} />
        </aside>
      )}
      {!item && (
        <aside className="page-side sheet">
          <Backlinks page={page} />
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

/**
 * Files listed under the method's code/ directory in its facts block, which is the one place the wiki keeps
 * that list. The facts writer links them as `/files/wiki/...`; hand-written pages may use a wikilink.
 */
function codeFilesOf(body: string): string[] {
  const found = [
    ...body.matchAll(/\/files\/wiki\/methods\/[^/)]+\/code\/([^)\s]+)/g),
    ...body.matchAll(/\[\[methods\/[^\]/]+\/code\/([^\]|]+)/g),
  ].map((m) => decodeURIComponent(m[1].trim()));
  return [...new Set(found)];
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
              <img src={imageOf(p.meta)!} alt="" loading="lazy" />
            </span>
            <span className="letters">{(meta.template_panels[p.path.replace(/^templates\/|\.md$/g, '')] ?? []).join(' · ')}</span>
            <span>{p.meta.title}</span>
          </a>
        ))}
      </div>
    </section>
  );
}

