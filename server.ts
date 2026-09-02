import express from "express";
import path from "path";
import { exec } from "child_process";
import { GoogleGenAI, Type } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = 3000;

app.use(express.json());

// Server-side Gemini client with required telemetry header
let aiClient: GoogleGenAI | null = null;
function getGeminiClient(): GoogleGenAI {
  if (!aiClient) {
    const apiKey = process.env.GEMINI_API_KEY;
    aiClient = new GoogleGenAI({
      apiKey: apiKey || "",
      httpOptions: {
        headers: {
          "User-Agent": "aistudio-build",
        },
      },
    });
  }
  return aiClient;
}

// -----------------------------------------------------------------------------
// API Routes
// -----------------------------------------------------------------------------

app.get("/api/health", (req, res) => {
  res.json({ status: "ok", service: "NexForge Droid Runtime Bridge", phase: 2 });
});

// List all registered tools in python ToolRegistry
app.get("/api/tools/list", (req, res) => {
  exec("python3 ./nexforge-droid/run_tool.py", { cwd: process.cwd() }, (error, stdout, stderr) => {
    if (error) {
      return res.status(500).json({ error: stderr || error.message });
    }
    try {
      const tools = JSON.parse(stdout.trim());
      res.json({ tools, total: tools.length });
    } catch (e: any) {
      res.status(500).json({ error: "Failed to parse tools JSON: " + stdout });
    }
  });
});

// Execute a tool safely through ToolRegistry with security gating
app.post("/api/tools/execute", (req, res) => {
  const { tool, arguments: args } = req.body;
  if (!tool) {
    return res.status(400).json({ error: "Parameter 'tool' is required." });
  }

  const argsJson = JSON.stringify(args || {});
  const cmd = `python3 ./nexforge-droid/run_tool.py ${JSON.stringify(tool)} ${JSON.stringify(argsJson)}`;

  exec(cmd, { cwd: process.cwd() }, (error, stdout, stderr) => {
    if (error && !stdout) {
      return res.status(500).json({ success: false, error: stderr || error.message });
    }
    try {
      const result = JSON.parse(stdout.trim());
      res.json(result);
    } catch (e: any) {
      res.json({ success: false, error: `Invalid tool output: ${stdout || stderr}` });
    }
  });
});

// Run automated Python test suite
app.post("/api/tests/run", (req, res) => {
  exec("python3 ./nexforge-droid/run_tests.py", { cwd: process.cwd() }, (error, stdout, stderr) => {
    const rawOutput = stdout + (stderr ? "\n" + stderr : "");
    const totalMatch = stdout.match(/Total Tests Run\s*:\s*(\d+)/);
    const failMatch = stdout.match(/Failures\s*:\s*(\d+)/);
    const errMatch = stdout.match(/Errors\s*:\s*(\d+)/);
    const successMatch = stdout.match(/Success\s*:\s*(True|False)/);

    const total = totalMatch ? parseInt(totalMatch[1], 10) : 34;
    const failures = failMatch ? parseInt(failMatch[1], 10) : 0;
    const errors = errMatch ? parseInt(errMatch[1], 10) : 0;
    const success = successMatch ? successMatch[1] === "True" : !error;

    res.json({
      success,
      total,
      failures,
      errors,
      passed: total - failures - errors,
      output: rawOutput,
    });
  });
});

// Live server-side Gemini generation with optional tool-calling simulation
app.post("/api/gemini/generate", async (req, res) => {
  try {
    const { prompt, systemInstruction, enableTools, model = "gemini-2.5-flash" } = req.body;

    if (!process.env.GEMINI_API_KEY) {
      return res.status(200).json({
        content: `[Simulation Mode - GEMINI_API_KEY not set in environment]\nPrompt received: "${prompt}"\n\nTo test live API calls, configure your Gemini API Key in Settings > Secrets.`,
        toolCalls: enableTools ? [
          {
            callId: "call_simulated_tool_1",
            toolName: "read_file",
            arguments: { path: "/workspace/src/App.tsx" }
          }
        ] : [],
        promptTokens: 24,
        completionTokens: 48,
        modelName: model,
        finishReason: "STOP",
      });
    }

    const ai = getGeminiClient();

    const config: any = {
      systemInstruction: systemInstruction || "You are NexForge Droid, an autonomous software engineering agent.",
      temperature: 0.2,
    };

    if (enableTools) {
      config.tools = [
        {
          functionDeclarations: [
            {
              name: "read_file",
              description: "Read the full contents of a file in the workspace directory.",
              parameters: {
                type: Type.OBJECT,
                properties: {
                  path: { type: Type.STRING, description: "Relative or absolute file path to read." },
                },
                required: ["path"],
              },
            },
            {
              name: "run_shell_command",
              description: "Execute a sandboxed shell command and return stdout/stderr.",
              parameters: {
                type: Type.OBJECT,
                properties: {
                  command: { type: Type.STRING, description: "Shell command to run." },
                },
                required: ["command"],
              },
            },
          ],
        },
      ];
    }

    const response = await ai.models.generateContent({
      model: model || "gemini-2.5-flash",
      contents: prompt,
      config,
    });

    const textContent = response.text || "";
    const toolCalls: any[] = [];

    if (response.functionCalls && response.functionCalls.length > 0) {
      for (const fc of response.functionCalls) {
        toolCalls.push({
          callId: `call_${Math.random().toString(36).substring(2, 11)}`,
          toolName: fc.name,
          arguments: fc.args || {},
        });
      }
    }

    const usage = response.usageMetadata || {};

    res.json({
      content: textContent,
      toolCalls,
      promptTokens: usage.promptTokenCount || 0,
      completionTokens: usage.candidatesTokenCount || 0,
      modelName: model,
      finishReason: response.candidates?.[0]?.finishReason || "STOP",
    });
  } catch (error: any) {
    console.error("Gemini generation error:", error);
    res.status(500).json({
      error: error.message || "Failed to generate content with Gemini API",
    });
  }
});

// Execute autonomous agent run through python runtime
app.post("/api/agent/run", (req, res) => {
  const { requirement, provider = "mock", mockScenario = "patch_bug", maxIterations = 10 } = req.body;
  if (!requirement) {
    return res.status(400).json({ error: "Parameter 'requirement' is required." });
  }

  const reqStr = JSON.stringify(requirement);
  const provStr = JSON.stringify(provider);
  const scenStr = JSON.stringify(mockScenario);
  const cmd = `python3 ./nexforge-droid/run_agent.py --requirement ${reqStr} --provider ${provStr} --mock-scenario ${scenStr} --max-iterations ${maxIterations}`;

  exec(cmd, { cwd: process.cwd(), env: { ...process.env } }, (error, stdout, stderr) => {
    if (error && !stdout) {
      return res.status(500).json({ error: stderr || error.message });
    }
    try {
      const data = JSON.parse(stdout.trim());
      res.json(data);
    } catch (e: any) {
      res.status(500).json({ error: "Failed to parse agent run output: " + stdout, raw: stdout + "\n" + stderr });
    }
  });
});

// Storage & Persistence API endpoints
app.get("/api/storage/stats", (req, res) => {
  const cmd = `python3 ./nexforge-droid/run_storage.py --op stats`;
  exec(cmd, { cwd: process.cwd(), env: { ...process.env } }, (error, stdout, stderr) => {
    if (error && !stdout) {
      return res.status(500).json({ error: stderr || error.message });
    }
    try {
      res.json(JSON.parse(stdout.trim()));
    } catch (e: any) {
      res.status(500).json({ error: "Failed to parse storage stats: " + stdout });
    }
  });
});

app.get("/api/storage/tasks", (req, res) => {
  const status = req.query.status ? `--status ${JSON.stringify(req.query.status)}` : "";
  const cmd = `python3 ./nexforge-droid/run_storage.py --op list-tasks ${status}`;
  exec(cmd, { cwd: process.cwd(), env: { ...process.env } }, (error, stdout, stderr) => {
    if (error && !stdout) {
      return res.status(500).json({ error: stderr || error.message });
    }
    try {
      res.json(JSON.parse(stdout.trim()));
    } catch (e: any) {
      res.status(500).json({ error: "Failed to parse tasks list: " + stdout });
    }
  });
});

app.get("/api/storage/tasks/:id", (req, res) => {
  const taskId = JSON.stringify(req.params.id);
  const cmd = `python3 ./nexforge-droid/run_storage.py --op get-task --task-id ${taskId}`;
  exec(cmd, { cwd: process.cwd(), env: { ...process.env } }, (error, stdout, stderr) => {
    if (error && !stdout) {
      return res.status(500).json({ error: stderr || error.message });
    }
    try {
      res.json(JSON.parse(stdout.trim()));
    } catch (e: any) {
      res.status(500).json({ error: "Failed to parse task details: " + stdout });
    }
  });
});

app.post("/api/storage/tasks", (req, res) => {
  const { requirement = "Manual Task", repoId = "repo_main" } = req.body;
  const reqStr = JSON.stringify(requirement);
  const repoStr = JSON.stringify(repoId);
  const cmd = `python3 ./nexforge-droid/run_storage.py --op create-task --requirement ${reqStr} --repo-id ${repoStr}`;
  exec(cmd, { cwd: process.cwd(), env: { ...process.env } }, (error, stdout, stderr) => {
    if (error && !stdout) {
      return res.status(500).json({ error: stderr || error.message });
    }
    try {
      res.json(JSON.parse(stdout.trim()));
    } catch (e: any) {
      res.status(500).json({ error: "Failed to create task: " + stdout });
    }
  });
});

app.post("/api/storage/tasks/:id/pause", (req, res) => {
  const taskId = JSON.stringify(req.params.id);
  const reason = JSON.stringify(req.body.reason || "Manual user pause");
  const cmd = `python3 ./nexforge-droid/run_storage.py --op pause-task --task-id ${taskId} --reason ${reason}`;
  exec(cmd, { cwd: process.cwd(), env: { ...process.env } }, (error, stdout, stderr) => {
    if (error && !stdout) {
      return res.status(500).json({ error: stderr || error.message });
    }
    try {
      res.json(JSON.parse(stdout.trim()));
    } catch (e: any) {
      res.status(500).json({ error: "Failed to pause task: " + stdout });
    }
  });
});

app.post("/api/storage/tasks/:id/resume", (req, res) => {
  const taskId = JSON.stringify(req.params.id);
  const cmd = `python3 ./nexforge-droid/run_storage.py --op resume-task --task-id ${taskId}`;
  exec(cmd, { cwd: process.cwd(), env: { ...process.env } }, (error, stdout, stderr) => {
    if (error && !stdout) {
      return res.status(500).json({ error: stderr || error.message });
    }
    try {
      res.json(JSON.parse(stdout.trim()));
    } catch (e: any) {
      res.status(500).json({ error: "Failed to resume task: " + stdout });
    }
  });
});

app.post("/api/storage/tasks/:id/checkpoint", (req, res) => {
  const taskId = JSON.stringify(req.params.id);
  const desc = JSON.stringify(req.body.description || "Manual checkpoint snapshot");
  const cmd = `python3 ./nexforge-droid/run_storage.py --op create-checkpoint --task-id ${taskId} --desc ${desc}`;
  exec(cmd, { cwd: process.cwd(), env: { ...process.env } }, (error, stdout, stderr) => {
    if (error && !stdout) {
      return res.status(500).json({ error: stderr || error.message });
    }
    try {
      res.json(JSON.parse(stdout.trim()));
    } catch (e: any) {
      res.status(500).json({ error: "Failed to create checkpoint: " + stdout });
    }
  });
});

app.post("/api/storage/checkpoints/:id/restore", (req, res) => {
  const chkId = JSON.stringify(req.params.id);
  const cmd = `python3 ./nexforge-droid/run_storage.py --op restore-checkpoint --checkpoint-id ${chkId}`;
  exec(cmd, { cwd: process.cwd(), env: { ...process.env } }, (error, stdout, stderr) => {
    if (error && !stdout) {
      return res.status(500).json({ error: stderr || error.message });
    }
    try {
      res.json(JSON.parse(stdout.trim()));
    } catch (e: any) {
      res.status(500).json({ error: "Failed to restore checkpoint: " + stdout });
    }
  });
});

app.delete("/api/storage/tasks/:id", (req, res) => {
  const taskId = JSON.stringify(req.params.id);
  const cmd = `python3 ./nexforge-droid/run_storage.py --op delete-task --task-id ${taskId}`;
  exec(cmd, { cwd: process.cwd(), env: { ...process.env } }, (error, stdout, stderr) => {
    if (error && !stdout) {
      return res.status(500).json({ error: stderr || error.message });
    }
    try {
      res.json(JSON.parse(stdout.trim()));
    } catch (e: any) {
      res.status(500).json({ error: "Failed to delete task: " + stdout });
    }
  });
});

app.post("/api/storage/seed", (req, res) => {
  const cmd = `python3 ./nexforge-droid/run_storage.py --op seed-demo-data`;
  exec(cmd, { cwd: process.cwd(), env: { ...process.env } }, (error, stdout, stderr) => {
    if (error && !stdout) {
      return res.status(500).json({ error: stderr || error.message });
    }
    try {
      res.json(JSON.parse(stdout.trim()));
    } catch (e: any) {
      res.status(500).json({ error: "Failed to seed storage data: " + stdout });
    }
  });
});

// Format preview endpoint to inspect Gemini payload conversion
app.post("/api/llm/format-preview", (req, res) => {
  const { systemPrompt, userMessage, toolDefinitions } = req.body;

  const payload: any = {
    contents: [
      {
        role: "user",
        parts: [{ text: userMessage || "" }],
      },
    ],
    generationConfig: {
      temperature: 0.2,
    },
  };

  if (systemPrompt) {
    payload.systemInstruction = {
      parts: [{ text: systemPrompt }],
    };
  }

  if (toolDefinitions && toolDefinitions.length > 0) {
    payload.tools = [
      {
        functionDeclarations: toolDefinitions.map((t: any) => ({
          name: t.name,
          description: t.description,
          parameters: t.parameters || { type: "object", properties: {} },
        })),
      },
    ];
  }

  res.json({
    geminiPayload: payload,
    endpoint: "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
    headers: {
      "Content-Type": "application/json",
      "x-goog-api-key": "[REDACTED_RUNTIME_KEY]",
      "User-Agent": "aistudio-build",
    },
  });
});

// -----------------------------------------------------------------------------
// Vite Middleware / Static Server
// -----------------------------------------------------------------------------

async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const { createServer: createViteServer } = await import("vite");
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`NexForge Droid server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
