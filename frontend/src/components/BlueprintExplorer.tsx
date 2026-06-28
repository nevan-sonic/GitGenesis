"use client";

import React, { useState, useEffect } from "react";
import { 
  ReactFlow, 
  Background, 
  Controls, 
  useNodesState, 
  useEdgesState,
  Handle,
  Position
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Search, Plus, X, Layers, AlertCircle } from "lucide-react";
import { apiFetch } from "@/app/api";

// Custom node rendering component
const CustomNode = ({ data }: any) => {
  const isSelected = data.isSelected;
  
  // Custom border color based on status
  let statusBorder = "border-black shadow-[4px_4px_0px_0px_#000000]";
  let statusHover = "hover:shadow-[6px_6px_0px_0px_#000000]";
  let statusSelected = "shadow-[6px_6px_0px_0px_#000000]";
  
  if (data.status === "done") {
    statusBorder = "border-lime-500 shadow-[4px_4px_0px_0px_#84cc16]";
    statusHover = "hover:shadow-[6px_6px_0px_0px_#84cc16]";
    statusSelected = "shadow-[6px_6px_0px_0px_#84cc16]";
  } else if (data.status === "in_progress") {
    statusBorder = "border-[#d97706] shadow-[4px_4px_0px_0px_#ffd54f]";
    statusHover = "hover:shadow-[6px_6px_0px_0px_#ffd54f]";
    statusSelected = "shadow-[6px_6px_0px_0px_#ffd54f]";
  }

  return (
    <div className={`p-4 border-3 w-64 text-left bg-white text-black transition-all duration-200 ${statusBorder} ${
      isSelected 
        ? `${statusSelected} -translate-x-0.5 -translate-y-0.5 bg-yellow-50` 
        : `${statusHover} hover:-translate-x-0.5 hover:-translate-y-0.5`
    }`}>
      {/* Node handles for connections */}
      <Handle type="target" position={Position.Top} className="!bg-black !w-3 !h-3 !border-2 !border-black" />
      
      <div className="flex items-center justify-between mb-2.5">
        <span className="text-[9px] uppercase font-mono font-black text-black bg-[#f4f0e6] px-2 py-0.5 border-2 border-black">
          {data.type}
        </span>
        <span className={`text-[8px] uppercase font-mono font-black border-2 border-black px-1.5 py-0.5 ${
          data.status === "done" 
            ? "bg-[#a3e635] text-black" 
            : data.status === "in_progress" 
            ? "bg-[#ffd54f] text-black" 
            : "bg-white text-zinc-650"
        }`}>
          {data.status?.replace("_", " ") || "todo"}
        </span>
      </div>
      
      <h3 className="text-xs font-black text-black truncate mb-1">{data.label}</h3>
      <p className="text-[10px] text-zinc-700 line-clamp-2 leading-relaxed font-medium">{data.summary}</p>
      
      <Handle type="source" position={Position.Bottom} className="!bg-black !w-3 !h-3 !border-2 !border-black" />
    </div>
  );
};

const nodeTypes = {
  customNode: CustomNode
};

interface BlueprintExplorerProps {
  blueprintId: string;
  activeBranchId: string;
  nodes: any[];
  edges: any[];
  onNodeSelect: (nodeId: string) => void;
  selectedNodeId: string | null;
  onRefresh: () => void;
}

export default function BlueprintExplorer({
  blueprintId,
  activeBranchId,
  nodes: rawNodes,
  edges: rawEdges,
  onNodeSelect,
  selectedNodeId,
  onRefresh
}: BlueprintExplorerProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([] as any[]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([] as any[]);
  
  const [searchQuery, setSearchQuery] = useState("");

  // Custom Node Creator Form States
  const [showNodeCreator, setShowNodeCreator] = useState(false);
  const [newNodeId, setNewNodeId] = useState("");
  const [newNodeName, setNewNodeName] = useState("");
  const [newNodeType, setNewNodeType] = useState("api");
  const [newNodeSummary, setNewNodeSummary] = useState("");
  const [createError, setCreateError] = useState("");

  // Layout algorithm: simple vertical layer grid positioning
  useEffect(() => {
    const layers = ["layer", "utilities", "database", "middleware", "api", "routing_api", "routing", "frontend", "frontend_ui", "other"];
    const grouped: { [key: string]: any[] } = {};
    
    rawNodes.forEach(node => {
      const type = (node.type || "other").toLowerCase();
      let matched = "other";
      for (const layer of layers) {
        if (type.includes(layer)) {
          matched = layer;
          break;
        }
      }
      if (!grouped[matched]) grouped[matched] = [];
      grouped[matched].push(node);
    });

    const formattedNodes: any[] = [];
    let currentY = 50;
    
    // Sort layers to layout logically
    const sortedLayers = ["utilities", "database", "middleware", "api", "routing_api", "routing", "frontend", "frontend_ui", "layer", "other"];
    
    sortedLayers.forEach(layer => {
      const layerNodes = grouped[layer] || [];
      if (layerNodes.length === 0) return;
      
      const count = layerNodes.length;
      const spacingX = 300;
      const startX = -((count - 1) * spacingX) / 2;
      
      layerNodes.forEach((node, idx) => {
        formattedNodes.push({
          id: node.id,
          type: "customNode",
          data: {
            label: node.name,
            type: node.type || "module",
            confidence: node.confidence_score || 90,
            summary: node.architectural_reasoning_summary,
            isSelected: node.id === selectedNodeId,
            status: node.status
          },
          position: { 
            x: startX + idx * spacingX + 400, 
            y: currentY 
          }
        });
      });
      currentY += 180;
    });

    setNodes(formattedNodes);

    const formattedEdges = rawEdges.map((edge, idx) => ({
      id: edge.id || `edge_${idx}`,
      source: edge.source_id,
      target: edge.target_id,
      type: "smoothstep",
      animated: true,
      style: { stroke: "#4f46e5", strokeWidth: 2 }
    }));
    
    setEdges(formattedEdges);
  }, [rawNodes, rawEdges, selectedNodeId]);

  // Apply search filtering (vector search fallback to local text match)
  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setNodes(prev => prev.map(node => ({
        ...node,
        data: {
          ...node.data,
          isSelected: node.id === selectedNodeId
        }
      })));
      return;
    }
    
    try {
      const res = await apiFetch(`/api/blueprints/${blueprintId}/search?q=${encodeURIComponent(searchQuery)}&branch_id=${activeBranchId}`);
      if (res.ok) {
        const data = await res.json();
        const matchedIds = new Set(data.results.map((r: any) => r.id));
        
        setNodes(prev => prev.map(node => ({
          ...node,
          data: {
            ...node.data,
            isSelected: matchedIds.has(node.id) || node.id === selectedNodeId
          }
        })));
        return;
      }
    } catch (e) {
      console.error("Vector search failed, falling back to local text search", e);
    }
    
    // Local fallback search (substring matching)
    setNodes(prev => prev.map(node => {
      const label = String(node.data.label).toLowerCase();
      const summary = String(node.data.summary).toLowerCase();
      const match = label.includes(searchQuery.toLowerCase()) || summary.includes(searchQuery.toLowerCase());
      return {
        ...node,
        data: {
          ...node.data,
          isSelected: match || node.id === selectedNodeId
        }
      };
    }));
  };

  // Handle visual drawing of connection edges
  const handleConnect = async (params: any) => {
    try {
      const res = await apiFetch(`/api/blueprints/${blueprintId}/edges`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          branch_id: activeBranchId,
          source_id: params.source,
          target_id: params.target
        })
      });
      if (res.ok) {
        onRefresh();
      }
    } catch (e) {
      console.error("Failed to add edge connection", e);
    }
  };

  // Submit new custom node creation
  const handleCreateNodeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError("");
    if (!newNodeId.trim() || !newNodeName.trim() || !newNodeSummary.trim()) {
      setCreateError("All fields are required.");
      return;
    }
    
    const cleanId = newNodeId.trim().toLowerCase().replace(/[^a-z0-9_]/g, "_");
    
    try {
      const res = await apiFetch(`/api/blueprints/${blueprintId}/nodes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          branch_id: activeBranchId,
          id: cleanId,
          name: newNodeName.trim(),
          type: newNodeType,
          summary: newNodeSummary.trim()
        })
      });
      if (res.ok) {
        setShowNodeCreator(false);
        setNewNodeId("");
        setNewNodeName("");
        setNewNodeType("api");
        setNewNodeSummary("");
        onRefresh();
      } else {
        const errData = await res.json().catch(() => ({}));
        setCreateError(errData.detail || "Failed to create custom node.");
      }
    } catch (err: any) {
      setCreateError(err.message || "Failed to connect to API server.");
    }
  };

  return (
    <div className="w-full h-full relative">
      {/* Search & Tool Header Bar Overlay */}
      <div className="absolute top-4 left-6 z-10 flex items-center gap-3">
        <div className="relative flex items-center">
          <Search className="absolute left-3 w-4 h-4 text-black" />
          <input
            type="text"
            placeholder="Search blueprint nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="w-60 pl-9 pr-4 py-2 bg-white border-3 border-black rounded-none focus:outline-none text-xs font-bold text-black placeholder-zinc-550 shadow-[3px_3px_0px_0px_#000000]"
          />
        </div>
        <button
          onClick={handleSearch}
          className="px-4 py-2 bg-yellow-400 border-3 border-black text-black font-extrabold hover:-translate-y-0.5 hover:shadow-[3px_3px_0px_0px_#000000] active:translate-y-0 active:shadow-none transition-all shadow-[2px_2px_0px_0px_#000000] text-xs cursor-pointer"
        >
          Search
        </button>
        <button
          onClick={() => setShowNodeCreator(true)}
          className="px-4 py-2 bg-indigo-600 border-3 border-black text-white font-extrabold hover:-translate-y-0.5 hover:shadow-[3px_3px_0px_0px_#000000] active:translate-y-0 active:shadow-none transition-all shadow-[2px_2px_0px_0px_#000000] text-xs cursor-pointer flex items-center gap-1"
        >
          <Plus className="w-3.5 h-3.5" /> Add Node
        </button>
      </div>

      {/* Canvas */}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onConnect={handleConnect}
        onNodeClick={(_, node) => onNodeSelect(node.id)}
        fitView
        className="w-full h-full"
      >
        <Background color="#000000" gap={20} size={1.5} style={{ opacity: 0.1 }} />
        <Controls className="!bg-white !border-3 !border-black !shadow-[4px_4px_0px_0px_#000000] [&>button]:!border-b-2 [&>button]:!border-black [&>button]:!text-black" />
      </ReactFlow>

      {/* Visual Custom Node Creator Modal overlay */}
      {showNodeCreator && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 text-black">
          <div className="absolute inset-0" onClick={() => setShowNodeCreator(false)} />
          <form 
            onSubmit={handleCreateNodeSubmit}
            className="w-full max-w-md bg-[#fbfaf7] border-3 border-black p-6 shadow-[6px_6px_0px_0px_#000000] z-10 relative flex flex-col gap-4"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b-2 border-black pb-2">
              <h3 className="text-sm font-black uppercase tracking-wider text-black flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-indigo-650" /> Add Custom Task Node
              </h3>
              <button 
                type="button"
                onClick={() => setShowNodeCreator(false)}
                className="p-1 hover:bg-zinc-100 border border-black cursor-pointer bg-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Error alerts */}
            {createError && (
              <div className="p-3 border-2 border-black bg-red-150 text-red-800 text-xs font-bold font-mono flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-700 shrink-0" />
                <span>{createError}</span>
              </div>
            )}

            {/* Fields */}
            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-[10px] uppercase font-black text-black">Node Identifier (Unique ID)</label>
                <input 
                  type="text"
                  placeholder="e.g. redis_caching"
                  value={newNodeId}
                  onChange={(e) => setNewNodeId(e.target.value)}
                  className="px-3 py-1.5 border-2 border-black bg-white focus:outline-none text-xs font-mono font-bold"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] uppercase font-black text-black">Task Node Name</label>
                <input 
                  type="text"
                  placeholder="e.g. Integrate Redis Cache middleware"
                  value={newNodeName}
                  onChange={(e) => setNewNodeName(e.target.value)}
                  className="px-3 py-1.5 border-2 border-black bg-white focus:outline-none text-xs font-bold"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] uppercase font-black text-black">Layer Category Type</label>
                <select 
                  value={newNodeType}
                  onChange={(e) => setNewNodeType(e.target.value)}
                  className="px-2.5 py-1.5 border-2 border-black bg-white focus:outline-none text-xs font-bold cursor-pointer"
                >
                  <option value="database">Database Layer</option>
                  <option value="api">API Layer</option>
                  <option value="middleware">Middleware Layer</option>
                  <option value="routing">Routing / Controller Layer</option>
                  <option value="frontend">Frontend UI Component</option>
                  <option value="utilities">Utilities & Config</option>
                  <option value="other">Other Module</option>
                </select>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[10px] uppercase font-black text-black">Implementation instructions / Summary</label>
                <textarea 
                  placeholder="Explain what needs to be implemented or built in this task..."
                  value={newNodeSummary}
                  onChange={(e) => setNewNodeSummary(e.target.value)}
                  className="px-3 py-2 border-2 border-black bg-white focus:outline-none text-xs font-medium h-24 resize-none leading-relaxed"
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2 justify-end mt-2">
              <button
                type="button"
                onClick={() => setShowNodeCreator(false)}
                className="px-4 py-2 border-2 border-black bg-white hover:bg-zinc-100 font-bold text-xs uppercase cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-[#a3e635] hover:bg-[#bbf247] border-2 border-black font-black text-xs uppercase shadow-[2px_2px_0px_0px_#000000] cursor-pointer"
              >
                Create Node
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
