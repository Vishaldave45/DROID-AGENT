import React, { useState, useEffect } from 'react';
import { Folder, FileText, ChevronRight, ChevronDown, Copy, Check, RefreshCw, FileCode, HardDrive } from 'lucide-react';
import { repoApi, RepoSummary } from '../api/repo';
import { toolsApi } from '../api/tools';

interface FileTreeNode {
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: FileTreeNode[];
  sizeBytes?: number;
  linesOfCode?: number;
  language?: string;
  isTest?: boolean;
}

export const FileTreeViewer: React.FC = () => {
  const [treeData, setTreeData] = useState<FileTreeNode | null>(null);
  const [selectedFilePath, setSelectedFilePath] = useState<string>('nexforge-droid/app/main.py');
  const [fileContent, setFileContent] = useState<string>('');
  const [loadingTree, setLoadingTree] = useState(true);
  const [loadingFile, setLoadingFile] = useState(false);
  const [copied, setCopied] = useState(false);
  const [repoSummary, setRepoSummary] = useState<RepoSummary | null>(null);
  const [openFolders, setOpenFolders] = useState<Record<string, boolean>>({
    'nexforge-droid': true,
    'nexforge-droid/app': true,
    'nexforge-droid/tests': true,
  });

  const loadRepositoryFiles = async () => {
    setLoadingTree(true);
    try {
      const summary = await repoApi.scan('./nexforge-droid');
      setRepoSummary(summary);

      // Build tree hierarchy from files sample
      const rootNode: FileTreeNode = {
        name: 'nexforge-droid',
        type: 'folder',
        path: 'nexforge-droid',
        children: [],
      };

      const folderMap: Record<string, FileTreeNode> = {
        'nexforge-droid': rootNode,
      };

      if (summary.files_sample) {
        summary.files_sample.forEach((f) => {
          const parts = f.relative_path.split('/');
          let currentPath = 'nexforge-droid';

          for (let i = 0; i < parts.length - 1; i++) {
            const folderName = parts[i];
            const nextPath = `${currentPath}/${folderName}`;
            if (!folderMap[nextPath]) {
              const newFolder: FileTreeNode = {
                name: folderName,
                type: 'folder',
                path: nextPath,
                children: [],
              };
              folderMap[nextPath] = newFolder;
              folderMap[currentPath].children?.push(newFolder);
            }
            currentPath = nextPath;
          }

          const fileName = parts[parts.length - 1];
          const fileNode: FileTreeNode = {
            name: fileName,
            type: 'file',
            path: `nexforge-droid/${f.relative_path}`,
            sizeBytes: f.size_bytes,
            linesOfCode: f.lines_of_code,
            language: f.language,
            isTest: f.is_test,
          };
          folderMap[currentPath].children?.push(fileNode);
        });
      }

      setTreeData(rootNode);
      if (summary.entry_points && summary.entry_points.length > 0) {
        loadFileContent(`nexforge-droid/${summary.entry_points[0]}`);
      } else {
        loadFileContent('nexforge-droid/app/main.py');
      }
    } catch (err) {
      console.error('Failed to load file tree:', err);
    } finally {
      setLoadingTree(false);
    }
  };

  const loadFileContent = async (filePath: string) => {
    setSelectedFilePath(filePath);
    setLoadingFile(true);
    try {
      const res = await toolsApi.execute('read_file', { path: filePath });
      if (res.success && res.output && typeof res.output.content === 'string') {
        setFileContent(res.output.content);
      } else if (res.output && typeof res.output === 'string') {
        setFileContent(res.output);
      } else {
        setFileContent(`# [Unable to read file content or binary file]\n# Path: ${filePath}`);
      }
    } catch (err: any) {
      setFileContent(`# Error reading file: ${err.message}`);
    } finally {
      setLoadingFile(false);
    }
  };

  useEffect(() => {
    loadRepositoryFiles();
  }, []);

  const toggleFolder = (folderPath: string) => {
    setOpenFolders((prev) => ({
      ...prev,
      [folderPath]: !prev[folderPath],
    }));
  };

  const handleCopy = () => {
    if (fileContent) {
      navigator.clipboard.writeText(fileContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const renderNode = (node: FileTreeNode, level: number = 0) => {
    if (node.type === 'folder') {
      const isOpen = openFolders[node.path] ?? true;
      return (
        <div key={node.path} className="select-none">
          <div
            onClick={() => toggleFolder(node.path)}
            className="flex items-center gap-1.5 py-1 px-2 text-xs font-medium text-slate-300 hover:bg-slate-800/60 rounded cursor-pointer transition-colors"
            style={{ paddingLeft: `${level * 14 + 8}px` }}
          >
            {isOpen ? (
              <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
            )}
            <Folder className="w-3.5 h-3.5 text-amber-400" />
            <span>{node.name}</span>
          </div>
          {isOpen && (
            <div className="space-y-0.5">
              {node.children
                ?.sort((a, b) => {
                  if (a.type !== b.type) return a.type === 'folder' ? -1 : 1;
                  return a.name.localeCompare(b.name);
                })
                .map((child) => renderNode(child, level + 1))}
            </div>
          )}
        </div>
      );
    }

    const isSelected = selectedFilePath === node.path;
    return (
      <div
        key={node.path}
        onClick={() => loadFileContent(node.path)}
        className={`flex items-center justify-between py-1 px-2 text-xs font-mono rounded cursor-pointer transition-colors ${
          isSelected
            ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/40'
            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
        }`}
        style={{ paddingLeft: `${level * 14 + 20}px` }}
      >
        <div className="flex items-center gap-1.5 truncate">
          <FileText className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span className="truncate">{node.name}</span>
        </div>
        {node.linesOfCode && (
          <span className="text-[10px] text-slate-500 shrink-0 font-sans ml-2">
            {node.linesOfCode}L
          </span>
        )}
      </div>
    );
  };

  return (
    <div id="file-tree-viewer-container" className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-slate-100 shadow-xl space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-semibold text-white tracking-tight flex items-center gap-2">
            <HardDrive className="w-5 h-5 text-emerald-400" />
            Live Repository Filesystem
          </h2>
          <p className="text-sm text-slate-400 mt-0.5">
            Browse real source files, test suites, and configuration contracts directly from disk
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadRepositoryFiles}
            disabled={loadingTree}
            className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors border border-slate-700"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingTree ? 'animate-spin' : ''}`} />
            Refresh Directory
          </button>
        </div>
      </div>

      {repoSummary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg">
            <div className="text-xs text-slate-400">Total Files</div>
            <div className="text-lg font-bold text-white font-mono mt-0.5">{repoSummary.total_files}</div>
          </div>
          <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg">
            <div className="text-xs text-slate-400">Total Lines of Code</div>
            <div className="text-lg font-bold text-emerald-400 font-mono mt-0.5">{repoSummary.total_lines_of_code.toLocaleString()}</div>
          </div>
          <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg">
            <div className="text-xs text-slate-400">Languages Detected</div>
            <div className="text-sm font-semibold text-slate-300 mt-1 truncate">{repoSummary.languages.join(', ')}</div>
          </div>
          <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg">
            <div className="text-xs text-slate-400">Test Framework</div>
            <div className="text-sm font-semibold text-indigo-400 mt-1 truncate">{repoSummary.test_frameworks.join(', ') || 'unittest'}</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[500px]">
        {/* Left: Tree Navigation */}
        <div className="lg:col-span-4 bg-slate-950/90 border border-slate-800 rounded-lg p-3 max-h-[550px] overflow-y-auto space-y-1">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-2 py-1 mb-1">
            Workspace Tree
          </div>
          {loadingTree ? (
            <div className="p-6 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-400" />
              Scanning filesystem...
            </div>
          ) : treeData ? (
            renderNode(treeData)
          ) : (
            <div className="p-4 text-xs text-slate-500 text-center">No files found.</div>
          )}
        </div>

        {/* Right: File Viewer */}
        <div className="lg:col-span-8 bg-slate-950/90 border border-slate-800 rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
              <div className="flex items-center gap-2 truncate">
                <FileCode className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="font-mono text-xs font-semibold text-white truncate">
                  {selectedFilePath}
                </span>
              </div>
              <button
                onClick={handleCopy}
                disabled={loadingFile}
                className="px-2.5 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded flex items-center gap-1.5 transition-colors border border-slate-700 shrink-0"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>

            {loadingFile ? (
              <div className="py-20 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-emerald-400" />
                Loading file from disk via Python Tool Registry...
              </div>
            ) : (
              <pre className="p-4 bg-slate-900/90 border border-slate-800/80 rounded-lg text-xs font-mono text-slate-200 overflow-x-auto max-h-[460px] leading-relaxed select-text">
                {fileContent || '// Select a file from the workspace tree to view its content'}
              </pre>
            )}
          </div>

          <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500 font-mono mt-4">
            <span>Encoding: UTF-8</span>
            <span>Lines: {fileContent.split('\n').length}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
