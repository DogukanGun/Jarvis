'use client';
import { useState, useEffect } from 'react';
import type { JobStatus } from '../lib/types';
import { fetchAllJobs } from '../lib/api';

export function useJobs() {
  const [jobs, setJobs] = useState<JobStatus[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const poll = () => {
      fetchAllJobs()
        .then(setJobs)
        .catch(() => {})
        .finally(() => setLoading(false));
    };
    poll();
    const interval = setInterval(poll, 3000);
    return () => clearInterval(interval);
  }, []);

  return { jobs, loading };
}
