"""Composable cross-domain evidence/prerequisite profiles.

Profiles are versioned *specification fixtures* (``domain_profiles.yaml``):
each declares which entities/objects/observations a class of tasks needs —
not that the corresponding algorithms exist, run, or are verified. Method and
figure references are canonical Wiki ids resolved live by the caller; a profile
never copies a mutable availability table.

Evaluation is three-valued against a project state (``project_state``):

- ``satisfied``   — matching, current, in-scope evidence exists; ``basis``
                    reports its strongest *effective* basis.
- ``unsatisfied`` — only explicit negative evidence (``value: false``) yields
                    this; absence is never treated as failure.
- ``unknown``     — no matching evidence, or only ``unknown``-valued records.
- ``conflicted``  — equal-tier positive and negative evidence both present.
- ``not_applicable`` — a conditional prerequisite whose ``when``/``unless``
                    gate says it does not apply to this task context.

Scope: ``subject`` binds evaluation to one coherent context (an object, entity
or task ref). Without a subject, only unscoped observations (``about=None``)
count — an observation *about another object* is never universal proof.

Freshness: object/artifact hits whose underlying material is missing or whose
fingerprint changed are excluded — stale evidence cannot satisfy a current
prerequisite. No separate manual pre-check is required.

Basis semantics: ``verified`` without an inspectable evidence file is treated
at ``author_stated`` tier — file existence/hash is an integrity fact, not
scientific proof.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from .errors import WikiError
from . import project_state as ps

PROFILE_FILE = Path(__file__).resolve().parent / 'domain_profiles.yaml'
_SCHEMA_VERSION = 1
_BASIS_RANK = {'verified': 3, 'author_stated': 2, 'unknown': 1}
STATES = ('satisfied', 'unsatisfied', 'unknown', 'conflicted', 'not_applicable')


def load_profiles(path: Path | None = None) -> dict:
    target = Path(path) if path else PROFILE_FILE
    try:
        data = yaml.safe_load(target.read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError) as error:
        raise WikiError(f'领域配置无法读取 {target}: {error}') from error
    if not isinstance(data, dict) or data.get('schema_version') != _SCHEMA_VERSION:
        raise WikiError(f'{target.name} schema_version 必须为 {_SCHEMA_VERSION}')
    profiles = data.get('profiles')
    if not isinstance(profiles, dict) or not profiles:
        raise WikiError(f'{target.name} 缺少 profiles')
    for pid, profile in profiles.items():
        if not isinstance(profile, dict):
            raise WikiError(f'profile {pid} 必须为对象')
        for key in ('version', 'domain', 'label', 'entity_kinds', 'object_kinds',
                    'context_fields', 'prerequisites', 'stage_evidence', 'result_checks'):
            if key not in profile:
                raise WikiError(f'profile {pid} 缺少 {key}')
    return profiles


def profile_ids(path: Path | None = None) -> list[str]:
    return sorted(load_profiles(path))


def profile_fingerprint(spec: dict) -> str:
    """Content hash of the evaluated spec — what ``register_profile`` binds."""
    payload = json.dumps(spec, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _as_list(value):
    return value if isinstance(value, list) else [value]


def _props_match(properties: dict, required: dict) -> bool:
    for key, wanted in (required or {}).items():
        if key not in properties:
            return False
        actual = properties[key]
        if isinstance(wanted, list):
            if actual not in wanted:
                return False
        elif actual != wanted:
            return False
    return True


def _match_record(record: dict, check: dict, kind_key: str = 'kind') -> bool:
    match = check.get('match') or {}
    kinds = _as_list(match.get(kind_key)) if match.get(kind_key) is not None else None
    if kinds is not None and record.get(kind_key) not in kinds:
        return False
    properties = record.get('properties') or {}
    if not _props_match(properties, match.get('properties')):
        return False
    required_keys = check.get('require_properties') or []
    return all(properties.get(key) is not None and properties.get(key) != ''
               for key in required_keys)


def _subject_context(state: dict, subject: str | None, root: Path) -> dict | None:
    """Coherent context for scoped evaluation: which records belong together.

    ``subject`` may reference an object, entity, or task. The allowed sets make
    prerequisites refer to one dataset/task instead of composing unrelated
    records into a fake complete context.
    """
    if subject is None:
        return None
    kind, ident = ps.resolve_ref(state, subject)
    subject_ref = f'{kind}:{ident}'
    if kind == 'object':
        item = state['objects'][ident]
        return {'subject': subject_ref,
                'objects': {ident},
                'entities': {e.split(':', 1)[1] for e in item.get('entities') or []},
                'observations': {oid for oid, o in state['observations'].items()
                                 if o.get('about') == subject_ref},
                'artifacts': {aid for aid, a in state['artifacts'].items()
                              if subject_ref in (a.get('inputs') or [])}}
    if kind == 'entity':
        objs = {oid for oid, o in state['objects'].items()
                if f'entity:{ident}' in (o.get('entities') or [])}
        refs = {f'object:{o}' for o in objs} | {subject_ref}
        return {'subject': subject_ref,
                'objects': objs,
                'entities': {ident},
                'observations': {oid for oid, o in state['observations'].items()
                                 if o.get('about') in refs},
                'artifacts': {aid for aid, a in state['artifacts'].items()
                              if refs & set(a.get('inputs') or [])}}
    if kind == 'task':
        item = state['tasks'][ident]
        refs = set(item.get('inputs') or [])
        # Scope derives only from declared inputs: object:/entity:/artifact:
        # refs, objects or artifacts sharing a declared file:/external: input
        # path, and objects linked to declared entities. A task with no object
        # linkage keeps an empty scope — prerequisites stay unknown rather
        # than borrowing unrelated project objects.
        objs = {r.split(':', 1)[1] for r in refs if r.startswith('object:')}
        declared_entities = {r.split(':', 1)[1] for r in refs
                             if r.startswith('entity:')}
        input_paths = {ps._ref_path(state, root, r) for r in refs
                       if r.startswith(('file:', 'external:'))}
        input_paths.discard(None)
        for oid, obj in state['objects'].items():
            if oid in objs:
                continue
            if {f'entity:{e}' for e in declared_entities} & set(obj.get('entities') or []):
                objs.add(oid)
                continue
            if input_paths and _object_path(obj, state, root) in input_paths:
                objs.add(oid)
        artifacts = {r.split(':', 1)[1] for r in refs if r.startswith('artifact:')}
        for aid, art in state['artifacts'].items():
            if aid in artifacts:
                continue
            try:
                if input_paths and ps.project_path(root, art['path']) in input_paths:
                    artifacts.add(aid)
            except (WikiError, KeyError):
                continue
        scope_refs = (refs | {f'object:{o}' for o in objs}
                      | {f'entity:{e}' for e in declared_entities}
                      | {f'artifact:{a}' for a in artifacts} | {subject_ref})
        return {'subject': subject_ref,
                'objects': objs,
                'entities': declared_entities,
                'observations': {oid for oid, o in state['observations'].items()
                                 if o.get('about') in scope_refs},
                'artifacts': artifacts}
    raise WikiError(f'不支持以 {kind} 作为评估主体（用 object/entity/task 引用）')


def _object_path(item: dict, state: dict, root: Path) -> Path | None:
    try:
        if item.get('external'):
            return ps.external_path(state, item['external'])
        if item.get('path'):
            return ps.project_path(root, item['path'])
    except WikiError:
        return None
    return None


def _check_objects(state: dict, check: dict, *, root: Path, ctx,
                   report: dict | None = None) -> tuple:
    excluded = []
    hits = []
    for oid, item in state['objects'].items():
        if ctx is not None and oid not in ctx['objects']:
            continue
        if not _match_record(item, check):
            continue
        path = _object_path(item, state, root)
        material = ps.material_state(state, root, path=path,
                                     recorded_sha=item.get('sha256'))
        if material == 'missing':
            excluded.append(f'object:{oid} 材料缺失或路径不可解析')
            continue
        if material == 'stale':
            excluded.append(f'object:{oid} 材料指纹已变化')
            continue
        hits.append((oid, item))
    result = _best(hits, 'object')
    if result[0] == 'unknown' and excluded:
        return 'unknown', 'unknown', [], '；'.join(excluded)
    return (*result, '; '.join(excluded) if excluded else '')


def _check_entities(state: dict, check: dict, *, root: Path, ctx,
                    report: dict | None = None) -> tuple:
    hits = [(eid, item) for eid, item in state['entities'].items()
            if (ctx is None or eid in ctx['entities']) and _match_record(item, check)]
    return (*_best(hits, 'entity'), '')


def _obs_rank(item: dict, state: dict, root: Path,
              report: dict | None = None) -> int:
    """Effective evidence tier via the shared freshness resolvers.

    A ``verified`` claim with no inspectable evidence drops to author-stated
    tier; a claim whose recorded evidence is missing, changed or otherwise
    unresolvable drops below authoritative entirely — changed evidence bytes
    invalidate the claim, they do not merely weaken it.

    Subject freshness is version-scoped: a claim *about* an object or artifact
    whose material was replaced or removed is not current proof about the new
    version (a report on input v1 says nothing about v2) and drops below
    authoritative for either sign — conservatively, without claiming false.
    ``verified`` additionally needs a subject whose integrity can be checked:
    unhashed or unknown-freshness subjects cannot carry a verified claim.
    """
    rank = _BASIS_RANK.get(item.get('basis'), 0)
    if rank == 3:
        state_v = ps.evidence_state(state, root, item.get('evidence'))
        if state_v == 'none':
            rank = 2
        elif state_v != 'resolves':
            rank = 1
    if rank > 1:
        about = item.get('about')
        subject_state = None
        # For artifact subjects the *computed* report is authoritative: an
        # upstream-stale artifact may have unchanged bytes and a recorded
        # 'current' flag — neither makes a claim about it current proof.
        if report is not None and isinstance(about, str) \
                and about.startswith('artifact:'):
            aid = about.split(':', 1)[1]
            entry = (report.get('artifacts') or {}).get(aid)
            if entry is not None:
                subject_state = entry.get('freshness')
        if subject_state is None:
            # object:/file: subjects sharing a path with a produced artifact
            # inherit its computed freshness — upstream-invalidated material
            # cannot hide behind an alias whose own bytes are unchanged.
            subject_state = ps.subject_material_state(state, root, about,
                                                      report=report)
        if subject_state in ('missing', 'stale'):
            rank = 1
        elif subject_state in ('unhashed', 'unknown') and rank == 3:
            rank = 1
    return rank


def _check_observations(state: dict, check: dict, *, root: Path, ctx,
                        report: dict | None = None) -> tuple:
    """Contradiction-aware claim check.

    Positive and negative evidence are compared by effective tier; equal-tier
    disagreement is ``conflicted`` (never silently satisfied) with refs from
    both sides. Unknown-basis or unknown-valued records are not authoritative.
    """
    match = check.get('match') or {}
    claims = _as_list(match.get('claim')) if match.get('claim') is not None else None
    positive, negative = [], []
    for oid, item in state['observations'].items():
        if ctx is None:
            # Unscoped evaluation: observations bound to a specific record are
            # not universal proof.
            if item.get('about'):
                continue
        elif oid not in ctx['observations']:
            continue
        if claims is not None and item.get('claim') not in claims:
            continue
        if match.get('about') and item.get('about') != match['about']:
            continue
        rank = _obs_rank(item, state, root, report=report)
        if rank <= 1 or item.get('value') not in ('true', 'false'):
            continue  # unknown basis/value is not authoritative either way
        (positive if item['value'] == 'true' else negative).append((oid, item, rank))
    pos = max((r for _, _, r in positive), default=0)
    neg = max((r for _, _, r in negative), default=0)
    pos_refs = [f'observation:{o}' for o, _, r in positive if r == pos]
    neg_refs = [f'observation:{o}' for o, _, r in negative if r == neg]
    if pos and neg and pos == neg:
        return ('conflicted', 'unknown', pos_refs + neg_refs,
                '同层正负证据冲突，需显式裁决证据')
    if pos > neg:
        basis = 'verified' if pos == 3 else 'author_stated'
        return 'satisfied', basis, pos_refs, ''
    if neg:
        basis = 'verified' if neg == 3 else 'author_stated'
        return 'unsatisfied', basis, neg_refs, ''
    return 'unknown', 'unknown', [], ''


def _check_artifacts(state: dict, check: dict, *, root: Path, ctx,
                     report: dict | None = None) -> tuple:
    hits = []
    excluded = []
    for aid, item in state['artifacts'].items():
        if ctx is not None and aid not in ctx['artifacts']:
            continue
        if not _match_record(item, check):
            continue
        # Freshness must agree with check_project: propagated stale/unknown
        # (including file: aliases) is authoritative, not just the recorded flag.
        if report is not None:
            entry = (report.get('artifacts') or {}).get(aid)
            fresh = entry.get('freshness') if entry else \
                (item.get('freshness') or {}).get('state')
        else:
            fresh = (item.get('freshness') or {}).get('state')
        if fresh in ('stale', 'unknown'):
            excluded.append(f'artifact:{aid} 新鲜度为 {fresh}')
            continue
        try:
            path = ps.project_path(root, item['path'])
        except (WikiError, KeyError):
            excluded.append(f'artifact:{aid} 路径不可解析')
            continue
        material = ps.material_state(state, root, path=path,
                                     recorded_sha=item.get('sha256'))
        if material in ('missing', 'stale', 'unhashed'):
            excluded.append(f'artifact:{aid} 材料{material}')
            continue
        hits.append((aid, item))
    result = _best(hits, 'artifact')
    return (*result, '；'.join(excluded) if excluded else '')


def _best(hits, prefix: str) -> tuple:
    """Strongest-basis match wins; ``unknown``-basis hits never satisfy."""
    if not hits:
        return 'unknown', 'unknown', []
    strongest = max(hits, key=lambda pair: _BASIS_RANK.get(pair[1].get('basis'), 0))
    basis = strongest[1].get('basis', 'unknown')
    if basis == 'unknown':
        return 'unknown', 'unknown', []
    return 'satisfied', basis, [f'{prefix}:{strongest[0]}']


_CHECKERS = {'object': _check_objects, 'entity': _check_entities,
             'observation': _check_observations, 'artifact': _check_artifacts}


def _stage_evidence(state: dict, spec: dict) -> list:
    """Map declared stage names to actually registered scoped claims.

    Claim-based, not domain-hardcoded: the profile declares stage vocabulary;
    tasks and observations claim stage membership via their ``stage`` field.
    ``recorded`` means matching claims exist (each claim's run status/basis is
    reported verbatim) — it never asserts the stage is complete or verified.
    Stage tags no profile declares are surfaced under ``undeclared_claims``.
    """
    declared = [str(s) for s in spec['stage_evidence']]
    entries = []
    for stage in declared:
        claims = []
        for tid, task in state['tasks'].items():
            if task.get('stage') == stage:
                claims.append({'ref': f'task:{tid}', 'status': task['status'],
                               'runs': [{'run': rid, 'status': r['status']}
                                        for rid, r in state['runs'].items()
                                        if r['task'] == tid]})
        for oid, obs in state['observations'].items():
            if obs.get('stage') == stage:
                claims.append({'ref': f'observation:{oid}', 'basis': obs['basis'],
                               'value': obs['value']})
        entries.append({'stage': stage,
                        'evidence_state': 'recorded' if claims else 'not_recorded',
                        'claims': claims,
                        'note': '登记声明/运行记录；不据此认定阶段完成或结果正确'})
    undeclared = sorted({t.get('stage') for t in state['tasks'].values()
                         if t.get('stage') and t.get('stage') not in declared} |
                        {o.get('stage') for o in state['observations'].values()
                         if o.get('stage') and o.get('stage') not in declared})
    return entries, undeclared


def _sub_check_state(state: dict, spec: dict, *, root: Path, ctx,
                     report: dict | None = None) -> str:
    """Evaluate a nested ``when``/``unless`` condition spec to a full state."""
    ctype = spec.get('type')
    checker = _CHECKERS.get(ctype)
    if checker is None:
        return 'unknown'
    return checker(state, spec, root=root, ctx=ctx, report=report)[0]


def _eval_check(state: dict, check: dict, *, root: Path, ctx,
                report: dict | None = None) -> dict:
    ctype = check.get('type')
    checker = _CHECKERS.get(ctype)
    base = {'id': check.get('id', '?'), 'description': check.get('description', ''),
            'type': ctype, 'state': 'unknown', 'basis': 'unknown', 'evidence': [],
            'note': ''}
    if checker is None:
        base['note'] = f'未知 check 类型: {ctype}'
        return base
    state_v, basis, refs, note = checker(state, check, root=root, ctx=ctx,
                                         report=report)
    base.update(state=state_v, basis=basis, evidence=refs, note=note)
    # Conditional prerequisite: only when the main check is not satisfied do
    # gates decide applicability — a satisfied check never hides behind them.
    # Three-valued gates: ``when`` exempts only on *explicit* unsatisfied
    # (negative evidence the condition does not hold); unknown/conflicted
    # condition evidence keeps the prerequisite evaluated conservatively and
    # never exempts it. ``unless`` exempts only on explicit satisfied.
    if state_v != 'satisfied':
        when = check.get('when')
        unless = check.get('unless')
        if when is not None \
                and _sub_check_state(state, when, root=root, ctx=ctx,
                                     report=report) == 'unsatisfied':
            base.update(state='not_applicable', evidence=[],
                        note='条件被否定，此前提对本任务不适用')
        elif unless is not None \
                and _sub_check_state(state, unless, root=root, ctx=ctx,
                                     report=report) == 'satisfied':
            base.update(state='not_applicable', evidence=[],
                        note='满足豁免条件，此前提对本任务不适用')
    return base


def evaluate_profile(state: dict, profile: str, *, profiles_path: Path | None = None,
                     subject: str | None = None) -> dict:
    """Evaluate one profile's prerequisites against a project state dict.

    ``subject`` optionally scopes evaluation to one object/entity/task so that
    prerequisites refer to a coherent context; without it, only unscoped
    observations count and each record is evaluated on its own.
    """
    profiles = load_profiles(profiles_path)
    if profile not in profiles:
        raise WikiError(f'未登记的领域配置: {profile}（已有: {"、".join(sorted(profiles))}）')
    spec = profiles[profile]
    root = Path(state['project_root']).resolve()
    ctx = _subject_context(state, subject, root)
    # One shared freshness resolution: the check_project report is computed
    # once so artifact staleness (incl. file: alias propagation) agrees
    # between check and evaluate instead of diverging per-checker.
    try:
        report = ps.check_project(root)
    except WikiError:
        report = None
    checks = [_eval_check(state, check, root=root, ctx=ctx, report=report)
              for check in spec['prerequisites']]
    stage_entries, undeclared_stages = _stage_evidence(state, spec)
    coverage = {s: 0 for s in STATES}
    for check in checks:
        coverage[check['state']] += 1
    current_hash = profile_fingerprint(spec)
    registered = next((p for p in state.get('profile_refs', []) if p['id'] == profile), None)
    registration = None
    if registered is not None:
        registration = {'version': registered['version'],
                        'spec_sha256': registered.get('spec_sha256'),
                        'matches_current':
                            registered['version'] == spec['version']
                            and (registered.get('spec_sha256') in (None, current_hash))}
        if not registration['matches_current']:
            registration['warning'] = (
                f'评估使用当前规格 v{spec["version"]}/{current_hash[:12]}，'
                f'与登记的 v{registered["version"]}/{str(registered.get("spec_sha256") or "")[:12]} 不一致；'
                '未静默沿用旧登记')
    return {'profile': profile, 'version': spec['version'], 'domain': spec['domain'],
            'label': spec['label'], 'subject': subject,
            'spec_sha256': current_hash, 'registration': registration,
            'checks': checks, 'coverage': coverage,
            'declared_stages': list(spec['stage_evidence']),
            'stage_evidence': stage_entries,
            'undeclared_stage_claims': undeclared_stages,
            'result_checks': spec['result_checks'],
            'method_refs': list(spec.get('method_refs') or []),
            'figure_refs': list(spec.get('figure_refs') or []),
            'knowledge_gaps': list(spec.get('knowledge_gaps') or []),
            'note': '前提满足只说明当前在册材料证据；实现可用性按家族/分支收据逐项核查，'
                    '配置/规则测试不授予算法实际通过。阶段名为声明，不等同已完成的阶段证据。'}
