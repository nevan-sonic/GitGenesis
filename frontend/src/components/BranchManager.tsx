"use client";

import React, { useState } from "react";
import { X, GitBranch, Plus, Check } from "lucide-react";
import { apiFetch } from "@/app/api";

interface BranchManagerProps {
  branches: any[];
  activeBranchId: string;
  onSwitch: (branchId: string) => void;
  onClose: () => void;
  blueprintId: string;
  onRefresh: () => void;
}

export default function BranchManager({ branches, activeBranchId, onSwitch, onClose, blueprintId, onRefresh }: BranchManagerProps) {
  const [newBranchName, setNewBranchName] = useState("");
  const [creating, setCreating] = useState(false);

  const handleCreateBranch = async () => {
    if (!newBranchName.trim() || creating) return;
    setCreating(true);
    try {
      const res = await apiFetch(`/api/blueprints/${blueprintId}/branches`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newBranchName })
      });
      if (res.ok) {
        setNewBranchName("");
        onRefresh(); // Refresh branch list in parent
      }
    } catch (e) {
      console.error("Failed to create branch variant", e);
    } finally {
      setCreating(false);
    }
  };

  const handleActivateBranch = async (branchId: string) => {
    try {
      const res = await apiFetch(`/api/blueprints/${blueprintId}/activate-branch/${branchId}`, {
        method: "POST"
      });
      if (res.ok) {
        onSwitch(branchId);
      }
    } catch (e) {
      console.error("Failed to activate branch", e);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex justify-end">
      {/* Background click to close */}
      <div className="absolute inset-0" onClick={onClose} />

      {/* Drawer Body */}
      <div className="w-96 h-full bg-[#fbfaf7] border-l-3 border-black z-10 p-6 flex flex-col justify-between shadow-[-4px_0px_0px_0px_#000000] relative text-black">
        <div className="flex flex-col gap-6 overflow-y-auto">
          {/* Header */}
          <div className="flex items-center justify-between border-b-2 border-black pb-4">
            <h3 className="text-sm font-black text-black uppercase tracking-wider flex items-center gap-2">
              <GitBranch className="w-4 h-4 text-black" /> Branch Manager
            </h3>
            <button 
              onClick={onClose}
              className="p-1 text-black hover:bg-zinc-200 border-2 border-black bg-white shadow-[2px_2px_0px_0px_#000000] hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-[1px_1px_0px_0px_#000000] transition-all cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Create Branch form */}
          <div className="flex flex-col gap-2">
            <label className="text-[10px] uppercase font-black text-black tracking-wider">Spawn New Variant Branch</label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="e.g. Supabase Auth Variant"
                value={newBranchName}
                onChange={(e) => setNewBranchName(e.target.value)}
                className="flex-1 px-3 py-2 bg-white border-2 border-black focus:outline-none focus:ring-0 text-xs text-black placeholder-zinc-500 shadow-[2px_2px_0px_0px_#000000]"
              />
              <button
                onClick={handleCreateBranch}
                disabled={!newBranchName.trim() || creating}
                className="p-2.5 bg-[#a3e635] hover:bg-[#bbf247] border-2 border-black text-black shadow-[2px_2px_0px_0px_#000000] hover:translate-x-[0.5px] hover:translate-y-[0.5px] hover:shadow-[1px_1px_0px_0px_#000000] transition-all disabled:opacity-50 flex items-center justify-center cursor-pointer"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Branch list */}
          <div className="flex flex-col gap-3">
            <label className="text-[10px] uppercase font-black text-black tracking-wider">Available Blueprint Variants</label>
            <div className="flex flex-col gap-2">
              {branches.map(branch => {
                const isActive = branch.id === activeBranchId;
                return (
                  <div 
                    key={branch.id} 
                    onClick={() => !isActive && handleActivateBranch(branch.id)}
                    className={`p-3.5 border-2 border-black flex items-center justify-between cursor-pointer transition-all ${
                      isActive 
                        ? "bg-[#ffd54f] shadow-[3px_3px_0px_0px_#000000]" 
                        : "bg-white hover:bg-zinc-50 shadow-[3px_3px_0px_0px_#000000] hover:translate-x-[0.5px] hover:translate-y-[0.5px] hover:shadow-[2px_2px_0px_0px_#000000]"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <GitBranch className={`w-4 h-4 ${isActive ? "text-black" : "text-zinc-600"}`} />
                      <div>
                        <h4 className={`text-xs ${isActive ? "font-black" : "font-bold"} text-black`}>{branch.name}</h4>
                        <span className="text-[9px] text-zinc-700 font-mono font-bold mt-0.5 block">
                          {new Date(branch.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    {isActive && (
                      <span className="w-5 h-5 rounded-none bg-white border-2 border-black flex items-center justify-center text-black shadow-[1px_1px_0px_0px_#000000]">
                        <Check className="w-3 h-3" />
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer info banner */}
        <div className="border-t-2 border-black pt-4 text-[10px] text-zinc-700 font-mono font-semibold">
          Creating a new branch variant copies all existing nodes/edges from your current active branch. You can then edit strategies and regenerate downstream tasks independently on each branch.
        </div>
      </div>
    </div>
  );
}
