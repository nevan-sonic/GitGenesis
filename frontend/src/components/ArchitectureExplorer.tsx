import React, { useState } from "react";
import { Folder, Layers, FileText, ChevronRight } from "lucide-react";

interface ArchitectureExplorerProps {
  nodes: any[];
  onViewFile?: (path: string) => void;
}

export default function ArchitectureExplorer({ nodes, onViewFile }: ArchitectureExplorerProps) {
  // State to track which card is showing all files
  const [expandedNodeId, setExpandedNodeId] = useState<string | null>(null);

  // Group source files and modules by layer types
  const layersMap: { [key: string]: any[] } = {};

  nodes.forEach(node => {
    const layer = node.type || "Other";
    if (!layersMap[layer]) layersMap[layer] = [];
    layersMap[layer].push(node);
  });

  return (
    <div className="w-full h-full p-8 overflow-y-auto bg-[#f4f0e6] text-black">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h2 className="text-xl font-black text-black flex items-center gap-2 uppercase tracking-wide">
            <Layers className="w-5 h-5 text-indigo-600" /> Architecture boundaries & Service Layers
          </h2>
          <p className="text-xs text-zinc-600 mt-1 font-mono font-bold">
            Analyzed packages, logical layer boundaries, and structural separations identified by the Architecture Specialist Agent.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Object.entries(layersMap).map(([layerName, layerNodes]) => (
            <div 
              key={layerName} 
              className="bg-white border-3 border-black p-5 shadow-[5px_5px_0px_0px_#000000] flex flex-col hover:-translate-y-0.5 hover:shadow-[6px_6px_0px_0px_#000000] transition-all"
            >
              {/* Header */}
              <div className="flex items-center gap-3 border-b-2 border-black pb-4 mb-4">
                <div className="w-10 h-10 bg-yellow-400 border-2 border-black flex items-center justify-center text-black shadow-[2px_2px_0px_0px_#000000]">
                  <Folder className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-black uppercase tracking-wider">{layerName} Layer</h3>
                  <p className="text-[10px] text-zinc-550 font-mono font-bold mt-0.5">{layerNodes.length} nodes</p>
                </div>
              </div>

              {/* Node List */}
              <div className="flex-1 flex flex-col gap-3">
                {layerNodes.map(node => {
                  const isExpanded = expandedNodeId === node.id;
                  const visibleFiles = isExpanded ? node.source_files : node.source_files.slice(0, 3);
                  
                  return (
                    <div 
                      key={node.id} 
                      className="p-3.5 border-2 border-black bg-[#fbfaf7] flex flex-col gap-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-black text-black truncate pr-2">{node.name}</span>
                        <span className="text-[9px] font-mono font-bold text-zinc-500">ID: {node.id.slice(0, 8)}</span>
                      </div>
                      
                      <p className="text-[11px] text-zinc-700 leading-relaxed font-medium">
                        {node.architectural_reasoning_summary}
                      </p>

                      {/* Source file count or list */}
                      {node.source_files && node.source_files.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-black/10 flex flex-col gap-1">
                          <span className="text-[9px] text-zinc-500 font-mono font-bold flex items-center gap-1">
                            <FileText className="w-3 h-3 text-black" /> Associated Source Files:
                          </span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {visibleFiles.map((f: string, idx: number) => (
                              <button
                                key={idx}
                                onClick={() => onViewFile?.(f)}
                                className="text-[9px] text-black bg-[#f4f0e6] hover:bg-zinc-100 border-2 border-black px-2 py-0.5 rounded-none truncate max-w-[140px] font-mono font-bold cursor-pointer transition-all active:translate-x-[0.5px] active:translate-y-[0.5px]"
                                title={`View ${f}`}
                              >
                                {f.split("/").pop()}
                              </button>
                            ))}
                            {node.source_files.length > 3 && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setExpandedNodeId(isExpanded ? null : node.id);
                                }}
                                className="text-[9px] text-black font-black bg-yellow-400 hover:bg-yellow-350 border-2 border-black px-1.5 py-0.5 cursor-pointer transition-all active:translate-x-[0.5px] active:translate-y-[0.5px]"
                                title={isExpanded ? "Collapse file list" : "Expand file list"}
                              >
                                {isExpanded ? "Less" : `+${node.source_files.length - 3}`}
                              </button>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
