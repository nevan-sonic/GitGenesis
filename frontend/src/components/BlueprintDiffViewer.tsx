"use client";

import React from "react";
import { Plus, Minus, FileText } from "lucide-react";

interface BlueprintDiffViewerProps {
  path: string;
  originalContent: string;
  modifiedContent: string;
}

export function computeLineDiff(oldText: string, newText: string) {
  const oldLines = oldText.split(/\r?\n/);
  const newLines = newText.split(/\r?\n/);

  // Compute LCS (Longest Common Subsequence) DP Table
  const dp: number[][] = Array(oldLines.length + 1)
    .fill(null)
    .map(() => Array(newLines.length + 1).fill(0));

  for (let i = 1; i <= oldLines.length; i++) {
    for (let j = 1; j <= newLines.length; j++) {
      if (oldLines[i - 1] === newLines[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  const diff: {
    type: "added" | "removed" | "unchanged";
    text: string;
    oldLineNum?: number;
    newLineNum?: number;
  }[] = [];

  let i = oldLines.length;
  let j = newLines.length;

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && oldLines[i - 1] === newLines[j - 1]) {
      diff.unshift({
        type: "unchanged",
        text: oldLines[i - 1],
        oldLineNum: i,
        newLineNum: j,
      });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      diff.unshift({
        type: "added",
        text: newLines[j - 1],
        newLineNum: j,
      });
      j--;
    } else {
      diff.unshift({
        type: "removed",
        text: oldLines[i - 1],
        oldLineNum: i,
      });
      i--;
    }
  }

  return diff;
}

export default function BlueprintDiffViewer({
  path,
  originalContent,
  modifiedContent,
}: BlueprintDiffViewerProps) {
  const diffLines = computeLineDiff(originalContent || "", modifiedContent || "");

  return (
    <div className="w-full flex flex-col border-2 border-black bg-white shadow-[4px_4px_0px_0px_#000000] overflow-hidden text-black">
      {/* File Header */}
      <div className="bg-[#f4f0e6] border-b-2 border-black p-3 flex items-center gap-2">
        <FileText className="w-4 h-4 text-blue-600" />
        <span className="font-mono text-xs font-black truncate">{path}</span>
      </div>

      {/* Diff Table */}
      <div className="flex-1 overflow-auto max-h-[450px] font-mono text-[11px] leading-relaxed">
        <table className="w-full border-collapse">
          <tbody>
            {diffLines.map((line, idx) => {
              let rowBg = "bg-white hover:bg-zinc-50";
              let numBg = "text-zinc-400 bg-zinc-50 border-r border-black/10 select-none text-right px-2 w-9";
              let prefix = " ";
              let prefixColor = "text-zinc-300";
              let textColor = "text-zinc-800";

              if (line.type === "added") {
                rowBg = "bg-green-50 hover:bg-green-100 text-green-900";
                prefix = "+";
                prefixColor = "text-green-500 font-bold";
                textColor = "text-green-800 font-medium";
              } else if (line.type === "removed") {
                rowBg = "bg-red-50 hover:bg-red-100 text-red-900 line-through";
                prefix = "-";
                prefixColor = "text-red-500 font-bold";
                textColor = "text-red-800";
              }

              return (
                <tr key={idx} className={`align-top border-none ${rowBg}`}>
                  {/* Line Numbers */}
                  <td className={numBg}>{line.oldLineNum || ""}</td>
                  <td className={numBg}>{line.newLineNum || ""}</td>
                  
                  {/* Operation Prefix */}
                  <td className="px-2 w-4 select-none text-center border-none">
                    <span className={prefixColor}>{prefix}</span>
                  </td>

                  {/* Code Line Content */}
                  <td className="px-2 whitespace-pre-wrap break-all border-none font-semibold">
                    <span className={textColor}>{line.text || " "}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
