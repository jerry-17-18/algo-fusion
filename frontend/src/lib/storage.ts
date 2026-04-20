const AUTH_TOKEN_KEY = "clinical-voice-ai-token";
const AUTH_USER_KEY = "clinical-voice-ai-user";

export function getAuthToken(): string | null {
  return window.localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setAuthToken(token: string): void {
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearAuthToken(): void {
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
}

export function getStoredUser<T>(): T | null {
  const rawValue = window.localStorage.getItem(AUTH_USER_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    return JSON.parse(rawValue) as T;
  } catch {
    return null;
  }
}

export function setStoredUser(value: unknown): void {
  window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(value));
}

export function clearStoredUser(): void {
  window.localStorage.removeItem(AUTH_USER_KEY);
}
