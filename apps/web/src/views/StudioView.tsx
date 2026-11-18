import { DragEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  api,
  displayStatus,
  effectiveStatus,
  imageOf,
  InputContractColumn,
  ItemMeta,
  PageDetail,
  PageSummary,
  pageHref,
  StudioDispatchResponse,
  StudioExampleFile,
  StudioParamSchema,
  StudioRenderResponse,
  StudioRunResponse,
  StudioSniffResponse,
  TYPE_LABEL,
} from '../api';
import type { AppData } from '../App';
import { StatusBadge } from '../components';
import { DEFAULT_PALETTE_CHOICES, GGSCI_PALETTES, paletteFor } from '../ggsciPalettes';
import { allPackages } from '../methods';

const DEFAULT_STUDIO_PARAMS: StudioParamSchema[] = [
  { name: 'palette', label: '顶刊配色 (ggsci)', type: 'palette', default: 'NPG', choices: DEFAULT_PALETTE_CHOICES, description: 'SCI 顶刊离散色板' },
  { name: 'width', label: '图宽 (in)', type: 'number', default: 7.0, min: 2, max: 20, step: 0.5 },
  { name: 'height', label: '图高 (in)', type: 'number', default: 5.5, min: 2, max: 20, step: 0.5 },
  { name: 'p_cutoff', label: '显著性阈值 (P / padj)', type: 'number', default: 0.05, min: 0.0001, max: 1, step: 0.005 },
  { name: 'log2fc_cutoff', label: '|log2FC| 阈值', type: 'number', default: 1.0, min: 0, max: 5, step: 0.1 },
  { name: 'title', label: '图标题 (Title)', type: 'string', default: '' },
  { name: 'font_size', label: '字体字号 (pt)', type: 'number', default: 12, min: 6, max: 24, step: 1 },
];

function normalizeParams(raw: StudioRenderResponse['spec']['parameters']): { schema: StudioParamSchema[]; isTier1: boolean } {
  if (!raw) return { schema: DEFAULT_STUDIO_PARAMS, isTier1: false };
  const list: StudioParamSchema[] = Array.isArray(raw)
    ? raw
    : Object.entries(raw).map(([name, cfg]) => ({ ...cfg, name }));
  if (!list.length) return { schema: DEFAULT_STUDIO_PARAMS, isTier1: false };
  return { schema: list, isTier1: true };
}

function defaultValueOf(param: StudioParamSchema): string | number | boolean {
  if (param.default !== undefined && param.default !== null) return param.default;
  if (param.type === 'boolean' || param.type === 'bool') return false;
  if (param.type === 'number' || param.type === 'range' || param.type === 'float' || param.type === 'int') return param.min ?? 1;
  if (param.choices?.length) return param.choices[0];
  return '';
}

function highlightLine(line: string): JSX.Element {
  const isComment = /^\s*#/.test(line);
  if (isComment) return <span className="tok-comment">{line}</span>;
  const tokens = line.split(/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|\b(?:library|require|import|from|def|function|return|if|else|for|in|TRUE|FALSE|True|False|NULL|None|NA|ggplot|aes|ggsave|read\.csv|read_csv|scale_color_npg|scale_fill_npg)\b|\b\d+(?:\.\d+)?\b)/g);
  return (
    <>
      {tokens.map((part, i) => {
        if (!part) return null;
        if (part.startsWith('"') || part.startsWith("'")) return <span key={i} className="tok-string">{part}</span>;
        if (/^\d+(?:\.\d+)?$/.test(part)) return <span key={i} className="tok-number">{part}</span>;
        if (/^(library|require|import|from|def|function|return|if|else|for|in|TRUE|FALSE|True|False|NULL|None|NA)$/.test(part)) {
          return <span key={i} className="tok-keyword">{part}</span>;
        }
        if (/^(ggplot|aes|ggsave|read\.csv|read_csv|scale_color_npg|scale_fill_npg)$/.test(part)) {
          return <span key={i} className="tok-fn">{part}</span>;
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

function computeLineDiff(baseline: string, current: string): { changedLines: Set<number>; headerLines: Set<number>; editedCount: number } {
  const baseArr = baseline.split('\n');
  const currArr = current.split('\n');
  const changedLines = new Set<number>();
  const headerLines = new Set<number>();
  let editedCount = 0;
  let inParamHeader = false;
  for (let i = 0; i < currArr.length; i++) {
    const line = currArr[i];
    if (/Bio-Template Studio|STUDIO_PARAM|bindings\.json|PARAM_HEADER/i.test(line)) {
      inParamHeader = true;
    }
    if (inParamHeader && i < 45) {
      headerLines.add(i);
      if (/^#\s*={3,}/.test(line) && i > 0 && !/Bio-Template Studio/i.test(line)) {
        inParamHeader = false;
      }
    }
    if (baseline && line !== (baseArr[i] ?? '')) {
      changedLines.add(i);
      editedCount++;
    }
  }
  return { changedLines, headerLines, editedCount };
}

function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const res = String(reader.result || '');
      const comma = res.indexOf(',');
      resolve(comma >= 0 ? res.slice(comma + 1) : res);
    };
    reader.onerror = () => reject(new Error('读取本地文件失败'));
    reader.readAsDataURL(file);
  });
}

type RightTab = 'preview' | 'code' | 'dispatch';

export function StudioView({ data, query = '', embedded = false }: { data: AppData; query?: string; embedded?: boolean }) {
  const studioItems = useMemo(() => {
    return data.pages
      .filter((p): p is PageSummary<ItemMeta> =>
        (p.meta.type === 'template' || p.meta.type === 'method' || p.meta.type === 'recipe') && p.meta.status !== 'archived',
      )
      .sort((a, b) => {
        const order = { template: 0, method: 1, recipe: 2, layout: 3 };
        const diff = order[a.meta.type] - order[b.meta.type];
        if (diff !== 0) return diff;
        if (a.meta.status === 'ready' && b.meta.status !== 'ready') return -1;
        if (b.meta.status === 'ready' && a.meta.status !== 'ready') return 1;
        return a.meta.title.localeCompare(b.meta.title);
      });
  }, [data.pages]);

  const queryId = new URLSearchParams(query).get('id') ?? '';
  const initialId = useMemo(() => {
    if (queryId) return queryId;
    return studioItems[0]?.meta.id ?? '';
  }, [queryId, studioItems]);

  const [selectedId, setSelectedId] = useState(initialId);
  const [itemFilter, setItemFilter] = useState('');
  const [switcherOpen, setSwitcherOpen] = useState(false);
  const [rightTab, setRightTab] = useState<RightTab>('preview');

  useEffect(() => {
    if (queryId) setSelectedId(queryId);
    else if (!selectedId && studioItems[0]) setSelectedId(studioItems[0].meta.id);
  }, [queryId, studioItems, selectedId]);

  const currentPage = useMemo(() => {
    const clean = selectedId.replace(/^(templates|methods|recipes)\//, '').replace(/\.md$/, '');
    return studioItems.find((p) => p.meta.id === clean || p.path === selectedId) ?? null;
  }, [studioItems, selectedId]);

  const [pageDetail, setPageDetail] = useState<PageDetail | null>(null);
  useEffect(() => {
    if (!currentPage) { setPageDetail(null); return; }
    let active = true;
    api.page(currentPage.path).then((d) => { if (active) setPageDetail(d); }).catch(() => {});
    return () => { active = false; };
  }, [currentPage]);

  // Data Input / Upload / Example State
  const [projectDir, setProjectDir] = useState('E:/research-wiki/projects/demo-project');
  const [dataFile, setDataFile] = useState('');
  const [sniffing, setSniffing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [loadingExample, setLoadingExample] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [exampleFiles, setExampleFiles] = useState<StudioExampleFile[]>([]);
  const [sniffResult, setSniffResult] = useState<StudioSniffResponse | null>(null);
  const [sniffError, setSniffError] = useState('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [bindings, setBindings] = useState<Record<string, string>>({});
  const [parameters, setParameters] = useState<Record<string, string | number | boolean>>({});

  // Code Editor State
  const [renderResp, setRenderResp] = useState<StudioRenderResponse | null>(null);
  const [rendering, setRendering] = useState(false);
  const [renderError, setRenderError] = useState('');
  const [baselineCode, setBaselineCode] = useState('');
  const [editorCode, setEditorCode] = useState('');
  const [manuallyEdited, setManuallyEdited] = useState(false);
  const [copyNote, setCopyNote] = useState('');

  // Execution & Dispatch State
  const [dispatching, setDispatching] = useState(false);
  const [dispatchResp, setDispatchResp] = useState<StudioDispatchResponse | null>(null);
  const [dispatchError, setDispatchError] = useState('');

  const [running, setRunning] = useState(false);
  const [runResp, setRunResp] = useState<StudioRunResponse | null>(null);
  const [runError, setRunError] = useState('');
  const [activeLogTab, setActiveLogTab] = useState<'stdout' | 'stderr'>('stdout');

  useEffect(() => {
    setBindings({});
    setParameters({});
    setManuallyEdited(false);
    setDispatchResp(null);
    setDispatchError('');
    setRunResp(null);
    setRunError('');
    setExampleFiles([]);
    setSniffResult(null);
    setSniffError('');
    setDataFile('');
    setRightTab('preview');
  }, [selectedId]);

  const { schema: paramSchema, isTier1 } = useMemo(
    () => normalizeParams(renderResp?.spec?.parameters),
    [renderResp?.spec?.parameters],
  );

  useEffect(() => {
    setParameters((prev) => {
      const next = { ...prev };
      let changed = false;
      for (const p of paramSchema) {
        if (next[p.name] === undefined) {
          next[p.name] = defaultValueOf(p);
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [paramSchema]);

  const targetTables = useMemo(() => {
    if (renderResp?.spec?.tables && Object.keys(renderResp.spec.tables).length > 0) {
      return Object.entries(renderResp.spec.tables).map(([key, tbl]) => {
        const ifaceSlug = tbl.interface || '';
        const ifacePage = data.pages.find((p) => p.meta.type === 'interface' && p.meta.slug === ifaceSlug);
        const rawCols = tbl.columns;
        const cols: InputContractColumn[] = Array.isArray(rawCols)
          ? rawCols
          : rawCols && typeof rawCols === 'object' && Object.keys(rawCols).length > 0
            ? Object.entries(rawCols).map(([name, c]) => ({
                name,
                type: String(c?.type ?? 'str'),
                description: String(c?.description ?? ''),
                required: c?.required !== false,
              }))
            : ifacePage?.meta.type === 'interface'
              ? Object.entries(ifacePage.meta.columns).map(([name, c]) => ({
                  name,
                  type: c.type,
                  description: c.description,
                  required: c.required !== false,
                }))
              : [];
        return { key, interface: ifaceSlug, description: tbl.description || '', required: tbl.required !== false, columns: cols };
      });
    }
    if (pageDetail?.input_contract?.tables?.length) {
      return pageDetail.input_contract.tables;
    }
    if (currentPage?.meta.type === 'method' && currentPage.meta.inputs?.length) {
      return currentPage.meta.inputs.map((slug) => {
        const ifacePage = data.pages.find((p) => p.meta.type === 'interface' && p.meta.slug === slug);
        const cols: InputContractColumn[] = ifacePage?.meta.type === 'interface'
          ? Object.entries(ifacePage.meta.columns).map(([name, c]) => ({
              name, type: c.type, description: c.description, required: c.required !== false,
            }))
          : [];
        return { key: slug, interface: slug, description: ifacePage?.meta.title ?? slug, required: true, columns: cols };
      });
    }
    return [];
  }, [renderResp?.spec?.tables, pageDetail?.input_contract, currentPage, data.pages]);

  const autoBindFromSniff = useCallback((sniff: StudioSniffResponse) => {
    if (!sniff.columns?.length || !targetTables.length) return;
    const colNames = sniff.columns.map((c) => c.name);
    setBindings((prev) => {
      const next = { ...prev };
      for (const tbl of targetTables) {
        for (const col of tbl.columns) {
          if (next[col.name]) continue;
          const exact = colNames.find((c) => c === col.name);
          const icase = exact ?? colNames.find((c) => c.toLowerCase() === col.name.toLowerCase());
          if (icase) next[col.name] = icase;
        }
      }
      return next;
    });
  }, [targetTables]);

  // Live code render (debounced)
  const renderAbort = useRef<AbortController | null>(null);
  const triggerRender = useCallback(async (id: string, pDir: string, dFile: string, b: Record<string, string>, params: Record<string, string | number | boolean>) => {
    if (!id) return;
    renderAbort.current?.abort();
    const ctrl = new AbortController();
    renderAbort.current = ctrl;
    setRendering(true);
    setRenderError('');
    try {
      const res = await api.studioRenderCode({
        id,
        project_dir: pDir,
        data_file: dFile,
        bindings: b,
        parameters: params,
      }, ctrl.signal);
      if (ctrl.signal.aborted) return;
      setRenderResp(res);
      setBaselineCode(res.code);
      if (!manuallyEdited) setEditorCode(res.code);
      setRendering(false);
    } catch (err) {
      if (ctrl.signal.aborted) return;
      setRenderError((err as Error).message);
      setRendering(false);
    }
  }, [manuallyEdited]);

  useEffect(() => {
    if (!selectedId) return;
    const timer = setTimeout(() => {
      void triggerRender(selectedId, projectDir, dataFile, bindings, parameters);
    }, 220);
    return () => clearTimeout(timer);
  }, [selectedId, projectDir, dataFile, bindings, parameters, triggerRender]);

  const handleSniff = async () => {
    if (!dataFile.trim()) {
      setSniffError('请先选择、上传或输入数据文件路径');
      return;
    }
    setSniffing(true);
    setSniffError('');
    try {
      const res = await api.studioSniff(dataFile.trim());
      setSniffResult(res);
      autoBindFromSniff(res);
    } catch (err) {
      setSniffError((err as Error).message);
    } finally {
      setSniffing(false);
    }
  };

  const handleUploadFile = async (file: File | undefined | null) => {
    if (!file) return;
    setUploading(true);
    setSniffError('');
    try {
      const b64 = await readFileAsBase64(file);
      const res = await api.studioUpload(file.name, b64);
      setDataFile(res.path);
      setSniffResult(res.sniff);
      setExampleFiles([]);
      autoBindFromSniff(res.sniff);
    } catch (err) {
      setSniffError((err as Error).message);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    void handleUploadFile(file);
  };

  const handleLoadExample = async (runAfter = false) => {
    if (!selectedId) return;
    setLoadingExample(true);
    setSniffError('');
    try {
      const res = await api.studioLoadExample(selectedId);
      setExampleFiles(res.files || []);
      setDataFile(res.primary_file);
      setSniffResult(res.sniff);
      if (res.suggested_bindings && Object.keys(res.suggested_bindings).length) {
        setBindings((prev) => ({ ...res.suggested_bindings, ...prev }));
      } else {
        autoBindFromSniff(res.sniff);
      }
      if (runAfter) {
        setRunning(true);
        setRunError('');
        setRightTab('preview');
        const runRes = await api.studioRun({
          id: selectedId,
          project_dir: projectDir.trim(),
          data_file: res.primary_file,
          bindings: res.suggested_bindings || bindings,
          parameters,
        });
        setRunResp(runRes);
        setActiveLogTab(!runRes.ok && runRes.stderr ? 'stderr' : 'stdout');
        setRunning(false);
      }
    } catch (err) {
      setSniffError((err as Error).message);
      setRunning(false);
    } finally {
      setLoadingExample(false);
    }
  };

  const bindingsJsonObj = useMemo(() => {
    if (renderResp?.bindings_json && Object.keys(renderResp.bindings_json).length > 0 && !Object.keys(bindings).length) {
      return renderResp.bindings_json;
    }
    return {
      template_id: selectedId,
      data_file: dataFile || undefined,
      columns: bindings,
      parameters,
    };
  }, [renderResp?.bindings_json, selectedId, dataFile, bindings, parameters]);

  const handleCopyCode = async () => {
    if (!editorCode) return;
    try {
      await navigator.clipboard.writeText(editorCode);
      setCopyNote('已复制代码到剪贴板');
      setTimeout(() => setCopyNote(''), 2500);
    } catch {
      setCopyNote('复制失败，请手动全选复制');
    }
  };

  const handleDownloadBundle = () => {
    const lang = (renderResp?.language || (currentPage?.meta && 'language' in currentPage.meta ? currentPage.meta.language : 'r')).toLowerCase();
    const ext = lang.includes('py') ? 'py' : 'R';
    const downloadBlob = (filename: string, content: string, mime: string) => {
      const blob = new Blob([content], { type: mime });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    };
    downloadBlob(`run_${selectedId || 'studio'}.${ext}`, editorCode, 'text/plain;charset=utf-8');
    downloadBlob('bindings.json', JSON.stringify(bindingsJsonObj, null, 2), 'application/json;charset=utf-8');
    setCopyNote('已下载脚本与 bindings.json');
  };

  const handleDispatch = async () => {
    if (!projectDir.trim()) {
      setDispatchError('请填写目标课题目录 (project_dir)');
      return;
    }
    setDispatching(true);
    setDispatchError('');
    setDispatchResp(null);
    try {
      const res = await api.studioDispatch({
        id: selectedId,
        project_dir: projectDir.trim(),
        data_file: dataFile.trim(),
        bindings,
        parameters,
        code: editorCode,
      });
      setDispatchResp(res);
    } catch (err) {
      setDispatchError((err as Error).message);
    } finally {
      setDispatching(false);
    }
  };

  const handleRun = async () => {
    setRunning(true);
    setRunError('');
    setRunResp(null);
    setRightTab('preview');
    try {
      const res = await api.studioRun({
        id: selectedId,
        project_dir: projectDir.trim(),
        data_file: dataFile.trim(),
        bindings,
        parameters,
        code: manuallyEdited ? editorCode : undefined,
      });
      setRunResp(res);
      if (!res.ok && res.stderr) setActiveLogTab('stderr');
      else setActiveLogTab('stdout');
    } catch (err) {
      setRunError((err as Error).message);
    } finally {
      setRunning(false);
    }
  };

  const filteredItems = useMemo(() => {
    const q = itemFilter.trim().toLowerCase();
    if (!q) return studioItems;
    return studioItems.filter((p) =>
      `${p.meta.id} ${p.meta.title} ${p.meta.tags.join(' ')}`.toLowerCase().includes(q),
    );
  }, [studioItems, itemFilter]);

  const diffInfo = useMemo(() => computeLineDiff(baselineCode, editorCode), [baselineCode, editorCode]);
  const editorLines = useMemo(() => (editorCode || '').split('\n'), [editorCode]);
  const language = renderResp?.language || (currentPage?.meta && 'language' in currentPage.meta ? String(currentPage.meta.language) : 'R');
  const tier = renderResp?.spec?.tier ?? (isTier1 ? 1 : 2);
  const deps = renderResp?.spec?.dependencies?.length
    ? renderResp.spec.dependencies
    : currentPage?.runtime ? allPackages(currentPage.runtime) : [];
  const referencePreview = currentPage ? imageOf(currentPage.meta) : null;

  return (
    <section className={`studio-page hiplot-studio${embedded ? ' is-embedded' : ''}`}>
      {/* Clean Hiplot/SRplot Top Workbench Bar */}
      <header className="studio-topbar sheet">
        <div className="studio-topbar-left">
          <div className="studio-title-block">
            <span className="studio-eyebrow">BIO-TEMPLATE WORKBENCH · 代码模版操控台</span>
            <div className="studio-active-heading">
              {embedded ? (
                <h2>{currentPage?.meta.title || selectedId || '作图工作台'}</h2>
              ) : (
                <h1>{currentPage?.meta.title || selectedId || '作图工作台'}</h1>
              )}
              {currentPage && (
                <div className="studio-meta-badges">
                  <span className={`lang-pill lang-${language.toLowerCase()}`}>{language.toUpperCase()}</span>
                  <StatusBadge status={effectiveStatus(currentPage.meta)} label={displayStatus(currentPage.meta)} />
                  <span className="badge">{tier === 1 ? '可调参模版' : TYPE_LABEL[currentPage.meta.type]}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="studio-topbar-actions">
          <button
            type="button"
            className="button small"
            onClick={() => setSwitcherOpen((v) => !v)}
          >
            切换模版 ({studioItems.length})
          </button>
          <button
            type="button"
            className="button small"
            disabled={loadingExample || !selectedId}
            onClick={() => void handleLoadExample(true)}
          >
            {loadingExample ? '加载中…' : '示例一键出图'}
          </button>
          <button
            type="button"
            className="button primary"
            disabled={running || !selectedId}
            onClick={() => void handleRun()}
          >
            {running ? '正在绘图中…' : '本机试跑并预览'}
          </button>
          {currentPage && (
            <a className="button small" href={pageHref(currentPage.path)}>模版详情</a>
          )}
        </div>
      </header>

      {/* Visual Template Switcher Drawer */}
      {switcherOpen && (
        <section className="studio-switcher-drawer sheet" aria-label="快速切换作图模版">
          <div className="switcher-head">
            <input
              type="search"
              placeholder="搜索图表标题、关键词或 ID…"
              aria-label="过滤模版"
              value={itemFilter}
              onChange={(e) => setItemFilter(e.target.value)}
            />
            <button type="button" className="ghost small" onClick={() => setSwitcherOpen(false)}>收起</button>
          </div>
          <div className="switcher-grid">
            {filteredItems.slice(0, 36).map((p) => {
              const thumb = imageOf(p.meta);
              const active = p.meta.id === selectedId;
              return (
                <button
                  key={p.path}
                  type="button"
                  className={active ? 'switcher-card active' : 'switcher-card'}
                  onClick={() => {
                    setSelectedId(p.meta.id);
                    setSwitcherOpen(false);
                  }}
                >
                  <div className="switcher-thumb">
                    {thumb ? <img src={thumb} alt={p.meta.title} loading="lazy" /> : <span className="muted small">{TYPE_LABEL[p.meta.type]}</span>}
                  </div>
                  <div className="switcher-info">
                    <strong>{p.meta.title}</strong>
                    <span className="small muted">{p.meta.id}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </section>
      )}

      {/* Spacious 2-Column Workbench */}
      <div className="studio-workbench-2col">
        {/* LEFT SIDEBAR: Data Upload / Example + Column Binder + Parameters */}
        <aside className="studio-col studio-left sheet" aria-label="数据绑定与参数操控">
          {/* Accessible compact select kept synced */}
          <div className="studio-section compact-select-row">
            <label className="studio-field">
              <span className="small muted">当前模版</span>
              <select
                aria-label="选择操作条目"
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
              >
                {!filteredItems.some((p) => p.meta.id === selectedId) && selectedId && (
                  <option value={selectedId}>{selectedId}</option>
                )}
                {(['template', 'method', 'recipe'] as const).map((kind) => {
                  const group = studioItems.filter((p) => p.meta.type === kind);
                  if (!group.length) return null;
                  return (
                    <optgroup key={kind} label={`${TYPE_LABEL[kind]} (${group.length})`}>
                      {group.map((p) => (
                        <option key={p.path} value={p.meta.id}>
                          {p.meta.title} [{p.meta.id}]
                        </option>
                      ))}
                    </optgroup>
                  );
                })}
              </select>
            </label>
          </div>

          {/* Step 1: Data Upload + 1-Click Example + Path Sniff */}
          <div className="studio-section">
            <div className="section-title-row">
              <h2>1. 数据输入</h2>
              <button
                type="button"
                className="button small"
                disabled={loadingExample || !selectedId}
                onClick={() => void handleLoadExample(false)}
              >
                {loadingExample ? '读取中…' : '加载内置示例'}
              </button>
            </div>

            <div
              className={dragOver ? 'studio-dropzone drag-over' : 'studio-dropzone'}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click(); }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.tsv,.txt,.rds"
                hidden
                onChange={(e) => void handleUploadFile(e.target.files?.[0])}
              />
              <strong>{uploading ? '正在上传并解析表头…' : '点击选择或拖拽上传 CSV / TSV 数据表'}</strong>
              <span className="small muted">上传后自动解析列名并匹配字段；也可点击右上「加载内置示例」体验</span>
            </div>

            {exampleFiles.length > 1 && (
              <div className="example-file-pills">
                <span className="small muted">示例多表：</span>
                {exampleFiles.map((ef) => (
                  <button
                    key={ef.path}
                    type="button"
                    className={dataFile === ef.path ? 'chip-btn active' : 'chip-btn'}
                    onClick={() => {
                      setDataFile(ef.path);
                      setSniffResult(ef.sniff);
                      autoBindFromSniff(ef.sniff);
                    }}
                  >
                    {ef.name}
                  </button>
                ))}
              </div>
            )}

            <details className="path-sniff-collapse" open={Boolean(dataFile)}>
              <summary className="small muted">或指定本地文件路径 (`.csv` / `.tsv` / `.rds`)</summary>
              <div className="studio-sniff-row" style={{ marginTop: 8 }}>
                <input
                  type="text"
                  value={dataFile}
                  onChange={(e) => setDataFile(e.target.value)}
                  placeholder="例如：E:/projects/deg.csv"
                  aria-label="本地数据文件路径"
                />
                <button type="button" className="primary small" disabled={sniffing} onClick={() => void handleSniff()}>
                  {sniffing ? '嗅探中…' : '嗅探表头'}
                </button>
              </div>
            </details>

            {sniffError && <p className="notice error small" role="alert">{sniffError}</p>}
            {sniffResult && (
              <div className="sniff-summary">
                <p className="small">
                  已就绪：<strong>{sniffResult.columns.length}</strong> 列 · 约 <strong>{sniffResult.row_count_estimate}</strong> 行
                  {sniffResult.note && <span className="muted"> · {sniffResult.note}</span>}
                </p>
                <div className="sniff-col-chips">
                  {sniffResult.columns.slice(0, 12).map((c) => (
                    <span key={c.name} className="sniff-chip" title={`样本: ${c.samples.slice(0, 3).join(', ')}`}>
                      <code>{c.name}</code>
                      <small>{c.type}</small>
                    </span>
                  ))}
                  {sniffResult.columns.length > 12 && <span className="small muted">+{sniffResult.columns.length - 12} 列</span>}
                </div>
                {sniffResult.preview_rows?.length > 0 && (
                  <details className="sniff-preview">
                    <summary className="small">预览前 {sniffResult.preview_rows.length} 行</summary>
                    <div className="sniff-table-scroll">
                      <table className="input-columns">
                        <thead>
                          <tr>{sniffResult.columns.map((c) => <th key={c.name}>{c.name}</th>)}</tr>
                        </thead>
                        <tbody>
                          {sniffResult.preview_rows.slice(0, 5).map((row, rIdx) => (
                            <tr key={rIdx}>
                              {sniffResult.columns.map((c) => <td key={c.name}>{String(row[c.name] ?? '')}</td>)}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                )}
              </div>
            )}
          </div>

          {/* Step 2: Column Binder */}
          <div className="studio-section">
            <h2>2. 可视化下拉列映射器</h2>
            {targetTables.length === 0 ? (
              <p className="small muted">本模版使用标准位置参数或内置数据表结构，直接点击出图即可。</p>
            ) : (
              targetTables.map((tbl) => (
                <div key={tbl.key} className="binder-table">
                  <div className="binder-table-head">
                    <strong>{tbl.description || tbl.key}</strong>
                    <code>{tbl.interface}.csv</code>
                  </div>
                  {tbl.columns.map((col) => {
                    const boundVal = bindings[col.name] ?? '';
                    const sniffedCols = sniffResult?.columns ?? [];
                    return (
                      <div key={col.name} className="binder-row">
                        <div className="binder-target">
                          <code>{col.name}</code>
                          <span className={col.required ? 'req-dot required' : 'req-dot'}>
                            {col.required ? '必需' : '可选'} · {col.type}
                          </span>
                          <small className="muted">{col.description}</small>
                        </div>
                        <div className="binder-control">
                          {sniffedCols.length > 0 ? (
                            <select
                              aria-label={`映射列 ${col.name}`}
                              value={boundVal}
                              onChange={(e) => setBindings((prev) => ({ ...prev, [col.name]: e.target.value }))}
                            >
                              <option value="">-- 默认列名 ({col.name}) --</option>
                              {sniffedCols.map((sc) => (
                                <option key={sc.name} value={sc.name}>
                                  {sc.name} ({sc.type}){sc.samples.length ? ` · 例: ${sc.samples[0]}` : ''}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <input
                              type="text"
                              aria-label={`映射列 ${col.name}`}
                              value={boundVal}
                              placeholder={`默认列名 ${col.name}`}
                              onChange={(e) => setBindings((prev) => ({ ...prev, [col.name]: e.target.value }))}
                            />
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))
            )}
          </div>

          {/* Step 3: Parameters & ggsci */}
          <div className="studio-section">
            <h2>3. 顶刊配色与作图参数</h2>
            <div className="param-form">
              {paramSchema.map((param) => {
                const value = parameters[param.name] ?? defaultValueOf(param);
                const isPalette = param.type === 'palette' || param.name.toLowerCase().includes('palette');
                if (isPalette) {
                  const choiceNames = param.choices?.length ? param.choices : DEFAULT_PALETTE_CHOICES;
                  return (
                    <div key={param.name} className="param-field palette-field">
                      <span className="param-label">{param.label || param.name}</span>
                      <div className="palette-picker" role="radiogroup" aria-label={param.label || '顶刊配色'}>
                        {choiceNames.map((name) => {
                          const pal = GGSCI_PALETTES.find((p) => p.id.toLowerCase() === name.toLowerCase()) ?? paletteFor(name);
                          const selected = String(value).toLowerCase() === name.toLowerCase();
                          return (
                            <button
                              key={name}
                              type="button"
                              role="radio"
                              aria-checked={selected}
                              title={`${pal.journal} · ${pal.rScaleColor}`}
                              className={selected ? 'palette-option active' : 'palette-option'}
                              onClick={() => setParameters((prev) => ({ ...prev, [param.name]: name }))}
                            >
                              <span className="palette-name">{name}</span>
                              <span className="palette-swatches" aria-hidden="true">
                                {pal.colors.slice(0, 6).map((hex) => (
                                  <span key={hex} className="swatch" style={{ backgroundColor: hex }} />
                                ))}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  );
                }
                if (param.type === 'boolean' || param.type === 'bool') {
                  return (
                    <label key={param.name} className="param-check" title={param.help || param.description || ''}>
                      <input
                        type="checkbox"
                        checked={Boolean(value)}
                        onChange={(e) => setParameters((prev) => ({ ...prev, [param.name]: e.target.checked }))}
                      />
                      <span>{param.label || param.name}</span>
                    </label>
                  );
                }
                if ((param.type === 'select' || param.choices?.length) && param.choices?.length) {
                  return (
                    <label key={param.name} className="param-field" title={param.help || param.description || ''}>
                      <span className="param-label">{param.label || param.name}</span>
                      <select
                        value={String(value)}
                        onChange={(e) => setParameters((prev) => ({ ...prev, [param.name]: e.target.value }))}
                      >
                        {param.choices.map((c) => <option key={c} value={c}>{c}</option>)}
                      </select>
                    </label>
                  );
                }
                if (param.type === 'number' || param.type === 'range' || param.type === 'float' || param.type === 'int') {
                  const min = param.min ?? 0;
                  const max = param.max ?? 100;
                  const step = param.step ?? (param.type === 'int' ? 1 : max <= 1 ? 0.01 : 0.1);
                  const numVal = Number(value) || 0;
                  return (
                    <div key={param.name} className="param-field" title={param.help || param.description || ''}>
                      <div className="param-label-row">
                        <span className="param-label">{param.label || param.name}</span>
                        <input
                          type="number"
                          className="param-num-input"
                          min={min}
                          max={max}
                          step={step}
                          value={numVal}
                          aria-label={param.label || param.name}
                          onChange={(e) => setParameters((prev) => ({ ...prev, [param.name]: Number(e.target.value) }))}
                        />
                      </div>
                      <input
                        type="range"
                        min={min}
                        max={max}
                        step={step}
                        value={Math.min(max, Math.max(min, numVal))}
                        onChange={(e) => setParameters((prev) => ({ ...prev, [param.name]: Number(e.target.value) }))}
                      />
                    </div>
                  );
                }
                return (
                  <label key={param.name} className="param-field">
                    <span className="param-label">{param.label || param.name}</span>
                    <input
                      type="text"
                      value={String(value)}
                      placeholder={param.help || param.description || ''}
                      onChange={(e) => setParameters((prev) => ({ ...prev, [param.name]: e.target.value }))}
                    />
                  </label>
                );
              })}
            </div>
          </div>
        </aside>

        {/* RIGHT MAIN STAGE: Tabbed Preview / Code / Dispatch */}
        <section className="studio-col studio-stage sheet" aria-label="成图预览与脚本工作区">
          <div className="studio-stage-tabs" role="tablist" aria-label="工作台主视图切换">
            <button
              type="button"
              role="tab"
              aria-selected={rightTab === 'preview'}
              className={rightTab === 'preview' ? 'stage-tab active' : 'stage-tab'}
              onClick={() => setRightTab('preview')}
            >
              成图预览与下载
              {runResp && (
                <span className={`dot status-${runResp.ok ? 'ready' : 'pending_signoff'}`} aria-hidden="true" />
              )}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={rightTab === 'code'}
              className={rightTab === 'code' ? 'stage-tab active' : 'stage-tab'}
              onClick={() => setRightTab('code')}
            >
              实时脚本 ({language.toUpperCase()})
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={rightTab === 'dispatch'}
              className={rightTab === 'dispatch' ? 'stage-tab active' : 'stage-tab'}
              onClick={() => setRightTab('dispatch')}
            >
              派发到课题与说明
            </button>
            <div className="stage-tab-status small muted">
              {deps.length > 0 && <span>依赖包：{deps.slice(0, 4).join('、')}{deps.length > 4 ? '…' : ''}</span>}
            </div>
          </div>

          {/* TAB 1: Preview & Downloads */}
          <div className="studio-tab-panel" hidden={rightTab !== 'preview'}>
            {runError && <p className="notice error small" role="alert">试跑请求失败：{runError}</p>}

            {running && (
              <div className="stage-loading-banner" role="status">
                <span>正在本机调用 {language.toUpperCase()} 环境绘图，请稍候…</span>
              </div>
            )}

            {runResp?.preview_url ? (
              <div className="live-result-stage">
                <div className="preview-stage-head">
                  <div className="preview-status-left">
                    <span className={`badge ${runResp.ok ? 'status-ready' : 'status-pending_signoff'}`}>
                      {runResp.ok ? '实时成图已生成' : `运行异常 (exit ${runResp.exit_code})`}
                    </span>
                    <span className="small muted">基于当前参数与数据实时绘制</span>
                  </div>
                  <div className="download-pill-bar">
                    {runResp.run_id && runResp.output_files.map((f) => (
                      <a
                        key={f}
                        className="button small"
                        href={`/api/studio/output/${encodeURIComponent(runResp.run_id!)}/${f.split('/').map(encodeURIComponent).join('/')}`}
                        download={f.split('/').pop()}
                      >
                        下载 {f.split('/').pop()}
                      </a>
                    ))}
                  </div>
                </div>
                <div className="preview-media-box large">
                  {/\.pdf($|\?)/i.test(runResp.preview_url) ? (
                    <iframe title="PDF 预览" src={runResp.preview_url} className="pdf-frame tall" />
                  ) : (
                    <a href={runResp.preview_url} target="_blank" rel="noreferrer" title="在新标签页查看原图">
                      <img src={runResp.preview_url} alt="实时成图预览" className="preview-img large" />
                    </a>
                  )}
                </div>
              </div>
            ) : (
              <div className="reference-result-stage">
                <div className="preview-stage-head">
                  <div className="preview-status-left">
                    <span className="badge">模版参考成图</span>
                    <span className="small muted">左侧上传 CSV 或点击右上「示例一键出图」，即可用你自己的参数重绘此图</span>
                  </div>
                </div>
                {referencePreview ? (
                  <div className="preview-media-box large">
                    <img src={referencePreview} alt={currentPage?.meta.title || '模版参考图'} className="preview-img large" />
                  </div>
                ) : (
                  <div className="preview-placeholder large">
                    <p className="muted">点击右上角 <strong>「示例一键出图」</strong> 或 <strong>「本机试跑并预览」</strong>，在此实时渲染高分辨率成图。</p>
                  </div>
                )}
              </div>
            )}

            {runResp && (
              <details className="console-collapse" open={!runResp.ok}>
                <summary className="small muted">
                  运行终端日志（exit {runResp.exit_code} · 产物 {runResp.output_files.length} 个）
                </summary>
                <div className="studio-section console-box" style={{ marginTop: 10 }}>
                  <div className="console-tabs" role="tablist">
                    <button
                      type="button"
                      role="tab"
                      aria-selected={activeLogTab === 'stdout'}
                      className={activeLogTab === 'stdout' ? 'active' : ''}
                      onClick={() => setActiveLogTab('stdout')}
                    >
                      stdout ({runResp.stdout ? runResp.stdout.split('\n').length : 0} 行)
                    </button>
                    <button
                      type="button"
                      role="tab"
                      aria-selected={activeLogTab === 'stderr'}
                      className={activeLogTab === 'stderr' ? 'active' : ''}
                      onClick={() => setActiveLogTab('stderr')}
                    >
                      stderr ({runResp.stderr ? runResp.stderr.split('\n').length : 0} 行)
                    </button>
                  </div>
                  <pre className="console-log">
                    {activeLogTab === 'stdout'
                      ? (runResp.stdout || '(stdout 为空)')
                      : (runResp.stderr || '(stderr 为空)')}
                  </pre>
                </div>
              </details>
            )}
          </div>

          {/* TAB 2: Interactive Script Editor */}
          <div className="studio-tab-panel" hidden={rightTab !== 'code'}>
            <div className="editor-toolbar">
              <div className="editor-status">
                <h2>实时脚本编辑器 ({language.toUpperCase()})</h2>
                <span className={`diff-indicator ${manuallyEdited ? 'edited' : 'synced'}`}>
                  {rendering
                    ? '正在渲染代码…'
                    : manuallyEdited
                      ? `已手动微调 ${diffInfo.editedCount} 行`
                      : `参数已同步注入 (${diffInfo.headerLines.size} 行参数头)`}
                </span>
              </div>
              <div className="editor-actions">
                {manuallyEdited && (
                  <button
                    type="button"
                    className="ghost small"
                    onClick={() => {
                      setManuallyEdited(false);
                      setEditorCode(baselineCode);
                    }}
                  >
                    重置为自动生成
                  </button>
                )}
                <button type="button" className="small" onClick={() => void handleCopyCode()} disabled={!editorCode}>
                  复制代码
                </button>
                <button type="button" className="small" onClick={handleDownloadBundle} disabled={!editorCode}>
                  下载脚本 + bindings.json
                </button>
              </div>
            </div>
            {copyNote && <p className="small muted editor-note" role="status">{copyNote}</p>}
            {renderError && (
              <p className="notice error small" role="alert">
                代码渲染服务响应异常：{renderError}（仍可在下方手动编写或重试）
              </p>
            )}

            <div className="code-editor-shell">
              <div className="code-gutter" aria-hidden="true">
                {editorLines.map((_, idx) => {
                  const isEdited = diffInfo.changedLines.has(idx);
                  const isHeader = diffInfo.headerLines.has(idx);
                  return (
                    <span
                      key={idx}
                      className={`gutter-no${isEdited ? ' diff-edited' : isHeader ? ' diff-header' : ''}`}
                      title={isEdited ? '手动修改行' : isHeader ? '自动注入参数头' : undefined}
                    >
                      {idx + 1}
                    </span>
                  );
                })}
              </div>
              <div className="code-surface">
                <pre className="code-highlight-layer" aria-hidden="true">
                  {editorLines.map((line, idx) => (
                    <div
                      key={idx}
                      className={`code-hl-line${diffInfo.changedLines.has(idx) ? ' is-edited' : diffInfo.headerLines.has(idx) ? ' is-header' : ''}`}
                    >
                      {line ? highlightLine(line) : '\u200B'}
                    </div>
                  ))}
                </pre>
                <textarea
                  className="code-input-layer"
                  aria-label="交互式代码编辑器"
                  spellCheck={false}
                  value={editorCode}
                  onChange={(e) => {
                    setManuallyEdited(true);
                    setEditorCode(e.target.value);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Tab') {
                      e.preventDefault();
                      const el = e.currentTarget;
                      const start = el.selectionStart;
                      const end = el.selectionEnd;
                      const next = editorCode.slice(0, start) + '  ' + editorCode.slice(end);
                      setManuallyEdited(true);
                      setEditorCode(next);
                      requestAnimationFrame(() => {
                        el.selectionStart = el.selectionEnd = start + 2;
                      });
                    }
                  }}
                />
              </div>
            </div>
          </div>

          {/* TAB 3: Dispatch to Project & Bindings */}
          <div className="studio-tab-panel" hidden={rightTab !== 'dispatch'}>
            <div className="dispatch-panel-grid">
              <div className="studio-section">
                <h2>派发可复现脚本到课题目录</h2>
                <label className="studio-field">
                  <span>目标课题目录 (<code>project_dir</code>)</span>
                  <input
                    type="text"
                    value={projectDir}
                    onChange={(e) => setProjectDir(e.target.value)}
                    placeholder="例如：E:/research-wiki/projects/demo-project"
                  />
                </label>
                <div className="runner-buttons" style={{ maxWidth: 260 }}>
                  <button
                    type="button"
                    className="button primary"
                    disabled={dispatching || !selectedId}
                    onClick={() => void handleDispatch()}
                  >
                    {dispatching ? '派发中…' : '一键派发到课题目录'}
                  </button>
                </div>
                <p className="small muted">
                  将把最小代码闭包、<code>bindings.json</code> 与当前定制脚本写入 <code>{projectDir || '<project_dir>'}/wiki-use/{selectedId || '<id>'}/</code>，方便课题内归档与 Git 版本追踪。
                </p>
                {dispatchError && <p className="notice error small" role="alert">派发失败：{dispatchError}</p>}
                {dispatchResp && (
                  <div className="dispatch-receipt">
                    <strong>派发完成</strong>
                    <p className="small">目标路径：<code>{dispatchResp.output_dir}</code></p>
                    {dispatchResp.files?.length > 0 && (
                      <ul className="small">
                        {dispatchResp.files.map((f) => <li key={f}><code>{f}</code></li>)}
                      </ul>
                    )}
                  </div>
                )}
              </div>

              <div className="studio-section">
                <h3>列映射配置文件 (<code>bindings.json</code>)</h3>
                <div className="bindings-json-preview">
                  <pre>{JSON.stringify(bindingsJsonObj, null, 2)}</pre>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </section>
  );
}
