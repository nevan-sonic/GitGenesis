"use client";

import React, { useState, useEffect } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { GitBranch, Layers, GitCompare, Download, RefreshCw, ChevronRight, Settings, Info, Cpu, GitPullRequest } from "lucide-react";

import BlueprintExplorer from "@/components/BlueprintExplorer";
import ArchitectureExplorer from "@/components/ArchitectureExplorer";
import BranchManager from "@/components/BranchManager";
import BlueprintComparator from "@/components/BlueprintComparator";
import ExportModal from "@/components/ExportModal";
import TaskInspector from "@/components/TaskInspector";
import BlueprintDiffViewer from "@/components/BlueprintDiffViewer";

import { apiFetch } from "@/app/api";
import { useAuth } from "@/components/AuthProvider";

export default function Workspace() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { supabaseToken, githubToken } = useAuth();

  const blueprintId = params.id as string;
  const initialBranchId = searchParams.get("branch_id") || "";

  // State
  const [activeBranchId, setActiveBranchId] = useState(initialBranchId);
  const [branches, setBranches] = useState<any[]>([]);
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [repoUrl, setRepoUrl] = useState<string>("");
  
  // Navigation Tabs
  const [activeTab, setActiveTab] = useState<"blueprint" | "architecture" | "compare">("blueprint");
  
  // Modals / Drawers
  const [showExportModal, setShowExportModal] = useState(false);
  const [showBranchManager, setShowBranchManager] = useState(false);
  
  // Secondary branch for compare mode
  const [compareBranchId, setCompareBranchId] = useState<string | null>(null);

  // Viewer state for codebase raw files
  const [viewingFilePath, setViewingFilePath] = useState<string | null>(null);



  // Fetch blueprint graph data
  const fetchGraphData = async (branchId: string) => {
    try {
      const res = await apiFetch(`/api/blueprints/${blueprintId}/data?branch_id=${branchId}`);
      if (res.ok) {
        const data = await res.json();
        setNodes(data.nodes);
        setEdges(data.edges);
        if (data.repo_url) {
          setRepoUrl(data.repo_url);
        }
      }
    } catch (e) {
      console.error("Failed to fetch graph data", e);
    }
  };

  // Fetch branches list
  const fetchBranches = async () => {
    try {
      const res = await apiFetch(`/api/blueprints/${blueprintId}/branches`);
      if (res.ok) {
        const data = await res.json();
        setBranches(data);
        if (!activeBranchId && data.length > 0) {
          const active = data.find((b: any) => b.active) || data[0];
          setActiveBranchId(active.id);
        }
      }
    } catch (e) {
      console.error("Failed to fetch branches list", e);
    }
  };

  useEffect(() => {
    fetchBranches();
  }, [blueprintId]);

  useEffect(() => {
    if (activeBranchId) {
      fetchGraphData(activeBranchId);
      // Update query param
      router.replace(`/blueprint/${blueprintId}?branch_id=${activeBranchId}`);
    }
  }, [activeBranchId]);

  const handleBranchSwitch = (branchId: string) => {
    setActiveBranchId(branchId);
    setSelectedNodeId(null);
  };

  const handleNodeSelect = (nodeId: string) => {
    setSelectedNodeId(nodeId);
  };

  const handleRegenerateNode = async (
    nodeId: string, 
    updatedStrategy: string,
    onLog: (msg: string) => void
  ) => {
    try {
      const res = await apiFetch(`/api/blueprints/${blueprintId}/regenerate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          branch_id: activeBranchId,
          node_id: nodeId,
          updated_strategy: updatedStrategy
        })
      });

      if (!res.ok) {
        onLog("[ERROR] Failed to contact regeneration server.");
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        onLog("[ERROR] Response stream not readable.");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6).trim();
            try {
              const data = JSON.parse(dataStr);
              if (data.type === "log") {
                onLog(data.message);
              } else if (data.type === "error") {
                onLog(`[ERROR] ${data.message}`);
              } else if (data.type === "completed") {
                onLog(`[SUCCESS] Regenerated ${data.regenerated_count} modules.`);
              }
            } catch (err) {
              console.error("Failed to parse event JSON", err);
            }
          }
        }
      }

      // Refresh nodes to show updated tasks
      await fetchGraphData(activeBranchId);
    } catch (e: any) {
      console.error("Error regenerating nodes", e);
      onLog(`[ERROR] Connection failed: ${e.message}`);
    }
  };

  const handleStatusChange = async (nodeId: string, newStatus: string) => {
    try {
      const res = await apiFetch(`/api/blueprints/${blueprintId}/branches/${activeBranchId}/nodes/${nodeId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus })
      });
      if (res.ok) {
        // Refresh nodes to show updated status
        await fetchGraphData(activeBranchId);
      }
    } catch (e) {
      console.error("Error updating node status", e);
    }
  };

  const handleDeleteNode = async (nodeId: string) => {
    try {
      const res = await apiFetch(`/api/blueprints/${blueprintId}/nodes/${nodeId}?branch_id=${activeBranchId}`, {
        method: "DELETE"
      });
      if (res.ok) {
        setSelectedNodeId(null);
        await fetchGraphData(activeBranchId);
      }
    } catch (e) {
      console.error("Error deleting node", e);
    }
  };

  const [committing, setCommitting] = useState(false);
  const [commitResult, setCommitResult] = useState<any>(null);
  const [showCommitModal, setShowCommitModal] = useState(false);

  const handleCommitToGitHub = async () => {
    if (!githubToken) {
      alert("GitHub authentication token not found. Please sign in again.");
      return;
    }
    setCommitting(true);
    setCommitResult(null);
    setShowCommitModal(true);
    try {
      const res = await apiFetch(`/api/blueprints/${blueprintId}/commit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          branch_id: activeBranchId
        })
      });
      if (res.ok) {
        const data = await res.json();
        setCommitResult(data);
      } else {
        const data = await res.json().catch(() => ({}));
        setCommitResult({
          error: data.detail || "Failed to commit blueprint to GitHub."
        });
      }
    } catch (e: any) {
      setCommitResult({
        error: e.message || "Failed to connect to API server."
      });
    } finally {
      setCommitting(false);
    }
  };

  // Find selected node details
  const selectedNode = nodes.find((n) => n.id === selectedNodeId);

  return (
    <div className="flex flex-col h-screen w-screen bg-[#f4f0e6] text-black overflow-hidden">
      {/* 1. Header Area */}
      <header className="h-20 border-b-4 border-black bg-white px-6 flex items-center justify-between z-20 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-yellow-400 border-3 border-black flex items-center justify-center text-black font-black text-base shadow-[2px_2px_0px_0px_#000000]">
            GG
          </div>
          <div>
            <h2 className="text-sm font-black tracking-wide text-black uppercase">GitGenesis by Nevan Workspace</h2>
            <div className="flex items-center gap-1.5 text-xs text-zinc-500 font-mono font-bold">
              <Cpu className="w-3.5 h-3.5" /> ID: {blueprintId.slice(0, 8)}...
            </div>
          </div>
        </div>

        {/* Tab switch navigation */}
        <div className="flex items-center gap-2 bg-[#f4f0e6] border-3 border-black p-1.5 shadow-[2px_2px_0px_0px_#000000]">
          <button
            onClick={() => setActiveTab("blueprint")}
            className={`px-4 py-2 text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
              activeTab === "blueprint" 
                ? "bg-yellow-400 border-2 border-black text-black shadow-[2px_2px_0px_0px_#000000]" 
                : "border-2 border-transparent text-zinc-650 hover:text-black"
            }`}
          >
            <GitBranch className="w-3.5 h-3.5" /> Blueprint Explorer
          </button>
          <button
            onClick={() => setActiveTab("architecture")}
            className={`px-4 py-2 text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
              activeTab === "architecture" 
                ? "bg-yellow-400 border-2 border-black text-black shadow-[2px_2px_0px_0px_#000000]" 
                : "border-2 border-transparent text-zinc-655 hover:text-black"
            }`}
          >
            <Layers className="w-3.5 h-3.5" /> Architecture Explorer
          </button>
          <button
            onClick={() => setActiveTab("compare")}
            className={`px-4 py-2 text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
              activeTab === "compare" 
                ? "bg-yellow-400 border-2 border-black text-black shadow-[2px_2px_0px_0px_#000000]" 
                : "border-2 border-transparent text-zinc-660 hover:text-black"
            }`}
          >
            <GitCompare className="w-3.5 h-3.5" /> Compare Branches
          </button>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/")}
            className="px-3 py-2 bg-white border-3 border-black hover:bg-zinc-50 text-xs font-black text-black flex items-center gap-1.5 cursor-pointer shadow-[3px_3px_0px_0px_#000000]"
            title="Go back to Home"
          >
            Home
          </button>

          <button
            onClick={() => setShowBranchManager(true)}
            className="px-4 py-2 bg-white border-3 border-black hover:bg-zinc-50 text-xs font-black text-black flex items-center gap-2 cursor-pointer shadow-[3px_3px_0px_0px_#000000]"
          >
            <GitBranch className="w-4 h-4 text-black" />
            Branch: <span className="text-red-600">{branches.find((b) => b.id === activeBranchId)?.name || "master"}</span>
          </button>

          <button
            onClick={handleCommitToGitHub}
            disabled={committing}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white font-extrabold border-3 border-black text-xs flex items-center gap-1.5 cursor-pointer shadow-[3px_3px_0px_0px_#000000] disabled:opacity-50"
          >
            {committing ? (
              <svg className="animate-spin h-3.5 w-3.5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            ) : (
              <GitPullRequest className="w-4 h-4" />
            )}
            Sync to GitHub
          </button>

          <button
            onClick={() => setShowExportModal(true)}
            className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-extrabold border-3 border-black text-xs flex items-center gap-1.5 cursor-pointer shadow-[3px_3px_0px_0px_#000000]"
          >
            <Download className="w-4 h-4" /> Export Blueprint
          </button>
        </div>
      </header>

      {/* 2. Main Workspace Split View */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Workspace Display Area */}
        <div className="flex-1 h-full relative overflow-hidden">
          {activeTab === "blueprint" && (
            <BlueprintExplorer 
              blueprintId={blueprintId}
              activeBranchId={activeBranchId}
              nodes={nodes} 
              edges={edges} 
              onNodeSelect={handleNodeSelect}
              selectedNodeId={selectedNodeId}
              onRefresh={() => fetchGraphData(activeBranchId)}
            />
          )}

          {activeTab === "architecture" && (
            <ArchitectureExplorer 
              nodes={nodes}
              onViewFile={setViewingFilePath}
            />
          )}

          {activeTab === "compare" && (
            <BlueprintComparator
              blueprintId={blueprintId}
              branches={branches}
              activeBranchId={activeBranchId}
            />
          )}
        </div>

        {/* 3. Right Drawers / Panels */}
        {/* Task Inspector Panel (grows when node selected) */}
        {selectedNode && activeTab === "blueprint" && (
          <TaskInspector
            node={selectedNode}
            onClose={() => setSelectedNodeId(null)}
            onRegenerate={handleRegenerateNode}
            onViewFile={setViewingFilePath}
            onStatusChange={handleStatusChange}
            onDeleteNode={handleDeleteNode}
          />
        )}
      </div>

      {/* 4. Overlay Modals */}
      {showExportModal && (
        <ExportModal
          blueprintId={blueprintId}
          branchId={activeBranchId}
          onClose={() => setShowExportModal(false)}
        />
      )}

      {showBranchManager && (
        <BranchManager
          branches={branches}
          activeBranchId={activeBranchId}
          onSwitch={handleBranchSwitch}
          onClose={() => setShowBranchManager(false)}
          blueprintId={blueprintId}
          onRefresh={fetchBranches}
        />
      )}

      {viewingFilePath && (
        <FileViewerModal
          blueprintId={blueprintId}
          activeBranchId={activeBranchId}
          path={viewingFilePath}
          onClose={() => setViewingFilePath(null)}
        />
      )}

      {/* Settings modal removed because authentication is handled via GitHub OAuth session */}

      {showCommitModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 text-black">
          <div className="absolute inset-0" onClick={() => !committing && setShowCommitModal(false)} />
          <div className="w-full max-w-lg bg-[#fbfaf7] border-3 border-black p-6 shadow-[6px_6px_0px_0px_#000000] z-10 relative flex flex-col gap-4">
            <h3 className="text-sm font-black uppercase tracking-wider text-black border-b-2 border-black pb-2 flex items-center gap-2">
              <GitPullRequest className="w-4 h-4" /> Sync Blueprint to GitHub
            </h3>
            {committing ? (
              <div className="flex flex-col items-center justify-center py-8 gap-3">
                <svg className="animate-spin h-8 w-8 text-black" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span className="text-xs font-black uppercase tracking-wider font-mono">
                  Creating branch, committing .cursorrules, and raising PR...
                </span>
              </div>
            ) : commitResult?.error ? (
              <div className="flex flex-col gap-3">
                <div className="border-2 border-black bg-red-100 p-4 font-bold text-xs flex flex-col gap-1.5 shadow-[2px_2px_0px_0px_#000000]">
                  <div className="text-red-700 font-black uppercase flex items-center gap-1.5">
                    ❌ Sync Failed
                  </div>
                  <div className="text-zinc-800 font-mono text-[10.5px]">
                    {commitResult.error}
                  </div>
                </div>
                <div className="flex justify-end mt-2">
                  <button
                    onClick={() => setShowCommitModal(false)}
                    className="px-4 py-2 bg-white border-2 border-black font-black text-xs uppercase shadow-[2px_2px_0px_0px_#000000] cursor-pointer hover:bg-zinc-50"
                  >
                    Close
                  </button>
                </div>
              </div>
            ) : commitResult ? (
              <div className="flex flex-col gap-3">
                <div className="border-2 border-black bg-[#dcfce7] p-4 font-bold text-xs flex flex-col gap-2 shadow-[2px_2px_0px_0px_#000000]">
                  <div className="text-green-800 font-black uppercase flex items-center gap-1.5">
                    ✅ Sync Successful!
                  </div>
                  <p className="text-zinc-800">
                    Your blueprints and rules have been pushed to GitHub successfully.
                  </p>
                  <div className="bg-white border border-black/20 p-2 font-mono text-[10px] text-zinc-700 flex flex-col gap-1">
                    <div><span className="font-bold">Branch:</span> {commitResult.branch}</div>
                    {commitResult.number && <div><span className="font-bold">PR Number:</span> #{commitResult.number}</div>}
                    <div><span className="font-bold">Action:</span> {commitResult.status === 'pr_created' ? 'PR Created' : 'Branch Created'}</div>
                  </div>
                </div>
                <div className="flex gap-2 justify-end mt-2">
                  <button
                    onClick={() => setShowCommitModal(false)}
                    className="px-4 py-2 border-2 border-black bg-white hover:bg-zinc-50 font-bold text-xs uppercase cursor-pointer"
                  >
                    Close
                  </button>
                  <a
                    href={commitResult.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-[#a3e635] hover:bg-[#bbf247] border-2 border-black font-black text-xs uppercase shadow-[2px_2px_0px_0px_#000000] cursor-pointer flex items-center gap-1.5"
                  >
                    View on GitHub
                  </a>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

interface FileViewerModalProps {
  blueprintId: string;
  activeBranchId: string;
  path: string;
  onClose: () => void;
}

function FileViewerModal({ blueprintId, activeBranchId, path, onClose }: FileViewerModalProps) {
  const [content, setContent] = useState<string>("");
  const [modifiedContent, setModifiedContent] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchFile = async () => {
      setLoading(true);
      setError(null);
      setModifiedContent(null);
      try {
        // 1. Fetch original content
        const originalRes = await apiFetch(
          `/api/blueprints/${blueprintId}/file-content?path=${encodeURIComponent(path)}`
        );
        let origText = "";
        if (originalRes.ok) {
          const data = await originalRes.json();
          origText = data.content;
          setContent(origText);
        } else {
          const data = await originalRes.json().catch(() => ({}));
          throw new Error(data.detail || "Failed to load original file contents from GitHub.");
        }

        // 2. Fetch modified files to see if modified in this branch
        const modifiedRes = await apiFetch(
          `/api/blueprints/${blueprintId}/modified-files?branch_id=${activeBranchId}`
        );
        if (modifiedRes.ok) {
          const modFiles = await modifiedRes.json();
          const match = modFiles.find(
            (m: any) => 
              m.file_path === path || 
              m.file_path.replace(/^\//, "") === path.replace(/^\//, "")
          );
          if (match) {
            setModifiedContent(match.content);
          }
        }
      } catch (e: any) {
        setError(e.message || "Failed to connect to API server.");
      } finally {
        setLoading(false);
      }
    };
    fetchFile();
  }, [blueprintId, activeBranchId, path]);

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0" onClick={onClose} />
      <div className="w-full max-w-4xl h-[600px] bg-[#fbfaf7] border-3 border-black z-10 shadow-[8px_8px_0px_0px_#000000] flex flex-col overflow-hidden relative text-black">
        {/* Header */}
        <div className="flex items-center justify-between border-b-3 border-black p-4 bg-[#f4f0e6] shrink-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-black uppercase bg-[#ffd54f] border-2 border-black px-2.5 py-1 shadow-[2px_2px_0px_0px_#000000]">
              FILE CONTENT
            </span>
            <span className="text-xs font-black truncate max-w-lg">{path}</span>
          </div>
          <button 
            onClick={onClose}
            className="p-1 text-black hover:bg-zinc-200 border-2 border-black bg-white shadow-[2px_2px_0px_0px_#000000] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[1px_1px_0px_0px_#000000] transition-all cursor-pointer"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
        </div>

        {/* Content Viewer Body */}
        <div className="flex-1 p-6 overflow-hidden flex flex-col bg-white">
          {loading ? (
            <div className="flex flex-col items-center justify-center gap-2">
              <svg className="animate-spin h-8 w-8 text-black" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span className="text-xs font-black uppercase tracking-wider font-mono">Loading from GitHub...</span>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center gap-3 border-2 border-black bg-red-100 p-6 shadow-[4px_4px_0px_0px_#000000] max-w-md mx-auto text-center font-bold">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="w-8 h-8 text-red-700"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
              <div>
                <h4 className="text-xs font-black uppercase text-black">Fetch Failed</h4>
                <p className="text-[11px] text-zinc-800 leading-normal font-bold mt-1">
                  {error}
                </p>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-hidden flex flex-col">
              {modifiedContent !== null ? (
                <div className="flex-1 overflow-hidden flex flex-col gap-3">
                  <div className="flex items-center justify-between border-2 border-black bg-[#fef08a] p-2.5 shadow-[2px_2px_0px_0px_#000000] font-mono text-[10px] font-black uppercase shrink-0 text-black">
                    <span>⚡ THIS FILE CONTAINS ACTIVE BLUEPRINT MODIFICATIONS</span>
                    <button 
                      onClick={() => setModifiedContent(null)}
                      className="px-2 py-1 bg-white hover:bg-zinc-50 border border-black shadow-[1px_1px_0px_0px_#000000] text-[9px] font-bold cursor-pointer"
                    >
                      Show Original Only
                    </button>
                  </div>
                  <div className="flex-1 overflow-auto">
                    <BlueprintDiffViewer
                      path={path}
                      originalContent={content}
                      modifiedContent={modifiedContent}
                    />
                  </div>
                </div>
              ) : (
                <div className="flex-1 border-2 border-black bg-[#fbfaf7] overflow-auto shadow-[3px_3px_0px_0px_#000000] p-4">
                  <pre className="font-mono text-[10.5px] leading-relaxed text-black whitespace-pre">
                    {content}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
