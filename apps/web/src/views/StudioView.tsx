import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  api,
  displayStatus,
  effectiveStatus,
  InputContractColumn,
  ItemMeta,
  PageDetail,
  PageSummary,
  pageHref,
  StudioDispatchResponse,
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
  if (param.default !== undefined) return param.default;
  if (param.type === 'boolean') return false;
  if (param.type === 'number' || param.type === 'range') return param.min ?? 1;
  if (param.choices?.length) return param.choices[0];
  return '';
}

function highlightLine(line: string, language: string): JSX.Element {
  const isComment = /^\s*#/.test(line);
  if (isComment) return <span className="tok-comment">{line}</span>;
  // Simple lightweight tokenizer for R & Python keywords/strings/numbers
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
        if (/^(ggplot|aes|ggsave|read\.csv|read_csv|scale_color_npg|scale_fill_npg)$/.test(part) || (language && false)) {
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

export function StudioView({ data, query = '' }: { data: AppData; query?: string }) {
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

  // Left Column State: Project Dir, Data File, Sniff, Column Bindings, Parameters
  const [projectDir, setProjectDir] = useState('E:/research-wiki/projects/demo-project');
  const [dataFile, setDataFile] = useState('');
  const [sniffing, setSniffing] = useState(false);
  const [sniffResult, setSniffResult] = useState<StudioSniffResponse | null>(null);
  const [sniffError, setSniffError] = useState('');

  const [bindings, setBindings] = useState<Record<string, string>>({});
  const [parameters, setParameters] = useState<Record<string, string | number | boolean>>({});

  // Center Column State: Live Rendered Code & Interactive Editor
  const [renderResp, setRenderResp] = useState<StudioRenderResponse | null>(null);
  const [rendering, setRendering] = useState(false);
  const [renderError, setRenderError] = useState('');
  const [baselineCode, setBaselineCode] = useState('');
  const [editorCode, setEditorCode] = useState('');
  const [manuallyEdited, setManuallyEdited] = useState(false);
  const [copyNote, setCopyNote] = useState('');

  // Right Column State: Dispatch & Local Run
  const [dispatching, setDispatching] = useState(false);
  const [dispatchResp, setDispatchResp] = useState<StudioDispatchResponse | null>(null);
  const [dispatchError, setDispatchError] = useState('');

  const [running, setRunning] = useState(false);
  const [runResp, setRunResp] = useState<StudioRunResponse | null>(null);
  const [runError, setRunError] = useState('');
  const [activeLogTab, setActiveLogTab] = useState<'stdout' | 'stderr'>('stdout');

  // Reset bindings & manual edits when switching template/method/recipe
  useEffect(() => {
    setBindings({});
    setParameters({});
    setManuallyEdited(false);
    setDispatchResp(null);
    setDispatchError('');
    setRunResp(null);
    setRunError('');
  }, [selectedId]);

  const { schema: paramSchema, isTier1 } = useMemo(
    () => normalizeParams(renderResp?.spec?.parameters),
    [renderResp?.spec?.parameters],
  );

  // Initialize parameter defaults whenever schema changes
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

  // Derive binding columns from renderResp.spec.tables OR pageDetail.input_contract
  const targetTables = useMemo(() => {
    if (renderResp?.spec?.tables && Object.keys(renderResp.spec.tables).length > 0) {
      return Object.entries(renderResp.spec.tables).map(([key, tbl]) => {
        const ifaceSlug = tbl.interface || '';
        const ifacePage = data.pages.find((p) => p.meta.type === 'interface' && p.meta.slug === ifaceSlug);
        const cols: InputContractColumn[] = tbl.columns?.length
          ? tbl.columns
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

  // Live code render effect (debounced)
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

  // Sniff local CSV/TSV/RDS headers
  const handleSniff = async () => {
    if (!dataFile.trim()) {
      setSniffError('请先填写本地数据文件路径（.csv / .tsv / .txt / .rds）');
      return;
    }
    setSniffing(true);
    setSniffError('');
    try {
      const res = await api.studioSniff(dataFile.trim());
      setSniffResult(res);
      // Auto-bind exact / case-insensitive matching columns
      if (res.columns?.length && targetTables.length) {
        const colNames = res.columns.map((c) => c.name);
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
      }
    } catch (err) {
      setSniffError((err as Error).message);
    } finally {
      setSniffing(false);
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
    try {
      const res = await api.studioRun({
        id: selectedId,
        project_dir: projectDir.trim(),
        data_file: dataFile.trim(),
        bindings,
        parameters,
        code: editorCode,
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
  const deps = currentPage?.runtime ? allPackages(currentPage.runtime) : [];

  return (
    <section className="studio-page">
      <header className="studio-topbar sheet">
        <div className="studio-title-block">
          <span className="studio-eyebrow">BIO-TEMPLATE STUDIO</span>
          <h1>代码模版操控台</h1>
        </div>
        <div className="studio-meta-strip">
          {currentPage && (
            <>
              <span className="badge">{TYPE_LABEL[currentPage.meta.type]}</span>
              <StatusBadge status={effectiveStatus(currentPage.meta)} label={displayStatus(currentPage.meta)} />
              <span className="lang">{language.toUpperCase()}</span>
              <span className="badge">{isTier1 ? 'Tier 1 全表单操控' : 'Tier 2 轻量源码操控'}</span>
              {deps.length > 0 && <span className="small muted">依赖：{deps.slice(0, 4).join('、')}{deps.length > 4 ? '…' : ''}</span>}
              <a className="button small" href={pageHref(currentPage.path)}>查看详情页</a>
            </>
          )}
        </div>
      </header>

      <div className="studio-workbench">
        {/* LEFT COLUMN: Data Binding & Parameter Controls */}
        <aside className="studio-col studio-left sheet" aria-label="数据绑定与参数操控">
          <div className="studio-section">
            <h2>1. 选择模版 / 方法 / 配方</h2>
            <input
              type="search"
              placeholder="过滤 ID 或标题…"
              aria-label="过滤模版"
              value={itemFilter}
              onChange={(e) => setItemFilter(e.target.value)}
            />
            <select
              aria-label="选择操作条目"
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
            >
              {!filteredItems.some((p) => p.meta.id === selectedId) && selectedId && (
                <option value={selectedId}>{selectedId}</option>
              )}
              {(['template', 'method', 'recipe'] as const).map((kind) => {
                const group = filteredItems.filter((p) => p.meta.type === kind);
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
          </div>

          <div className="studio-section">
            <h2>2. 课题目录与本地数据嗅探</h2>
            <label className="studio-field">
              <span>目标课题目录 (<code>project_dir</code>)</span>
              <input
                type="text"
                value={projectDir}
                onChange={(e) => setProjectDir(e.target.value)}
                placeholder="例如：E:/projects/asthma-scrna"
              />
            </label>
            <label className="studio-field">
              <span>本地数据文件路径 (<code>data_file</code>)</span>
              <div className="studio-sniff-row">
                <input
                  type="text"
                  value={dataFile}
                  onChange={(e) => setDataFile(e.target.value)}
                  placeholder="例如：E:/projects/asthma-scrna/deg.csv"
                />
                <button type="button" className="primary small" disabled={sniffing} onClick={() => void handleSniff()}>
                  {sniffing ? '嗅探中…' : '嗅探表头'}
                </button>
              </div>
            </label>
            {sniffError && <p className="notice error small" role="alert">{sniffError}</p>}
            {sniffResult && (
              <div className="sniff-summary">
                <p className="small">
                  已嗅探 <strong>{sniffResult.columns.length}</strong> 列 · 约 <strong>{sniffResult.row_count_estimate}</strong> 行
                  {sniffResult.note && <span className="muted"> · {sniffResult.note}</span>}
                </p>
                <div className="sniff-col-chips">
                  {sniffResult.columns.map((c) => (
                    <span key={c.name} className="sniff-chip" title={`样本: ${c.samples.slice(0, 3).join(', ')}`}>
                      <code>{c.name}</code>
                      <small>{c.type}</small>
                    </span>
                  ))}
                </div>
                {sniffResult.preview_rows?.length > 0 && (
                  <details className="sniff-preview">
                    <summary className="small">预览前 {sniffResult.preview_rows.length} 行数据</summary>
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

          <div className="studio-section">
            <h2>3. 可视化下拉列映射器</h2>
            {targetTables.length === 0 ? (
              <p className="small muted">当前条目未声明结构化输入接口表；可直接在右侧代码头部或下方参数表单指定数据路径与字段。</p>
            ) : (
              targetTables.map((tbl) => (
                <div key={tbl.key} className="binder-table">
                  <div className="binder-table-head">
                    <strong>表 {tbl.key}</strong>
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
                              <option value="">-- 未绑定（默认 {col.name}）--</option>
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
                              placeholder={`输入列名（默认 ${col.name}）`}
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
            <details className="bindings-json-preview">
              <summary className="small">查看自动生成的 <code>bindings.json</code></summary>
              <pre>{JSON.stringify(bindingsJsonObj, null, 2)}</pre>
            </details>
          </div>

          <div className="studio-section">
            <h2>4. 动态参数表单与顶刊配色</h2>
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
                if (param.type === 'boolean') {
                  return (
                    <label key={param.name} className="param-check">
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
                    <label key={param.name} className="param-field">
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
                if (param.type === 'number' || param.type === 'range') {
                  const min = param.min ?? 0;
                  const max = param.max ?? 100;
                  const step = param.step ?? 0.1;
                  const numVal = Number(value) || 0;
                  return (
                    <div key={param.name} className="param-field">
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
                      placeholder={param.description || ''}
                      onChange={(e) => setParameters((prev) => ({ ...prev, [param.name]: e.target.value }))}
                    />
                  </label>
                );
              })}
            </div>
          </div>
        </aside>

        {/* CENTER COLUMN: Live Code Generator & Interactive Editor */}
        <section className="studio-col studio-center sheet" aria-label="实时代码生成与编辑器">
          <div className="editor-toolbar">
            <div className="editor-status">
              <h2>实时脚本编辑器 ({language.toUpperCase()})</h2>
              <span className={`diff-indicator ${manuallyEdited ? 'edited' : 'synced'}`}>
                {rendering
                  ? '正在渲染代码…'
                  : manuallyEdited
                    ? `已手动微调 ${diffInfo.editedCount} 行`
                    : `参数头已实时同步 (${diffInfo.headerLines.size} 行注入)`}
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
                    {line ? highlightLine(line, language) : '\u200B'}
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
        </section>

        {/* RIGHT COLUMN: Dispatch & Local Execution Preview */}
        <aside className="studio-col studio-right sheet" aria-label="派发执行与成图预览">
          <div className="studio-section">
            <h2>5. 派发与本机试跑</h2>
            <div className="runner-buttons">
              <button
                type="button"
                className="button"
                disabled={dispatching || !selectedId}
                onClick={() => void handleDispatch()}
              >
                {dispatching ? '派发中…' : '一键派发到课题目录'}
              </button>
              <button
                type="button"
                className="button primary"
                disabled={running || !selectedId}
                onClick={() => void handleRun()}
              >
                {running ? '正在本机试跑…' : '本机试跑并预览'}
              </button>
            </div>
            <p className="small muted">
              派发将把最小代码闭包、<code>bindings.json</code> 与当前定制脚本写入 <code>{projectDir || '<project_dir>'}/wiki-use/{selectedId || '<id>'}/</code>。
            </p>
          </div>

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

          {runError && <p className="notice error small" role="alert">试跑请求失败：{runError}</p>}

          <div className="studio-section preview-stage">
            <div className="preview-stage-head">
              <h3>成图预览窗</h3>
              {runResp && (
                <span className={`badge ${runResp.ok ? 'status-ready' : 'status-pending_signoff'}`}>
                  {runResp.ok ? `运行成功 (exit ${runResp.exit_code})` : `运行失败 (exit ${runResp.exit_code})`}
                </span>
              )}
            </div>

            {!runResp && !running && (
              <div className="preview-placeholder">
                <p className="small muted">点击「本机试跑并预览」执行当前脚本并在此实时查看成图（PNG / SVG / PDF）与终端输出。</p>
              </div>
            )}

            {running && <p className="notice small" role="status">正在本机执行脚本并等待出图…</p>}

            {runResp?.preview_url && (
              <div className="preview-media-box">
                {/\.pdf($|\?)/i.test(runResp.preview_url) ? (
                  <div className="pdf-preview-wrap">
                    <iframe title="PDF 预览" src={runResp.preview_url} className="pdf-frame" />
                    <a className="button small" href={runResp.preview_url} target="_blank" rel="noreferrer">在新窗口打开 PDF</a>
                  </div>
                ) : (
                  <a href={runResp.preview_url} target="_blank" rel="noreferrer" title="点击查看大图">
                    <img src={runResp.preview_url} alt="试跑预览图" className="preview-img" />
                  </a>
                )}
              </div>
            )}

            {runResp && !runResp.preview_url && (
              <p className="small muted">本次运行未返回预览图 URL，请查看下方输出文件与终端日志。</p>
            )}

            {!!runResp?.output_files?.length && (
              <div className="output-files-box">
                <span className="small muted">产物文件：</span>
                <ul className="small">
                  {runResp.output_files.map((f) => <li key={f}><code>{f}</code></li>)}
                </ul>
              </div>
            )}
          </div>

          {runResp && (
            <div className="studio-section console-box">
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
          )}
        </aside>
      </div>
    </section>
  );
}
