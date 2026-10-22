import type { Compatibility, Relation, Verification } from './api';

export const COMPATIBILITY_LABEL: Record<Compatibility, string> = {
  direct: '直接可接', adaptable: '需要适配', candidate: '待核实',
};

export function verificationLabel(verification?: Verification): string {
  const labels: Record<string, string> = { not_run: '未运行验证', example: '示例验证', project: '课题验证', unknown: '验证状态未知' };
  return labels[verification?.state ?? 'unknown'] ?? '验证状态未知';
}

export function relationTargetLabel(relation: Relation): string {
  if (relation.target_kind === 'layout') return '来源图样参考；执行时查看关联模板';
  if (relation.figure_status !== 'ready') return '模板尚未确认可用';
  return '可调用模板；调用前仍需检查课题条件';
}

/** Semantic templates shown when no template consumes the method's declared output interface. */
export function adaptableTemplateRelations(relations: Relation[]): Relation[] {
  return relations.filter((relation) => relation.active
    && relation.target_kind === 'template'
    && relation.compatibility === 'adaptable');
}

/** Explicit state survives archive history; inactive records are never executable recommendations. */
export function relationLabel(relation: Relation): string {
  return `${COMPATIBILITY_LABEL[relation.compatibility]}${relation.active ? '' : ' · 已停用'}`;
}
