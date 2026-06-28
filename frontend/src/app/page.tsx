"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { GitFork, ArrowRight, Play, AlertCircle, User, LogOut } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import { WS_BASE_URL } from "./api";

export default function Home() {
  const router = useRouter();
  const { user, supabaseToken, githubToken, logout } = useAuth();
  
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [statusMsg, setStatusMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const consoleEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  const handleExampleClick = (url: string) => {
    setRepoUrl(url);
  };

  const handleAnalyze = () => {
    if (!repoUrl.trim()) return;
    setLoading(true);
    setErrorMsg("");
    setLogs([]);
    setStatusMsg("Establishing live connection to GitGenesis Agent Cluster...");

    const wsUrl = `${WS_BASE_URL}/api/ws/analyze`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      // Send the Supabase access token (JWT) and GitHub OAuth token (from session)
      socket.send(JSON.stringify({ 
        url: repoUrl, 
        token: supabaseToken,
        github_token: githubToken 
      }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "status") {
        setStatusMsg(data.message);
        setLogs((prev) => [...prev, `[System] ${data.message}`]);
      } else if (data.type === "log") {
        setLogs((prev) => [...prev, data.message]);
      } else if (data.type === "completed") {
        setLogs((prev) => [...prev, "[System] Inference complete. Persisting Executable Engineering Blueprint..."]);
        setTimeout(() => {
          router.push(`/blueprint/${data.blueprint_id}?branch_id=${data.branch_id}`);
        }, 1500);
      } else if (data.type === "error") {
        setErrorMsg(data.message);
        setLoading(false);
        socket.close();
      }
    };

    socket.onerror = () => {
      setErrorMsg("WebSocket connection failed. Make sure the FastAPI server is running on port 8000.");
      setLoading(false);
    };
  };

  return (
    <main className="min-h-screen bg-[#f4f0e6] flex flex-col justify-between text-black relative font-sans">
      
      {/* 1. Header Navigation */}
      <header className="w-full h-20 border-b-4 border-black px-6 md:px-12 flex items-center justify-between bg-white z-10 shrink-0">
        <div className="flex items-center gap-2">
          <div className="px-3 py-1 bg-yellow-400 neo-border font-extrabold text-lg uppercase tracking-tight select-none shadow-[2px_2px_0px_0px_#000000]">
            GitGenesis
          </div>
          <span className="text-xs font-mono font-bold text-zinc-500 uppercase tracking-widest pl-1 mt-1">by Nevan</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 border-3 border-black px-3 py-1.5 bg-[#fffbef]">
            {user?.user_metadata?.avatar_url ? (
              <img 
                src={user.user_metadata.avatar_url} 
                alt="Avatar" 
                className="w-6 h-6 rounded-full border-2 border-black" 
              />
            ) : (
              <User className="w-5 h-5 text-black" />
            )}
            <span className="text-xs font-bold font-mono text-black truncate max-w-[120px]">
              {user?.user_metadata?.full_name || user?.email || "User"}
            </span>
          </div>
          <button
            onClick={logout}
            className="px-4 py-2 border-3 border-black font-bold text-xs uppercase hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-[3px_3px_0px_0px_#000000] active:translate-x-0 active:translate-y-0 transition-all bg-red-500 text-white cursor-pointer"
          >
            Logout
          </button>
        </div>
      </header>

      {/* 2. Main Body Content */}
      <div className="flex-1 flex flex-col justify-center items-center py-16 px-6 z-10">
        <div className="w-full max-w-4xl flex flex-col items-center">
          
          {/* Main Title Section */}
          <div className="text-center mb-10 max-w-2xl">
            <h1 className="text-5xl md:text-7xl font-black tracking-tight leading-none mb-6 uppercase">
              Repository to <br/> blueprint.
            </h1>
            <p className="text-sm md:text-base font-medium text-zinc-700 max-w-lg mx-auto leading-relaxed">
              Reverse engineer a codebase into an explainable, visual, and AI-executable blueprint graph representing tasks and boundaries.
            </p>
          </div>

          {!loading ? (
            /* Input card */
            <motion.div 
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full max-w-2xl bg-[#fffbef] border-4 border-black p-6 md:p-8 rounded-none shadow-[8px_8px_0px_0px_#000000] flex flex-col gap-6"
            >
              <div className="flex flex-col md:flex-row items-stretch gap-4">
                <div className="flex-1 relative flex items-center">
                  <GitFork className="absolute left-4 w-5 h-5 text-black" />
                  <input
                    type="text"
                    placeholder="https://github.com/..."
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
                    className="w-full pl-12 pr-4 py-3.5 bg-white border-3 border-black rounded-none focus:outline-none text-sm font-bold text-black placeholder-zinc-500"
                  />
                </div>
                
                <button
                  onClick={handleAnalyze}
                  disabled={!repoUrl.trim()}
                  className="px-6 py-3.5 bg-red-600 disabled:opacity-50 text-white font-extrabold border-3 border-black text-sm uppercase hover:-translate-x-1 hover:-translate-y-1 hover:shadow-[5px_5px_0px_0px_#000000] active:translate-x-0 active:translate-y-0 active:shadow-none transition-all shadow-[4px_4px_0px_0px_#000000] flex items-center justify-center gap-2 cursor-pointer"
                >
                  Get Blueprint <ArrowRight className="w-4.5 h-4.5" />
                </button>
              </div>

              {/* Example repositories */}
              <div className="flex flex-col gap-4 border-t-2 border-black/10 pt-4">
                <div className="flex flex-col gap-2">
                  <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wider">Try example repos:</span>
                  <div className="flex flex-wrap gap-2">
                    {[
                      { name: "Next.js Payments", url: "https://github.com/vercel/nextjs-subscription-payments" },
                      { name: "FastAPI Boilerplate", url: "https://github.com/tiangolo/fastapi-template" },
                      { name: "Openclaw", url: "https://github.com/OpenClaw/OpenClaw" },
                      { name: "SupaBase", url: "https://github.com/supabase/supabase" }
                    ].map((example) => (
                      <button
                        key={example.name}
                        onClick={() => handleExampleClick(example.url)}
                        className="px-3 py-1.5 border-2 border-black bg-white hover:bg-zinc-100 text-xs font-bold transition-all hover:-translate-y-0.5 hover:shadow-[2px_2px_0px_0px_#000000] active:translate-x-0 active:translate-y-0 active:shadow-none shadow-[1px_1px_0px_0px_#000000] cursor-pointer"
                      >
                        {example.name}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {errorMsg && (
                <div className="flex items-center gap-2 text-red-600 text-xs mt-2 border-2 border-black bg-red-100 p-3.5 font-bold shadow-[3px_3px_0px_0px_#000000]">
                  <AlertCircle className="w-4.5 h-4.5 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}
            </motion.div>
          ) : (
            /* Neo-Brutalist Log console panel */
            <motion.div 
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full max-w-3xl bg-white border-4 border-black rounded-none shadow-[8px_8px_0px_0px_#000000] flex flex-col h-[400px] overflow-hidden"
            >
              {/* Header */}
              <div className="bg-[#fffbef] px-5 py-3 border-b-4 border-black flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1.5">
                    <span className="w-3 h-3 rounded-full bg-black" />
                    <span className="w-3 h-3 rounded-full bg-black" />
                    <span className="w-3 h-3 rounded-full bg-black" />
                  </div>
                  <span className="text-black text-xs font-mono font-extrabold uppercase pl-2">Live Agent Orchestration Console</span>
                </div>
                <div className="flex items-center gap-1.5 text-xs text-red-600 font-mono font-bold animate-pulse">
                  <Play className="w-3.5 h-3.5 fill-current" /> RUNNING
                </div>
              </div>

              {/* Logs */}
              <div className="flex-1 bg-white p-5 font-mono text-xs overflow-y-auto flex flex-col gap-2.5 text-black border-b-4 border-black">
                {logs.map((log, idx) => (
                  <div key={idx} className="flex gap-2">
                    <span className="text-zinc-400 select-none">[{idx + 1}]</span>
                    <span className={log.startsWith("[System]") ? "text-indigo-600 font-extrabold" : log.includes("Error") ? "text-red-600 font-extrabold" : "text-black"}>
                      {log}
                    </span>
                  </div>
                ))}
                <div ref={consoleEndRef} />
              </div>

              {/* Footer */}
              <div className="bg-[#fffbef] px-5 py-3.5 flex items-center justify-between text-xs font-mono font-bold">
                <div className="text-black truncate pr-4">Status: <span className="underline">{statusMsg}</span></div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="w-2.5 h-2.5 bg-black rounded-none animate-ping" />
                  <span className="text-black uppercase">Processing...</span>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* 3. Footer Area */}
      <footer className="w-full py-6 border-t-4 border-black px-6 md:px-12 flex flex-col sm:flex-row items-center justify-between bg-white text-xs font-bold gap-4 shrink-0">
        <span className="text-zinc-600 font-mono select-none">GitGenesis &copy; 2026. Made by Nevan.</span>
        <div className="flex gap-6 text-black uppercase">
          <a href="#" className="hover:underline">GitHub</a>
          <a href="#" className="hover:underline">Discord</a>
          <a href="#" className="hover:underline">Sponsor</a>
        </div>
      </footer>
    </main>
  );
}
