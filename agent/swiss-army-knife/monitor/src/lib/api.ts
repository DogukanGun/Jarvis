const API_BASE = 'http://localhost:8787';

export async function fetchTools() {
  const res = await fetch(`${API_BASE}/api/tools`);
  if (!res.ok) throw new Error('Failed to fetch tools');
  return res.json() as Promise<{ tools: import('./types').ToolMetadata[]; total: number }>;
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/api/health`);
  return res.json();
}

export async function executeSync(req: import('./types').ExecuteRequest) {
  const res = await fetch(`${API_BASE}/api/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error('Execution failed');
  return res.json() as Promise<import('./types').ExecuteResponse>;
}

export async function executeAsync(req: import('./types').ExecuteRequest) {
  const res = await fetch(`${API_BASE}/api/execute/async`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error('Async execution failed');
  return res.json() as Promise<import('./types').AsyncExecuteResponse>;
}

export async function confirmJob(jobId: string, confirmed: boolean) {
  const res = await fetch(`${API_BASE}/api/execute/confirm/${jobId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirmed }),
  });
  return res.json();
}

export async function fetchJob(jobId: string) {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
  if (!res.ok) throw new Error('Job not found');
  return res.json() as Promise<import('./types').JobStatus>;
}

export async function fetchAllJobs(status?: string) {
  const url = status ? `${API_BASE}/api/jobs?status=${status}` : `${API_BASE}/api/jobs`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch jobs');
  const data = await res.json();
  return data.jobs as import('./types').JobStatus[];
}

export async function fetchJobOutput(jobId: string, since = 0) {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}/output?since=${since}`);
  if (!res.ok) return null;
  return res.json() as Promise<{ job_id: string; output: string; offset: number }>;
}

export async function sendSessionCommand(jobId: string, command: string) {
  const res = await fetch(`${API_BASE}/api/sessions/${jobId}/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command }),
  });
  return res.json();
}
