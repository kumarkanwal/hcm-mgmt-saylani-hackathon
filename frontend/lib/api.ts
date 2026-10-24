import { mockRequest } from "@/lib/mocks";

export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCK_API !== "false";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";
const TOKEN_KEY = "hcm_access_token";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined>;
};

export function getToken() {
  return typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

function buildPath(path: string, query?: RequestOptions["query"]) {
  const url = new URL(path, "http://hcm.local");
  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== "") url.searchParams.set(key, String(value));
  });
  return `${url.pathname}${url.search}`;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const requestPath = buildPath(path, options.query);
  const token = getToken();

  if (USE_MOCKS) {
    try {
      return await mockRequest<T>(method, requestPath, options.body, token);
    } catch (error) {
      const mockError = error as { status?: number; detail?: { code?: string; message?: string } };
      throw new ApiError(mockError.status ?? 500, mockError.detail?.code ?? "MOCK_ERROR", mockError.detail?.message ?? "The sample request failed.");
    }
  }

  const isFormData = options.body instanceof FormData;
  const response = await fetch(`${API_URL}${requestPath}`, {
    method,
    headers: {
      ...(isFormData ? {} : options.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: options.body ? (isFormData ? options.body : JSON.stringify(options.body)) : undefined,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: { code: "HTTP_ERROR", message: response.statusText } }));
    const code = payload?.detail?.code ?? "HTTP_ERROR";
    const message = payload?.detail?.message ?? response.statusText;
    if (response.status === 401) {
      setToken(null);
      window.dispatchEvent(new Event("hcm-auth-cleared"));
    }
    if (response.status === 403 && code === "PASSWORD_CHANGE_REQUIRED") window.location.assign("/change-password");
    throw new ApiError(response.status, code, message);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string, query?: RequestOptions["query"]) => apiRequest<T>(path, { query }),
  post: <T>(path: string, body?: unknown, query?: RequestOptions["query"]) => apiRequest<T>(path, { method: "POST", body, query }),
  put: <T>(path: string, body?: unknown) => apiRequest<T>(path, { method: "PUT", body }),
  patch: <T>(path: string, body?: unknown) => apiRequest<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) => apiRequest<T>(path, { method: "DELETE" }),
};
