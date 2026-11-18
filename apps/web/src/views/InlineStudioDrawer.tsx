import { useEffect } from 'react';
import { studioHref } from '../api';
import type { AppData } from '../App';
import { StudioView } from './StudioView';

export interface InlineStudioDrawerProps {
  templateId: string;
  templateTitle?: string;
  data: AppData;
  onClose: () => void;
}

export function InlineStudioDrawer({ templateId, templateTitle, data, onClose }: InlineStudioDrawerProps) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    addEventListener('keydown', onKey);
    return () => removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div
      className="inline-studio-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label={`内联作图工作台：${templateTitle || templateId}`}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="inline-studio-drawer sheet">
        <div className="inline-studio-bar">
          <div className="inline-studio-meta">
            <span className="badge">内联参数定制与本机试跑</span>
            <strong>{templateTitle || templateId}</strong>
            <code>{templateId}</code>
          </div>
          <div className="inline-studio-actions">
            <a className="button small" href={studioHref(templateId)}>
              在独立工作台打开
            </a>
            <button type="button" className="button small" onClick={onClose}>
              关闭抽屉
            </button>
          </div>
        </div>
        <div className="inline-studio-body">
          <StudioView data={data} query={`id=${encodeURIComponent(templateId)}`} embedded />
        </div>
      </div>
    </div>
  );
}
