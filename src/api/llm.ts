import { api } from './client';

export interface GeminiToolCall {
  callId: string;
  toolName: string;
  arguments: Record<string, any>;
}

export interface GeminiGenerateResponse {
  content: string;
  toolCalls: GeminiToolCall[];
  promptTokens: number;
  completionTokens: number;
  modelName: string;
  finishReason: string;
  error?: string;
}

export interface GeminiFormatPreviewResponse {
  geminiPayload: any;
  endpoint: string;
  headers: Record<string, string>;
}

export const llmApi = {
  generate: (params: {
    prompt: string;
    systemInstruction?: string;
    enableTools?: boolean;
    model?: string;
  }) => api.post<GeminiGenerateResponse>('/api/gemini/generate', params),

  previewFormat: (params: {
    systemPrompt?: string;
    userMessage: string;
    toolDefinitions?: any[];
  }) => api.post<GeminiFormatPreviewResponse>('/api/llm/format-preview', params),
};
