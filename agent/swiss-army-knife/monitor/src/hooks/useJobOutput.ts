'use client';
import { useState, useEffect, useRef } from 'react';
import { fetchJobOutput } from '../lib/api';

export function useJobOutput(jobId: string | null) {
  const [output, setOutput] = useState('');
  const offsetRef = useRef(0);

  useEffect(() => {
    if (!jobId) {
      setOutput('');
      offsetRef.current = 0;
      return;
    }

    const poll = async () => {
      const data = await fetchJobOutput(jobId, offsetRef.current);
      if (data && data.output) {
        setOutput((prev) => prev + data.output);
        offsetRef.current += data.output.length;
      }
    };

    poll();
    const interval = setInterval(poll, 1000);
    return () => clearInterval(interval);
  }, [jobId]);

  return { output };
}
