/**
 * HeyZen Unified API Client
 *
 * Implements typed, standardized communication with the HeyZen FastAPI backend.
 * Features:
 * - Credentials & HttpOnly cookie support (credentials: "include")
 * - In-memory access token storage
 * - Automatic 401 token rotation and retry
 * - Standardized error extraction matching FastAPI APIErrorResponse
 * - Pre-signed MinIO direct binary uploads
 * - SSE Job Event streaming helper with lifecycle cleanup
 */

export function getApiBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  if (typeof window !== "undefined") {
    try {
      const url = new URL(envUrl);
      if (
        (window.location.hostname === "localhost" && url.hostname === "127.0.0.1") ||
        (window.location.hostname === "127.0.0.1" && url.hostname === "localhost")
      ) {
        url.hostname = window.location.hostname;
        return url.origin;
      }
    } catch {
      // ignore
    }
  }
  return envUrl;
}

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

let memoryAccessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function getStoredAccessToken(): string | null {
  if (memoryAccessToken) return memoryAccessToken;
  if (typeof window !== "undefined") {
    try {
      const token = localStorage.getItem("vidoai_token");
      if (token) {
        memoryAccessToken = token;
        return token;
      }
      return null;
    } catch {
      return null;
    }
  }
  return null;
}

export function setStoredAccessToken(token: string | null): void {
  memoryAccessToken = token;
  if (typeof window !== "undefined") {
    try {
      if (token) {
        localStorage.setItem("vidoai_token", token);
      } else {
        localStorage.removeItem("vidoai_token");
      }
    } catch {
      // ignore
    }
  }
}

export interface ApiErrorPayload {
  code: string;
  message: string;
  request_id?: string;
  details?: any;
}

export class ApiError extends Error {
  public readonly code: string;
  public readonly status: number;
  public readonly requestId?: string;
  public readonly details?: any;

  constructor(
    message: string,
    code: string = "API_ERROR",
    status: number = 500,
    requestId?: string,
    details?: any
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.requestId = requestId;
    this.details = details;
  }
}

function generateRequestId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "req_" + Math.random().toString(36).substring(2, 11) + Date.now().toString(36);
}

export interface OnboardingStatusResponse {
  step_1_digital_twin: boolean;
  step_2_voice: boolean;
  step_3_look: boolean;
  step_4_video: boolean;
  completed_steps: number[];
  completed_count: number;
  total_steps: number;
  is_step_2_unlocked: boolean;
  is_step_3_unlocked: boolean;
  is_step_4_unlocked: boolean;
}

export interface BrandKitItemResponse {
  id: string;
  workspace_id: string;
  created_by: string;
  name: string;
  description?: string | null;
  logo_asset_id?: string | null;
  colors: Record<string, any>;
  typography: Record<string, any>;
  settings: Record<string, any>;
  is_default: boolean;
  created_at: string;
  updated_at: string;
  primary_color?: string;
  accent_color?: string;
  secondary_color?: string;
  font_family?: string;
}

export interface BrandGlossaryItemResponse {
  id: string;
  workspace_id: string;
  brand_kit_id?: string | null;
  created_by: string;
  name: string;
  description?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface BrandGlossaryRuleItemResponse {
  id: string;
  glossary_id: string;
  source_term: string;
  preferred_term: string;
  forbidden_term?: string | null;
  source_language: string;
  target_language?: string | null;
  case_sensitive: boolean;
  status: string;
  created_at: string;
  updated_at: string;
  term?: string;
  replacement?: string;
  phonetic_spelling?: string;
  rule_type?: "pronunciation" | "do_not_translate" | "force_translate" | string;
}

/**
 * Low-level request wrapper with automatic error parsing and 401 token rotation.
 */
export async function apiRequest<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = path.startsWith("http") ? path : `${baseUrl}${path}`;
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (!headers.has("X-Request-ID")) {
    headers.set("X-Request-ID", generateRequestId());
  }

  const token = getStoredAccessToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const fetchOptions: RequestInit = {
    ...options,
    headers,
    credentials: "include", // Required for HttpOnly refresh cookie transmission
  };

  let response: Response;
  try {
    response = await fetch(url, fetchOptions);
  } catch (netErr: any) {
    throw new ApiError(
      netErr?.message || "Network connection failed. Is the backend server running?",
      "NETWORK_ERROR",
      0
    );
  }

  // Handle 401 Unauthorized: Attempt token refresh once, then retry
  const isAuthEndpoint =
    path.includes("/auth/login") ||
    path.includes("/auth/signup") ||
    path.includes("/auth/refresh") ||
    path.includes("/auth/logout");

  if (response.status === 401 && !isAuthEndpoint) {
    const newToken = await handleTokenRefresh();
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      const retryResponse = await fetch(url, { ...options, headers, credentials: "include" });
      return parseResponse<T>(retryResponse);
    }
  }

  return parseResponse<T>(response);
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as unknown as T;
  }

  let data: any = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else {
    try {
      data = await response.text();
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    let code = "HTTP_ERROR";
    let details: any = undefined;
    let requestId: string | undefined =
      response.headers.get("X-Request-ID") || undefined;

    if (data && typeof data === "object") {
      if (data.error) {
        message = data.error.message || message;
        code = data.error.code || code;
        requestId = data.error.request_id || requestId;
        details = data.error.details;
      } else if (data.detail) {
        message = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
        code = "BAD_REQUEST";
      }
    }

    throw new ApiError(message, code, response.status, requestId, details);
  }

  return data as T;
}

/**
 * Mutexed token refresh preventing multiple concurrent refresh requests
 */
export async function handleTokenRefresh(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const baseUrl = getApiBaseUrl();
        const resp = await fetch(`${baseUrl}/api/v1/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({}),
        });

        if (!resp.ok) {
          setStoredAccessToken(null);
          return null;
        }

        const authData = await resp.json();
        const newToken = authData?.tokens?.access_token || null;
        setStoredAccessToken(newToken);
        return newToken;
      } catch {
        setStoredAccessToken(null);
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

// -----------------------------------------------------------------------------
// Domain Schemas & API Methods
// -----------------------------------------------------------------------------

export interface UserSummary {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  is_verified?: boolean;
  avatar_url?: string | null;
  created_at?: string;
}

export interface WorkspaceSummary {
  id: string;
  name: string;
  slug: string;
  role: string;
}

export interface AuthResponse {
  user: UserSummary;
  workspace: WorkspaceSummary | null;
  tokens: {
    access_token: string;
    token_type: string;
    expires_in_seconds: number;
  };
}

export interface UserWithWorkspacesResponse {
  user: UserSummary;
  workspaces: WorkspaceSummary[];
}

export interface ProjectResponse {
  id: string;
  workspace_id: string;
  folder_id: string | null;
  created_by: string;
  title: string;
  project_type: string;
  status: string;
  aspect_ratio: string;
  width: number;
  height: number;
  fps: number;
  duration_ms: number;
  thumbnail_asset_id: string | null;
  current_version_id: string | null;
  revision: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectDocumentV1 {
  schema_version: 1;
  settings?: {
    aspect_ratio?: string;
    width?: number;
    height?: number;
    fps?: number;
    total_duration?: number;
  };
  scenes: Array<{
    id: string;
    sequence: number;
    duration: number;
    transition?: any;
    background?: { type: string; value: string };
    avatar?: {
      avatar_id: string;
      position?: { x: number; y: number; scale: number; rotation: number };
      view_mode?: string;
    };
    speech?: {
      voice_id: string;
      script: string;
      speed?: number;
      pitch?: number;
    };
    layers?: any[];
    subtitles?: any[];
  }>;
  audio_tracks?: any[];
  assets?: any[];
  metadata?: Record<string, any>;
  [key: string]: any;
}

export interface ProjectVersionResponse {
  id: string;
  project_id: string;
  revision: number;
  document: Record<string, any>;
  source: string;
  created_by: string;
  created_at: string;
}

export interface FolderResponse {
  id: string;
  workspace_id: string;
  parent_id: string | null;
  name: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface AssetUploadIntentResponse {
  asset_id: string;
  storage_bucket: string;
  storage_key: string;
  signed_upload_url: string;
  expires_in_seconds: number;
  required_headers: Record<string, string>;
}

export interface AssetConfirmResponse {
  asset_id: string;
  status: string;
  size_bytes: number;
  mime_type: string;
}

export interface AssetResponse {
  id: string;
  workspace_id: string;
  user_id: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  asset_type: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface JobResponse {
  id: string;
  workspace_id: string;
  user_id?: string;
  created_by?: string;
  job_type: string;
  status: "queued" | "running" | "succeeded" | "completed" | "failed" | "cancelled" | string;
  stage?: string;
  stage_message?: string;
  progress_pct?: number;
  progress_percent: number;
  error_message?: string | null;
  error_details?: Record<string, any> | null;
  result?: Record<string, any> | null;
  result_payload?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface JobEventPayload {
  job_id: string;
  event_type?: string;
  status: "queued" | "running" | "succeeded" | "completed" | "failed" | "cancelled" | string;
  progress_pct: number;
  progress_percent: number;
  stage?: string;
  message?: string;
  timestamp?: string;
  result?: any;
  result_payload?: any;
  error_details?: any;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ProjectEditSuggestion {
  type: "project_edit_suggestion";
  operation: string;
  scene_id?: string | null;
  reason: string;
  proposed_value: any;
}

export interface AskRhysRequestPayload {
  message: string;
  project_id?: string | null;
  conversation_id?: string | null;
  context_mode?: "general" | "project" | "selection";
  history?: ChatMessage[];
}

export interface AskRhysResponsePayload {
  conversation_id: string;
  message: string;
  response: string;
  context_used: boolean;
  provider: string;
  model: string;
  latency_ms: number;
  suggestions: string[];
  actions: ProjectEditSuggestion[];
}

export interface ApiKeyItemResponse {
  id: string;
  workspace_id: string;
  name: string;
  prefix: string;
  environment: "production" | "sandbox";
  permissions: "full" | "read_only";
  status: string;
  expires_at?: string | null;
  last_used_at?: string | null;
  created_at: string;
}

export interface ApiKeyCreatedResponse extends ApiKeyItemResponse {
  secret_key: string;
}

export interface WebhookItemResponse {
  id: string;
  workspace_id: string;
  url: string;
  events: string[];
  status: string;
  description?: string | null;
  failure_count: number;
  created_at: string;
  updated_at: string;
}

export interface WebhookCreatedResponse {
  id: string;
  workspace_id: string;
  url: string;
  secret: string;
  events: string[];
  status: string;
  description?: string | null;
  created_at: string;
}

export interface WebhookDeliveryItemResponse {
  id: string;
  webhook_id: string;
  event_id: string;
  event_type: string;
  payload: Record<string, any>;
  response_status_code?: number | null;
  response_body?: string | null;
  latency_ms?: number | null;
  status: string;
  attempt: number;
  error_message?: string | null;
  created_at: string;
}

export const api = {
  askRhys: (
    workspaceId: string,
    payload: AskRhysRequestPayload
  ) =>
    apiRequest<AskRhysResponsePayload>(
      `/api/v1/workspaces/${workspaceId}/ask-rhys`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    ),

  auth: {

    signup: (payload: { email: string; password: string; display_name: string }) =>
      apiRequest<AuthResponse>("/api/v1/auth/signup", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    login: (payload: { email: string; password: string }) =>
      apiRequest<AuthResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    refresh: (payload?: { refresh_token?: string }) =>
      apiRequest<AuthResponse>("/api/v1/auth/refresh", {
        method: "POST",
        body: JSON.stringify(payload || {}),
      }),
    logout: () =>
      apiRequest<{ status: string; message: string }>("/api/v1/auth/logout", {
        method: "POST",
        body: JSON.stringify({}),
      }),
    getMe: () =>
      apiRequest<UserWithWorkspacesResponse>("/api/v1/auth/me", {
        method: "GET",
      }),
  },

  workspaces: {
    list: () =>
      apiRequest<WorkspaceSummary[]>("/api/v1/workspaces", { method: "GET" }),
    get: (workspaceId: string) =>
      apiRequest<WorkspaceSummary>(`/api/v1/workspaces/${workspaceId}`, { method: "GET" }),
    create: (payload: { name: string }) =>
      apiRequest<WorkspaceSummary>("/api/v1/workspaces", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    update: (workspaceId: string, payload: { name: string }) =>
      apiRequest<WorkspaceSummary>(`/api/v1/workspaces/${workspaceId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    getMembers: (workspaceId: string) =>
      apiRequest<any[]>(`/api/v1/workspaces/${workspaceId}/members`, {
        method: "GET",
      }),
    createInvitation: (
      workspaceId: string,
      payload: { email: string; role?: string }
    ) =>
      apiRequest<any>(`/api/v1/workspaces/${workspaceId}/invitations`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    listInvitations: (workspaceId: string) =>
      apiRequest<any[]>(`/api/v1/workspaces/${workspaceId}/invitations`, {
        method: "GET",
      }),
    acceptInvitation: (token: string) =>
      apiRequest<any>(`/api/v1/invitations/${token}/accept`, {
        method: "POST",
      }),
  },

  onboarding: {
    getStatus: (workspaceId: string) =>
      apiRequest<{
        step_1_digital_twin: boolean;
        step_2_voice: boolean;
        step_3_look: boolean;
        step_4_video: boolean;
        completed_steps: number[];
        completed_count: number;
        total_steps: number;
        is_step_2_unlocked: boolean;
        is_step_3_unlocked: boolean;
        is_step_4_unlocked: boolean;
      }>(`/api/v1/workspaces/${workspaceId}/onboarding`, {
        method: "GET",
      }),

    completeStep: (workspaceId: string, step: number) =>
      apiRequest<{
        step_1_digital_twin: boolean;
        step_2_voice: boolean;
        step_3_look: boolean;
        step_4_video: boolean;
        completed_steps: number[];
        completed_count: number;
        total_steps: number;
        is_step_2_unlocked: boolean;
        is_step_3_unlocked: boolean;
        is_step_4_unlocked: boolean;
      }>(`/api/v1/workspaces/${workspaceId}/onboarding/complete-step`, {
        method: "POST",
        body: JSON.stringify({ step }),
      }),
  },

  projects: {
    list: (
      workspaceId: string,
      params: {
        folder_id?: string;
        filter_folder?: boolean;
        status?: string;
        search?: string;
        limit?: number;
        offset?: number;
      } = {}
    ) => {
      const q = new URLSearchParams();
      if (params.folder_id) q.set("folder_id", params.folder_id);
      if (params.filter_folder) q.set("filter_folder", "true");
      if (params.status) q.set("status", params.status);
      if (params.search) q.set("search", params.search);
      if (params.limit) q.set("limit", String(params.limit));
      if (params.offset) q.set("offset", String(params.offset));
      const queryStr = q.toString() ? `?${q.toString()}` : "";
      return apiRequest<ProjectResponse[]>(
        `/api/v1/workspaces/${workspaceId}/projects${queryStr}`,
        { method: "GET" }
      );
    },

    get: (workspaceId: string, projectId: string) =>
      apiRequest<ProjectResponse>(
        `/api/v1/workspaces/${workspaceId}/projects/${projectId}`,
        { method: "GET" }
      ),

    create: (
      workspaceId: string,
      payload: {
        title: string;
        folder_id?: string | null;
        project_type?: string;
        aspect_ratio?: string;
        width?: number;
        height?: number;
        fps?: number;
      }
    ) =>
      apiRequest<ProjectResponse>(
        `/api/v1/workspaces/${workspaceId}/projects`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),

    update: (
      workspaceId: string,
      projectId: string,
      payload: {
        title?: string;
        folder_id?: string | null;
        status?: string;
        aspect_ratio?: string;
        thumbnail_asset_id?: string | null;
      }
    ) =>
      apiRequest<ProjectResponse>(
        `/api/v1/workspaces/${workspaceId}/projects/${projectId}`,
        {
          method: "PATCH",
          body: JSON.stringify(payload),
        }
      ),

    delete: (workspaceId: string, projectId: string) =>
      apiRequest<void>(
        `/api/v1/workspaces/${workspaceId}/projects/${projectId}`,
        { method: "DELETE" }
      ),

    listVersions: (workspaceId: string, projectId: string) =>
      apiRequest<ProjectVersionResponse[]>(
        `/api/v1/workspaces/${workspaceId}/projects/${projectId}/versions`,
        { method: "GET" }
      ),

    getVersion: (workspaceId: string, projectId: string, versionId: string) =>
      apiRequest<ProjectVersionResponse>(
        `/api/v1/workspaces/${workspaceId}/projects/${projectId}/versions/${versionId}`,
        { method: "GET" }
      ),

    createVersion: (
      workspaceId: string,
      projectId: string,
      payload: {
        expected_revision: number;
        document: Record<string, any>;
        source?: string;
      }
    ) =>
      apiRequest<ProjectVersionResponse>(
        `/api/v1/workspaces/${workspaceId}/projects/${projectId}/versions`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),

    getLatestVersion: async (workspaceId: string, projectId: string) => {
      const versions = await api.projects.listVersions(workspaceId, projectId);
      return versions[0] || null;
    },
  },

  folders: {
    list: (workspaceId: string, parentId?: string) => {
      const q = parentId ? `?parent_id=${parentId}&filter_parent=true` : "";
      return apiRequest<FolderResponse[]>(
        `/api/v1/workspaces/${workspaceId}/folders${q}`,
        { method: "GET" }
      );
    },
    create: (
      workspaceId: string,
      payload: { name: string; parent_id?: string | null }
    ) =>
      apiRequest<FolderResponse>(
        `/api/v1/workspaces/${workspaceId}/folders`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),
    update: (
      workspaceId: string,
      folderId: string,
      payload: { name?: string; parent_id?: string | null }
    ) =>
      apiRequest<FolderResponse>(
        `/api/v1/workspaces/${workspaceId}/folders/${folderId}`,
        {
          method: "PATCH",
          body: JSON.stringify(payload),
        }
      ),
    delete: (workspaceId: string, folderId: string) =>
      apiRequest<void>(
        `/api/v1/workspaces/${workspaceId}/folders/${folderId}`,
        { method: "DELETE" }
      ),
  },

  assets: {
    createUploadIntent: (
      workspaceId: string,
      payload: {
        original_filename: string;
        mime_type: string;
        size_bytes: number;
        asset_type: string;
        checksum_sha256?: string;
      }
    ) =>
      apiRequest<AssetUploadIntentResponse>(
        `/api/v1/workspaces/${workspaceId}/assets/upload-intents`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),

    /**
     * Upload binary object directly to MinIO/S3 using the pre-signed PUT URL.
     */
    uploadBinaryDirect: async (
      signedUrl: string,
      file: File | Blob,
      mimeType: string
    ): Promise<void> => {
      const resp = await fetch(signedUrl, {
        method: "PUT",
        headers: { "Content-Type": mimeType },
        body: file,
      });
      if (!resp.ok) {
        throw new ApiError(
          `MinIO storage upload failed with status ${resp.status}`,
          "STORAGE_UPLOAD_FAILED",
          resp.status
        );
      }
    },

    confirmUpload: (workspaceId: string, assetId: string) =>
      apiRequest<AssetConfirmResponse>(
        `/api/v1/workspaces/${workspaceId}/assets/${assetId}/confirm`,
        { method: "POST" }
      ),

    getDownloadUrl: (workspaceId: string, assetId: string) =>
      apiRequest<{ asset_id: string; download_url: string; expires_in_seconds: number }>(
        `/api/v1/workspaces/${workspaceId}/assets/${assetId}/download`,
        { method: "GET" }
      ),

    ingestUrl: (workspaceId: string, url: string) =>
      apiRequest<AssetResponse>(`/api/v1/workspaces/${workspaceId}/assets/ingest-url`, {
        method: "POST",
        body: JSON.stringify({ url }),
      }),

    uploadFile: async (
      workspaceId: string,
      file: File,
      assetType = "video"
    ): Promise<{ id: string; filename: string; mime_type: string }> => {
      const intent = await api.assets.createUploadIntent(workspaceId, {
        original_filename: file.name,
        mime_type: file.type || "video/mp4",
        size_bytes: file.size,
        asset_type: assetType,
      });

      await api.assets.uploadBinaryDirect(intent.signed_upload_url, file, file.type || "video/mp4");
      const confirmed = await api.assets.confirmUpload(workspaceId, intent.asset_id);
      return {
        id: confirmed.asset_id,
        filename: file.name,
        mime_type: confirmed.mime_type,
      };
    },

    list: (
      workspaceId: string,
      params: { asset_type?: string; status?: string; search?: string } = {}
    ) => {
      const q = new URLSearchParams();
      if (params.asset_type) q.set("asset_type", params.asset_type);
      if (params.status) q.set("status", params.status);
      if (params.search) q.set("search", params.search);
      const queryStr = q.toString() ? `?${q.toString()}` : "";
      return apiRequest<AssetResponse[]>(
        `/api/v1/workspaces/${workspaceId}/assets${queryStr}`,
        { method: "GET" }
      );
    },
  },

  orchestration: {
    generateProject: (
      workspaceId: string,
      payload: {
        prompt: string;
        run_async?: boolean;
        target_duration_seconds?: number;
        aspect_ratio?: string;
        avatar_id?: string;
        voice_id?: string;
        brand_kit_id?: string;
        video_tone?: string;
        auto_synthesize_speech?: boolean;
        provider?: string;
        device?: string;
      }
    ) => {
      const cleanPayload: Record<string, any> = {
        prompt: (payload.prompt || "").trim(),
        run_async: payload.run_async ?? false,
      };

      if (payload.target_duration_seconds !== undefined) {
        cleanPayload.target_duration_seconds = payload.target_duration_seconds;
      }

      if (payload.aspect_ratio) {
        const ar = payload.aspect_ratio.toLowerCase();
        if (ar === "horizontal" || ar === "landscape" || ar === "16/9") {
          cleanPayload.aspect_ratio = "16:9";
        } else if (ar === "vertical" || ar === "portrait" || ar === "9/16") {
          cleanPayload.aspect_ratio = "9:16";
        } else if (ar === "square" || ar === "1/1") {
          cleanPayload.aspect_ratio = "1:1";
        } else {
          cleanPayload.aspect_ratio = payload.aspect_ratio;
        }
      }

      if (payload.avatar_id && payload.avatar_id.trim()) {
        cleanPayload.avatar_id = payload.avatar_id.trim();
      }
      if (payload.voice_id && payload.voice_id.trim()) {
        cleanPayload.voice_id = payload.voice_id.trim();
      }
      if (payload.brand_kit_id && payload.brand_kit_id.trim()) {
        cleanPayload.brand_kit_id = payload.brand_kit_id.trim();
      }
      if (payload.video_tone && payload.video_tone.trim()) {
        cleanPayload.video_tone = payload.video_tone.trim();
      }
      if (payload.auto_synthesize_speech !== undefined) {
        cleanPayload.auto_synthesize_speech = payload.auto_synthesize_speech;
      }
      if (payload.provider && payload.provider.trim()) {
        cleanPayload.provider = payload.provider.trim();
      }
      if (payload.device && payload.device.trim()) {
        cleanPayload.device = payload.device.trim();
      }

      return apiRequest<JobResponse | ProjectResponse>(
        `/api/v1/workspaces/${workspaceId}/projects/generate`,
        {
          method: "POST",
          headers: workspaceId ? { "X-Workspace-ID": workspaceId } : {},
          body: JSON.stringify(cleanPayload),
        }
      );
    },

    synthesizeSpeech: (
      workspaceId: string,
      projectId: string,
      payload: {
        expected_revision: number;
        run_async?: boolean;
        scene_ids?: string[];
        voice_id_override?: string;
      }
    ) =>
      apiRequest<JobResponse | ProjectVersionResponse>(
        `/api/v1/workspaces/${workspaceId}/projects/${projectId}/synthesize-speech`,
        {
          method: "POST",
          body: JSON.stringify({ run_async: true, ...payload }),
        }
      ),

    translateProject: (
      workspaceId: string,
      projectId: string,
      payload: {
        target_language: string;
        target_languages?: string[];
        source_language?: string;
        target_voice_id?: string;
        video_asset_id?: string;
        enable_subtitles?: boolean;
        enable_lip_sync?: boolean;
        enable_voice_clone?: boolean;
        glossary_id?: string;
        create_fork?: boolean;
        expected_revision?: number;
        run_async?: boolean;
      }
    ) =>
      apiRequest<JobResponse | ProjectResponse | ProjectVersionResponse>(
        `/api/v1/workspaces/${workspaceId}/projects/${projectId}/translate`,
        {
          method: "POST",
          body: JSON.stringify({ run_async: true, ...payload }),
        }
      ),

    renderProject: (
      workspaceId: string,
      projectId: string,
      payload: {
        expected_revision: number;
        resolution?: "720p" | "1080p" | "4k" | string;
        fps?: number;
        format?: string;
        export_format?: "mp4" | "webm" | string;
        quality?: string;
        idempotency_key?: string;
      }
    ) =>
      apiRequest<JobResponse>(
        `/api/v1/workspaces/${workspaceId}/projects/${projectId}/render`,
        {
          method: "POST",
          body: JSON.stringify({
            expected_revision: payload.expected_revision,
            resolution: payload.resolution || "1080p",
            fps: payload.fps || 30,
            export_format: (payload.export_format || payload.format || "mp4").toLowerCase(),
            ...(payload.idempotency_key ? { idempotency_key: payload.idempotency_key } : {}),
          }),
        }
      ),

    validateTimeline: (workspaceId: string, projectId: string) =>
      apiRequest<any>(
        `/api/v1/workspaces/${workspaceId}/projects/${projectId}/validate`,
        { method: "POST" }
      ),

    transcribeAudio: (
      workspaceId: string,
      projectId: string,
      payload: {
        expected_revision: number;
        scene_id: string;
        audio_asset_id?: string;
        language?: string;
        run_async?: boolean;
      }
    ) =>
      apiRequest<JobResponse | ProjectVersionResponse>(
        `/api/v1/workspaces/${workspaceId}/projects/${projectId}/transcribe`,
        {
          method: "POST",
          body: JSON.stringify({ run_async: true, ...payload }),
        }
      ),

    generateAvatarVideo: (
      workspaceId: string,
      projectId: string,
      payload: {
        expected_revision: number;
        scene_id: string;
        avatar_id_override?: string;
        provider?: string;
        device?: string;
        run_async?: boolean;
      }
    ) =>
      apiRequest<JobResponse | ProjectVersionResponse>(
        `/api/v1/workspaces/${workspaceId}/projects/${projectId}/generate-avatar-video`,
        {
          method: "POST",
          body: JSON.stringify({ run_async: true, ...payload }),
        }
      ),
  },

  jobs: {
    get: (jobId: string) =>
      apiRequest<JobResponse>(`/api/v1/jobs/${jobId}`, { method: "GET" }),

    cancel: (jobId: string, reason?: string) => {
      const q = reason ? `?reason=${encodeURIComponent(reason)}` : "";
      return apiRequest<any>(`/api/v1/jobs/${jobId}/cancel${q}`, {
        method: "POST",
      });
    },

    /**
     * Subscribe to real-time Server-Sent Events for a background job.
     * Passes short-lived access token as query parameter for browser EventSource auth.
     * Enforces durable job state sync via GET /jobs/{id} on initial connect and reconnects.
     * Returns an unsubscribe/cleanup function.
     */
    stream: (
      jobId: string,
      onEvent: (event: JobEventPayload) => void,
      onError?: (err: any) => void
    ): (() => void) => {
      if (typeof window === "undefined") {
        return () => {};
      }

      let isClosed = false;
      const token = getStoredAccessToken();
      const q = token ? `?token=${encodeURIComponent(token)}` : "";
      const url = `${getApiBaseUrl()}/api/v1/jobs/${jobId}/stream${q}`;
      const eventSource = new EventSource(url, { withCredentials: true });

      // Durable State Initial Sync: Query current job state immediately in case it completed before EventSource opened
      api.jobs
        .get(jobId)
        .then((job) => {
          if (isClosed) return;
          const normalized: JobEventPayload = {
            job_id: job.id,
            event_type: "initial_sync",
            status: job.status,
            progress_pct: job.progress_percent ?? 0,
            progress_percent: job.progress_percent ?? 0,
            stage: job.stage || undefined,
            message: job.stage_message || undefined,
            timestamp: job.updated_at,
            result: job.result,
            result_payload: job.result,
            error_details: job.error_details,
          };
          onEvent(normalized);
          if (
            job.status === "succeeded" ||
            job.status === "completed" ||
            job.status === "failed" ||
            job.status === "cancelled"
          ) {
            isClosed = true;
            eventSource.close();
          }
        })
        .catch(() => {
          // Non-fatal, stream will continue
        });

      eventSource.onmessage = (event) => {
        if (isClosed) return;
        try {
          const raw = JSON.parse(event.data);
          const normalizedStatus = raw.status === "succeeded" ? "succeeded" : raw.status;
          const progress =
            raw.progress_percent !== undefined
              ? raw.progress_percent
              : raw.progress_pct ?? 0;
          const resultData = raw.result !== undefined ? raw.result : raw.result_payload;

          const normalized: JobEventPayload = {
            job_id: raw.job_id || jobId,
            event_type: raw.event_type || raw.stage || "progress",
            status: normalizedStatus,
            progress_pct: progress,
            progress_percent: progress,
            stage: raw.stage,
            message: raw.message || raw.stage_message,
            timestamp: raw.timestamp,
            result: resultData,
            result_payload: resultData,
            error_details: raw.error_details,
          };
          onEvent(normalized);

          // If terminal status reached, automatically close
          if (
            normalized.status === "succeeded" ||
            normalized.status === "completed" ||
            normalized.status === "failed" ||
            normalized.status === "cancelled"
          ) {
            isClosed = true;
            eventSource.close();
          }
        } catch {
          // ignore non-JSON keepalive/ping comments
        }
      };

      eventSource.onerror = (err) => {
        if (isClosed) return;
        // On connection drop or error, query durable backend state
        api.jobs
          .get(jobId)
          .then((job) => {
            if (isClosed) return;
            const normalized: JobEventPayload = {
              job_id: job.id,
              event_type: "reconnect_poll",
              status: job.status,
              progress_pct: job.progress_percent ?? 0,
              progress_percent: job.progress_percent ?? 0,
              stage: job.stage || undefined,
              message: job.stage_message || undefined,
              timestamp: job.updated_at,
              result: job.result,
              result_payload: job.result,
              error_details: job.error_details,
            };
            onEvent(normalized);
            if (
              job.status === "succeeded" ||
              job.status === "completed" ||
              job.status === "failed" ||
              job.status === "cancelled"
            ) {
              isClosed = true;
              eventSource.close();
            }
          })
          .catch(() => {
            if (onError) onError(err);
          });
      };

      return () => {
        isClosed = true;
        eventSource.close();
      };
    },
  },

  creative: {
    listAvatars: (
      params: { avatar_type?: string; search?: string } = {},
      workspaceId?: string
    ) => {
      const q = new URLSearchParams();
      if (params.avatar_type) q.set("avatar_type", params.avatar_type);
      if (params.search) q.set("search", params.search);
      const queryStr = q.toString() ? `?${q.toString()}` : "";
      return apiRequest<any[]>(`/api/v1/avatars${queryStr}`, {
        method: "GET",
        headers: workspaceId ? { "X-Workspace-ID": workspaceId } : {},
      });
    },

    listAvatarLooks: (avatarId: string, workspaceId?: string) =>
      apiRequest<any[]>(`/api/v1/avatars/${avatarId}/looks`, {
        method: "GET",
        headers: workspaceId ? { "X-Workspace-ID": workspaceId } : {},
      }),

    createAvatar: (
      payload: {
        name: string;
        description?: string;
        avatar_type?: string;
        visibility?: string;
        provider?: string;
        provider_reference?: string;
        provider_metadata?: Record<string, any>;
      },
      workspaceId?: string
    ) =>
      apiRequest<any>("/api/v1/avatars", {
        method: "POST",
        body: JSON.stringify(payload),
        headers: workspaceId ? { "X-Workspace-ID": workspaceId } : {},
      }),

    createAvatarLook: (
      avatarId: string,
      payload: {
        name: string;
        description?: string;
        configuration?: Record<string, any>;
      },
      workspaceId?: string
    ) =>
      apiRequest<any>(`/api/v1/avatars/${avatarId}/looks`, {
        method: "POST",
        body: JSON.stringify(payload),
        headers: workspaceId ? { "X-Workspace-ID": workspaceId } : {},
      }),

    listVoices: (
      params: { language?: string; gender?: string; search?: string } = {},
      workspaceId?: string
    ) => {
      const q = new URLSearchParams();
      if (params.language) q.set("language", params.language);
      if (params.gender) q.set("gender", params.gender);
      if (params.search) q.set("search", params.search);
      const queryStr = q.toString() ? `?${q.toString()}` : "";
      return apiRequest<any[]>(`/api/v1/voices${queryStr}`, {
        method: "GET",
        headers: workspaceId ? { "X-Workspace-ID": workspaceId } : {},
      });
    },

    getVoicePreview: (voiceId: string, workspaceId?: string) =>
      apiRequest<{
        voice_id: string;
        preview_asset_id?: string;
        preview_url: string;
        provider: string;
        status: string;
        expires_in_seconds: number;
      }>(`/api/v1/voices/${voiceId}/preview`, {
        method: "GET",
        headers: workspaceId ? { "X-Workspace-ID": workspaceId } : {},
      }),

    createVoice: (
      payload: {
        name: string;
        description?: string;
        voice_type?: string;
        language?: string;
        gender?: string;
        provider?: string;
      },
      workspaceId?: string
    ) =>
      apiRequest<any>("/api/v1/voices", {
        method: "POST",
        body: JSON.stringify(payload),
        headers: workspaceId ? { "X-Workspace-ID": workspaceId } : {},
      }),

    cloneVoice: (
      workspaceId: string,
      payload: {
        name: string;
        reference_asset_id: string;
        language?: string;
        description?: string;
        gender?: string;
        options?: Record<string, any>;
      }
    ) =>
      apiRequest<{
        job_id: string;
        voice_id: string;
        status: string;
        voice_name: string;
        workspace_id: string;
        created_at: string;
      }>(`/api/v1/workspaces/${workspaceId}/voices/clone`, {
        method: "POST",
        body: JSON.stringify(payload),
        headers: { "X-Workspace-ID": workspaceId },
      }),

    listTemplates: (
      params: { category?: string; search?: string } = {},
      workspaceId?: string
    ) => {
      const q = new URLSearchParams();
      if (params.category) q.set("category", params.category);
      if (params.search) q.set("search", params.search);
      const queryStr = q.toString() ? `?${q.toString()}` : "";
      return apiRequest<any[]>(`/api/v1/templates${queryStr}`, {
        method: "GET",
        headers: workspaceId ? { "X-Workspace-ID": workspaceId } : {},
      });
    },

    instantiateTemplate: (
      templateId: string,
      title?: string,
      workspaceId?: string
    ) => {
      const q = title ? `?title=${encodeURIComponent(title)}` : "";
      return apiRequest<ProjectResponse>(
        `/api/v1/templates/${templateId}/instantiate${q}`,
        {
          method: "POST",
          headers: workspaceId ? { "X-Workspace-ID": workspaceId } : {},
        }
      );
    },
  },

  brandKits: {
    list: (workspaceId?: string, limit = 50, offset = 0) => {
      const headers: Record<string, string> = {};
      if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
      return apiRequest<BrandKitItemResponse[]>(
        `/api/v1/brand-kits?limit=${limit}&offset=${offset}`,
        { method: "GET", headers }
      );
    },

    get: (kitId: string, workspaceId?: string) => {
      const headers: Record<string, string> = {};
      if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
      return apiRequest<BrandKitItemResponse>(
        `/api/v1/brand-kits/${kitId}`,
        { method: "GET", headers }
      );
    },

    create: (payload: any, workspaceId?: string) => {
      const headers: Record<string, string> = {};
      if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
      return apiRequest<BrandKitItemResponse>(
        `/api/v1/brand-kits`,
        { method: "POST", headers, body: JSON.stringify(payload) }
      );
    },

    update: (kitId: string, payload: any, workspaceId?: string) => {
      const headers: Record<string, string> = {};
      if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
      return apiRequest<BrandKitItemResponse>(
        `/api/v1/brand-kits/${kitId}`,
        { method: "PATCH", headers, body: JSON.stringify(payload) }
      );
    },

    delete: (kitId: string, workspaceId?: string) => {
      const headers: Record<string, string> = {};
      if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
      return apiRequest<void>(
        `/api/v1/brand-kits/${kitId}`,
        { method: "DELETE", headers }
      );
    },
  },

  brandGlossaries: {
    list: (workspaceId?: string, limit = 50, offset = 0) => {
      const headers: Record<string, string> = {};
      if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
      return apiRequest<BrandGlossaryItemResponse[]>(
        `/api/v1/brand-glossaries?limit=${limit}&offset=${offset}`,
        { method: "GET", headers }
      );
    },

    get: (glossaryId: string, workspaceId?: string) => {
      const headers: Record<string, string> = {};
      if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
      return apiRequest<BrandGlossaryItemResponse>(
        `/api/v1/brand-glossaries/${glossaryId}`,
        { method: "GET", headers }
      );
    },

    create: (payload: any, workspaceId?: string) => {
      const headers: Record<string, string> = {};
      if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
      return apiRequest<BrandGlossaryItemResponse>(
        `/api/v1/brand-glossaries`,
        { method: "POST", headers, body: JSON.stringify(payload) }
      );
    },

    update: (glossaryId: string, payload: any, workspaceId?: string) => {
      const headers: Record<string, string> = {};
      if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
      return apiRequest<BrandGlossaryItemResponse>(
        `/api/v1/brand-glossaries/${glossaryId}`,
        { method: "PATCH", headers, body: JSON.stringify(payload) }
      );
    },

    delete: (glossaryId: string, workspaceId?: string) => {
      const headers: Record<string, string> = {};
      if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
      return apiRequest<void>(
        `/api/v1/brand-glossaries/${glossaryId}`,
        { method: "DELETE", headers }
      );
    },

    listRules: (glossaryId: string, workspaceId?: string) => {
      const headers: Record<string, string> = {};
      if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
      return apiRequest<BrandGlossaryRuleItemResponse[]>(
        `/api/v1/brand-glossaries/${glossaryId}/rules`,
        { method: "GET", headers }
      );
    },

    createRule: (glossaryId: string, payload: any, workspaceId?: string) => {
      const headers: Record<string, string> = {};
      if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
      return apiRequest<BrandGlossaryRuleItemResponse>(
        `/api/v1/brand-glossaries/${glossaryId}/rules`,
        { method: "POST", headers, body: JSON.stringify(payload) }
      );
    },

    updateRule: (ruleId: string, payload: any, workspaceId?: string) => {
      const headers: Record<string, string> = {};
      if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
      return apiRequest<BrandGlossaryRuleItemResponse>(
        `/api/v1/brand-glossary-rules/${ruleId}`,
        { method: "PATCH", headers, body: JSON.stringify(payload) }
      );
    },

    deleteRule: (glossaryId: string, ruleId: string, workspaceId?: string) => {
      const headers: Record<string, string> = {};
      if (workspaceId) headers["X-Workspace-ID"] = workspaceId;
      return apiRequest<void>(
        `/api/v1/brand-glossaries/${glossaryId}/rules/${ruleId}`,
        { method: "DELETE", headers }
      );
    },
  },

  developer: {
    listApiKeys: (workspaceId: string, limit = 50, offset = 0) =>
      apiRequest<{ items: ApiKeyItemResponse[]; total: number }>(
        `/api/v1/workspaces/${workspaceId}/developer/api-keys?limit=${limit}&offset=${offset}`,
        { method: "GET" }
      ),

    createApiKey: (
      workspaceId: string,
      payload: {
        name: string;
        environment?: "production" | "sandbox";
        permissions?: "full" | "read_only";
        expires_in_days?: number | null;
      }
    ) =>
      apiRequest<ApiKeyCreatedResponse>(
        `/api/v1/workspaces/${workspaceId}/developer/api-keys`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),

    revokeApiKey: (workspaceId: string, keyId: string) =>
      apiRequest<ApiKeyItemResponse>(
        `/api/v1/workspaces/${workspaceId}/developer/api-keys/${keyId}`,
        { method: "DELETE" }
      ),

    listWebhooks: (workspaceId: string, statusFilter?: string) =>
      apiRequest<{ items: WebhookItemResponse[]; total: number }>(
        `/api/v1/workspaces/${workspaceId}/developer/webhooks${statusFilter ? `?status=${statusFilter}` : ""}`,
        { method: "GET" }
      ),

    createWebhook: (
      workspaceId: string,
      payload: {
        url: string;
        events?: string[];
        description?: string;
      }
    ) =>
      apiRequest<WebhookCreatedResponse>(
        `/api/v1/workspaces/${workspaceId}/developer/webhooks`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),

    updateWebhook: (
      workspaceId: string,
      webhookId: string,
      payload: {
        url?: string;
        events?: string[];
        status?: "active" | "disabled" | "revoked";
        description?: string;
      }
    ) =>
      apiRequest<WebhookItemResponse>(
        `/api/v1/workspaces/${workspaceId}/developer/webhooks/${webhookId}`,
        {
          method: "PATCH",
          body: JSON.stringify(payload),
        }
      ),

    deleteWebhook: (workspaceId: string, webhookId: string) =>
      apiRequest<void>(
        `/api/v1/workspaces/${workspaceId}/developer/webhooks/${webhookId}`,
        { method: "DELETE" }
      ),

    testWebhook: (workspaceId: string, webhookId: string) =>
      apiRequest<{ status: string; event_id: string; destination_url: string }>(
        `/api/v1/workspaces/${workspaceId}/developer/webhooks/${webhookId}/test`,
        { method: "POST" }
      ),

    listWebhookDeliveries: (
      workspaceId: string,
      webhookId: string,
      limit = 50,
      offset = 0
    ) =>
      apiRequest<{ items: WebhookDeliveryItemResponse[]; total: number }>(
        `/api/v1/workspaces/${workspaceId}/developer/webhooks/${webhookId}/deliveries?limit=${limit}&offset=${offset}`,
        { method: "GET" }
      ),
  },
};


