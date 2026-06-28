import { supabase } from "./supabase";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
export const WS_BASE_URL = API_BASE_URL.replace(/^http/, "ws");

/**
 * Custom fetch wrapper that automatically injects the current Supabase session JWT 
 * as Authorization Bearer header, and the GitHub provider token as X-GitHub-Token header.
 */
export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const { data: { session } } = await supabase.auth.getSession();
  const supabaseToken = session?.access_token;
  const githubToken = session?.provider_token || (typeof window !== "undefined" ? localStorage.getItem("gitgenesis_github_token") : null);

  const headers = new Headers(options.headers || {});
  
  if (supabaseToken) {
    headers.set("Authorization", `Bearer ${supabaseToken}`);
  }
  
  if (githubToken) {
    headers.set("X-GitHub-Token", githubToken);
  }

  return fetch(url, {
    ...options,
    headers
  });
}

