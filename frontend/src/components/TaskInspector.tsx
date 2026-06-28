"use client";

import React, { useState, useEffect } from "react";
import { X, CheckCircle2, AlertTriangle, FileText, Play, Info, Check } from "lucide-react";

interface TaskInspectorProps {
  node: any;
  onClose: () => void;
  onRegenerate: (nodeId: string, updatedStrategy: string, onLog: (msg: string) => void) => Promise<void>;
  onViewFile?: (path: string) => void;
  onStatusChange?: (nodeId: string, status: string) => Promise<void>;
  onDeleteNode?: (nodeId: string) => Promise<void>;
}

export default function TaskInspector({ node, onClose, onRegenerate, onViewFile, onStatusChange, onDeleteNode }: TaskInspectorProps) {
  const [strategyInput, setStrategyInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [copiedPrompt, setCopiedPrompt] = useState(false);

  const [terminalLogs, setTerminalLogs] = useState<string[]>([]);
  const [isRegenerating, setIsRegenerating] = useState(false);

  // Sync inputs on node click
  useEffect(() => {
    setStrategyInput("");
    setSaved(false);
    setCopiedPrompt(false);
    setTerminalLogs([]);
    setIsRegenerating(false);
  }, [node.id]);

  const handleRegenerateClick = async () => {
    if (!strategyInput.trim() || loading) return;
    setLoading(true);
    setSaved(false);
    setIsRegenerating(true);
    setTerminalLogs(["Connecting to sandbox environments..."]);
    try {
      await onRegenerate(node.id, strategyInput, (msg) => {
        setTerminalLogs(prev => [...prev, msg]);
      });
      setSaved(true);
      setStrategyInput("");
    } catch (e) {
      console.error("Failed to regenerate node tasks", e);
      setTerminalLogs(prev => [...prev, "[ERROR] Process failed."]);
    } finally {
      setLoading(false);
      setIsRegenerating(false);
    }
  };

  // Safe parse for JSON arrays/fields
  const parseList = (val: any): string[] => {
    if (typeof val === "string") {
      try {
        return JSON.parse(val);
      } catch {
        return [val];
      }
    }
    return Array.isArray(val) ? val : [];
  };

  const evidence = parseList(node.supporting_evidence);
  const relatedModules = parseList(node.related_modules);

  return (
    <div className="w-96 h-full bg-[#fbfaf7] border-l-3 border-black p-6 flex flex-col justify-between overflow-y-auto shrink-0 z-10 shadow-[-4px_0px_0px_0px_#000000] relative text-black">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex items-center justify-between border-b-2 border-black pb-4">
          <div>
            <h3 className="text-sm font-black text-black uppercase tracking-wider">{node.name}</h3>
            <span className="text-[10px] text-zinc-700 font-mono font-bold">Type: {node.type || "layer"}</span>
          </div>
          <button 
            onClick={onClose}
            className="p-1 text-black hover:bg-zinc-200 border-2 border-black bg-white shadow-[2px_2px_0px_0px_#000000] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[1px_1px_0px_0px_#000000] transition-all cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Status Selector */}
        <div className="flex flex-col gap-1.5 p-3 bg-white border-2 border-black shadow-[2px_2px_0px_0px_#000000]">
          <span className="text-[10px] uppercase font-black text-black tracking-wider">Node Checklist Status</span>
          <div className="grid grid-cols-3 border-2 border-black text-[10.5px] font-bold overflow-hidden shadow-[1px_1px_0px_0px_#000000] bg-white">
            <button
              onClick={() => onStatusChange?.(node.id, "todo")}
              className={`py-1.5 text-center cursor-pointer transition-all border-none ${
                node.status === "todo" || !node.status ? "bg-[#e5e7eb] text-black font-black" : "bg-white text-zinc-500 hover:bg-zinc-50"
              }`}
            >
              Todo
            </button>
            <button
              onClick={() => onStatusChange?.(node.id, "in_progress")}
              className={`py-1.5 text-center cursor-pointer transition-all border-l-2 border-black ${
                node.status === "in_progress" ? "bg-[#ffd54f] text-black font-black" : "bg-white text-zinc-500 hover:bg-zinc-50"
              }`}
            >
              In Progress
            </button>
            <button
              onClick={() => onStatusChange?.(node.id, "done")}
              className={`py-1.5 text-center cursor-pointer transition-all border-l-2 border-black ${
                node.status === "done" ? "bg-[#a3e635] text-black font-black" : "bg-white text-zinc-500 hover:bg-zinc-50"
              }`}
            >
              Done
            </button>
          </div>
        </div>

        {/* Explainability Segment */}
        <div className="flex flex-col gap-4 bg-white p-4 border-2 border-black shadow-[3px_3px_0px_0px_#000000]">
          <h4 className="text-[10px] uppercase font-black text-black tracking-wider flex items-center gap-1.5 border-b border-black pb-1">
            <Info className="w-3.5 h-3.5 text-blue-600" /> Explainability Metadata
          </h4>

          {/* Confidence Score Bar */}
          <div className="flex flex-col gap-1.5 mt-1">
            <div className="flex items-center justify-between text-[11px] font-bold">
              <span className="text-zinc-700">Analysis Confidence:</span>
              <span className={`font-black ${
                node.confidence_score >= 90 ? "text-green-600" : "text-yellow-600"
              }`}>{node.confidence_score || 95}%</span>
            </div>
            <div className="w-full bg-white rounded-none h-3 border-2 border-black overflow-hidden">
              <div 
                className={`h-full ${
                  node.confidence_score >= 90 ? "bg-[#a3e635]" : "bg-[#fbbf24]"
                }`}
                style={{ width: `${node.confidence_score || 95}%` }}
              />
            </div>
          </div>

          {/* Confidence Explanation */}
          {node.confidence_explanation && (
            <div className="flex flex-col gap-1 mt-1.5 p-2 bg-[#f4f0e6] border border-black/40 text-black">
              <span className="text-[9px] text-zinc-700 font-mono font-bold uppercase">Confidence Reasoning:</span>
              <p className="text-[10.5px] text-zinc-800 italic leading-relaxed">
                "{node.confidence_explanation}"
              </p>
            </div>
          )}

          {/* Reasoning Summary */}
          <div className="flex flex-col gap-1 mt-2">
            <span className="text-[10px] text-zinc-700 font-mono font-bold">Reasoning Summary:</span>
            <p className="text-[11px] text-zinc-800 leading-relaxed font-sans mt-0.5">
              {node.architectural_reasoning_summary}
            </p>
          </div>

          {/* Supporting Evidence list */}
          {evidence.length > 0 && (
            <div className="flex flex-col gap-1.5 mt-2">
              <span className="text-[10px] text-zinc-700 font-mono font-bold">Supporting Evidence (Source Files):</span>
              <div className="flex flex-col gap-1.5 mt-1">
                {evidence.map((file, idx) => (
                  <button
                    key={idx}
                    onClick={() => onViewFile?.(file)}
                    className="flex items-center gap-1.5 text-[10px] text-zinc-800 font-mono hover:text-blue-600 hover:underline text-left cursor-pointer transition-all border-none bg-transparent p-0 w-full"
                  >
                    <FileText className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                    <span className="truncate flex-1">{file}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* AI Task strategy modification Form */}
        <div className="flex flex-col gap-3">
          <h4 className="text-[10px] uppercase font-black text-black tracking-wider">Modify Strategy</h4>
          <p className="text-[10px] text-zinc-700 leading-normal font-medium">
            Update implementation specifications below. Clicking regenerate will update this node and compile new instructions for all downstream nodes.
          </p>

          <textarea
            placeholder="e.g. Change authentication provider from custom JWT implementation to Clerk + OAuth login."
            value={strategyInput}
            onChange={(e) => setStrategyInput(e.target.value)}
            className="w-full h-24 p-3 bg-white border-2 border-black rounded-none focus:outline-none focus:ring-0 text-xs text-black placeholder-zinc-500 leading-relaxed resize-none shadow-[2px_2px_0px_0px_#000000]"
          />

          <button
            onClick={handleRegenerateClick}
            disabled={!strategyInput.trim() || loading}
            className="w-full py-2.5 bg-[#ff5e5e] hover:bg-[#ff7a7a] disabled:opacity-50 text-black font-black uppercase text-xs border-2 border-black rounded-none shadow-[2px_2px_0px_0px_#000000] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[1px_1px_0px_0px_#000000] transition-all flex items-center justify-center gap-1.5 cursor-pointer"
          >
            {loading ? "Regenerating..." : <><Play className="w-3.5 h-3.5 fill-current" /> Regenerate Downstream</>}
          </button>

          {saved && (
            <div className="flex items-center gap-2 text-green-700 text-xs border-2 border-black bg-green-100 p-2.5 rounded-none font-mono font-bold shadow-[2px_2px_0px_0px_#000000]">
              <CheckCircle2 className="w-4 h-4" /> Downstream tasks successfully aligned!
            </div>
          )}

          {/* Live Sandbox Terminal logs */}
          {(isRegenerating || terminalLogs.length > 0) && (
            <div className="flex flex-col gap-1.5 mt-2 bg-black border-2 border-black p-3.5 shadow-[2px_2px_0px_0px_#000000] text-emerald-400 font-mono text-[9px] h-48 overflow-y-auto rounded-none">
              <div className="flex justify-between items-center text-[8.5px] border-b border-zinc-800 pb-1.5 font-sans font-black tracking-wider text-white uppercase shrink-0 select-none">
                <span className="flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full bg-emerald-500 ${isRegenerating ? "animate-pulse" : ""}`} />
                  Sandbox Execution Logs
                </span>
                <span className="font-mono text-[8px] text-zinc-500">{isRegenerating ? "RUNNING" : "FINISHED"}</span>
              </div>
              <div className="flex-1 flex flex-col gap-1.5 overflow-y-auto leading-normal">
                {terminalLogs.map((log, index) => {
                  let logColor = "text-emerald-450";
                  if (log.startsWith("[ERROR]")) {
                    logColor = "text-red-400 font-bold";
                  } else if (log.startsWith("[SUCCESS]")) {
                    logColor = "text-yellow-400 font-black";
                  } else if (log.startsWith("Self-Healing Iteration") || log.startsWith("Self-Healing:")) {
                    logColor = "text-purple-400";
                  }
                  return (
                    <div key={index} className={`whitespace-pre-wrap break-all ${logColor}`}>
                      {log}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Display Current Task Prompt */}
        <div className="flex flex-col gap-2.5 mt-2">
          <div className="flex justify-between items-center">
            <label className="text-[10px] uppercase font-black text-black tracking-wider">Generated Task Prompts</label>
            <button
              onClick={() => {
                navigator.clipboard.writeText(node.generated_task || "");
                setCopiedPrompt(true);
                setTimeout(() => setCopiedPrompt(false), 2000);
              }}
              className="px-2.5 py-1 bg-white hover:bg-zinc-50 border-2 border-black font-black text-[9px] uppercase shadow-[1px_1px_0px_0px_#000000] cursor-pointer active:translate-x-[0.5px] active:translate-y-[0.5px] active:shadow-none transition-all flex items-center gap-1 shrink-0"
            >
              {copiedPrompt ? <CheckCircle2 className="w-2.5 h-2.5 text-green-600" /> : null}
              {copiedPrompt ? "Copied" : "Copy Prompt"}
            </button>
          </div>
          <div className="p-3 bg-white border-2 border-black rounded-none shadow-[2px_2px_0px_0px_#000000] max-h-56 overflow-y-auto font-mono text-[10.5px] leading-relaxed text-black whitespace-pre-wrap">
            {node.generated_task}
          </div>
        </div>

        {/* Danger Zone: Delete Node */}
        {onDeleteNode && (
          <div className="border-2 border-red-500 bg-red-50 p-4 shadow-[3px_3px_0px_0px_#ef4444] mt-4 flex flex-col gap-2 shrink-0">
            <h5 className="text-[10px] font-black uppercase text-red-700 tracking-wider">Danger Zone</h5>
            <p className="text-[9px] text-zinc-700 font-medium">
              Deleting this blueprint node will permanently remove it and all of its dependency edge links.
            </p>
            <button
              onClick={() => {
                if (confirm(`Are you sure you want to delete the node "${node.name}"?`)) {
                  onDeleteNode(node.id);
                }
              }}
              className="w-full py-2 bg-red-600 hover:bg-red-500 text-white font-extrabold text-xs uppercase border-2 border-black shadow-[2px_2px_0px_0px_#000000] hover:translate-x-[0.5px] hover:translate-y-[0.5px] hover:shadow-[1px_1px_0px_0px_#000000] cursor-pointer transition-all"
            >
              Delete Node
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
