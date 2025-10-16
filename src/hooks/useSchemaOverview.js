import { useState, useEffect } from 'react';
import { fetchSchemaOverview } from '../services/api';

export const useSchemaOverview = () => {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    const loadOverview = async () => {
      try {
        const data = await fetchSchemaOverview();
        if (isMounted) {
          setOverview(data);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || 'Failed to load schema overview');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadOverview();
    return () => {
      isMounted = false;
    };
  }, []);

  return { overview, loading, error };
};
