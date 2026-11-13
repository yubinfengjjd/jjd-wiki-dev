import { useEffect, useState } from 'react';
import { api, LogEntry } from '../api';

export function LogView() {
  const [entries, setEntries] = useState<LogEntry[] | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.log().then(setEntries, (e: Error) => setError(e.message));
  }, []);

  if (error) return <p className="notice error">{error}</p>;
  if (!entries) return null;

  return (
    <section className="narrow">
      <h1 className="page-title">操作日志</h1>
      <p className="muted">每次收录、签核、编辑都会记一条，并在总库里生成一次 git 提交。</p>
      <ol className="log">
        {entries.map((e, i) => (
          <li key={i}>
            <time>{e.time}</time>
            <span>{e.message}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
