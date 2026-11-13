import { useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { api, CodeFile, CodeListing, CodeText, CodeVariant, codeDownload, ImplementationBranch, ItemMeta, KIND_OF } from './api';
import { IMPLEMENTATION_LABEL, packageFacts, portabilityLabel, runtimeModeLabel } from './methods';
import { verificationLabel } from './relations';

const VARIANTS: CodeVariant[] = ['original', 'reusable'];
const VARIANT_LABEL: Record<CodeVariant, string> = { original: '原始版', reusable: '复用版' };

export const codeFileKey = (file: Pick<CodeFile, 'variant' | 'path'>) => `${file.variant}:${file.path}`;
export const sourceText = (source: unknown): string => typeof source === 'string' ? source : source == null ? '来源未记录' : JSON.stringify(source);
export const isReconstruction = (source: unknown) => /replica|reconstruct|generated|重建|复刻|生成/i.test(sourceText(source));
export const isSnippet = (source: unknown) => /snippet|fragment|片段/i.test(sourceText(source));

/** Shared entrypoint files can carry several independently verified branches. */
export function CodeBranchList({ branches }: { branches: ImplementationBranch[] }) {
  if (!branches.length) return null;
  return <div className="code-branches small">
    <h4>实现分支</h4>
    <ul>{branches.map(branch => <li key={branch.id}>
      <strong>{branch.title}</strong>
      <span className={`implementation-state implementation-${branch.state}`}>{IMPLEMENTATION_LABEL[branch.state] ?? '未运行'}</span>
      <span>{branch.scope || '未声明验证范围'}</span>
      {branch.runtime && <>
        <span className={`runtime-mode runtime-${branch.runtime.mode}`}>{runtimeModeLabel(branch.runtime)}</span>
        <span className={`portability portability-${branch.runtime.portability.state}`}>{portabilityLabel(branch.runtime)}</span>
        <span className="muted">必要依赖：{packageFacts(branch.runtime) || '未声明'}</span>
        {!!branch.runtime.portability.issues?.length && <span className="error-text">清单问题：{branch.runtime.portability.issues.join('；')}</span>}
      </>}
      {branch.receipt && <code>{branch.receipt}</code>}
    </li>)}</ul>
  </div>;
}

/** An independent action, never nested inside a card's navigation link or flip button. */
export function CodeButton({ meta, className = '' }: { meta: ItemMeta; className?: string }) {
  const [open, setOpen] = useState(false);
  // The code endpoints serve methods, layouts and templates only; a recipe's bytes are listed in its facts.
  if (meta.type === 'recipe') return null;
  return <>
    <button type="button" className={`ghost small ${className}`} onClick={(e) => { e.stopPropagation(); setOpen(true); }} aria-haspopup="dialog">查看代码</button>
    {open && createPortal(<CodeDialog key={`${meta.type}/${meta.id}`} meta={meta} onClose={() => setOpen(false)} />, document.body)}
  </>;
}

export function CodeDialog({ meta, onClose }: { meta: ItemMeta; onClose: () => void }) {
  const id = useId();
  const dialog = useRef<HTMLElement>(null);
  const close = useRef<HTMLButtonElement>(null);
  const closeAction = useRef(onClose);
  closeAction.current = onClose;
  const [listing, setListing] = useState<CodeListing | null>(null);
  const [listError, setListError] = useState('');
  const [variant, setVariant] = useState<CodeVariant>('original');
  const [selected, setSelected] = useState('');
  const [loaded, setLoaded] = useState<{ key: string; value?: CodeText; error?: string } | null>(null);
  const [copyState, setCopyState] = useState('');
  const [fetching, setFetching] = useState(false);
  const [assetRevision, setAssetRevision] = useState(0);
  const kind = KIND_OF[meta.type];
  const files = (listing?.files ?? []).filter((f) => f.variant === variant);
  const current = files.find((f) => codeFileKey(f) === selected) ?? files[0];
  const currentKey = current ? codeFileKey(current) : '';
  const content = loaded?.key === currentKey ? loaded : null;

  useEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    close.current?.focus();
    const keyboard = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeAction.current(); }
      if (e.key !== 'Tab') return;
      const focusable = [...(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], [tabindex="0"]') ?? [])];
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (!first) { e.preventDefault(); return; }
      if (e.shiftKey && (document.activeElement === first || !dialog.current?.contains(document.activeElement))) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && (document.activeElement === last || !dialog.current?.contains(document.activeElement))) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', keyboard, true);
    return () => {
      document.removeEventListener('keydown', keyboard, true);
      document.body.style.overflow = overflow;
      if (previous?.isConnected) previous.focus();
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setListing(null); setListError(''); setLoaded(null); setSelected('');
    api.codeFiles(kind, meta.id, controller.signal).then((result) => {
      if (controller.signal.aborted) return;
      setListing(result);
      const reusable = result.files.filter((file) => file.variant === 'reusable');
      const preferredVariant = reusable.length ? 'reusable' : 'original';
      setVariant(preferredVariant);
      const entries = meta.type === 'method'
        ? (meta.implementations ?? []).map((item) => item.entrypoint.split(':')[0])
        : ['code/render.R', 'code/render.py', 'code/core.R'];
      const pool = result.files.filter((file) => file.variant === preferredVariant);
      const preferred = pool.find((file) => entries.includes(file.path)) ?? pool[0];
      if (preferred) setSelected(codeFileKey(preferred));
    }, (e: Error) => { if (!controller.signal.aborted) setListError(e.message); });
    return () => controller.abort();
  }, [kind, meta.id, assetRevision]);

  useEffect(() => {
    setCopyState('');
    if (!current) return;
    const controller = new AbortController();
    api.code(kind, meta.id, current.variant, current.path, controller.signal).then((value) => {
      if (!controller.signal.aborted) setLoaded({ key: currentKey, value });
    }, (e: Error) => { if (!controller.signal.aborted) setLoaded({ key: currentKey, error: e.message }); });
    return () => controller.abort();
  }, [kind, meta.id, currentKey]);

  const copy = async () => {
    const text = content?.value?.text;
    if (text == null) return;
    try { await navigator.clipboard.writeText(text); setCopyState('已复制当前文件'); }
    catch { setCopyState('复制失败；可选中代码复制，或下载原文件'); }
  };

  return <div className="code-backdrop" onPointerMove={(e) => e.stopPropagation()} onClick={(e) => { e.stopPropagation(); if (e.target === e.currentTarget) onClose(); }}>
    <section ref={dialog} className="sheet code-dialog" role="dialog" aria-modal="true" aria-labelledby={`${id}-title`} aria-describedby={`${id}-hint`}>
      <div className="panel-row">
        <h2 id={`${id}-title`}>{meta.title} · 查看代码</h2>
        <button ref={close} type="button" className="ghost small" onClick={onClose}>关闭</button>
      </div>
      <p id={`${id}-hint`} className="muted small">只读浏览条目已有文件。复制到课题环境后按前提适配；页面不执行代码。代码存在与页面可用均不表示已运行验证。</p>
      {listError ? <p className="notice error" role="alert">代码清单加载失败：{listError}</p> : !listing ? <p role="status">正在加载代码清单…</p> : <>
        {listing.note && <p className="small muted">{listing.note}</p>}
        {listing.asset_availability === 'not_downloaded' && <p className="notice">代码资料尚未下载到本机。<button type="button" disabled={fetching} onClick={async () => {
          setFetching(true); setListError('');
          try { await api.fetchAsset(listing.asset_id || meta.id); setAssetRevision(value => value + 1); }
          catch (error) { setListError(`资料下载失败：${(error as Error).message}`); }
          finally { setFetching(false); }
        }}>{fetching ? '正在下载…' : '下载资料'}</button></p>}
        {listing.asset_availability === 'missing' && <p className="notice">代码资料缺失；请核对来源登记和本机文件。</p>}
        <div className="tabs code-tabs" role="tablist" aria-label="代码版本">
          {VARIANTS.map((v) => <button type="button" key={v} id={`${id}-${v}`} role="tab" aria-controls={`${id}-files`} aria-selected={variant === v} className={variant === v ? 'active' : ''} onClick={() => { setVariant(v); setSelected(''); setLoaded(null); setCopyState(''); }}>{VARIANT_LABEL[v]} <span className="count">{listing.files.filter((f) => f.variant === v).length}</span></button>)}
        </div>
        <div id={`${id}-files`} className="code-browser" role="tabpanel" aria-labelledby={`${id}-${variant}`}>
          {files.length === 0 ? <p className="notice">暂无{VARIANT_LABEL[variant]}代码文件。{listing.files.length === 0 ? '此条目尚未保存代码。' : '可切换另一个版本查看已有文件。'}</p> : <>
            <nav className="code-file-list" aria-label={`${VARIANT_LABEL[variant]}文件`}>
              {files.map((f) => <button type="button" key={codeFileKey(f)} className={currentKey === codeFileKey(f) ? 'active' : ''} aria-pressed={currentKey === codeFileKey(f)} onClick={() => { setSelected(codeFileKey(f)); setCopyState(''); }}><span>{f.path}</span><small>{f.language || '未知语言'} · {f.size.toLocaleString()} 字节</small></button>)}
            </nav>
            {current && <div className="code-current">
              <h3>{current.path}</h3>
              {isReconstruction(current.source) && <p className="code-provenance">重建／复刻代码，并非原作者完整实现；验证范围以所列证据为准。</p>}
              {isSnippet(current.source) && <p className="code-provenance">此文件仅为代码片段，不代表完整可运行实现。</p>}
              <dl className="facts small">
                <dt>版本／语言</dt><dd>{VARIANT_LABEL[current.variant]} · {current.language || '未知语言'}</dd>
                <dt>来源</dt><dd>{sourceText(current.source)}</dd>
                <dt>运行验证</dt><dd>{verificationLabel(current.verification)}</dd>
                <dt>验证范围</dt><dd>{current.verification?.scope || '未记录；不能据此承诺可运行'}</dd>
                {!!current.verification?.evidence?.length && <><dt>验证证据</dt><dd>{current.verification.evidence.join('；')}</dd></>}
                <dt>SHA-256</dt><dd className="code-hash">{current.sha256 || '未提供'}</dd>
              </dl>
              <CodeBranchList branches={current.branches ?? []} />
              <div className="panel-row code-toolbar">
                <button type="button" className="small" disabled={content?.value?.text == null} onClick={copy}>复制当前文件</button>
                <a className="button small" href={codeDownload(kind, meta.id, current)} download>下载原文件</a>
                <span className="small muted" role="status">{copyState}</span>
              </div>
              {!content ? <p role="status">正在读取文件…</p> : content.error ? <p className="notice error" role="alert">文件读取失败：{content.error}。可重选文件或下载原件。</p> : content.value && <>
                {content.value.note && <p className="small muted">{content.value.note}</p>}
                {content.value.text == null ? <p className="notice">此文件无法作为文本显示，请下载原文件。未执行或转换其内容。</p> : <CodeTextView text={content.value.text} />}
              </>}
            </div>}
          </>}
        </div>
      </>}
    </section>
  </div>;
}

/** React escapes each line; HTML, Markdown and notebook output remain literal text. */
export function CodeTextView({ text }: { text: string }) {
  const lines = text.split('\n');
  return <pre className="code-text" tabIndex={0} aria-label="只读代码"><code>{lines.map((line, i) => <span className="code-line" key={i}><span className="line-number" aria-hidden="true">{i + 1}</span><span>{line}{i < lines.length - 1 ? '\n' : ''}</span></span>)}</code></pre>;
}
