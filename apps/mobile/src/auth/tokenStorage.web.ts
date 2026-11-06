let accessToken: string | null = null;

export async function readToken(): Promise<string | null> {
  return accessToken;
}

export async function writeToken(token: string): Promise<void> {
  accessToken = token;
}

export async function clearToken(): Promise<void> {
  accessToken = null;
}
