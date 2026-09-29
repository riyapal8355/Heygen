"use client";

import React, { useState, useEffect } from "react";
import {
  Video,
  FolderPlus,
  Trash2,
  PanelLeftClose,
  Folder,
  Lock,
  Users,
} from "lucide-react";
import CreateFolderModal from "../projects/CreateFolderModal";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { api } from "@/lib/api";

interface FolderItem {
  id: string;
  name: string;
  accessLevel: "Private" | "Workspace" | "Public";
}

interface ProjectsSidebarProps {
  activeSection: "my_projects" | "trash" | string;
  onSelectSection: (section: string) => void;
  onNewFolder?: () => void;
}

export default function ProjectsSidebar({
  activeSection,
  onSelectSection,
  onNewFolder,
}: ProjectsSidebarProps) {
  const { currentWorkspace } = useAuth();
  const { theme } = useTheme();
  const isLight = theme === "light";
  const [isFolderModalOpen, setIsFolderModalOpen] = useState(false);
  const [folders, setFolders] = useState<FolderItem[]>([]);

  useEffect(() => {
    if (!currentWorkspace?.id) return;
    api.folders
      .list(currentWorkspace.id)
      .then((res) => {
        setFolders(
          res.map((f) => ({
            id: f.id,
            name: f.name,
            accessLevel: "Workspace",
          }))
        );
      })
      .catch(() => {});
  }, [currentWorkspace?.id]);

  const handleCreateFolder = async (folderData: {
    name: string;
    accessLevel: "Private" | "Workspace" | "Public";
  }) => {
    if (currentWorkspace?.id) {
      try {
        const created = await api.folders.create(currentWorkspace.id, {
          name: folderData.name,
          parent_id: null,
        });
        const newFolder: FolderItem = {
          id: created.id,
          name: created.name,
          accessLevel: folderData.accessLevel,
        };
        setFolders((prev) => [...prev, newFolder]);
        onSelectSection(newFolder.id);
        return;
      } catch (err: any) {
        alert(err?.message || "Failed to create folder");
      }
    }
  };

  return (
    <>
      <aside className={`w-60 h-screen flex flex-col justify-between shrink-0 font-sans select-none z-20 transition-colors ${
        isLight ? "bg-white border-r border-slate-200" : "bg-[#0a0e17] border-r border-[#141b2c]"
      }`}>
        <div className="p-4 flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-2 py-1 mb-4">
            <span className={`text-sm font-bold ${isLight ? "text-slate-900" : "text-white"}`}>Projects</span>
            <button
              title="Collapse sidebar"
              className={`transition-colors p-1 rounded-lg cursor-pointer ${
                isLight ? "text-slate-400 hover:text-slate-900 hover:bg-slate-100" : "text-slate-400 hover:text-slate-200 hover:bg-[#121828]"
              }`}
            >
              <PanelLeftClose size={16} />
            </button>
          </div>

          {/* Navigation Items */}
          <nav className="space-y-1">
            <div
              onClick={() => onSelectSection("my_projects")}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all text-left cursor-pointer ${
                activeSection === "my_projects"
                  ? isLight
                    ? "bg-[#eef4ff] text-blue-700 border border-blue-200/70 shadow-xs"
                    : "bg-[#151f36] text-cyan-400 border border-cyan-500/20 shadow-sm"
                  : isLight
                  ? "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  : "text-slate-400 hover:bg-[#111728] hover:text-slate-200"
              }`}
            >
              <div className="flex items-center gap-2.5">
                <Video size={16} className={`shrink-0 ${
                  activeSection === "my_projects"
                    ? isLight ? "text-blue-600" : "text-cyan-400"
                    : "text-slate-400"
                }`} />
                <span>My Projects</span>
              </div>
            </div>

            {/* Custom Folders List */}
            {folders.map((folder) => {
              const isFolderActive = activeSection === folder.id;
              return (
                <div
                  key={folder.id}
                  onClick={() => onSelectSection(folder.id)}
                  className={`w-full flex items-center justify-between px-3.5 py-2 rounded-xl text-xs font-medium transition-all text-left cursor-pointer ${
                    isFolderActive
                      ? isLight
                        ? "bg-[#eef4ff] text-blue-700 border border-blue-200/70 shadow-xs"
                        : "bg-[#151f36] text-cyan-400 border border-cyan-500/20 shadow-sm"
                      : isLight
                      ? "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                      : "text-slate-400 hover:bg-[#111728] hover:text-slate-200"
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <Folder size={14} className={`shrink-0 ${isLight ? "text-blue-600" : "text-cyan-500"}`} />
                    <span className="truncate">{folder.name}</span>
                  </div>
                  {folder.accessLevel === "Private" ? (
                    <Lock size={12} className="text-slate-400" />
                  ) : (
                    <Users size={12} className="text-slate-400" />
                  )}
                </div>
              );
            })}

            {/* New Folder Button */}
            <button
              onClick={() => {
                if (onNewFolder) onNewFolder();
                setIsFolderModalOpen(true);
              }}
              className={`w-full flex items-center gap-2.5 px-6 py-2 rounded-xl text-xs font-medium transition-colors cursor-pointer ${
                isLight ? "text-slate-600 hover:text-slate-900 hover:bg-slate-50" : "text-slate-400 hover:text-slate-200 hover:bg-[#111728]"
              }`}
            >
              <FolderPlus size={14} className="text-slate-400" />
              <span>New Folder</span>
            </button>
          </nav>
        </div>

        {/* Bottom Trash Button */}
        <div className={`p-4 border-t ${isLight ? "border-slate-200" : "border-[#141b2c]"}`}>
          <button
            onClick={() => onSelectSection("trash")}
            className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold transition-colors cursor-pointer ${
              activeSection === "trash"
                ? "bg-rose-50 text-rose-600 border border-rose-200 font-bold dark:bg-[#151f36] dark:text-rose-400 dark:border-rose-500/20"
                : isLight
                ? "text-slate-500 hover:text-rose-600 hover:bg-rose-50/50"
                : "text-slate-400 hover:text-rose-400 hover:bg-[#121828]"
            }`}
          >
            <Trash2 size={16} />
            <span>Trash</span>
          </button>
        </div>
      </aside>

      {/* Create Folder Modal */}
      <CreateFolderModal
        isOpen={isFolderModalOpen}
        onClose={() => setIsFolderModalOpen(false)}
        onCreateFolder={handleCreateFolder}
      />
    </>
  );
}
