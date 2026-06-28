"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "../app/supabase";
import { Session, User } from "@supabase/supabase-js";
import { GitPullRequest, LogIn } from "lucide-react";

interface AuthContextType {
  user: User | null;
  session: Session | null;
  supabaseToken: string | null;
  githubToken: string | null;
  loading: boolean;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  session: null,
  supabaseToken: null,
  githubToken: null,
  loading: true,
  logout: async () => {},
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [storedGithubToken, setStoredGithubToken] = useState<string | null>(null);

  useEffect(() => {
    // Load stored GitHub token if any
    const saved = localStorage.getItem("gitgenesis_github_token");
    if (saved) {
      setStoredGithubToken(saved);
    }

    // 1. Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      if (session?.provider_token) {
        localStorage.setItem("gitgenesis_github_token", session.provider_token);
        setStoredGithubToken(session.provider_token);
      }
      setLoading(false);
    });

    // 2. Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      if (session?.provider_token) {
        localStorage.setItem("gitgenesis_github_token", session.provider_token);
        setStoredGithubToken(session.provider_token);
      } else if (!session) {
        localStorage.removeItem("gitgenesis_github_token");
        setStoredGithubToken(null);
      }
      setLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const handleLogin = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "github",
      options: {
        scopes: "repo write:repo_hook read:org workflow",
        redirectTo: typeof window !== "undefined" ? window.location.origin : undefined,
      },
    });
  };

  const logout = async () => {
    await supabase.auth.signOut();
  };

  const supabaseToken = session?.access_token || null;
  const githubToken = session?.provider_token || storedGithubToken || null;

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f4f0e6] flex flex-col items-center justify-center text-black font-sans">
        <div className="px-6 py-4 border-4 border-black bg-white shadow-[8px_8px_0px_0px_#000000] font-bold text-lg uppercase tracking-tight">
          Checking Authentication Status...
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="min-h-screen bg-[#f4f0e6] flex flex-col justify-between text-black font-sans">
        {/* Header Navigation */}
        <header className="w-full h-20 border-b-4 border-black px-6 md:px-12 flex items-center justify-between bg-white z-10 shrink-0">
          <div className="flex items-center gap-2">
            <div className="px-3 py-1 bg-yellow-400 neo-border font-extrabold text-lg uppercase tracking-tight select-none shadow-[2px_2px_0px_0px_#000000]">
              GitGenesis
            </div>
            <span className="text-xs font-mono font-bold text-zinc-500 uppercase tracking-widest pl-1 mt-1">by Nevan</span>
          </div>
        </header>

        {/* Hero Card */}
        <div className="flex-1 flex flex-col justify-center items-center py-16 px-6 z-10">
          <div className="w-full max-w-md bg-[#fffbef] border-4 border-black p-8 rounded-none shadow-[8px_8px_0px_0px_#000000] flex flex-col gap-6 text-center">
            <div className="w-16 h-16 bg-yellow-400 border-4 border-black rounded-none flex items-center justify-center mx-auto shadow-[4px_4px_0px_0px_#000000]">
              <GitPullRequest className="w-8 h-8 text-black" />
            </div>
            <div>
              <h2 className="text-3xl font-black uppercase tracking-tight leading-none mb-4">
                Authentication Required
              </h2>
              <p className="text-sm font-medium text-zinc-700 leading-relaxed">
                Connect your GitHub account to reverse engineer codebases, build interactive engineering blueprints, and run verification suites securely.
              </p>
            </div>

            <button
              onClick={handleLogin}
              className="w-full px-6 py-4 bg-yellow-400 text-black font-extrabold border-4 border-black text-sm uppercase hover:-translate-x-1 hover:-translate-y-1 hover:shadow-[5px_5px_0px_0px_#000000] active:translate-x-0 active:translate-y-0 active:shadow-none transition-all shadow-[4px_4px_0px_0px_#000000] flex items-center justify-center gap-2 cursor-pointer"
            >
              <LogIn className="w-5 h-5" /> Sign in with GitHub
            </button>
          </div>
        </div>

        {/* Footer */}
        <footer className="w-full h-16 border-t-4 border-black px-6 md:px-12 flex items-center justify-center bg-white z-10 shrink-0 text-xs font-bold uppercase tracking-wider text-zinc-600">
          GitGenesis © 2026. Cloud isolated sandboxes.
        </footer>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user: session.user, session, supabaseToken, githubToken, loading, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
