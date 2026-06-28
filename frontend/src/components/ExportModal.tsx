"use client";

import React, { useState } from "react";
import { X, Download, Copy, Check, FileCode, CheckCircle } from "lucide-react";
import { apiFetch } from "@/app/api";

interface ExportModalProps {
  blueprintId: string;
  branchId: string;
  onClose: () => void;
}

export default function ExportModal({ blueprintId, branchId, onClose }: ExportModalProps) {
  const [selectedFormat, setSelectedFormat] = useState("json");
  const [exportData, setExportData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const formats = [
    { id: "json", name: "Blueprint Schema (JSON)", desc: "Full Executable Engineering Blueprint structure." },
    { id: "markdown", name: "Blueprint Document (Markdown)", desc: "Readable markdown checklist and summaries." },
    { id: "dag", name: "Task Dependency Graph (DOT)", desc: "DOT/Graphviz schema representing DAG dependencies." },
    { id: "codex", name: "Codex Task Pack", desc: "Task pipeline for Codex execution routines." },
    { id: "cursor", name: "Cursor Task Pack", desc: ".cursorrules task checklist and setup rules." },
    { id: "workflow", name: "Generic Workflow Manifest", desc: "Logical DAG workflow representation." }
  ];

  const handleGenerateExport = async () => {
    setLoading(true);
    setCopied(false);
    try {
      const res = await apiFetch(`/api/blueprints/${blueprintId}/export?branch_id=${branchId}&format=${selectedFormat}`);
      if (res.ok) {
        const data = await res.json();
        setExportData(data);
      }
    } catch (e) {
      console.error("Failed to generate export file", e);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyToClipboard = () => {
    if (!exportData) return;
    navigator.clipboard.writeText(exportData.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadFile = () => {
    if (!exportData) return;
    const blob = new Blob([exportData.content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = exportData.filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      {/* Background click to close */}
      <div className="absolute inset-0" onClick={onClose} />

      {/* Modal Card */}
      <div className="w-full max-w-4xl h-[600px] bg-[#fbfaf7] border-3 border-black z-10 shadow-[8px_8px_0px_0px_#000000] flex flex-col md:flex-row overflow-hidden relative text-black">
        
        {/* Left pane: Format selector */}
        <div className="w-full md:w-80 border-r-3 border-black bg-[#f4f0e6] p-6 flex flex-col justify-between overflow-y-auto">
          <div className="flex flex-col gap-5">
            <div>
              <h3 className="text-sm font-black text-black uppercase tracking-wider flex items-center gap-2">
                <FileCode className="w-4.5 h-4.5 text-black" /> Export Blueprint
              </h3>
              <p className="text-[10px] text-zinc-700 font-mono font-bold mt-1">Select execution target format.</p>
            </div>

            <div className="flex flex-col gap-2">
              {formats.map((f) => (
                <button
                  key={f.id}
                  onClick={() => {
                    setSelectedFormat(f.id);
                    setExportData(null);
                  }}
                  className={`p-3 border-2 border-black text-left transition-all cursor-pointer shadow-[2px_2px_0px_0px_#000000] hover:translate-x-[0.5px] hover:translate-y-[0.5px] hover:shadow-[1px_1px_0px_0px_#000000] ${
                    selectedFormat === f.id
                      ? "bg-[#ffd54f]"
                      : "bg-white hover:bg-zinc-100"
                  }`}
                >
                  <h4 className="text-xs font-black text-black">{f.name}</h4>
                  <p className="text-[10px] text-zinc-700 mt-1 leading-normal font-medium">{f.desc}</p>
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleGenerateExport}
            disabled={loading}
            className="w-full mt-4 py-2.5 bg-[#ff5e5e] hover:bg-[#ff7a7a] disabled:opacity-50 text-black font-black uppercase border-2 border-black rounded-none shadow-[3px_3px_0px_0px_#000000] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[2px_2px_0px_0px_#000000] transition-all text-xs cursor-pointer flex items-center justify-center"
          >
            {loading ? "Generating..." : "Compile Artifact"}
          </button>
        </div>

        {/* Right pane: Preview Console */}
        <div className="flex-1 bg-[#fbfaf7] p-6 flex flex-col justify-between overflow-hidden relative">
          <button 
            onClick={onClose}
            className="absolute top-4 right-4 p-1 text-black hover:bg-zinc-200 border-2 border-black bg-white shadow-[2px_2px_0px_0px_#000000] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[1px_1px_0px_0px_#000000] transition-all cursor-pointer z-10"
          >
            <X className="w-4 h-4" />
          </button>

          {exportData ? (
            /* Preview view */
            <div className="flex-1 flex flex-col justify-between overflow-hidden h-full mt-8">
              <div className="flex items-center justify-between border-b-2 border-black pb-3 mb-4">
                <span className="text-xs font-mono font-bold text-black">File Preview: <span className="font-black text-blue-700">{exportData.filename}</span></span>
                <div className="flex gap-2">
                  <button
                    onClick={handleCopyToClipboard}
                    className="p-1.5 bg-white border-2 border-black hover:bg-zinc-100 text-black font-black flex items-center gap-1.5 text-xs font-mono cursor-pointer shadow-[2px_2px_0px_0px_#000000] hover:translate-x-[0.5px] hover:translate-y-[0.5px] hover:shadow-[1px_1px_0px_0px_#000000] transition-all"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />} {copied ? "Copied" : "Copy"}
                  </button>
                  <button
                    onClick={handleDownloadFile}
                    className="p-1.5 bg-[#a3e635] hover:bg-[#bbf247] border-2 border-black text-black font-black flex items-center gap-1.5 text-xs font-mono cursor-pointer shadow-[2px_2px_0px_0px_#000000] hover:translate-x-[0.5px] hover:translate-y-[0.5px] hover:shadow-[1px_1px_0px_0px_#000000] transition-all"
                  >
                    <Download className="w-3.5 h-3.5" /> Download
                  </button>
                </div>
              </div>

              {/* Code text frame */}
              <div className="flex-1 bg-white p-4 border-2 border-black overflow-y-auto font-mono text-[10.5px] text-black whitespace-pre shadow-[3px_3px_0px_0px_#000000]">
                {exportData.content}
              </div>
            </div>
          ) : (
            /* Idle View */
            <div className="flex-1 flex flex-col items-center justify-center text-center gap-3">
              <FileCode className="w-12 h-12 text-black" />
              <div>
                <h4 className="text-xs font-black uppercase text-black">Compilation Ready</h4>
                <p className="text-[11px] text-zinc-700 max-w-sm mt-1 leading-relaxed font-bold">
                  Select a compilation target on the left and click "Compile Artifact" to generate the task pack instructions preview.
                </p>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
