import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { imageOf, pageHref, PageSummary, paperHref, studioHref, TemplateMeta } from './api';

export interface SpotlightItem {
  id: string;
  group: '快速操作' | '论文复刻' | '绘图模版' | '分析方法' | '课题与决策树';
  title: string;
  subtitle: string;
  href?: string;
  action?: () => void;
  thumb?: string | null;
  badge?: string;
  searchText: string;
}

export function buildSpotlightItems(
  pages: PageSummary[],
  onReload?: () => void,
): SpotlightItem[] {
  const items: SpotlightItem[] = [
    {
      id: 'action-gallery',
      group: '快速操作',
      title: '浏览生物信息绘图图库',
      subtitle: '按输出槽位与顶刊画风切换可复用模版',
      href: '#/gallery',
      badge: '图库',
      searchText: 'gallery 绘图图库 模板 template slot 风格',
    },
    {
      id: 'action-papers',
      group: '快速操作',
      title: '进入论文 1:1 复刻展示栏',
      subtitle: '检阅完整主/附图原图对照与逐 Panel 独立脚本',
      href: '#/papers',
      badge: '1:1',
      searchText: 'papers 论文复刻 cai nirmal cancer discovery npj',
    },
    {
      id: 'action-studio',
      group: '快速操作',
      title: '打开作图工作台（Studio）',
      subtitle: '加载示例表或上传本地 CSV/TSV 一键出图',
      href: '#/studio',
      badge: 'Studio',
      searchText: 'studio 工作台 作图 调参 csv tsv',
    },
    {
      id: 'action-playbooks',
      group: '快速操作',
      title: '多路决策沙盘（Playbooks）',
      subtitle: '按科研问题与阶段步进查找分析思路分支树',
      href: '#/next',
      badge: '思路',
      searchText: 'playbooks next 多路决策沙盘 思路 分支树',
    },
  ];

  if (onReload) {
    items.push({
      id: 'action-reload',
      group: '快速操作',
      title: '同步知识库',
      subtitle: '从本地 Wiki 重新核对最新条目与验证状态',
      action: onReload,
      badge: '同步',
      searchText: 'reload sync 同步 刷新 知识库',
    });
  }

  for (const p of pages) {
    const meta = p.meta;
    if ('status' in meta && meta.status === 'archived') continue;

    if (meta.type === 'method' && meta.method_kind === 'workflow') {
      const id = meta.id;
      const isPaper =
        id.includes('stromal-tme') ||
        id.includes('immunoediting') ||
        (meta.tags ?? []).includes('paper-replication') ||
        (meta.keywords ?? []).includes('paper-replication');
      if (isPaper) {
        items.push({
          id: `paper-${id}`,
          group: '论文复刻',
          title: meta.title,
          subtitle: meta.summary || id,
          href: paperHref(id),
          badge: '论文复刻',
          searchText: `${meta.title} ${id} ${meta.summary ?? ''} ${(meta.keywords ?? []).join(' ')} ${(meta.tags ?? []).join(' ')}`,
        });
      }
      continue;
    }

    if (meta.type === 'template') {
      const tm = meta as TemplateMeta;
      const rawThumb = imageOf(tm);
      const thumb = rawThumb && rawThumb.startsWith('/files/') && !rawThumb.includes('?') ? `${rawThumb}?w=240` : rawThumb;
      items.push({
        id: `tpl-${tm.id}`,
        group: '绘图模版',
        title: tm.title,
        subtitle: [tm.journal_style, tm.chart_types?.[0], tm.id].filter(Boolean).join(' · '),
        href: pageHref(p.path),
        thumb,
        badge: tm.journal_style || (tm.language === 'r' ? 'R' : 'Python'),
        searchText: `${tm.title} ${tm.id} ${tm.journal_style ?? ''} ${tm.primary_method ?? ''} ${(tm.chart_types ?? []).join(' ')} ${(tm.tags ?? []).join(' ')}`,
      });
      continue;
    }

    if (meta.type === 'method' && meta.method_kind === 'analysis') {
      items.push({
        id: `method-${meta.id}`,
        group: '分析方法',
        title: meta.title,
        subtitle: meta.summary || meta.id,
        href: pageHref(p.path),
        badge: '方法',
        searchText: `${meta.title} ${meta.id} ${meta.summary ?? ''} ${(meta.tags ?? []).join(' ')} ${(meta.keywords ?? []).join(' ')}`,
      });
      continue;
    }

    if (meta.type === 'project' || meta.type === 'scenario') {
      const key = 'slug' in meta ? meta.slug : 'id' in meta ? meta.id : p.path;
      const summary = 'summary' in meta && typeof meta.summary === 'string' ? meta.summary : '';
      items.push({
        id: `${meta.type}-${key}`,
        group: '课题与决策树',
        title: meta.title,
        subtitle: summary || p.path,
        href: meta.type === 'project' ? '#/projects' : '#/next',
        badge: meta.type === 'project' ? '课题' : '决策树',
        searchText: `${meta.title} ${summary} ${p.path} ${'tags' in meta && Array.isArray(meta.tags) ? meta.tags.join(' ') : ''}`,
      });
    }
  }

  return items;
}

export function filterSpotlightItems(items: SpotlightItem[], query: string): SpotlightItem[] {
  const q = query.trim().toLowerCase();
  if (!q) {
    const groups: SpotlightItem['group'][] = ['快速操作', '论文复刻', '绘图模版', '分析方法', '课题与决策树'];
    const picked: SpotlightItem[] = [];
    for (const g of groups) {
      const limit = g === '快速操作' ? 4 : g === '绘图模版' ? 5 : 3;
      picked.push(...items.filter((i) => i.group === g).slice(0, limit));
    }
    return picked;
  }
  const tokens = q.split(/\s+/).filter(Boolean);
  return items
    .filter((item) => {
      const hay = item.searchText.toLowerCase();
      return tokens.every((t) => hay.includes(t));
    })
    .slice(0, 24);
}

export function SpotlightPalette({
  open,
  onClose,
  pages,
  onReload,
}: {
  open: boolean;
  onClose: () => void;
  pages: PageSummary[];
  onReload: () => void;
}) {
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const allItems = useMemo(() => buildSpotlightItems(pages, onReload), [pages, onReload]);
  const results = useMemo(() => filterSpotlightItems(allItems, query), [allItems, query]);

  useEffect(() => {
    if (!open) return;
    setQuery('');
    setActiveIndex(0);
    const id = requestAnimationFrame(() => inputRef.current?.focus());
    return () => cancelAnimationFrame(id);
  }, [open]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  const execute = (item: SpotlightItem | undefined) => {
    if (!item) return;
    onClose();
    if (item.action) {
      item.action();
    } else if (item.href) {
      window.location.hash = item.href.startsWith('#') ? item.href : `#${item.href}`;
    }
  };

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex((i) => (results.length ? (i + 1) % results.length : 0));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex((i) => (results.length ? (i - 1 + results.length) % results.length : 0));
      } else if (e.key === 'Enter' && results[activeIndex]) {
        e.preventDefault();
        execute(results[activeIndex]);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, results, activeIndex, onClose]);

  if (!open) return null;

  let runningIndex = 0;
  const grouped: { group: SpotlightItem['group']; items: (SpotlightItem & { idx: number })[] }[] = [];
  for (const item of results) {
    let bucket = grouped.find((g) => g.group === item.group);
    if (!bucket) {
      bucket = { group: item.group, items: [] };
      grouped.push(bucket);
    }
    bucket.items.push({ ...item, idx: runningIndex++ });
  }

  const dialog = (
    <div
      className="spotlight-backdrop"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <section className="spotlight-sheet" role="dialog" aria-modal="true" aria-label="Spotlight 快速检索">
        <div className="spotlight-input-row">
          <svg className="spotlight-search-icon" viewBox="0 0 20 20" aria-hidden="true">
            <circle cx="9" cy="9" r="6" />
            <path d="M13.5 13.5L17.5 17.5" />
          </svg>
          <input
            ref={inputRef}
            type="search"
            className="spotlight-input"
            placeholder="搜索绘图模版、分析方法、期刊画风、论文复刻或课题…"
            aria-label="Spotlight 搜索"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <kbd className="spotlight-kbd">Esc</kbd>
        </div>

        <div className="spotlight-results" role="listbox">
          {grouped.length === 0 ? (
            <div className="spotlight-empty">
              <p>未找到与“{query}”匹配的条目</p>
              <a
                className="spotlight-fallback-link"
                href={`#/search?q=${encodeURIComponent(query)}`}
                onClick={onClose}
              >
                在全文检索引擎中深入搜索 “{query}” →
              </a>
            </div>
          ) : (
            grouped.map((section) => (
              <div key={section.group} className="spotlight-group">
                <div className="spotlight-group-label">{section.group}</div>
                {section.items.map((item) => {
                  const isActive = item.idx === activeIndex;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      role="option"
                      aria-selected={isActive}
                      className={isActive ? 'spotlight-item active' : 'spotlight-item'}
                      onMouseEnter={() => setActiveIndex(item.idx)}
                      onClick={() => execute(item)}
                    >
                      {item.thumb ? (
                        <span className="spotlight-thumb">
                          <img src={item.thumb} alt="" loading="lazy" />
                        </span>
                      ) : (
                        <span className="spotlight-dot" aria-hidden="true" />
                      )}
                      <span className="spotlight-item-text">
                        <span className="spotlight-item-title">{item.title}</span>
                        <span className="spotlight-item-sub">{item.subtitle}</span>
                      </span>
                      {item.badge && <span className="spotlight-badge">{item.badge}</span>}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>

        <footer className="spotlight-foot">
          <span><kbd>↑</kbd><kbd>↓</kbd> 选择</span>
          <span><kbd>↵</kbd> 打开</span>
          <span><kbd>Esc</kbd> 关闭</span>
          {results.some((r) => r.group === '绘图模版') && (
            <a className="spotlight-foot-studio" href={studioHref('scrna-celltype-umap')} onClick={onClose}>
              作图工作台 ↗
            </a>
          )}
        </footer>
      </section>
    </div>
  );

  return typeof document !== 'undefined' && document.body ? createPortal(dialog, document.body) : dialog;
}
