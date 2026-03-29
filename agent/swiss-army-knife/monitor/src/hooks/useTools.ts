'use client';
import { useState, useEffect } from 'react';
import type { ToolMetadata } from '../lib/types';
import { fetchTools } from '../lib/api';

export function useTools() {
  const [tools, setTools] = useState<ToolMetadata[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTools()
      .then((data) => setTools(data.tools))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return { tools, loading };
}
