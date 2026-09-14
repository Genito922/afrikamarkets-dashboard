import { useState, useEffect, useCallback } from "react";
import { botsApi, credentialsApi } from "../api/bots";

export function useBots() {
  const [bots,  setBots]  = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,  setError]  = useState(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const data = await botsApi.list();
      setBots(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return { bots, loading, error, refresh };
}

export function useCredentials() {
  const [creds,   setCreds]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const data = await credentialsApi.list();
      setCreds(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return { creds, loading, error, refresh };
}
