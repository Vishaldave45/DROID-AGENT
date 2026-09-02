import React, { useState } from 'react';
import { Folder, FileText, ChevronRight, ChevronDown, Copy, Check } from 'lucide-react';

interface FileNode {
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: FileNode[];
  content?: string;
}

const FILE_TREE: FileNode = {
  name: 'nexforge-droid',
  type: 'folder',
  path: 'nexforge-droid',
  children: [
    {
      name: 'app',
      type: 'folder',
      path: 'nexforge-droid/app',
      children: [
        {
          name: 'main.py',
          type: 'file',
          path: 'nexforge-droid/app/main.py',
          content: `"""NexForge Droid - Application Entrypoint and Service Registry."""

from typing import Any, Dict
from app.config import get_settings
from app.observability.logger import configure_logging, get_logger

settings = get_settings()
configure_logging(level=settings.log_level, json_output=settings.is_production())
logger = get_logger("nexforge.main")

def get_system_manifest() -> Dict[str, Any]:
    return {
        "system": "NexForge Droid",
        "version": "0.1.0",
        "phase": 0,
        "environment": settings.environment,
        "subsystems": {
            "llm": "LLMProvider Abstraction Ready",
            "tools": "Tool & ToolRegistry Interface Ready",
            "agent": "DroidRuntime Contract Ready",
            "storage": "TaskState & TaskStore Contract Ready",
            "security": "PolicyEngine & SecurityContext Ready",
            "context": "ContextEngine & EngineeringGraph Ready",
            "execution": "SandboxExecutor Contract Ready",
            "git": "GitEngine Interface Ready",
            "evaluation": "EvaluationEngine Interface Ready",
            "observability": "Structured JSON Logger & Tracing Ready",
        },
    }`,
        },
        {
          name: 'config.py',
          type: 'file',
          path: 'nexforge-droid/app/config.py',
          content: `@dataclass(frozen=True)
class Settings:
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    default_model: str = field(default_factory=lambda: os.getenv("DEFAULT_MODEL", "gemini-2.5-flash"))
    workspace_root: str = field(default_factory=lambda: os.getenv("WORKSPACE_ROOT", "/workspace"))
    sandbox_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "120")))
    max_iterations: int = field(default_factory=lambda: int(os.getenv("MAX_ITERATIONS", "25")))
    max_context_tokens: int = field(default_factory=lambda: int(os.getenv("MAX_CONTEXT_TOKENS", "32000")))`,
        },
        {
          name: 'security',
          type: 'folder',
          path: 'nexforge-droid/app/security',
          children: [
            {
              name: 'base.py',
              type: 'file',
              path: 'nexforge-droid/app/security/base.py',
              content: `class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    APPROVE = "APPROVE"  # Requires human authorization gate
    DENY = "DENY"

class PolicyEngine(ABC):
    @abstractmethod
    def evaluate(self, tool_name: str, arguments: Dict[str, Any], context: SecurityContext) -> PolicyDecision:
        pass`,
            },
          ],
        },
        {
          name: 'tools',
          type: 'folder',
          path: 'nexforge-droid/app/tools',
          children: [
            {
              name: 'base.py',
              type: 'file',
              path: 'nexforge-droid/app/tools/base.py',
              content: `class Tool(ABC):
    name: str
    description: str
    input_schema: Dict[str, Any]
    requires_permission: bool = False

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        pass`,
            },
          ],
        },
      ],
    },
    {
      name: 'tests',
      type: 'folder',
      path: 'nexforge-droid/tests',
      children: [
        { name: 'test_config.py', type: 'file', path: 'nexforge-droid/tests/test_config.py' },
        { name: 'test_observability.py', type: 'file', path: 'nexforge-droid/tests/test_observability.py' },
        { name: 'test_security_policy.py', type: 'file', path: 'nexforge-droid/tests/test_security_policy.py' },
        { name: 'test_tools_foundation.py', type: 'file', path: 'nexforge-droid/tests/test_tools_foundation.py' },
        { name: 'test_storage_foundation.py', type: 'file', path: 'nexforge-droid/tests/test_storage_foundation.py' },
        { name: 'test_architecture_contracts.py', type: 'file', path: 'nexforge-droid/tests/test_architecture_contracts.py' },
      ],
    },
    { name: 'Dockerfile', type: 'file', path: 'nexforge-droid/Dockerfile' },
    { name: 'docker-compose.yml', type: 'file', path: 'nexforge-droid/docker-compose.yml' },
    { name: 'pyproject.toml', type: 'file', path: 'nexforge-droid/pyproject.toml' },
    { name: 'run_tests.py', type: 'file', path: 'nexforge-droid/run_tests.py' },
    { name: 'README.md', type: 'file', path: 'nexforge-droid/README.md' },
    { name: '.env.example', type: 'file', path: 'nexforge-droid/.env.example' },
  ],
};

export const FileTreeViewer: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<FileNode>(
    FILE_TREE.children![0].children![0] // app/main.py
  );
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (selectedFile.content) {
      navigator.clipboard.writeText(selectedFile.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const renderNode = (node: FileNode, level: number = 0) => {
    if (node.type === 'folder') {
      return (
        <div key={node.path} className="select-none">
          <div className="flex items-center gap-1.5 py-1 px-2 text-xs font-medium text-slate-300 hover:bg-slate-800/60 rounded cursor-pointer" style={{ paddingLeft: `${level * 14 + 8}px` }}>
            <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
            <Folder className="w-3.5 h-3.5 text-amber-400" />
            <span>{node.name}</span>
          </div>
          <div className="space-y-0.5">
            {node.children?.map((child) => renderNode(child, level + 1))}
          </div>
        </div>
      );
    }

    const isSelected = selectedFile?.path === node.path;
    return (
      <div
        key={node.path}
        onClick={() => setSelectedFile(node)}
        className={`flex items-center gap-1.5 py-1 px-2 text-xs font-mono rounded cursor-pointer transition-colors ${
          isSelected
            ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/40'
            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
        }`}
        style={{ paddingLeft: `${level * 14 + 20}px` }}
      >
        <FileText className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <span className="truncate">{node.name}</span>
      </div>
    );
  };

  return (
    <div id="file-tree-viewer" className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-slate-100 shadow-xl">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
        <div>
          <h2 className="text-xl font-semibold text-white tracking-tight flex items-center gap-2">
            <Folder className="w-5 h-5 text-amber-400" />
            Phase 0 Project Filesystem Explorer
          </h2>
          <p className="text-sm text-slate-400 mt-0.5">Physical directory structure and clean Python source artifacts</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-4 bg-slate-950/80 border border-slate-800 rounded-lg p-3 max-h-[360px] overflow-y-auto">
          {renderNode(FILE_TREE)}
        </div>

        <div className="lg:col-span-8 bg-slate-950 border border-slate-800 rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs font-mono text-slate-400">
              <span className="text-emerald-400 font-semibold">{selectedFile.path}</span>
              {selectedFile.content && (
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1 hover:text-white transition-colors"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              )}
            </div>

            <pre className="mt-3 text-xs font-mono text-slate-300 overflow-x-auto p-2 bg-slate-900/60 rounded border border-slate-800/80 leading-relaxed max-h-[260px]">
              {selectedFile.content || `# File path: ${selectedFile.path}\n# Test and module files generated in /nexforge-droid`}
            </pre>
          </div>

          <div className="mt-3 pt-2 text-[11px] text-slate-500 font-mono flex items-center justify-between">
            <span>Modular package layout</span>
            <span>Clean Architecture</span>
          </div>
        </div>
      </div>
    </div>
  );
};
