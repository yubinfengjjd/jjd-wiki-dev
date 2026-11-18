import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { api, PageSummary, ProjectRecord, ProjectStepItem, studioHref } from '../api';
import type { AppData } from '../App';
import { pageLink } from '../nav';

function parseMarkdownSteps(body: string): ProjectStepItem[] {
  const steps: ProjectStepItem[] = [];
  const blocks = body.split(/^###\s+/m).slice(1);
  for (const block of blocks) {
    const lines = block.split('\n');
    const title = (lines[0] ?? '').trim();
    if (!title) continue;
    const rest = lines.slice(1).join('\n');
    const extractField = (pattern: RegExp) => {
      const m = rest.match(pattern);
      return m ? m[1].trim() : '';
    };
    const templates = extractField(/[-*]\s*\*\*【所用模版】\*\*[：:]\s*(.+)/);
    const observation = extractField(/[-*]\s*\*\*【观察结果与排坑】\*\*[：:]\s*(.+)/);
    const next_branch = extractField(/[-*]\s*\*\*【触发下一步】\*\*[：:]\s*(.+)/);
    steps.push({ title, templates, observation, next_branch, raw: rest.trim() });
  }
  return steps;
}

function normalizeProjects(raw: ProjectRecord[] | { projects?: ProjectRecord[] } | null, pages: PageSummary[]): ProjectRecord[] {
  const list = Array.isArray(raw) ? raw : raw?.projects ?? [];
  if (list.length > 0) {
    return list.map((p) => ({
      ...p,
      steps: p.steps?.length ? p.steps : parseMarkdownSteps(p.body || ''),
    }));
  }
  return pages
    .filter((p) => p.meta.type === 'project')
    .map((p) => {
      const id = p.path.replace(/^projects\/|\.md$/g, '');
      return {
        id,
        title: p.meta.title,
        path: p.path,
        steps: [],
        body: '',
      };
    });
}

export function ProjectsView({ data }: { data: AppData }) {
  const [serverProjects, setServerProjects] = useState<ProjectRecord[] | { projects?: ProjectRecord[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState('');

  // Form fields for appending a 3-line step
  const [stepTitle, setStepTitle] = useState('');
  const [stepTemplates, setStepTemplates] = useState('');
  const [stepObservation, setStepObservation] = useState('');
  const [stepNextBranch, setStepNextBranch] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [submitOk, setSubmitOk] = useState('');

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const res = await api.projects();
      setServerProjects(res);
    } catch (err) {
      setLoadError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  const projects = useMemo(() => normalizeProjects(serverProjects, data.pages), [serverProjects, data.pages]);

  useEffect(() => {
    if (projects.length && (!selectedProjectId || !projects.some((p) => p.id === selectedProjectId))) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  const activeProject = projects.find((p) => p.id === selectedProjectId) ?? projects[0];
  const templateChoices = useMemo(
    () =>
      data.pages
        .filter((p) => (p.meta.type === 'template' || p.meta.type === 'method' || p.meta.type === 'recipe') && p.meta.status !== 'archived')
        .map((p) => ({ id: 'id' in p.meta ? p.meta.id : p.path, title: p.meta.title }))
        .sort((a, b) => a.id.localeCompare(b.id)),
    [data.pages],
  );

  const handleAppendStep = async (e: FormEvent) => {
    e.preventDefault();
    if (!activeProject) return;
    if (!stepTitle.trim()) {
      setSubmitError('请填写步骤标题');
      return;
    }
    setSubmitting(true);
    setSubmitError('');
    setSubmitOk('');
    try {
      const updated = await api.addProjectStep(activeProject.id, {
        title: stepTitle.trim(),
        templates: stepTemplates.trim() || '未指定模版',
        observation: stepObservation.trim() || '已完成本步计算与检查',
        next_branch: stepNextBranch.trim() || '待根据结果选择下一步分支',
      });
      setServerProjects((prev) => {
        const current = Array.isArray(prev) ? prev : prev?.projects ?? [];
        const replaced = current.map((p) => (p.id === updated.id ? updated : p));
        if (!replaced.some((p) => p.id === updated.id)) replaced.push(updated);
        return replaced;
      });
      setStepTitle('');
      setStepTemplates('');
      setStepObservation('');
      setStepNextBranch('');
      setSubmitOk(`已追加步进记录到 ${activeProject.id}`);
    } catch (err) {
      setSubmitError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="projects-board">
      <header className="hero slim">
        <div className="hero-text">
          <h1>课题步进看板</h1>
          <p className="lede">
            记录每个生信课题的极简 3 行式步进进展（所用模版 / 观察结果与排坑 / 触发下一步），打通「步进决策导航 → 代码模版操控台 → 课题档案」。
          </p>
        </div>
        <div className="playbook-quick-links">
          <a className="button" href="#/playbooks">返回步进决策导航</a>
          <a className="button primary" href="#/studio">打开代码操控台</a>
        </div>
      </header>

      {loading && <p className="notice" role="status">正在读取课题步进卡…</p>}
      {loadError && !projects.length && <p className="notice error" role="alert">读取课题列表失败：{loadError}</p>}

      <div className="projects-layout">
        <aside className="projects-sidebar sheet" aria-label="课题列表">
          <h2>课题列表 ({projects.length})</h2>
          {projects.length === 0 ? (
            <p className="small muted">暂无课题卡片。可在 <code>wiki/projects/</code> 创建课题 Markdown。</p>
          ) : (
            <ul className="project-selector-list">
              {projects.map((p) => (
                <li key={p.id}>
                  <button
                    type="button"
                    className={activeProject?.id === p.id ? 'project-select-btn active' : 'project-select-btn'}
                    onClick={() => setSelectedProjectId(p.id)}
                  >
                    <strong>{p.title}</strong>
                    <span className="small muted">{p.id} · {(p.steps ?? []).length} 步</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        {activeProject && (
          <div className="projects-main">
            <article className="sheet project-detail-card">
              <div className="project-card-head">
                <div>
                  <span className="studio-eyebrow">PROJECT STEPWISE CARD</span>
                  <h2>{activeProject.title}</h2>
                  <p className="small muted">
                    文件：<code>{activeProject.path}</code>
                    {' · '}
                    <a {...pageLink(activeProject.path)}>查看原始 Wiki 页</a>
                  </p>
                </div>
                <span className="badge status-ready">{(activeProject.steps ?? []).length} 个已记录步骤</span>
              </div>

              {(activeProject.steps ?? []).length === 0 ? (
                <p className="notice">此课题尚无步进记录，在下方表单添加 Step 1。</p>
              ) : (
                <ol className="project-timeline">
                  {(activeProject.steps ?? []).map((st, idx) => {
                    const tokens = (st.templates || '')
                      .split(/[,\s、;]+/)
                      .map((s) => s.replace(/`/g, '').trim())
                      .filter((s) => s && templateChoices.some((tc) => tc.id === s));
                    return (
                      <li key={`${st.title}:${idx}`} className="project-step-item">
                        <div className="project-step-header">
                          <span className="step-index">Step {idx + 1}</span>
                          <h3>{st.title}</h3>
                        </div>
                        <dl className="project-step-fields small">
                          <dt>所用模版</dt>
                          <dd>
                            <span>{st.templates || '未填写'}</span>
                            {tokens.map((tid) => (
                              <a key={tid} className="button small inline-studio-btn" href={studioHref(tid)}>
                                在操控台打开 {tid}
                              </a>
                            ))}
                          </dd>
                          <dt>观察结果与排坑</dt>
                          <dd>{st.observation || '—'}</dd>
                          <dt>触发下一步</dt>
                          <dd>{st.next_branch || '—'}</dd>
                        </dl>
                      </li>
                    );
                  })}
                </ol>
              )}
            </article>

            <form className="sheet project-step-form" onSubmit={(e) => void handleAppendStep(e)}>
              <h2>追加新步进记录（3 行式卡片）</h2>
              <div className="step-form-grid">
                <label>
                  <span>步骤标题</span>
                  <input
                    type="text"
                    required
                    value={stepTitle}
                    onChange={(e) => setStepTitle(e.target.value)}
                    placeholder="例如：Step 4：髓系亚群乳酸化多算法打分与拟时序"
                  />
                </label>

                <label>
                  <span>所用分析 / 可视化模版</span>
                  <div className="template-pick-row">
                    <input
                      type="text"
                      value={stepTemplates}
                      onChange={(e) => setStepTemplates(e.target.value)}
                      placeholder="例如：gene-set-scoring, fig03-ridge"
                    />
                    <select
                      aria-label="快速插入模版 ID"
                      value=""
                      onChange={(e) => {
                        if (!e.target.value) return;
                        setStepTemplates((prev) => (prev.trim() ? `${prev.trim()}, ${e.target.value}` : e.target.value));
                      }}
                    >
                      <option value="">+ 快速选择模版 ID</option>
                      {templateChoices.map((tc) => (
                        <option key={tc.id} value={tc.id}>{tc.title} ({tc.id})</option>
                      ))}
                    </select>
                  </div>
                </label>

                <label>
                  <span>观察结果与排坑</span>
                  <textarea
                    rows={3}
                    value={stepObservation}
                    onChange={(e) => setStepObservation(e.target.value)}
                    placeholder="记录核心生物学发现、参数阈值（如 padj < 0.05）及遇到的坑"
                  />
                </label>

                <label>
                  <span>触发下一步分支</span>
                  <input
                    type="text"
                    value={stepNextBranch}
                    onChange={(e) => setStepNextBranch(e.target.value)}
                    placeholder="例如：分支 C（高乳酸化巨噬细胞拟时序分化）→ trajectory-inference"
                  />
                </label>
              </div>

              {submitError && <p className="notice error small" role="alert">{submitError}</p>}
              {submitOk && <p className="notice small" role="status">{submitOk}</p>}

              <div className="step-form-actions">
                <button type="submit" className="button primary" disabled={submitting}>
                  {submitting ? '正在保存…' : '追加步骤到课题卡'}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </section>
  );
}
