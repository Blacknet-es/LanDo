import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { clearToken, readToken, writeToken } from './tokenStorage';

interface SessionContextValue {
  accessToken: string | null;
  storageError: string | null;
  ready: boolean;
  signIn(token: string): Promise<void>;
  signOut(): Promise<void>;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [storageError, setStorageError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    void readToken()
      .then((token) => {
        if (!active) return;
        setAccessToken(token);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setStorageError(error instanceof Error ? error.message : 'No se pudo leer la sesión.');
      })
      .finally(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
    };
  }, []);

  const signIn = useCallback(async (token: string) => {
    await writeToken(token);
    setAccessToken(token);
  }, []);

  const signOut = useCallback(async () => {
    try {
      await clearToken();
      setStorageError(null);
    } catch (error) {
      setStorageError(error instanceof Error ? error.message : 'No se pudo cerrar la sesión.');
      throw error;
    } finally {
      setAccessToken(null);
    }
  }, []);

  const value = useMemo(
    () => ({ accessToken, storageError, ready, signIn, signOut }),
    [accessToken, ready, signIn, signOut, storageError],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const session = useContext(SessionContext);
  if (!session) throw new Error('useSession must be used within SessionProvider');
  return session;
}
