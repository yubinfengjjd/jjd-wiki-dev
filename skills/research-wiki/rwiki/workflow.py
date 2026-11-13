"""Read-only remaining actions. Persistent signoff states are never rewritten here."""
from pathlib import Path

from .catalog import readable_pages
from .acceptance import entry_errors, acceptance_stale


def workflow_snapshot(config) -> dict[str, dict]:
    root = config.wiki_root
    records = {p.relative_to(root).as_posix(): meta for p, meta in readable_pages(root)}
    from .asset_checkout import profile
    if profile(config) == 'light':
        return {path: {'stage': 'archived' if meta.get('status') == 'archived' else 'checking',
                       'queue': None,
                       'label': '已归档' if meta.get('status') == 'archived' else '轻量检出 · 未核对完整证据',
                       'reason': '轻量检出不据资产省略判断科学或回放失败；正式维护请切换 full。',
                       'templates': []}
                for path, meta in records.items()
                if meta.get('type') in ('method', 'template', 'recipe', 'layout')}
    result = {}

    def put(path, stage, queue, label, reason, templates=()):
        result[path] = dict(stage=stage, queue=queue, label=label, reason=reason,
                            templates=list(templates))

    for path, meta in records.items():
        kind, status = meta.get('type'), meta.get('status')
        if status == 'archived':
            put(path, 'archived', None, '已归档', '已归档，不进入待办。')
        elif kind == 'template' and status in ('draft', 'ready'):
            errors = entry_errors(config, root / path)
            if not errors and status == 'ready' and not acceptance_stale(root / path):
                put(path, 'complete', None, '可用', '已确认可用；当前笔记与回放完整。')
            elif not errors and status == 'draft':
                put(path, 'template_confirm', 'confirm', '回放通过 · 待确认',
                    '已有成功回放记录及输出；对照图样后由作者确认，回放不自动标为可用。')
            else:
                put(path, 'template_work', 'agent', '待完成回放',
                    '；'.join(errors) or '验收记录与当前内容不同，请 check-entry --record；不重复新建。')
        elif kind == 'method' and status in ('draft', 'ready'):
            from .method_implementations import METHOD_KINDS, implementation_status
            errors = entry_errors(config, root / path)
            method_kind = meta.get('method_kind')
            if method_kind not in METHOD_KINDS:
                put(path, 'method_classify', 'agent', '待分类', '旧方法尚未分类；先核对研究问题与资料类型。')
            elif errors or (status == 'ready' and acceptance_stale(root / path)):
                put(path, 'method_work', 'agent', '待完善笔记', '；'.join(errors) or '验收记录需重新核对。')
            elif status == 'draft':
                put(path, 'method_confirm', 'confirm', '待你确认', '笔记与知识关联检查已填写，待作者核对。')
            elif method_kind in ('workflow', 'technical'):
                label = '流程资料已确认' if method_kind == 'workflow' else '技术资料已确认'
                put(path, 'complete', None, label,
                    '笔记与资料内容已确认；不作为可执行分析推荐，也不要求分析实现收据。')
            else:
                states = implementation_status(root / path, meta)
                verified = any(item['state'] == 'verified' for item in states)
                if verified:
                    put(path, 'complete', None, '已验证实现', '笔记已确认；仅实现收据中列明的分支和范围通过验证。')
                else:
                    put(path, 'method_implementation', 'agent', '待验证实现' if states else '待实现',
                        '笔记已确认；实现尚无当前有效验证，不作为可执行分析推荐。')
        elif kind == 'recipe' and status in ('draft', 'ready'):
            from .repair_acceptance import validate_repair
            errors = entry_errors(config, root / path)
            repair_ok = validate_repair(config, root / path, require_approval=True)['valid']
            if repair_ok:
                put(path, 'repair_complete', None, '修补版运行通过',
                    '作者已确认当前 repair/ 修补版的通过收据；原样 source/ 及其运行记录保持独立，修补确认不改变原样运行资格。')
            elif not errors and status == 'ready' and not acceptance_stale(root / path):
                put(path, 'complete', None, '可原样运行', '已确认；当前原字节有通过的原样运行收据。')
            elif not errors and status == 'draft':
                put(path, 'recipe_confirm', 'confirm', '原样运行通过 · 待确认',
                    '原样运行已通过；可与同批配方一起 mark-ready。运行通过不等于科学有效。')
            else:
                waiting = any(message.startswith('最近运行为 not_run') for message in errors)
                reason = '；'.join(errors) or '验收记录与当前内容不同，请 check-entry --record'
                put(path, 'recipe_work', 'agent', '待装包' if waiting else '待补齐',
                    reason + ('（装包须作者按批次批准一次）' if waiting else ''))
        elif status == 'ready' and kind != 'layout':
            put(path, 'complete', None, '可用', '已确认可用。')

    for path, meta in records.items():
        if meta.get('type') != 'layout' or meta.get('status') == 'archived':
            continue
        if meta.get('status') == 'pending_signoff':
            put(path, 'signoff', 'signoff', '待签核', '来源图样或新版本仍待作者签核。')
            continue
        if meta.get('status') == 'ready':
            from .templates import layout_ready_errors
            try:
                errors = layout_ready_errors(config, meta)
            except (KeyError, TypeError, ValueError, OSError) as error:
                errors = [f'版式元数据无效: {error}']
            if errors:
                put(path, 'layout_work', 'agent', '待核查版式', '；'.join(errors),
                    [f'templates/{tid}.md' for tid in meta.get('templates', [])])
                continue
            if acceptance_stale(root / path):
                put(path, 'layout_work', 'agent', '待核查版式',
                    '验收记录与当前内容不同，请 check-entry --record',
                    [f'templates/{tid}.md' for tid in meta.get('templates', [])])
                continue
        panels = meta.get('panels') if isinstance(meta.get('panels'), dict) else {}
        tids = meta.get('templates') if isinstance(meta.get('templates'), list) else []
        mapping = meta.get('template_panels') if isinstance(meta.get('template_panels'), dict) else {}
        covered, active = [], []
        invalid = set(mapping) != set(tids)
        for tid in tids:
            template_path = f'templates/{tid}.md'
            tm = records.get(template_path)
            letters = mapping.get(tid, [])
            if (not tm or tm.get('type') != 'template' or tm.get('status') == 'archived'
                    or meta['id'] not in tm.get('layouts', []) or not letters
                    or len(tm.get('chart_types', [])) != 1
                    or any(letter not in panels or panels[letter] != tm['chart_types'][0]
                           for letter in letters)):
                invalid = True
                continue
            covered.extend(letters)
            active.append(template_path)
        if invalid or not panels or set(covered) != set(panels) or len(covered) != len(set(covered)):
            put(path, 'template_missing', 'agent', '待补齐模板',
                '选定 panel 的有效模板覆盖尚未完整；先核查缺失、归档或关联，不重做已完成模板。', active)
        elif all(result.get(p, {}).get('stage') == 'complete' for p in active):
            put(path, 'complete', None, '模板已就绪',
                '选定 panel 已由可用模板完整覆盖，来源不再计入待办；不表示另做了来源版式回放。', active)
        else:
            waiting = all(result.get(p, {}).get('queue') == 'confirm'
                          for p in active if result.get(p, {}).get('stage') != 'complete')
            put(path, 'template_confirm' if waiting else 'template_work', None,
                '模板回放通过 · 待确认' if waiting else '模板制作中',
                '工作列在关联模板，不再把来源重复计数。', active)
    return result


def pending_sources(config) -> list[str]:
    """CLI keeps returning source IDs; work on their existing draft where present."""
    workflow = workflow_snapshot(config)
    return sorted(Path(path).stem for path, item in workflow.items()
                  if path.startswith('layouts/') and item['stage'] != 'archived'
                  and (item['queue'] == 'agent' or any(
                      workflow.get(tid, {}).get('queue') == 'agent' for tid in item['templates'])))
