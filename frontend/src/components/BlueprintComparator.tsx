"use client";

import React, { useState, useEffect } from "react";
import { GitBranch, GitCompare, HelpCircle, CheckCircle2, RefreshCw } from "lucide-react";
import { apiFetch } from "@/app/api";

interface BlueprintComparatorProps {
  blueprintId: string;
  branches: any[];
  activeBranchId: string;
}

export default function BlueprintComparator({ blueprintId, branches, activeBranchId }: BlueprintComparatorProps) {
  const [branch1, setBranch1] = useState(activeBranchId);
  const [branch2, setBranch2] = useState("");
  
  const [comparison, setComparison] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (activeBranchId) {
      setBranch1(activeBranchId);
    }
  }, [activeBranchId]);

  const handleCompare = async () => {
    if (!branch1 || !branch2) return;
    setLoading(true);
    try {
      const res = await apiFetch(`/api/blueprints/compare?branch1=${branch1}&branch2=${branch2}`);
      if (res.ok) {
        const data = await res.json();
        setComparison(data);
      }
    } catch (e) {
      console.error("Failed to compare branch blueprints", e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full h-full p-8 overflow-y-auto bg-[#f4f0e6] text-black">
      <div className="max-w-4xl mx-auto">
        {/* Header Title */}
        <div className="mb-8 border-b-2 border-black pb-4">
          <h2 className="text-2xl font-black text-black flex items-center gap-2 uppercase tracking-tight">
            <GitCompare className="w-6 h-6 text-black" /> GitGenesis Variant Comparator
          </h2>
          <p className="text-xs text-zinc-700 mt-1 font-mono font-bold">
            Compare two variants/branches side-by-side to highlight where strategies, tasks, or dependency nodes diverge.
          </p>
        </div>

        {/* Branch Selectors controls */}
        <div className="bg-white p-6 border-3 border-black mb-8 flex flex-col sm:flex-row items-end gap-4 shadow-[4px_4px_0px_0px_#000000]">
          <div className="flex-1 flex flex-col gap-2 w-full">
            <label className="text-[10px] uppercase font-black text-black tracking-wider">Select Primary Branch</label>
            <select
              value={branch1}
              onChange={(e) => setBranch1(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-white border-2 border-black focus:outline-none focus:ring-0 text-xs text-black font-bold shadow-[2px_2px_0px_0px_#000000] cursor-pointer"
            >
              {branches.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </div>

          <div className="flex-1 flex flex-col gap-2 w-full">
            <label className="text-[10px] uppercase font-black text-black tracking-wider">Select Comparison Branch</label>
            <select
              value={branch2}
              onChange={(e) => setBranch2(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-white border-2 border-black focus:outline-none focus:ring-0 text-xs text-black font-bold shadow-[2px_2px_0px_0px_#000000] cursor-pointer"
            >
              <option value="">-- Choose Branch Variant --</option>
              {branches.filter((b) => b.id !== branch1).map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </div>

          <button
            onClick={handleCompare}
            disabled={!branch1 || !branch2 || loading}
            className="w-full sm:w-auto px-5 py-3 bg-[#a3e635] hover:bg-[#bbf247] disabled:opacity-50 text-black font-black uppercase border-2 border-black shadow-[3px_3px_0px_0px_#000000] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[2px_2px_0px_0px_#000000] transition-all text-xs flex items-center justify-center gap-1.5 cursor-pointer shrink-0"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <GitCompare className="w-4 h-4" />} Compare Variants
          </button>
        </div>

        {/* Comparison Outputs */}
        {comparison && (
          <div className="flex flex-col gap-6">
            {/* Match Rate summary widget */}
            <div className="flex items-center justify-between p-4 border-2 border-black bg-white shadow-[3px_3px_0px_0px_#000000] font-mono text-xs font-bold">
              <span className="text-zinc-700">Structural Graph Alignment Match:</span>
              <span className={`text-sm font-black border border-black px-2 py-0.5 shadow-[1px_1px_0px_0px_#000000] ${
                comparison.match_rate >= 90 ? "text-green-700 bg-green-100" : comparison.match_rate >= 60 ? "text-yellow-700 bg-yellow-100" : "text-red-700 bg-red-100"
              }`}>
                {comparison.match_rate.toFixed(1)}% Match
              </span>
            </div>

            {/* Differences node logs */}
            <div className="flex flex-col gap-4">
              <h3 className="text-xs font-black uppercase tracking-wider text-black">Divergent Node Adjustments</h3>
              
              {comparison.divergent_nodes.length === 0 ? (
                <div className="p-8 text-center text-zinc-800 text-xs border-2 border-dashed border-black bg-white shadow-[3px_3px_0px_0px_#000000] flex flex-col items-center gap-2 font-bold">
                  <CheckCircle2 className="w-8 h-8 text-green-600" />
                  No divergence. The two blueprint variants are 100% identical.
                </div>
              ) : (
                <div className="flex flex-col gap-3.5">
                  {comparison.divergent_nodes.map((diff: any) => (
                    <div 
                      key={diff.id} 
                      className={`p-4 border-2 border-black flex flex-col gap-3 shadow-[3px_3px_0px_0px_#000000] ${
                        diff.status === "added_in_branch2" 
                          ? "bg-[#dcfce7]" 
                          : diff.status === "removed_in_branch2" 
                          ? "bg-[#fee2e2]" 
                          : "bg-white"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-black text-black">
                          {diff.status === "added_in_branch2" ? diff.node.name : diff.status === "removed_in_branch2" ? diff.node.name : diff.branch1_node.name}
                        </h4>
                        <span className={`text-[9px] uppercase font-mono tracking-wider px-2 py-0.5 rounded border-2 border-black shadow-[1px_1px_0px_0px_#000000] ${
                          diff.status === "added_in_branch2" 
                            ? "text-green-800 bg-[#86efac]" 
                            : diff.status === "removed_in_branch2" 
                            ? "text-red-800 bg-[#fca5a5]" 
                            : "text-amber-800 bg-[#fdba74]"
                        }`}>
                          {diff.status.replace("_", " ")}
                        </span>
                      </div>

                      {/* Details of changes */}
                      {diff.status === "modified" && (
                        <div className="flex flex-col gap-3 font-mono text-[10px] mt-2 border-t-2 border-black pt-3 font-bold">
                          {diff.changes.includes("confidence_score") && (
                            <div className="flex items-center gap-4">
                              <span className="text-zinc-600">Confidence Score:</span>
                              <div className="flex items-center gap-1.5 text-black">
                                <span>{diff.branch1_node.confidence_score}%</span>
                                <span>&rarr;</span>
                                <span>{diff.branch2_node.confidence_score}%</span>
                              </div>
                            </div>
                          )}
                          {diff.changes.includes("generated_task") && (
                            <LineDiffViewer 
                              text1={diff.branch1_node.generated_task}
                              text2={diff.branch2_node.generated_task}
                            />
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

interface LineDiffViewerProps {
  text1: string;
  text2: string;
}

function LineDiffViewer({ text1, text2 }: LineDiffViewerProps) {
  const [viewMode, setViewMode] = useState<"unified" | "split">("unified");
  
  // LCS line diff algorithm
  const lines1 = text1.split('\n');
  const lines2 = text2.split('\n');
  
  const dp: number[][] = Array(lines1.length + 1).fill(null).map(() => Array(lines2.length + 1).fill(0));
  for (let i = 1; i <= lines1.length; i++) {
    for (let j = 1; j <= lines2.length; j++) {
      if (lines1[i - 1] === lines2[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }
  
  const diff: { type: 'added' | 'removed' | 'unchanged'; value: string; line1?: number; line2?: number }[] = [];
  let i = lines1.length;
  let j = lines2.length;
  
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && lines1[i - 1] === lines2[j - 1]) {
      diff.unshift({ type: 'unchanged', value: lines1[i - 1], line1: i, line2: j });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      diff.unshift({ type: 'added', value: lines2[j - 1], line2: j });
      j--;
    } else {
      diff.unshift({ type: 'removed', value: lines1[i - 1], line1: i });
      i--;
    }
  }

  return (
    <div className="flex flex-col gap-2 w-full mt-2">
      <div className="flex items-center justify-between border-b border-black pb-2">
        <span className="text-[10px] uppercase font-black text-black">Instruction Line Diff</span>
        <div className="flex border-2 border-black text-[10px] font-bold overflow-hidden shadow-[1px_1px_0px_0px_#000000] bg-white">
          <button
            onClick={() => setViewMode("unified")}
            className={`px-3 py-1 cursor-pointer transition-all border-none ${
              viewMode === "unified" ? "bg-[#ffd54f] font-black" : "bg-white hover:bg-zinc-100"
            }`}
          >
            Unified
          </button>
          <button
            onClick={() => setViewMode("split")}
            className={`px-3 py-1 cursor-pointer transition-all border-l-2 border-black ${
              viewMode === "split" ? "bg-[#ffd54f] font-black" : "bg-white hover:bg-zinc-100"
            }`}
          >
            Split
          </button>
        </div>
      </div>

      {viewMode === "unified" ? (
        <div className="border-2 border-black bg-white shadow-[2px_2px_0px_0px_#000000] overflow-x-auto text-[11px] leading-relaxed font-mono">
          <table className="w-full border-collapse">
            <tbody>
              {diff.map((line, idx) => {
                let rowBg = "bg-white text-black";
                let prefix = " ";
                if (line.type === "added") {
                  rowBg = "bg-[#e6ffed] text-[#22863a] font-bold";
                  prefix = "+";
                } else if (line.type === "removed") {
                  rowBg = "bg-[#ffeef0] text-[#cb2431] font-bold line-through";
                  prefix = "-";
                }
                
                return (
                  <tr key={idx} className={`${rowBg} hover:bg-zinc-50/50`}>
                    <td className="w-10 text-right select-none text-zinc-400 font-mono px-2 py-0.5 border-r border-zinc-200">
                      {line.line1 || ""}
                    </td>
                    <td className="w-10 text-right select-none text-zinc-400 font-mono px-2 py-0.5 border-r border-zinc-200">
                      {line.line2 || ""}
                    </td>
                    <td className="px-3 py-0.5 select-none text-zinc-450 border-r border-zinc-200 font-mono text-center font-bold">
                      {prefix}
                    </td>
                    <td className="px-3 py-0.5 whitespace-pre-wrap break-all font-mono">
                      {line.value}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="grid grid-cols-2 border-2 border-black bg-white shadow-[2px_2px_0px_0px_#000000] overflow-x-auto text-[11px] leading-relaxed font-mono divide-x-2 divide-black">
          {/* Left Pane (Branch 1 - removed / unchanged) */}
          <div className="flex flex-col">
            <div className="bg-[#f4f0e6] px-3 py-1 font-bold border-b border-black text-[10px] uppercase font-mono tracking-wider">
              Primary Variant
            </div>
            <div className="flex-1 p-2 flex flex-col font-mono text-[10.5px]">
              {diff.filter(l => l.type !== "added").map((line, idx) => {
                const isRemoved = line.type === "removed";
                return (
                  <div key={idx} className={`flex ${isRemoved ? "bg-[#ffeef0] text-[#cb2431] line-through font-bold" : ""} py-0.5 px-1 font-mono`}>
                    <span className="w-6 text-right text-zinc-400 mr-2 font-mono select-none">{line.line1}</span>
                    <span className="font-mono">{line.value}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Pane (Branch 2 - added / unchanged) */}
          <div className="flex flex-col">
            <div className="bg-[#f4f0e6] px-3 py-1 font-bold border-b border-black text-[10px] uppercase font-mono tracking-wider">
              Comparison Variant
            </div>
            <div className="flex-1 p-2 flex flex-col font-mono text-[10.5px]">
              {diff.filter(l => l.type !== "removed").map((line, idx) => {
                const isAdded = line.type === "added";
                return (
                  <div key={idx} className={`flex ${isAdded ? "bg-[#e6ffed] text-[#22863a] font-bold" : ""} py-0.5 px-1 font-mono`}>
                    <span className="w-6 text-right text-zinc-400 mr-2 font-mono select-none">{line.line2}</span>
                    <span className="font-mono">{line.value}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
