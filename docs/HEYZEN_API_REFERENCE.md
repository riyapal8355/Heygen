# HeyZen REST API Reference (Complete Inventory)

This document provides the definitive, comprehensive API reference for the HeyZen autonomous AI video backend.
All endpoints are generated directly from the live FastAPI OpenAPI specification (`/openapi.json`) and route inventory (`route_inventory.json`).

## Overview & Standards
- **Base URL**: `http://127.0.0.1:8000` (development) or configured production reverse proxy.
- **API Version Prefix**: `/api/v1` for versioned application endpoints; root level for health probes (`/health`, `/ready`).
- **Authentication**: HTTP Bearer JWT tokens in `Authorization: Bearer <token>` header, or HttpOnly cookie `hz_refresh_token` for rotation.
- **Workspace Multi-Tenancy**: All project, asset, avatar, voice, job, and developer operations require workspace context via `{workspace_id}` path parameter.
- **Optimistic Concurrency Control (OCC)**: Mutation endpoints on projects and versions enforce integer `expected_revision` to eliminate overwrite races.
- **Standard Response Wrappers**: Consistent JSON envelopes; errors follow `APIErrorResponse` with structured error codes.

### Global Error Response Schema (`APIErrorResponse`)
```json
{
  "error": {
    "code": "ERROR_CODE_STRING",
    "message": "Human readable message",
    "request_id": "req_xxxxxxxxxxxx",
    "details": {}
  }
}
```

### Summary Table
| Group | Endpoints | Authentication |
|---|---|---|
| [Health, Diagnostics & Probes](#health-diagnostics--probes) | 8 | Mixed |
| [Authentication & Session Management](#authentication--session-management) | 5 | Mixed |
| [Workspaces & Membership Management](#workspaces--membership-management) | 11 | Bearer / Protected |
| [Workspace Invitations](#workspace-invitations) | 4 | Bearer / Protected |
| [Folders](#folders) | 5 | Bearer / Protected |
| [Projects & Version Snapshots (OCC)](#projects--version-snapshots-occ) | 9 | Bearer / Protected |
| [Project Orchestration (Video Agent, Speech, Translation & Render)](#project-orchestration-video-agent-speech-translation--render) | 9 | Bearer / Protected |
| [Assets & Object Storage](#assets--object-storage) | 7 | Bearer / Protected |
| [Avatars & Digital Twin Looks](#avatars--digital-twin-looks) | 10 | Bearer / Protected |
| [Voices & Voice Cloning](#voices--voice-cloning) | 8 | Bearer / Protected |
| [Templates](#templates) | 9 | Bearer / Protected |
| [Brand Kits & Terminology Glossaries](#brand-kits--terminology-glossaries) | 17 | Bearer / Protected |
| [Jobs & Real-time SSE Streaming](#jobs--real-time-sse-streaming) | 6 | Bearer / Protected |
| [Developer API Keys & Webhooks](#developer-api-keys--webhooks) | 11 | Bearer / Protected |
| [Ask Rhys AI Copilot](#ask-rhys-ai-copilot) | 2 | Bearer / Protected |

## Health, Diagnostics & Probes
*Total Endpoints: 8*

### 1. `GET` /api/v1/health
**Summary**: Application Liveness Probe  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `get_health_api_v1_health_get`  

**Purpose**:
Returns HTTP 200 if the FastAPI application process is alive.

**Parameters**: None

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `HealthResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(optional)*, default: `ok` — Liveness status indicator
- `app` (string) *(required)* — Application name
- `version` (string) *(required)* — Application version
  </details>

**Possible Error Codes**:
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 2. `GET` /api/v1/health/ai
**Summary**: AI Runtime & Capability Health Probe  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `get_ai_health_api_v1_health_ai_get`  

**Purpose**:
Reports host hardware detection, compute runtimes (CPU/GPU), and AI capability statuses.

**Parameters**: None

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `AIHealthResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(required)* — Overall AI subsystem operational health
- `mode` (string) *(required)* — AI runtime mode: mock or real
- `hardware` (object) *(required)* — Host hardware specifications
- `runtimes` (object) *(required)* — Compute runtimes health states (cpu, gpu)
- `capabilities` (object) *(required)* — Per-capability status
- `gpu_worker` (object) *(optional)* — GPU worker and queue status
  </details>

**Possible Error Codes**:
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 3. `GET` /api/v1/metrics
**Summary**: Application Operational Metrics  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `get_metrics_api_v1_metrics_get`  

**Purpose**:
Returns runtime metrics, API request counts, job transitions, and subsystem errors.

**Parameters**: None

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `object`: Snapshot of application runtime metrics counters, latency histograms, and worker statistics.

**Possible Error Codes**:
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 4. `GET` /api/v1/ready
**Summary**: Application Readiness Probe  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `get_readiness_api_v1_ready_get`  

**Purpose**:
Verifies operational connectivity to PostgreSQL, Redis, and MinIO/S3 storage.

**Parameters**: None

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `ReadinessResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(required)* — Readiness status: 'ready' or 'unhealthy'
- `checks` (object) *(required)* — Dependency health statuses: database, redis, storage
  </details>

**Possible Error Codes**:
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 5. `GET` /health
**Summary**: Application Liveness Probe  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `get_health_health_get`  

**Purpose**:
Returns HTTP 200 if the FastAPI application process is alive.

**Parameters**: None

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `HealthResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(optional)*, default: `ok` — Liveness status indicator
- `app` (string) *(required)* — Application name
- `version` (string) *(required)* — Application version
  </details>

**Possible Error Codes**:
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 6. `GET` /health/ai
**Summary**: AI Runtime & Capability Health Probe  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `get_ai_health_health_ai_get`  

**Purpose**:
Reports host hardware detection, compute runtimes (CPU/GPU), and AI capability statuses.

**Parameters**: None

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `AIHealthResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(required)* — Overall AI subsystem operational health
- `mode` (string) *(required)* — AI runtime mode: mock or real
- `hardware` (object) *(required)* — Host hardware specifications
- `runtimes` (object) *(required)* — Compute runtimes health states (cpu, gpu)
- `capabilities` (object) *(required)* — Per-capability status
- `gpu_worker` (object) *(optional)* — GPU worker and queue status
  </details>

**Possible Error Codes**:
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 7. `GET` /metrics
**Summary**: Application Operational Metrics  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `get_metrics_metrics_get`  

**Purpose**:
Returns runtime metrics, API request counts, job transitions, and subsystem errors.

**Parameters**: None

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `object`: Snapshot of application runtime metrics counters, latency histograms, and worker statistics.

**Possible Error Codes**:
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 8. `GET` /ready
**Summary**: Application Readiness Probe  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `get_readiness_ready_get`  

**Purpose**:
Verifies operational connectivity to PostgreSQL, Redis, and MinIO/S3 storage.

**Parameters**: None

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `ReadinessResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(required)* — Readiness status: 'ready' or 'unhealthy'
- `checks` (object) *(required)* — Dependency health statuses: database, redis, storage
  </details>

**Possible Error Codes**:
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Authentication & Session Management
*Total Endpoints: 5*

### 9. `POST` /api/v1/auth/login
**Summary**: User Authentication  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `login_api_v1_auth_login_post`  

**Purpose**:
Authenticates credentials, starts a new session, and sets an HttpOnly refresh cookie.

**Parameters**: None

**Request Body** (`application/json`): `LoginRequest`
- `email` (string) *(required)* — Registered user email
- `password` (string) *(required)* — User password

**Responses**:
- **HTTP 200** — Model: `AuthResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `user` (object) *(required)*
  - `id` (string) *(required)*
  - `email` (string) *(required)*
  - `display_name` (string) *(required)*
  - `status` (string) *(required)*
  - `avatar_url` (object) *(optional)*
  - `created_at` (string) *(required)*
  - `updated_at` (string) *(required)*
  - `last_login_at` (object) *(optional)*
- `workspace` (object) *(optional)*
- `tokens` (object) *(required)*
  - `access_token` (string) *(required)*
  - `token_type` (string) *(optional)*, default: `bearer`
  - `expires_in_seconds` (integer) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 10. `POST` /api/v1/auth/logout
**Summary**: User Logout  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `logout_api_v1_auth_logout_post`  

**Purpose**:
Invalidates current refresh token session and clears the HttpOnly auth cookie.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `heyzen_refresh_token` | cookie | string | No |  |

**Request Body** (`application/json`): `custom`
- Raw binary payload or unstructured object.

**Responses**:
- **HTTP 200** — Model: `LogoutResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(optional)*, default: `ok` — Status confirmation
- `message` (string) *(optional)*, default: `Logged out successfully.` — Logout message
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 11. `GET` /api/v1/auth/me
**Summary**: Current Authenticated User Profile  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_me_api_v1_auth_me_get`  

**Purpose**:
Returns the profile and workspace memberships of the authenticated user.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `UserWithWorkspacesResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `user` (object) *(required)*
  - `id` (string) *(required)*
  - `email` (string) *(required)*
  - `display_name` (string) *(required)*
  - `status` (string) *(required)*
  - `avatar_url` (object) *(optional)*
  - `created_at` (string) *(required)*
  - `updated_at` (string) *(required)*
  - `last_login_at` (object) *(optional)*
- `workspaces` (array) *(required)*
  - *Item properties:*
    - `id` (string) *(required)*
    - `name` (string) *(required)*
    - `slug` (string) *(required)*
    - `role` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 12. `POST` /api/v1/auth/refresh
**Summary**: Rotate Session & Access Token  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `refresh_tokens_api_v1_auth_refresh_post`  

**Purpose**:
Rotates the refresh token (session rotation) and issues a new access token.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `heyzen_refresh_token` | cookie | string | No |  |

**Request Body** (`application/json`): `custom`
- Raw binary payload or unstructured object.

**Responses**:
- **HTTP 200** — Model: `AuthResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `user` (object) *(required)*
  - `id` (string) *(required)*
  - `email` (string) *(required)*
  - `display_name` (string) *(required)*
  - `status` (string) *(required)*
  - `avatar_url` (object) *(optional)*
  - `created_at` (string) *(required)*
  - `updated_at` (string) *(required)*
  - `last_login_at` (object) *(optional)*
- `workspace` (object) *(optional)*
- `tokens` (object) *(required)*
  - `access_token` (string) *(required)*
  - `token_type` (string) *(optional)*, default: `bearer`
  - `expires_in_seconds` (integer) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 13. `POST` /api/v1/auth/signup
**Summary**: User Registration  
**Classification**: A. Public application API | **Auth Required**: No (Public)  
**Operation ID**: `signup_api_v1_auth_signup_post`  

**Purpose**:
Atomically registers a new user, creates a personal workspace, and sets an HttpOnly refresh cookie.

**Parameters**: None

**Request Body** (`application/json`): `SignupRequest`
- `email` (string) *(required)* — Valid user email address
- `display_name` (string) *(required)* — User's display name
- `password` (string) *(required)* — Password (minimum 8 characters)

**Responses**:
- **HTTP 201** — Model: `AuthResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `user` (object) *(required)*
  - `id` (string) *(required)*
  - `email` (string) *(required)*
  - `display_name` (string) *(required)*
  - `status` (string) *(required)*
  - `avatar_url` (object) *(optional)*
  - `created_at` (string) *(required)*
  - `updated_at` (string) *(required)*
  - `last_login_at` (object) *(optional)*
- `workspace` (object) *(optional)*
- `tokens` (object) *(required)*
  - `access_token` (string) *(required)*
  - `token_type` (string) *(optional)*, default: `bearer`
  - `expires_in_seconds` (integer) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Workspaces & Membership Management
*Total Endpoints: 11*

### 14. `GET` /api/v1/workspaces
**Summary**: List User Workspaces  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_workspaces_api_v1_workspaces_get`  

**Purpose**:
Lists all workspaces the authenticated user belongs to.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 15. `POST` /api/v1/workspaces
**Summary**: Create Workspace  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_workspace_api_v1_workspaces_post`  

**Purpose**:
Creates a new workspace tenant and assigns the authenticated user as Owner.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |

**Request Body** (`application/json`): `WorkspaceCreate`
- `name` (string) *(required)* — Organization or workspace title

**Responses**:
- **HTTP 201** — Model: `WorkspaceResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `name` (string) *(required)*
- `slug` (string) *(required)*
- `owner_id` (string) *(required)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `role` (object) *(optional)* — Caller's role in this workspace
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 16. `DELETE` /api/v1/workspaces/{workspace_id}
**Summary**: Soft-Delete Workspace  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_workspace_api_v1_workspaces__workspace_id__delete`  

**Purpose**:
Marks workspace as deleted. Requires 'workspace.delete' (Owner only).

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 17. `GET` /api/v1/workspaces/{workspace_id}
**Summary**: Get Workspace Details  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_workspace_api_v1_workspaces__workspace_id__get`  

**Purpose**:
Fetch details of a specific workspace. Caller must be an active member.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `WorkspaceResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `name` (string) *(required)*
- `slug` (string) *(required)*
- `owner_id` (string) *(required)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `role` (object) *(optional)* — Caller's role in this workspace
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 18. `PATCH` /api/v1/workspaces/{workspace_id}
**Summary**: Update Workspace  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_workspace_api_v1_workspaces__workspace_id__patch`  

**Purpose**:
Update workspace title or status. Requires 'workspace.update' permission.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `WorkspaceUpdate`
- `name` (object) *(optional)*
- `status` (object) *(optional)* — Workspace status: active, suspended

**Responses**:
- **HTTP 200** — Model: `WorkspaceResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `name` (string) *(required)*
- `slug` (string) *(required)*
- `owner_id` (string) *(required)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `role` (object) *(optional)* — Caller's role in this workspace
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 19. `GET` /api/v1/workspaces/{workspace_id}/members
**Summary**: List Workspace Members  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_members_api_v1_workspaces__workspace_id__members_get`  

**Purpose**:
List all members of the workspace. Requires 'workspace.read' permission.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 20. `DELETE` /api/v1/workspaces/{workspace_id}/members/{user_id}
**Summary**: Remove Workspace Member  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `remove_member_api_v1_workspaces__workspace_id__members__user_id__delete`  

**Purpose**:
Removes a member from the workspace. Owner cannot be removed.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `user_id` | path | string | Yes | Target Workspace Member User UUID |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 21. `PATCH` /api/v1/workspaces/{workspace_id}/members/{user_id}
**Summary**: Update Member Role  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_member_role_api_v1_workspaces__workspace_id__members__user_id__patch`  

**Purpose**:
Update a member's role. Requires 'workspace.manage_members' permission.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `user_id` | path | string | Yes | Target Workspace Member User UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `WorkspaceMemberUpdate`
- `role` (string) *(required)* — Supported workspace collaboration roles in descending hierarchy order.

**Responses**:
- **HTTP 200** — Model: `WorkspaceMemberResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `user_id` (string) *(required)*
- `email` (string) *(required)*
- `display_name` (string) *(required)*
- `avatar_url` (object) *(optional)*
- `role` (string) *(required)*
- `status` (string) *(required)*
- `joined_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 22. `GET` /api/v1/workspaces/{workspace_id}/onboarding
**Summary**: Get Onboarding Setup Status  
**Classification**: Application API | **Auth Required**: Protected (HTTPBearer)  
**Operation ID**: `get_onboarding_status_api_v1_workspaces__workspace_id__onboarding_get`  

**Purpose**:
Retrieves the 4-step account setup progress derived from real workspace entity state.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `OnboardingStatusResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `step_1_digital_twin` (boolean) *(required)* — Whether Digital Twin has been created
- `step_2_voice` (boolean) *(required)* — Whether Voice has been polished/cloned
- `step_3_look` (boolean) *(required)* — Whether a Look has been created
- `step_4_video` (boolean) *(required)* — Whether first video project has been created
- `completed_steps` (array) *(optional)* — Array of completed step numbers (1-4)
- `completed_count` (integer) *(required)* — Number of completed steps (0-4)
- `total_steps` (integer) *(optional)*, default: `4` — Total number of setup steps
- `is_step_2_unlocked` (boolean) *(required)* — Whether Step 2 is unlocked (requires Step 1)
- `is_step_3_unlocked` (boolean) *(required)* — Whether Step 3 is unlocked (requires Step 1)
- `is_step_4_unlocked` (boolean) *(required)* — Whether Step 4 is unlocked (requires Step 2 or 3)
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 23. `POST` /api/v1/workspaces/{workspace_id}/onboarding/complete-step
**Summary**: Complete Onboarding Step  
**Classification**: Application API | **Auth Required**: Protected (HTTPBearer)  
**Operation ID**: `complete_onboarding_step_api_v1_workspaces__workspace_id__onboarding_complete_step_post`  

**Purpose**:
Explicitly completes an onboarding step and ensures required workspace entity records exist.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `None`
- `step` (integer) *(required)* — Step number (1-4) to complete

**Responses**:
- **HTTP 200** — Model: `OnboardingStatusResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `step_1_digital_twin` (boolean) *(required)* — Whether Digital Twin has been created
- `step_2_voice` (boolean) *(required)* — Whether Voice has been polished/cloned
- `step_3_look` (boolean) *(required)* — Whether a Look has been created
- `step_4_video` (boolean) *(required)* — Whether first video project has been created
- `completed_steps` (array) *(optional)* — Array of completed step numbers (1-4)
- `completed_count` (integer) *(required)* — Number of completed steps (0-4)
- `total_steps` (integer) *(optional)*, default: `4` — Total number of setup steps
- `is_step_2_unlocked` (boolean) *(required)* — Whether Step 2 is unlocked (requires Step 1)
- `is_step_3_unlocked` (boolean) *(required)* — Whether Step 3 is unlocked (requires Step 1)
- `is_step_4_unlocked` (boolean) *(required)* — Whether Step 4 is unlocked (requires Step 2 or 3)
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 24. `POST` /api/v1/workspaces/{workspace_id}/transfer-ownership
**Summary**: Transfer Workspace Ownership  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `transfer_ownership_api_v1_workspaces__workspace_id__transfer_ownership_post`  

**Purpose**:
Atomically transfers workspace ownership to another active member. Owner only.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `TransferOwnershipRequest`
- `target_user_id` (string) *(required)* — Target member user ID to receive workspace ownership

**Responses**:
- **HTTP 200** — Model: `WorkspaceResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `name` (string) *(required)*
- `slug` (string) *(required)*
- `owner_id` (string) *(required)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `role` (object) *(optional)* — Caller's role in this workspace
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Workspace Invitations
*Total Endpoints: 4*

### 25. `POST` /api/v1/invitations/{token}/accept
**Summary**: Accept Workspace Invitation  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `accept_invitation_api_v1_invitations__token__accept_post`  

**Purpose**:
Redeems an invitation token and adds the authenticated user to the workspace with the invited role.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `token` | path | string | Yes | Invitation secret token |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `InvitationAcceptResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `workspace` (object) *(required)*
  - `id` (string) *(required)*
  - `name` (string) *(required)*
  - `slug` (string) *(required)*
  - `owner_id` (string) *(required)*
  - `status` (string) *(required)*
  - `created_at` (string) *(required)*
  - `updated_at` (string) *(required)*
  - `role` (object) *(optional)* — Caller's role in this workspace
- `role` (string) *(required)*
- `message` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 26. `GET` /api/v1/workspaces/{workspace_id}/invitations
**Summary**: List Pending Invitations  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_invitations_api_v1_workspaces__workspace_id__invitations_get`  

**Purpose**:
Lists pending invitations. Requires 'workspace.manage_members'.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 27. `POST` /api/v1/workspaces/{workspace_id}/invitations
**Summary**: Invite Member  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_invitation_api_v1_workspaces__workspace_id__invitations_post`  

**Purpose**:
Creates an invitation. Returns token only in development/testing mode.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `WorkspaceInvitationCreate`
- `email` (string) *(required)* — Invitee's email address
- `role` (string) *(optional)*, default: `creator` — Supported workspace collaboration roles in descending hierarchy order.

**Responses**:
- **HTTP 201** — Model: `WorkspaceInvitationResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `email` (string) *(required)*
- `role` (string) *(required)*
- `status` (string) *(required)*
- `expires_at` (string) *(required)*
- `created_at` (string) *(required)*
- `invitation_token` (object) *(optional)* — Plaintext redemption token (Returned ONLY in development/testing)
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 28. `POST` /api/v1/workspaces/{workspace_id}/invitations/{invitation_id}/revoke
**Summary**: Revoke Invitation  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `revoke_invitation_api_v1_workspaces__workspace_id__invitations__invitation_id__revoke_post`  

**Purpose**:
Revokes an unaccepted invitation. Requires 'workspace.manage_members'.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `invitation_id` | path | string | Yes | Target Invitation UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `WorkspaceRevokeResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(optional)*, default: `ok` — Revocation status
- `message` (string) *(optional)*, default: `Invitation revoked successfully.` — Status message
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Folders
*Total Endpoints: 5*

### 29. `GET` /api/v1/workspaces/{workspace_id}/folders
**Summary**: List Folders  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_folders_api_v1_workspaces__workspace_id__folders_get`  

**Purpose**:
Lists active folders in the workspace, optionally filtering by parent folder.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `parent_id` | query | string | No | Filter by parent folder ID |
| `filter_parent` | query | boolean | No | Whether to filter explicitly by parent_id |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 30. `POST` /api/v1/workspaces/{workspace_id}/folders
**Summary**: Create Folder  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_folder_api_v1_workspaces__workspace_id__folders_post`  

**Purpose**:
Creates a new organizational folder within the active workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `FolderCreate`
- `name` (string) *(required)* — Folder display name
- `parent_id` (object) *(optional)* — Optional parent folder UUID

**Responses**:
- **HTTP 201** — Model: `FolderResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `parent_id` (object) *(optional)*
- `name` (string) *(required)*
- `created_by` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 31. `DELETE` /api/v1/workspaces/{workspace_id}/folders/{folder_id}
**Summary**: Delete Folder  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_folder_api_v1_workspaces__workspace_id__folders__folder_id__delete`  

**Purpose**:
Soft-deletes an empty folder. Fails with 409 if folder contains children or projects.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `folder_id` | path | string | Yes | Target Folder UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 32. `GET` /api/v1/workspaces/{workspace_id}/folders/{folder_id}
**Summary**: Get Folder  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_folder_api_v1_workspaces__workspace_id__folders__folder_id__get`  

**Purpose**:
Fetches details of a specific workspace folder.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `folder_id` | path | string | Yes | Target Folder UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `FolderResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `parent_id` (object) *(optional)*
- `name` (string) *(required)*
- `created_by` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 33. `PATCH` /api/v1/workspaces/{workspace_id}/folders/{folder_id}
**Summary**: Update Folder  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_folder_api_v1_workspaces__workspace_id__folders__folder_id__patch`  

**Purpose**:
Renames or moves a folder to a new parent location.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `folder_id` | path | string | Yes | Target Folder UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `FolderUpdate`
- `name` (object) *(optional)* — Updated name
- `parent_id` (object) *(optional)* — New parent folder UUID for moves

**Responses**:
- **HTTP 200** — Model: `FolderResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `parent_id` (object) *(optional)*
- `name` (string) *(required)*
- `created_by` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Projects & Version Snapshots (OCC)
*Total Endpoints: 9*

### 34. `GET` /api/v1/workspaces/{workspace_id}/projects
**Summary**: List Projects  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_projects_api_v1_workspaces__workspace_id__projects_get`  

**Purpose**:
Lists active projects in the workspace with optional folder, status, and title filtering.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `folder_id` | query | string | No | Filter by folder ID |
| `filter_folder` | query | boolean | No | Whether to filter explicitly by folder_id |
| `status` | query | string | No | Filter by status: draft, processing, ready, archived |
| `search` | query | string | No | Search by title keyword |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 35. `POST` /api/v1/workspaces/{workspace_id}/projects
**Summary**: Create Project  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_project_api_v1_workspaces__workspace_id__projects_post`  

**Purpose**:
Initializes a new video project with default ProjectDocumentV1 at revision 1.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `ProjectCreate`
- `title` (string) *(required)* — Project title
- `folder_id` (object) *(optional)* — Optional target folder UUID
- `project_type` (string) *(optional)*, default: `standard` — standard, avatar_video, agent, translation, template_based
- `aspect_ratio` (string) *(optional)*, default: `16:9` — 16:9, 9:16, 1:1
- `width` (integer) *(optional)*, default: `1920`
- `height` (integer) *(optional)*, default: `1080`
- `fps` (integer) *(optional)*, default: `30`

**Responses**:
- **HTTP 201** — Model: `ProjectResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `folder_id` (object) *(optional)*
- `created_by` (string) *(required)*
- `title` (string) *(required)*
- `project_type` (string) *(required)*
- `status` (string) *(required)*
- `aspect_ratio` (string) *(required)*
- `width` (object) *(optional)*
- `height` (object) *(optional)*
- `fps` (object) *(optional)*
- `duration_ms` (object) *(optional)*
- `thumbnail_asset_id` (object) *(optional)*
- `current_version_id` (object) *(optional)*
- `revision` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 36. `DELETE` /api/v1/workspaces/{workspace_id}/projects/{project_id}
**Summary**: Delete Project  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_project_api_v1_workspaces__workspace_id__projects__project_id__delete`  

**Purpose**:
Soft-deletes a project and removes it from normal query results.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 37. `GET` /api/v1/workspaces/{workspace_id}/projects/{project_id}
**Summary**: Get Project  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_project_api_v1_workspaces__workspace_id__projects__project_id__get`  

**Purpose**:
Fetches metadata summary for a single project.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `ProjectResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `folder_id` (object) *(optional)*
- `created_by` (string) *(required)*
- `title` (string) *(required)*
- `project_type` (string) *(required)*
- `status` (string) *(required)*
- `aspect_ratio` (string) *(required)*
- `width` (object) *(optional)*
- `height` (object) *(optional)*
- `fps` (object) *(optional)*
- `duration_ms` (object) *(optional)*
- `thumbnail_asset_id` (object) *(optional)*
- `current_version_id` (object) *(optional)*
- `revision` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 38. `PATCH` /api/v1/workspaces/{workspace_id}/projects/{project_id}
**Summary**: Update Project Metadata  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_project_api_v1_workspaces__workspace_id__projects__project_id__patch`  

**Purpose**:
Updates project title, folder assignment, status, or thumbnail poster.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `ProjectUpdate`
- `title` (object) *(optional)*
- `folder_id` (object) *(optional)*
- `status` (object) *(optional)* — draft, processing, ready, archived
- `aspect_ratio` (object) *(optional)*
- `thumbnail_asset_id` (object) *(optional)*

**Responses**:
- **HTTP 200** — Model: `ProjectResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `folder_id` (object) *(optional)*
- `created_by` (string) *(required)*
- `title` (string) *(required)*
- `project_type` (string) *(required)*
- `status` (string) *(required)*
- `aspect_ratio` (string) *(required)*
- `width` (object) *(optional)*
- `height` (object) *(optional)*
- `fps` (object) *(optional)*
- `duration_ms` (object) *(optional)*
- `thumbnail_asset_id` (object) *(optional)*
- `current_version_id` (object) *(optional)*
- `revision` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 39. `GET` /api/v1/workspaces/{workspace_id}/projects/{project_id}/versions
**Summary**: List Project Versions  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_project_versions_api_v1_workspaces__workspace_id__projects__project_id__versions_get`  

**Purpose**:
Lists chronological version history snapshots for a project.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 409`: `CONCURRENCY_CONFLICT` (revision mismatch under OCC)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 40. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/versions
**Summary**: Save New Project Version (Optimistic Concurrency)  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_project_version_api_v1_workspaces__workspace_id__projects__project_id__versions_post`  

**Purpose**:
Saves a new immutable project version. Fails with 409 Conflict if expected_revision does not match.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateProjectVersionRequest`
- `expected_revision` (integer) *(required)* — Current revision caller expects to update
- `document` (object) *(required)* — Canonical HeyZen Project Document specification (Version 1).
  - `schema_version` (integer) *(optional)*, default: `1` — Schema version tag (must be 1 for V1)
  - `settings` (object) *(optional)* — Core timeline and render canvas configuration.
    - `aspect_ratio` (string) *(optional)*, default: `16:9` — Canvas ratio: 16:9, 9:16, 1:1, etc.
    - `width` (integer) *(optional)*, default: `1920` — Pixel width
    - `height` (integer) *(optional)*, default: `1080` — Pixel height
    - `fps` (integer) *(optional)*, default: `30` — Render framerate
    - `total_duration` (number) *(optional)*, default: `0.0` — Computed runtime in seconds
    - `captions` (object) *(optional)* — Project-level caption toggle and styling configuration.
      - `enabled` (boolean) *(optional)*, default: `True` — Whether subtitles/captions are displayed and burned
      - `style` (object) *(optional)* — Visual typography and placement styling for burned/displayed subtitles.
  - `scenes` (array) *(optional)*
    - *Item properties:*
      - `id` (string) *(required)* — Unique scene UUID/string
      - `sequence` (integer) *(required)* — 1-indexed sequence order
      - `duration` (number) *(optional)*, default: `5.0` — Scene length in seconds
      - `transition` (object) *(optional)*
      - `camera_motion` (object) *(optional)*, default: `static` — Camera movement: static, slow_zoom_in, slow_zoom_out, pan_left, pan_right, presenter_closeup, presenter_medium, presenter_wide
      - `background` (object) *(optional)*
      - `avatar` (object) *(optional)*
      - `speech` (object) *(optional)*
      - `layers` (array) *(optional)*
        - *Item properties:*

      - `subtitles` (array) *(optional)* — Timestamped speech transcription cues: [{'id': int, 'start': float, 'end': float, 'text': str, 'words': [...]}]
  - `audio_tracks` (array) *(optional)*
    - *Item properties:*
      - `id` (string) *(required)* — Unique track ID
      - `asset_id` (object) *(optional)* — Reference to assets.id in object storage
      - `name` (string) *(optional)*, default: `Audio Track`
      - `volume` (number) *(optional)*, default: `1.0`
      - `start_time` (number) *(optional)*, default: `0.0`
      - `duration` (object) *(optional)*
      - `fade_in_duration` (number) *(optional)*, default: `0.0`
      - `fade_out_duration` (number) *(optional)*, default: `0.0`
      - `loop` (boolean) *(optional)*, default: `False`
      - `muted` (boolean) *(optional)*, default: `False` — Whether audio track is muted
  - `assets` (array) *(optional)*
    - *Item properties:*
      - `asset_id` (string) *(required)* — UUID string of the asset
      - `asset_type` (string) *(required)* — image, video, audio, font, other
      - `storage_key` (object) *(optional)*
  - `metadata` (object) *(optional)*
- `source` (object) *(optional)*, default: `manual` — manual, autosave, template, agent, import

**Responses**:
- **HTTP 201** — Model: `ProjectVersionResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `project_id` (string) *(required)*
- `revision` (integer) *(required)*
- `document` (object) *(required)* — Project document snapshot
- `source` (string) *(required)*
- `created_by` (string) *(required)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 409`: `CONCURRENCY_CONFLICT` (revision mismatch under OCC)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 41. `GET` /api/v1/workspaces/{workspace_id}/projects/{project_id}/versions/latest
**Summary**: Get Latest Project Version Snapshot  
**Classification**: Application API | **Auth Required**: Protected (HTTPBearer)  
**Operation ID**: `get_latest_project_version_api_v1_workspaces__workspace_id__projects__project_id__versions_latest_get`  

**Purpose**:
Fetches full ProjectDocument JSON for the latest project version snapshot.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `ProjectVersionResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `project_id` (string) *(required)*
- `revision` (integer) *(required)*
- `document` (object) *(required)* — Project document snapshot
- `source` (string) *(required)*
- `created_by` (string) *(required)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 409`: `CONCURRENCY_CONFLICT` (revision mismatch under OCC)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 42. `GET` /api/v1/workspaces/{workspace_id}/projects/{project_id}/versions/{version_id}
**Summary**: Get Project Version Snapshot  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_project_version_api_v1_workspaces__workspace_id__projects__project_id__versions__version_id__get`  

**Purpose**:
Fetches full ProjectDocument JSON for an immutable version snapshot.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `version_id` | path | string | Yes | Target Project Version UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `ProjectVersionResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `project_id` (string) *(required)*
- `revision` (integer) *(required)*
- `document` (object) *(required)* — Project document snapshot
- `source` (string) *(required)*
- `created_by` (string) *(required)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 409`: `CONCURRENCY_CONFLICT` (revision mismatch under OCC)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Project Orchestration (Video Agent, Speech, Translation & Render)
*Total Endpoints: 9*

### 43. `POST` /api/v1/workspaces/{workspace_id}/projects/generate
**Summary**: Generate Project from Prompt  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `generate_project_api_v1_workspaces__workspace_id__projects_generate_post`  

**Purpose**:
Video Agent endpoint decomposing a natural language prompt into an initialized multi-scene project. Supports async Celery execution (HTTP 202) or synchronous return (HTTP 201).

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `GenerateProjectRequest`
- `prompt` (string) *(required)* — Natural language project prompt
- `target_duration_seconds` (object) *(optional)*, default: `30.0` — Desired total video duration
- `aspect_ratio` (string) *(optional)*, default: `16:9` — Aspect ratio canvas format
- `avatar_id` (object) *(optional)* — Optional default catalog avatar ID
- `voice_id` (object) *(optional)* — Optional default catalog voice ID
- `brand_kit_id` (object) *(optional)* — Optional brand kit for color scheme and styling
- `video_tone` (string) *(optional)*, default: `Professional` — Video tone (Professional, Energetic, Casual, Educational)
- `auto_synthesize_speech` (boolean) *(optional)*, default: `False` — Whether to kick off async speech synthesis immediately
- `run_async` (boolean) *(optional)*, default: `False` — Whether to run generation asynchronously via Celery job
- `provider` (object) *(optional)* — Optional LLM provider override ('qwen', 'mock')
- `device` (object) *(optional)* — Optional compute device override ('cpu', 'cuda')
- `idempotency_key` (object) *(optional)* — Optional idempotency key for async task deduplication

**Responses**:
- **HTTP 201**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 44. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/enhance-speech
**Summary**: Enhance Speech Audio and Studio Cleanup  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `enhance_speech_api_v1_workspaces__workspace_id__projects__project_id__enhance_speech_post`  

**Purpose**:
Enhances scene speech audio (noise suppression, pause trimming, broadcast mastering). Async returns HTTP 202 JobResponse; sync returns HTTP 200 ProjectVersionResponse.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `EnhanceProjectSpeechRequest`
- `expected_revision` (integer) *(required)* — Required current project revision for optimistic concurrency check
- `scene_id` (object) *(optional)* — Optional target scene ID; if None, targets all scenes with speech
- `denoise` (boolean) *(optional)*, default: `True` — Enable neural noise suppression
- `remove_silence` (boolean) *(optional)*, default: `False` — Enable Silero VAD dead-pause trimming
- `remove_fillers` (boolean) *(optional)*, default: `False` — Filler removal toggle (disabled/NOT_IMPLEMENTED)
- `master_audio` (boolean) *(optional)*, default: `True` — Apply broadcast EQ, compression, and loudness mastering
- `provider` (object) *(optional)* — Optional provider override ('deepfilter' or 'mock')
- `run_async` (boolean) *(optional)*, default: `True` — Canonical execution mode: async via Celery job (HTTP 202)
- `idempotency_key` (object) *(optional)* — Optional idempotency key for deduplication

**Responses**:
- **HTTP 202**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 45. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/generate-avatar-video
**Summary**: Synthesize Talking Avatar Video  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `generate_avatar_video_api_v1_workspaces__workspace_id__projects__project_id__generate_avatar_video_post`  

**Purpose**:
Synthesizes neural lip-synced avatar video for a project scene. Async returns HTTP 202 JobResponse; sync returns HTTP 200 ProjectVersionResponse.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `GenerateAvatarVideoRequest`
- `expected_revision` (integer) *(required)* — Required current project revision for optimistic concurrency check
- `scene_id` (object) *(optional)* — Optional target scene ID; if None, targets first scene with avatar
- `avatar_id_override` (object) *(optional)* — Optional avatar ID or asset ID override
- `provider` (object) *(optional)* — Optional provider override ('wav2lip', 'musetalk', 'mock')
- `device` (object) *(optional)* — Optional device target ('cpu', 'cuda')
- `run_async` (boolean) *(optional)*, default: `True` — Canonical execution mode: async via Celery job (HTTP 202)
- `idempotency_key` (object) *(optional)* — Optional idempotency key for deduplication

**Responses**:
- **HTTP 202**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 46. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/render
**Summary**: Export Video Render  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `render_project_api_v1_workspaces__workspace_id__projects__project_id__render_post`  

**Purpose**:
Freezes exact expected_revision, performs pre-flight validation, and dispatches composite render job.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `RenderProjectRequest`
- `resolution` (string) *(optional)*, default: `1080p` — Output render resolution
- `fps` (integer) *(optional)*, default: `30` — Video framerate
- `export_format` (string) *(optional)*, default: `mp4` — Output video format
- `expected_revision` (integer) *(required)* — Required exact project revision to freeze and render
- `idempotency_key` (object) *(optional)* — Optional idempotency key

**Responses**:
- **HTTP 202** — Model: `JobResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `job_type` (string) *(required)*
- `status` (string) *(required)*
- `priority` (integer) *(required)*
- `idempotency_key` (object) *(optional)*
- `progress_percent` (integer) *(required)*
- `stage` (object) *(optional)*
- `stage_message` (object) *(optional)*
- `payload` (object) *(required)*
- `result` (object) *(optional)*
- `error_details` (object) *(optional)*
- `celery_task_id` (object) *(optional)*
- `retry_count` (integer) *(required)*
- `max_retries` (integer) *(required)*
- `started_at` (object) *(optional)*
- `completed_at` (object) *(optional)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 409`: `CONCURRENCY_CONFLICT` (revision mismatch under OCC)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 47. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/scenes/{scene_id}/generate-visual
**Summary**: Generate Scene Visual  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `generate_scene_visual_api_v1_workspaces__workspace_id__projects__project_id__scenes__scene_id__generate_visual_post`  

**Purpose**:
Generates AI background image or b-roll video for a target scene layer.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `scene_id` | path | string | Yes | Target Scene Identifier |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `GenerateSceneVisualRequest`
- `visual_type` (string) *(optional)*, default: `image` — Visual media type to generate
- `prompt` (string) *(required)* — Visual description prompt
- `aspect_ratio` (string) *(optional)*, default: `16:9` — Asset aspect ratio
- `expected_revision` (integer) *(required)* — Required current revision for optimistic concurrency check
- `provider` (object) *(optional)* — Optional provider override ('stable_diffusion' or 'mock')
- `negative_prompt` (object) *(optional)* — Excluded visual concepts
- `seed` (object) *(optional)* — Deterministic generation seed
- `run_async` (boolean) *(optional)*, default: `True` — Canonical execution mode: async via Celery job
- `idempotency_key` (object) *(optional)* — Optional idempotency key

**Responses**:
- **HTTP 202**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 48. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/synthesize-speech
**Summary**: Synthesize Timeline Speech  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `synthesize_speech_api_v1_workspaces__workspace_id__projects__project_id__synthesize_speech_post`  

**Purpose**:
Synthesizes speech audio for scenes. Canonically async (HTTP 202 JobResponse); sync for tests.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `SynthesizeProjectSpeechRequest`
- `scene_ids` (object) *(optional)* — Target scene IDs; None means all scenes with speech text
- `expected_revision` (integer) *(required)* — Required current revision for optimistic concurrency check
- `voice_id_override` (object) *(optional)* — Optional voice ID override for target scenes
- `run_async` (boolean) *(optional)*, default: `True` — Canonical execution mode: async via Celery job
- `idempotency_key` (object) *(optional)* — Optional idempotency key for async task deduplication

**Responses**:
- **HTTP 202**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 49. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/transcribe
**Summary**: Transcribe Project Audio to Subtitles  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `transcribe_project_audio_api_v1_workspaces__workspace_id__projects__project_id__transcribe_post`  

**Purpose**:
Transcribes scene speech audio into structured subtitle cues. Async returns HTTP 202 JobResponse; sync returns HTTP 200 ProjectVersionResponse.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `TranscribeProjectAudioRequest`
- `expected_revision` (integer) *(required)* — Required current project revision for optimistic concurrency check
- `scene_id` (object) *(optional)* — Optional target scene ID; if None, targets first scene with audio
- `audio_asset_id` (object) *(optional)* — Optional direct audio asset ID override
- `language` (object) *(optional)* — Optional language hint (e.g. 'en')
- `provider` (object) *(optional)* — Optional provider override ('whisper' or 'mock')
- `run_async` (boolean) *(optional)*, default: `True` — Canonical execution mode: async via Celery job
- `idempotency_key` (object) *(optional)* — Optional idempotency key for deduplication

**Responses**:
- **HTTP 202**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 50. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/translate
**Summary**: Translate Project Timeline  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `translate_project_api_v1_workspaces__workspace_id__projects__project_id__translate_post`  

**Purpose**:
Translates multi-scene scripts with Brand Glossary compliance. Returns JobResponse or localized project.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `TranslateProjectRequest`
- `target_language` (string) *(optional)*, default: `es` — Target language code (e.g. 'es', 'fr', 'de')
- `target_languages` (object) *(optional)* — Optional multi-language targets for multi-output translation
- `source_language` (string) *(optional)*, default: `en` — Source language code
- `target_voice_id` (object) *(optional)* — Optional voice ID matching target language
- `video_asset_id` (object) *(optional)* — Optional source video asset UUID for direct video dubbing
- `enable_subtitles` (boolean) *(optional)*, default: `True` — Generate and embed translated subtitles
- `enable_lip_sync` (boolean) *(optional)*, default: `False` — Apply lip-sync synchronization
- `enable_voice_clone` (boolean) *(optional)*, default: `False` — Apply voice cloning to target audio
- `glossary_id` (object) *(optional)* — Brand Glossary UUID to enforce
- `create_fork` (boolean) *(optional)*, default: `True` — Create new project fork vs new version on same project
- `expected_revision` (object) *(optional)* — Required when create_fork=False
- `run_async` (boolean) *(optional)*, default: `True` — Canonical execution mode: async via Celery job
- `idempotency_key` (object) *(optional)* — Optional idempotency key

**Responses**:
- **HTTP 202**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 51. `POST` /api/v1/workspaces/{workspace_id}/projects/{project_id}/validate
**Summary**: Validate Project Timeline  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `validate_timeline_api_v1_workspaces__workspace_id__projects__project_id__validate_post`  

**Purpose**:
Synchronous pre-flight diagnostics evaluating whether project is ready for rendering.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `project_id` | path | string | Yes | Target Project UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `TimelineValidationResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `is_valid` (boolean) *(required)* — Whether project passes all pre-flight checks
- `scene_count` (integer) *(required)* — Number of scenes in the project timeline
- `total_duration` (number) *(required)* — Calculated total duration in seconds
- `errors` (array) *(optional)* — Fatal blocking issues that prevent rendering
- `warnings` (array) *(optional)* — Non-blocking recommendations
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 404`: `PROJECT_NOT_FOUND` (target project does not exist)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Assets & Object Storage
*Total Endpoints: 7*

### 52. `GET` /api/v1/workspaces/{workspace_id}/assets
**Summary**: List Workspace Assets  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_assets_api_v1_workspaces__workspace_id__assets_get`  

**Purpose**:
Lists active assets with optional filtering by asset type, status, or filename.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `asset_type` | query | string | No | Filter by category: image, video, audio, etc. |
| `status` | query | string | No | Filter by lifecycle state |
| `search` | query | string | No | Keyword search in original filename |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 53. `POST` /api/v1/workspaces/{workspace_id}/assets/ingest-url
**Summary**: Ingest Video from URL  
**Classification**: Application API | **Auth Required**: Protected (HTTPBearer)  
**Operation ID**: `ingest_video_url_api_v1_workspaces__workspace_id__assets_ingest_url_post`  

**Purpose**:
Ingests a video from a remote URL (YouTube, Google Drive, direct MP4) into MinIO object storage.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `None`
- `url` (string) *(required)* — Public video URL

**Responses**:
- **HTTP 201** — Model: `AssetResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `original_filename` (string) *(required)*
- `storage_bucket` (string) *(required)*
- `storage_key` (string) *(required)*
- `mime_type` (string) *(required)*
- `size_bytes` (object) *(optional)*
- `checksum_sha256` (object) *(optional)*
- `asset_type` (string) *(required)*
- `status` (string) *(required)*
- `metadata` (object) *(optional)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 54. `POST` /api/v1/workspaces/{workspace_id}/assets/upload-intents
**Summary**: Create Upload Intent  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_upload_intent_api_v1_workspaces__workspace_id__assets_upload_intents_post`  

**Purpose**:
Registers upload intent and generates a pre-signed PUT URL for direct MinIO/S3 upload.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `AssetUploadIntentRequest`
- `original_filename` (string) *(required)*
- `mime_type` (string) *(required)*
- `size_bytes` (object) *(optional)* — Expected file size in bytes
- `asset_type` (string) *(optional)*, default: `other` — Generic category: image, video, audio, document, font, other
- `checksum_sha256` (object) *(optional)* — Claimed SHA-256 digest of binary content

**Responses**:
- **HTTP 201** — Model: `AssetUploadIntentResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `asset_id` (string) *(required)*
- `storage_bucket` (string) *(required)*
- `storage_key` (string) *(required)*
- `signed_upload_url` (string) *(required)*
- `expires_in_seconds` (integer) *(required)*
- `required_headers` (object) *(optional)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 55. `DELETE` /api/v1/workspaces/{workspace_id}/assets/{asset_id}
**Summary**: Delete Asset  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_asset_api_v1_workspaces__workspace_id__assets__asset_id__delete`  

**Purpose**:
Soft-deletes asset record from database. Physical object cleanup is scheduled asynchronously.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `asset_id` | path | string | Yes | Target Asset UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 56. `GET` /api/v1/workspaces/{workspace_id}/assets/{asset_id}
**Summary**: Get Asset Metadata  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_asset_api_v1_workspaces__workspace_id__assets__asset_id__get`  

**Purpose**:
Fetches metadata record for an individual asset.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `asset_id` | path | string | Yes | Target Asset UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `AssetResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `original_filename` (string) *(required)*
- `storage_bucket` (string) *(required)*
- `storage_key` (string) *(required)*
- `mime_type` (string) *(required)*
- `size_bytes` (object) *(optional)*
- `checksum_sha256` (object) *(optional)*
- `asset_type` (string) *(required)*
- `status` (string) *(required)*
- `metadata` (object) *(optional)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 57. `POST` /api/v1/workspaces/{workspace_id}/assets/{asset_id}/confirm
**Summary**: Confirm Asset Upload  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `confirm_asset_upload_api_v1_workspaces__workspace_id__assets__asset_id__confirm_post`  

**Purpose**:
Verifies the uploaded binary object in storage and transitions status to 'ready'.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `asset_id` | path | string | Yes | Target Asset UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `AssetConfirmResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `asset_id` (string) *(required)*
- `status` (string) *(required)*
- `size_bytes` (object) *(optional)*
- `mime_type` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 58. `GET` /api/v1/workspaces/{workspace_id}/assets/{asset_id}/download
**Summary**: Get Signed Download URL  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_asset_download_url_api_v1_workspaces__workspace_id__assets__asset_id__download_get`  

**Purpose**:
Generates a secure pre-signed GET URL for direct asset consumption from storage.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `asset_id` | path | string | Yes | Target Asset UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `AssetDownloadResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `asset_id` (string) *(required)*
- `download_url` (string) *(required)*
- `expires_in_seconds` (integer) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Avatars & Digital Twin Looks
*Total Endpoints: 10*

### 59. `GET` /api/v1/avatars
**Summary**: List Avatars  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_avatars_api_v1_avatars_get`  

**Purpose**:
Lists active avatars in the active workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_type` | query | string | No |  |
| `status` | query | string | No |  |
| `search` | query | string | No |  |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 60. `POST` /api/v1/avatars
**Summary**: Create Avatar  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_avatar_api_v1_avatars_post`  

**Purpose**:
Initializes a new avatar in the active workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateAvatarRequest`
- `name` (string) *(required)* — Avatar name
- `description` (object) *(optional)*
- `avatar_type` (object) *(optional)*, default: `custom`
- `visibility` (object) *(optional)*, default: `workspace`
- `provider` (object) *(optional)*, default: `mock`
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(optional)*
- `preview_asset_id` (object) *(optional)*
- `source_asset_id` (object) *(optional)*
- `initial_look` (object) *(optional)*

**Responses**:
- **HTTP 201** — Model: `AvatarResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `avatar_type` (string) *(required)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `source_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `looks` (array) *(optional)*
  - *Item properties:*
    - `id` (string) *(required)*
    - `avatar_id` (string) *(required)*
    - `name` (string) *(required)*
    - `description` (object) *(optional)*
    - `status` (string) *(required)*
    - `configuration` (object) *(required)*
    - `preview_asset_id` (object) *(optional)*
    - `preview_url` (object) *(optional)*
    - `provider` (string) *(required)*
    - `provider_reference` (object) *(optional)*
    - `created_at` (string) *(required)*
    - `updated_at` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 61. `DELETE` /api/v1/avatars/{avatar_id}
**Summary**: Delete Avatar  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_avatar_api_v1_avatars__avatar_id__delete`  

**Purpose**:
Soft-deletes an avatar record.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_id` | path | string | Yes | Target Avatar UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 62. `GET` /api/v1/avatars/{avatar_id}
**Summary**: Get Avatar  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_avatar_api_v1_avatars__avatar_id__get`  

**Purpose**:
Fetches an avatar and its looks by ID.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_id` | path | string | Yes | Target Avatar UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `AvatarResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `avatar_type` (string) *(required)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `source_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `looks` (array) *(optional)*
  - *Item properties:*
    - `id` (string) *(required)*
    - `avatar_id` (string) *(required)*
    - `name` (string) *(required)*
    - `description` (object) *(optional)*
    - `status` (string) *(required)*
    - `configuration` (object) *(required)*
    - `preview_asset_id` (object) *(optional)*
    - `preview_url` (object) *(optional)*
    - `provider` (string) *(required)*
    - `provider_reference` (object) *(optional)*
    - `created_at` (string) *(required)*
    - `updated_at` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 63. `PATCH` /api/v1/avatars/{avatar_id}
**Summary**: Update Avatar  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_avatar_api_v1_avatars__avatar_id__patch`  

**Purpose**:
Updates avatar metadata, status, or asset references.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_id` | path | string | Yes | Target Avatar UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `UpdateAvatarRequest`
- `name` (object) *(optional)*
- `description` (object) *(optional)*
- `avatar_type` (object) *(optional)*
- `status` (object) *(optional)*
- `visibility` (object) *(optional)*
- `provider` (object) *(optional)*
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(optional)*
- `preview_asset_id` (object) *(optional)*
- `source_asset_id` (object) *(optional)*

**Responses**:
- **HTTP 200** — Model: `AvatarResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `avatar_type` (string) *(required)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `source_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `looks` (array) *(optional)*
  - *Item properties:*
    - `id` (string) *(required)*
    - `avatar_id` (string) *(required)*
    - `name` (string) *(required)*
    - `description` (object) *(optional)*
    - `status` (string) *(required)*
    - `configuration` (object) *(required)*
    - `preview_asset_id` (object) *(optional)*
    - `preview_url` (object) *(optional)*
    - `provider` (string) *(required)*
    - `provider_reference` (object) *(optional)*
    - `created_at` (string) *(required)*
    - `updated_at` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 64. `GET` /api/v1/avatars/{avatar_id}/looks
**Summary**: List Avatar Looks  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_avatar_looks_api_v1_avatars__avatar_id__looks_get`  

**Purpose**:
Lists all visual presentation looks for an avatar.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_id` | path | string | Yes | Target Avatar UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 65. `POST` /api/v1/avatars/{avatar_id}/looks
**Summary**: Create Avatar Look  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_avatar_look_api_v1_avatars__avatar_id__looks_post`  

**Purpose**:
Adds a new visual look/pose to an avatar.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_id` | path | string | Yes | Target Avatar UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateAvatarLookRequest`
- `name` (string) *(required)* — Look display name
- `description` (object) *(optional)*
- `configuration` (object) *(optional)* — Pose, framing, style options
- `preview_asset_id` (object) *(optional)* — Look preview asset reference
- `provider` (object) *(optional)*, default: `mock`
- `provider_reference` (object) *(optional)*

**Responses**:
- **HTTP 201** — Model: `AvatarLookResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `avatar_id` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `status` (string) *(required)*
- `configuration` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 66. `DELETE` /api/v1/avatars/{avatar_id}/looks/{look_id}
**Summary**: Delete Avatar Look  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_avatar_look_api_v1_avatars__avatar_id__looks__look_id__delete`  

**Purpose**:
Deletes a visual look from an avatar.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_id` | path | string | Yes | Target Avatar UUID |
| `look_id` | path | string | Yes | Target Avatar Look UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 67. `GET` /api/v1/avatars/{avatar_id}/looks/{look_id}
**Summary**: Get Avatar Look  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_avatar_look_api_v1_avatars__avatar_id__looks__look_id__get`  

**Purpose**:
Fetches a specific avatar look by ID.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_id` | path | string | Yes | Target Avatar UUID |
| `look_id` | path | string | Yes | Target Avatar Look UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `AvatarLookResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `avatar_id` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `status` (string) *(required)*
- `configuration` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 68. `PATCH` /api/v1/avatars/{avatar_id}/looks/{look_id}
**Summary**: Update Avatar Look  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_avatar_look_api_v1_avatars__avatar_id__looks__look_id__patch`  

**Purpose**:
Updates look configuration, styling, or preview asset.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `avatar_id` | path | string | Yes | Target Avatar UUID |
| `look_id` | path | string | Yes | Target Avatar Look UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `UpdateAvatarLookRequest`
- `name` (object) *(optional)*
- `description` (object) *(optional)*
- `status` (object) *(optional)*
- `configuration` (object) *(optional)*
- `preview_asset_id` (object) *(optional)*
- `provider` (object) *(optional)*
- `provider_reference` (object) *(optional)*

**Responses**:
- **HTTP 200** — Model: `AvatarLookResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `avatar_id` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `status` (string) *(required)*
- `configuration` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Voices & Voice Cloning
*Total Endpoints: 8*

### 69. `GET` /api/v1/voices
**Summary**: List Voices  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_voices_api_v1_voices_get`  

**Purpose**:
Lists active voices in the workspace with filtering.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `language` | query | string | No |  |
| `gender` | query | string | No |  |
| `voice_type` | query | string | No |  |
| `status` | query | string | No |  |
| `search` | query | string | No |  |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 70. `POST` /api/v1/voices
**Summary**: Create Voice  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_voice_api_v1_voices_post`  

**Purpose**:
Registers a new speech synthesis voice in the workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateVoiceRequest`
- `name` (string) *(required)* — Voice display name
- `description` (object) *(optional)*
- `voice_type` (object) *(optional)*, default: `custom`
- `language` (object) *(optional)*, default: `en`
- `gender` (object) *(optional)*, default: `neutral`
- `provider` (object) *(optional)*, default: `mock`
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(optional)*
- `preview_asset_id` (object) *(optional)*
- `visibility` (object) *(optional)*, default: `workspace`

**Responses**:
- **HTTP 201** — Model: `VoiceResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `voice_type` (string) *(required)*
- `language` (string) *(required)*
- `gender` (string) *(required)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 71. `POST` /api/v1/voices/clone
**Summary**: Clone Voice (Header-scoped)  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `clone_voice_header_api_v1_voices_clone_post`  

**Purpose**:
Initiates asynchronous zero-shot voice cloning from a reference audio asset.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `VoiceCloneRequest`
- `name` (string) *(required)* — Display name for the cloned voice
- `reference_asset_id` (string) *(required)* — ID of the audio Asset to use as reference speaker sample
- `language` (object) *(optional)*, default: `en` — Target language code (e.g., 'en', 'es', 'zh')
- `description` (object) *(optional)* — Optional description of voice style/tone
- `gender` (object) *(optional)*, default: `neutral` — Perceived voice gender (male, female, neutral)
- `options` (object) *(optional)* — Additional model inference options

**Responses**:
- **HTTP 202** — Model: `VoiceCloneJobResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `job_id` (string) *(required)* — Durable job tracking ID
- `voice_id` (string) *(required)* — Pre-allocated voice record ID
- `status` (string) *(required)* — Current job status (queued, running, etc.)
- `voice_name` (string) *(required)* — Cloned voice name
- `workspace_id` (string) *(required)* — Owning workspace ID
- `created_at` (string) *(required)* — Creation timestamp
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 72. `DELETE` /api/v1/voices/{voice_id}
**Summary**: Delete Voice  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_voice_api_v1_voices__voice_id__delete`  

**Purpose**:
Soft-deletes a voice.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `voice_id` | path | string | Yes | Target Voice Catalog UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 73. `GET` /api/v1/voices/{voice_id}
**Summary**: Get Voice  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_voice_api_v1_voices__voice_id__get`  

**Purpose**:
Fetches a specific voice by ID.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `voice_id` | path | string | Yes | Target Voice Catalog UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `VoiceResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `voice_type` (string) *(required)*
- `language` (string) *(required)*
- `gender` (string) *(required)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 74. `PATCH` /api/v1/voices/{voice_id}
**Summary**: Update Voice  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_voice_api_v1_voices__voice_id__patch`  

**Purpose**:
Updates voice metadata, language, or preview sample asset.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `voice_id` | path | string | Yes | Target Voice Catalog UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `UpdateVoiceRequest`
- `name` (object) *(optional)*
- `description` (object) *(optional)*
- `voice_type` (object) *(optional)*
- `language` (object) *(optional)*
- `gender` (object) *(optional)*
- `provider` (object) *(optional)*
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(optional)*
- `preview_asset_id` (object) *(optional)*
- `status` (object) *(optional)*
- `visibility` (object) *(optional)*

**Responses**:
- **HTTP 200** — Model: `VoiceResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `voice_type` (string) *(required)*
- `language` (string) *(required)*
- `gender` (string) *(required)*
- `provider` (string) *(required)*
- `provider_reference` (object) *(optional)*
- `provider_metadata` (object) *(required)*
- `preview_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 75. `GET` /api/v1/voices/{voice_id}/preview
**Summary**: Get Voice Preview Audio  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_voice_preview_api_v1_voices__voice_id__preview_get`  

**Purpose**:
Generates a signed URL for direct audio playback of the voice preview sample.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `voice_id` | path | string | Yes | Target Voice Catalog UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `VoicePreviewResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `voice_id` (string) *(required)*
- `preview_asset_id` (object) *(optional)*
- `preview_url` (object) *(optional)*
- `provider` (string) *(required)*
- `status` (string) *(required)*
- `expires_in_seconds` (integer) *(optional)*, default: `3600`
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 76. `POST` /api/v1/workspaces/{workspace_id}/voices/clone
**Summary**: Clone Voice (Workspace-scoped)  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `clone_voice_workspace_api_v1_workspaces__workspace_id__voices_clone_post`  

**Purpose**:
Initiates asynchronous zero-shot voice cloning from a reference audio asset in the workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `VoiceCloneRequest`
- `name` (string) *(required)* — Display name for the cloned voice
- `reference_asset_id` (string) *(required)* — ID of the audio Asset to use as reference speaker sample
- `language` (object) *(optional)*, default: `en` — Target language code (e.g., 'en', 'es', 'zh')
- `description` (object) *(optional)* — Optional description of voice style/tone
- `gender` (object) *(optional)*, default: `neutral` — Perceived voice gender (male, female, neutral)
- `options` (object) *(optional)* — Additional model inference options

**Responses**:
- **HTTP 202** — Model: `VoiceCloneJobResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `job_id` (string) *(required)* — Durable job tracking ID
- `voice_id` (string) *(required)* — Pre-allocated voice record ID
- `status` (string) *(required)* — Current job status (queued, running, etc.)
- `voice_name` (string) *(required)* — Cloned voice name
- `workspace_id` (string) *(required)* — Owning workspace ID
- `created_at` (string) *(required)* — Creation timestamp
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Templates
*Total Endpoints: 9*

### 77. `GET` /api/v1/templates
**Summary**: List Templates  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_templates_api_v1_templates_get`  

**Purpose**:
Lists active templates in the workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `category` | query | string | No |  |
| `status` | query | string | No |  |
| `search` | query | string | No |  |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 78. `POST` /api/v1/templates
**Summary**: Create Template  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_template_api_v1_templates_post`  

**Purpose**:
Initializes a new template with revision 1 immutable TemplateVersion.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateTemplateRequest`
- `name` (string) *(required)* — Template display name
- `description` (object) *(optional)*
- `category` (object) *(optional)*, default: `marketing`
- `visibility` (object) *(optional)*, default: `workspace`
- `thumbnail_asset_id` (object) *(optional)*
- `configuration` (object) *(optional)*
- `initial_document` (object) *(optional)*

**Responses**:
- **HTTP 201** — Model: `TemplateResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `category` (string) *(required)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `thumbnail_asset_id` (object) *(optional)*
- `configuration` (object) *(required)*
- `current_version_id` (object) *(optional)*
- `revision` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 79. `DELETE` /api/v1/templates/{template_id}
**Summary**: Delete Template  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_template_api_v1_templates__template_id__delete`  

**Purpose**:
Soft-deletes a template.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `template_id` | path | string | Yes | Target Video Template UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 80. `GET` /api/v1/templates/{template_id}
**Summary**: Get Template  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_template_api_v1_templates__template_id__get`  

**Purpose**:
Fetches a specific template and its active version snapshot.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `template_id` | path | string | Yes | Target Video Template UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `TemplateResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `category` (string) *(required)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `thumbnail_asset_id` (object) *(optional)*
- `configuration` (object) *(required)*
- `current_version_id` (object) *(optional)*
- `revision` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 81. `PATCH` /api/v1/templates/{template_id}
**Summary**: Update Template  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_template_api_v1_templates__template_id__patch`  

**Purpose**:
Updates template metadata and settings without modifying historical version snapshots.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `template_id` | path | string | Yes | Target Video Template UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `UpdateTemplateRequest`
- `name` (object) *(optional)*
- `description` (object) *(optional)*
- `category` (object) *(optional)*
- `status` (object) *(optional)*
- `visibility` (object) *(optional)*
- `thumbnail_asset_id` (object) *(optional)*
- `configuration` (object) *(optional)*

**Responses**:
- **HTTP 200** — Model: `TemplateResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `category` (string) *(required)*
- `status` (string) *(required)*
- `visibility` (string) *(required)*
- `thumbnail_asset_id` (object) *(optional)*
- `configuration` (object) *(required)*
- `current_version_id` (object) *(optional)*
- `revision` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 82. `POST` /api/v1/templates/{template_id}/instantiate
**Summary**: Instantiate Template  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `instantiate_template_api_v1_templates__template_id__instantiate_post`  

**Purpose**:
Instantiates a template into an active video project pre-populated with its document.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `template_id` | path | string | Yes | Target Video Template UUID |
| `title` | query | string | No | Optional custom title for the new project |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 201** — Model: `ProjectResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `folder_id` (object) *(optional)*
- `created_by` (string) *(required)*
- `title` (string) *(required)*
- `project_type` (string) *(required)*
- `status` (string) *(required)*
- `aspect_ratio` (string) *(required)*
- `width` (object) *(optional)*
- `height` (object) *(optional)*
- `fps` (object) *(optional)*
- `duration_ms` (object) *(optional)*
- `thumbnail_asset_id` (object) *(optional)*
- `current_version_id` (object) *(optional)*
- `revision` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 83. `GET` /api/v1/templates/{template_id}/versions
**Summary**: List Template Versions  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_template_versions_api_v1_templates__template_id__versions_get`  

**Purpose**:
Lists all immutable historical version snapshots of a template.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `template_id` | path | string | Yes | Target Video Template UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 409`: `CONCURRENCY_CONFLICT` (revision mismatch under OCC)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 84. `POST` /api/v1/templates/{template_id}/versions
**Summary**: Create Template Version  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_template_version_api_v1_templates__template_id__versions_post`  

**Purpose**:
Creates a new immutable snapshot of the template document and bumps revision.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `template_id` | path | string | Yes | Target Video Template UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateTemplateVersionRequest`
- `document` (object) *(required)* — Validated template document with scenes, layers, placeholders

**Responses**:
- **HTTP 201** — Model: `TemplateVersionResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `template_id` (string) *(required)*
- `revision` (integer) *(required)*
- `document` (object) *(required)*
- `created_by` (string) *(required)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 409`: `CONCURRENCY_CONFLICT` (revision mismatch under OCC)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 85. `GET` /api/v1/templates/{template_id}/versions/{version_id}
**Summary**: Get Template Version  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_template_version_api_v1_templates__template_id__versions__version_id__get`  

**Purpose**:
Fetches a specific immutable version snapshot by ID.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `template_id` | path | string | Yes | Target Video Template UUID |
| `version_id` | path | string | Yes | Target Template Version UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `TemplateVersionResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `template_id` (string) *(required)*
- `revision` (integer) *(required)*
- `document` (object) *(required)*
- `created_by` (string) *(required)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 409`: `CONCURRENCY_CONFLICT` (revision mismatch under OCC)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Brand Kits & Terminology Glossaries
*Total Endpoints: 17*

### 86. `GET` /api/v1/brand-glossaries
**Summary**: List Glossaries  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_glossaries_api_v1_brand_glossaries_get`  

**Purpose**:
Lists all active glossaries in the workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 87. `POST` /api/v1/brand-glossaries
**Summary**: Create Glossary  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_glossary_api_v1_brand_glossaries_post`  

**Purpose**:
Creates a new terminology glossary in the workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateBrandGlossaryRequest`
- `name` (string) *(required)* — Glossary display name
- `description` (object) *(optional)*
- `brand_kit_id` (object) *(optional)* — Optional parent brand kit relationship
- `status` (object) *(optional)*, default: `active`

**Responses**:
- **HTTP 201** — Model: `BrandGlossaryResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `brand_kit_id` (object) *(optional)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 88. `DELETE` /api/v1/brand-glossaries/{glossary_id}
**Summary**: Delete Glossary  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_glossary_api_v1_brand_glossaries__glossary_id__delete`  

**Purpose**:
Soft-deletes a glossary.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `glossary_id` | path | string | Yes | Target Brand Glossary UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 89. `GET` /api/v1/brand-glossaries/{glossary_id}
**Summary**: Get Glossary  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_glossary_api_v1_brand_glossaries__glossary_id__get`  

**Purpose**:
Fetches a glossary and its rules by ID.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `glossary_id` | path | string | Yes | Target Brand Glossary UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `BrandGlossaryResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `brand_kit_id` (object) *(optional)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 90. `PATCH` /api/v1/brand-glossaries/{glossary_id}
**Summary**: Update Glossary  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_glossary_api_v1_brand_glossaries__glossary_id__patch`  

**Purpose**:
Updates glossary name, status, or description.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `glossary_id` | path | string | Yes | Target Brand Glossary UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `UpdateBrandGlossaryRequest`
- `name` (object) *(optional)*
- `description` (object) *(optional)*
- `brand_kit_id` (object) *(optional)*
- `status` (object) *(optional)*

**Responses**:
- **HTTP 200** — Model: `BrandGlossaryResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `brand_kit_id` (object) *(optional)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 91. `GET` /api/v1/brand-glossaries/{glossary_id}/rules
**Summary**: List Glossary Rules  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_glossary_rules_api_v1_brand_glossaries__glossary_id__rules_get`  

**Purpose**:
Lists terminology substitution rules in a glossary.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `glossary_id` | path | string | Yes | Target Brand Glossary UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 92. `POST` /api/v1/brand-glossaries/{glossary_id}/rules
**Summary**: Create Glossary Rule  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_glossary_rule_api_v1_brand_glossaries__glossary_id__rules_post`  

**Purpose**:
Adds a new terminology substitution rule to a glossary.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `glossary_id` | path | string | Yes | Target Brand Glossary UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateBrandGlossaryRuleRequest`
- `source_term` (object) *(optional)* — Term to match
- `preferred_term` (object) *(optional)* — Approved or phonetic replacement
- `forbidden_term` (object) *(optional)*
- `source_language` (object) *(optional)*, default: `en`
- `target_language` (object) *(optional)*
- `case_sensitive` (object) *(optional)*, default: `False`
- `status` (object) *(optional)*, default: `active`
- `term` (object) *(optional)*
- `replacement` (object) *(optional)*
- `phonetic_spelling` (object) *(optional)*
- `rule_type` (object) *(optional)*

**Responses**:
- **HTTP 201** — Model: `BrandGlossaryRuleResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `glossary_id` (string) *(required)*
- `source_term` (string) *(required)*
- `preferred_term` (string) *(required)*
- `forbidden_term` (object) *(optional)*
- `source_language` (string) *(required)*
- `target_language` (object) *(optional)*
- `case_sensitive` (boolean) *(required)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `term` (string) *(required)*
- `replacement` (string) *(required)*
- `phonetic_spelling` (string) *(required)*
- `rule_type` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 93. `DELETE` /api/v1/brand-glossaries/{glossary_id}/rules/{rule_id}
**Summary**: Delete Glossary Rule (Nested)  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_glossary_rule_nested_api_v1_brand_glossaries__glossary_id__rules__rule_id__delete`  

**Purpose**:
Deletes a terminology rule under a glossary.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `glossary_id` | path | string | Yes | Target Brand Glossary UUID |
| `rule_id` | path | string | Yes | Target Brand Glossary Rule UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 94. `DELETE` /api/v1/brand-glossary-rules/{rule_id}
**Summary**: Delete Glossary Rule  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_glossary_rule_api_v1_brand_glossary_rules__rule_id__delete`  

**Purpose**:
Deletes a terminology rule.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `rule_id` | path | string | Yes | Target Brand Glossary Rule UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 95. `PATCH` /api/v1/brand-glossary-rules/{rule_id}
**Summary**: Update Glossary Rule  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_glossary_rule_api_v1_brand_glossary_rules__rule_id__patch`  

**Purpose**:
Updates a terminology rule.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `rule_id` | path | string | Yes | Target Brand Glossary Rule UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `UpdateBrandGlossaryRuleRequest`
- `source_term` (object) *(optional)*
- `preferred_term` (object) *(optional)*
- `forbidden_term` (object) *(optional)*
- `source_language` (object) *(optional)*
- `target_language` (object) *(optional)*
- `case_sensitive` (object) *(optional)*
- `status` (object) *(optional)*
- `term` (object) *(optional)*
- `replacement` (object) *(optional)*
- `phonetic_spelling` (object) *(optional)*
- `rule_type` (object) *(optional)*

**Responses**:
- **HTTP 200** — Model: `BrandGlossaryRuleResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `glossary_id` (string) *(required)*
- `source_term` (string) *(required)*
- `preferred_term` (string) *(required)*
- `forbidden_term` (object) *(optional)*
- `source_language` (string) *(required)*
- `target_language` (object) *(optional)*
- `case_sensitive` (boolean) *(required)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `term` (string) *(required)*
- `replacement` (string) *(required)*
- `phonetic_spelling` (string) *(required)*
- `rule_type` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 96. `GET` /api/v1/brand-kits
**Summary**: List Brand Kits  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_brand_kits_api_v1_brand_kits_get`  

**Purpose**:
Lists active brand kits in the workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 97. `POST` /api/v1/brand-kits
**Summary**: Create Brand Kit  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_brand_kit_api_v1_brand_kits_post`  

**Purpose**:
Registers a new workspace brand identity guideline kit.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateBrandKitRequest`
- `name` (string) *(required)* — Brand kit display name
- `description` (object) *(optional)*
- `logo_asset_id` (object) *(optional)*
- `colors` (object) *(optional)*
- `typography` (object) *(optional)*
- `settings` (object) *(optional)*
- `is_default` (object) *(optional)*, default: `False`
- `primary_color` (object) *(optional)*
- `accent_color` (object) *(optional)*
- `secondary_color` (object) *(optional)*
- `font_family` (object) *(optional)*

**Responses**:
- **HTTP 201** — Model: `BrandKitResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `logo_asset_id` (object) *(optional)*
- `colors` (object) *(optional)*
- `typography` (object) *(optional)*
- `settings` (object) *(optional)*
- `is_default` (boolean) *(optional)*, default: `False`
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `primary_color` (object) *(required)*
- `accent_color` (object) *(required)*
- `secondary_color` (object) *(required)*
- `font_family` (object) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 98. `DELETE` /api/v1/brand-kits/{brand_kit_id}
**Summary**: Delete Brand Kit  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_brand_kit_api_v1_brand_kits__brand_kit_id__delete`  

**Purpose**:
Soft-deletes a brand kit.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `brand_kit_id` | path | string | Yes | Target Brand Kit UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 99. `GET` /api/v1/brand-kits/{brand_kit_id}
**Summary**: Get Brand Kit  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_brand_kit_api_v1_brand_kits__brand_kit_id__get`  

**Purpose**:
Fetches a brand kit by ID.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `brand_kit_id` | path | string | Yes | Target Brand Kit UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `BrandKitResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `logo_asset_id` (object) *(optional)*
- `colors` (object) *(optional)*
- `typography` (object) *(optional)*
- `settings` (object) *(optional)*
- `is_default` (boolean) *(optional)*, default: `False`
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `primary_color` (object) *(required)*
- `accent_color` (object) *(required)*
- `secondary_color` (object) *(required)*
- `font_family` (object) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 100. `PATCH` /api/v1/brand-kits/{brand_kit_id}
**Summary**: Update Brand Kit  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_brand_kit_api_v1_brand_kits__brand_kit_id__patch`  

**Purpose**:
Updates brand kit colors, typography, or logo asset.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `brand_kit_id` | path | string | Yes | Target Brand Kit UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `UpdateBrandKitRequest`
- `name` (object) *(optional)*
- `description` (object) *(optional)*
- `logo_asset_id` (object) *(optional)*
- `colors` (object) *(optional)*
- `typography` (object) *(optional)*
- `settings` (object) *(optional)*
- `is_default` (object) *(optional)*
- `primary_color` (object) *(optional)*
- `accent_color` (object) *(optional)*
- `secondary_color` (object) *(optional)*
- `font_family` (object) *(optional)*

**Responses**:
- **HTTP 200** — Model: `BrandKitResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `logo_asset_id` (object) *(optional)*
- `colors` (object) *(optional)*
- `typography` (object) *(optional)*
- `settings` (object) *(optional)*
- `is_default` (boolean) *(optional)*, default: `False`
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
- `primary_color` (object) *(required)*
- `accent_color` (object) *(required)*
- `secondary_color` (object) *(required)*
- `font_family` (object) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 101. `GET` /api/v1/brand-kits/{brand_kit_id}/glossaries
**Summary**: List Brand Kit Glossaries  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_brand_kit_glossaries_api_v1_brand_kits__brand_kit_id__glossaries_get`  

**Purpose**:
Lists glossaries associated with a specific brand kit.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `brand_kit_id` | path | string | Yes | Target Brand Kit UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 102. `POST` /api/v1/brand-kits/{brand_kit_id}/glossaries
**Summary**: Create Brand Kit Glossary  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_brand_kit_glossary_api_v1_brand_kits__brand_kit_id__glossaries_post`  

**Purpose**:
Creates a new terminology glossary bound to a brand kit.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `brand_kit_id` | path | string | Yes | Target Brand Kit UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `CreateBrandGlossaryRequest`
- `name` (string) *(required)* — Glossary display name
- `description` (object) *(optional)*
- `brand_kit_id` (object) *(optional)* — Optional parent brand kit relationship
- `status` (object) *(optional)*, default: `active`

**Responses**:
- **HTTP 201** — Model: `BrandGlossaryResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `brand_kit_id` (object) *(optional)*
- `created_by` (string) *(required)*
- `name` (string) *(required)*
- `description` (object) *(optional)*
- `status` (string) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Jobs & Real-time SSE Streaming
*Total Endpoints: 6*

### 103. `GET` /api/v1/jobs
**Summary**: List Jobs  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_jobs_api_v1_jobs_get`  

**Purpose**:
List background jobs in the current workspace with optional type and status filtering.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `job_type` | query | string | No | Filter by workload type |
| `status` | query | string | No | Filter by job status |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 104. `POST` /api/v1/jobs
**Summary**: Submit Job  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `submit_job_api_v1_jobs_post`  

**Purpose**:
Enqueue an asynchronous task pipeline job with optional idempotency key.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Short-lived access token for browser EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `JobSubmitRequest`
- `job_type` (string) *(required)* — Type of workload: render_video, tts_synthesis, lip_sync, translate_project, voice_clone, avatar_train
- `payload` (object) *(optional)* — Parameters, configuration, and inputs required for the worker task
- `priority` (integer) *(optional)*, default: `10` — Queue priority score (higher executes first)
- `idempotency_key` (object) *(optional)* — Client-supplied idempotency key to prevent duplicate job creation
- `max_retries` (integer) *(optional)*, default: `3` — Maximum retry attempts on transient failure

**Responses**:
- **HTTP 201** — Model: `JobResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `job_type` (string) *(required)*
- `status` (string) *(required)*
- `priority` (integer) *(required)*
- `idempotency_key` (object) *(optional)*
- `progress_percent` (integer) *(required)*
- `stage` (object) *(optional)*
- `stage_message` (object) *(optional)*
- `payload` (object) *(required)*
- `result` (object) *(optional)*
- `error_details` (object) *(optional)*
- `celery_task_id` (object) *(optional)*
- `retry_count` (integer) *(required)*
- `max_retries` (integer) *(required)*
- `started_at` (object) *(optional)*
- `completed_at` (object) *(optional)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 105. `GET` /api/v1/jobs/{job_id}
**Summary**: Get Job  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_job_api_v1_jobs__job_id__get`  

**Purpose**:
Fetch a job by ID within the active workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `job_id` | path | string | Yes | Target Asynchronous Job UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `JobResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `created_by` (string) *(required)*
- `job_type` (string) *(required)*
- `status` (string) *(required)*
- `priority` (integer) *(required)*
- `idempotency_key` (object) *(optional)*
- `progress_percent` (integer) *(required)*
- `stage` (object) *(optional)*
- `stage_message` (object) *(optional)*
- `payload` (object) *(required)*
- `result` (object) *(optional)*
- `error_details` (object) *(optional)*
- `celery_task_id` (object) *(optional)*
- `retry_count` (integer) *(required)*
- `max_retries` (integer) *(required)*
- `started_at` (object) *(optional)*
- `completed_at` (object) *(optional)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 106. `POST` /api/v1/jobs/{job_id}/cancel
**Summary**: Cancel Job  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `cancel_job_api_v1_jobs__job_id__cancel_post`  

**Purpose**:
Cancel a running or queued job and revoke the associated Celery task.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `job_id` | path | string | Yes | Target Asynchronous Job UUID |
| `reason` | query | string | No | Cancellation reason |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `JobCancelResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `job_id` (string) *(required)*
- `status` (string) *(required)*
- `message` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 107. `GET` /api/v1/jobs/{job_id}/events
**Summary**: Get Job Audit Events  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_job_events_api_v1_jobs__job_id__events_get`  

**Purpose**:
Retrieve chronological lifecycle and progress events for a job.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `job_id` | path | string | Yes | Target Asynchronous Job UUID |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `array`: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 108. `GET` /api/v1/jobs/{job_id}/stream
**Summary**: Stream Job Progress (SSE)  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `stream_job_progress_api_v1_jobs__job_id__stream_get`  

**Purpose**:
Subscribe to live real-time Server-Sent Events (SSE) updates for a job via Redis Pub/Sub.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `job_id` | path | string | Yes | Target Asynchronous Job UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200**: Real-time Server-Sent Events (SSE) stream yielding live job progress and transition events.
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Developer API Keys & Webhooks
*Total Endpoints: 11*

### 109. `GET` /api/v1/workspaces/{workspace_id}/developer/api-keys
**Summary**: List Developer API Keys  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_api_keys_api_v1_workspaces__workspace_id__developer_api_keys_get`  

**Purpose**:
List all developer API keys for the workspace. Never exposes plaintext secrets or hashes.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `ApiKeyListResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `items` (array) *(required)*
  - *Item properties:*
    - `id` (string) *(required)*
    - `workspace_id` (string) *(required)*
    - `name` (string) *(required)*
    - `prefix` (string) *(required)*
    - `environment` (string) *(required)*
    - `permissions` (string) *(required)*
    - `status` (string) *(required)*
    - `expires_at` (object) *(optional)*
    - `last_used_at` (object) *(optional)*
    - `created_at` (string) *(required)*
- `total` (integer) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 110. `POST` /api/v1/workspaces/{workspace_id}/developer/api-keys
**Summary**: Create Developer API Key  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_api_key_api_v1_workspaces__workspace_id__developer_api_keys_post`  

**Purpose**:
Generate a new workspace developer API key. Plaintext secret is returned ONCE.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `ApiKeyCreateRequest`
- `name` (string) *(required)* — Label for the API key
- `environment` (string) *(optional)*, default: `production` — Target environment
- `permissions` (string) *(optional)*, default: `full` — Permission scope
- `expires_in_days` (object) *(optional)* — Optional key lifetime in days

**Responses**:
- **HTTP 201** — Model: `ApiKeyCreatedResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `name` (string) *(required)*
- `prefix` (string) *(required)*
- `secret_key` (string) *(required)* — Full secret key. This value is never shown again.
- `environment` (string) *(required)*
- `permissions` (string) *(required)*
- `status` (string) *(required)*
- `expires_at` (object) *(optional)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 111. `DELETE` /api/v1/workspaces/{workspace_id}/developer/api-keys/{key_id}
**Summary**: Revoke Developer API Key  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `revoke_api_key_api_v1_workspaces__workspace_id__developer_api_keys__key_id__delete`  

**Purpose**:
Revoke an API key. Once revoked, it can no longer authenticate.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `key_id` | path | string | Yes | Target Developer API Key UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `ApiKeyResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `name` (string) *(required)*
- `prefix` (string) *(required)*
- `environment` (string) *(required)*
- `permissions` (string) *(required)*
- `status` (string) *(required)*
- `expires_at` (object) *(optional)*
- `last_used_at` (object) *(optional)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 112. `GET` /api/v1/workspaces/{workspace_id}/developer/api-keys/{key_id}
**Summary**: Get Developer API Key  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_api_key_api_v1_workspaces__workspace_id__developer_api_keys__key_id__get`  

**Purpose**:
Retrieve safe metadata for a specific API key.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `key_id` | path | string | Yes | Target Developer API Key UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `ApiKeyResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `name` (string) *(required)*
- `prefix` (string) *(required)*
- `environment` (string) *(required)*
- `permissions` (string) *(required)*
- `status` (string) *(required)*
- `expires_at` (object) *(optional)*
- `last_used_at` (object) *(optional)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 113. `GET` /api/v1/workspaces/{workspace_id}/developer/webhooks
**Summary**: List Webhooks  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_webhooks_api_v1_workspaces__workspace_id__developer_webhooks_get`  

**Purpose**:
List all registered webhooks for the workspace.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `status` | query | string | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `WebhookListResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `items` (array) *(required)*
  - *Item properties:*
    - `id` (string) *(required)*
    - `workspace_id` (string) *(required)*
    - `url` (string) *(required)*
    - `events` (array) *(required)*
    - `status` (string) *(required)*
    - `description` (object) *(optional)*
    - `failure_count` (integer) *(required)*
    - `created_at` (string) *(required)*
    - `updated_at` (string) *(required)*
- `total` (integer) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 114. `POST` /api/v1/workspaces/{workspace_id}/developer/webhooks
**Summary**: Register Webhook Endpoint  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `create_webhook_api_v1_workspaces__workspace_id__developer_webhooks_post`  

**Purpose**:
Register a new webhook endpoint. Plaintext signing secret is returned ONCE.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `WebhookCreateRequest`
- `url` (string) *(required)* — Destination HTTP/HTTPS URL
- `events` (array) *(optional)* — Subscribed event types
- `description` (object) *(optional)* — Optional description

**Responses**:
- **HTTP 201** — Model: `WebhookCreatedResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `url` (string) *(required)*
- `secret` (string) *(required)* — HMAC-SHA256 signing secret. Store securely.
- `events` (array) *(required)*
- `status` (string) *(required)*
- `description` (object) *(optional)*
- `created_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 115. `DELETE` /api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}
**Summary**: Delete / Revoke Webhook  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `delete_webhook_api_v1_workspaces__workspace_id__developer_webhooks__webhook_id__delete`  

**Purpose**:
Revoke and soft-delete a registered webhook endpoint.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `webhook_id` | path | string | Yes | Target Webhook Subscription UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 204**: Successful Response
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 116. `GET` /api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}
**Summary**: Get Webhook  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `get_webhook_api_v1_workspaces__workspace_id__developer_webhooks__webhook_id__get`  

**Purpose**:
Retrieve webhook metadata.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `webhook_id` | path | string | Yes | Target Webhook Subscription UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `WebhookResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `url` (string) *(required)*
- `events` (array) *(required)*
- `status` (string) *(required)*
- `description` (object) *(optional)*
- `failure_count` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 117. `PATCH` /api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}
**Summary**: Update Webhook  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `update_webhook_api_v1_workspaces__workspace_id__developer_webhooks__webhook_id__patch`  

**Purpose**:
Update destination URL, event subscriptions, or description.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `webhook_id` | path | string | Yes | Target Webhook Subscription UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `WebhookUpdateRequest`
- `url` (object) *(optional)* — New destination URL
- `events` (object) *(optional)* — Updated event subscriptions
- `status` (object) *(optional)* — Endpoint state
- `description` (object) *(optional)* — Updated description

**Responses**:
- **HTTP 200** — Model: `WebhookResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `id` (string) *(required)*
- `workspace_id` (string) *(required)*
- `url` (string) *(required)*
- `events` (array) *(required)*
- `status` (string) *(required)*
- `description` (object) *(optional)*
- `failure_count` (integer) *(required)*
- `created_at` (string) *(required)*
- `updated_at` (string) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 118. `GET` /api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}/deliveries
**Summary**: List Webhook Deliveries  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `list_webhook_deliveries_api_v1_workspaces__workspace_id__developer_webhooks__webhook_id__deliveries_get`  

**Purpose**:
Retrieve delivery attempt history and latency metrics for a webhook.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `webhook_id` | path | string | Yes | Target Webhook Subscription UUID |
| `limit` | query | integer | No |  |
| `offset` | query | integer | No |  |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `WebhookDeliveryListResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `items` (array) *(required)*
  - *Item properties:*
    - `id` (string) *(required)*
    - `webhook_id` (string) *(required)*
    - `event_id` (string) *(required)*
    - `event_type` (string) *(required)*
    - `payload` (object) *(required)*
    - `response_status_code` (object) *(optional)*
    - `response_body` (object) *(optional)*
    - `latency_ms` (object) *(optional)*
    - `status` (string) *(required)*
    - `attempt` (integer) *(required)*
    - `error_message` (object) *(optional)*
    - `created_at` (string) *(required)*
- `total` (integer) *(required)*
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 119. `POST` /api/v1/workspaces/{workspace_id}/developer/webhooks/{webhook_id}/test
**Summary**: Trigger Test Webhook Ping  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `test_webhook_api_v1_workspaces__workspace_id__developer_webhooks__webhook_id__test_post`  

**Purpose**:
Dispatch a signed test event to the registered webhook endpoint.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `webhook_id` | path | string | Yes | Target Webhook Subscription UUID |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body**: None (GET/parameterized query)

**Responses**:
- **HTTP 200** — Model: `WebhookTestResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `status` (string) *(optional)*, default: `enqueued` — Dispatch status of the test ping
- `event_id` (string) *(required)* — Unique test event identifier
- `destination_url` (string) *(required)* — Target webhook URL receiving the ping event
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

## Ask Rhys AI Copilot
*Total Endpoints: 2*

### 120. `POST` /api/v1/ask-rhys/chat
**Summary**: Query AskRhys AI Copilot Direct Chat  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `ask_rhys_direct_api_v1_ask_rhys_chat_post`  

**Purpose**:
Direct endpoint for conversational queries directed to Rhys AI Copilot using X-Workspace-ID header.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `X-Request-ID` | header | string | No |  |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `AskRhysRequest`
- `message` (string) *(required)* — User's prompt or question for AskRhys.
- `project_id` (object) *(optional)* — Optional active project ID for project-aware context.
- `conversation_id` (object) *(optional)* — Optional client conversation tracking identifier.
- `context_mode` (string) *(optional)*, default: `general` — Context modes supported by AskRhys.
- `history` (object) *(optional)* — Bounded conversational history from client (up to 6 previous messages).

**Responses**:
- **HTTP 200** — Model: `AskRhysResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `conversation_id` (string) *(required)* — Conversation session identifier.
- `message` (string) *(required)* — Echo of user's query prompt.
- `response` (string) *(required)* — Truthful response generated by local Qwen 2.5 0.5B ONNX CPU model.
- `context_used` (boolean) *(optional)*, default: `False` — Whether active project context was incorporated into inference.
- `provider` (string) *(optional)*, default: `qwen` — AI provider name that generated the response.
- `model` (string) *(optional)*, default: `llm/qwen-2.5-0.5b-cpu` — Specific model identifier used.
- `latency_ms` (number) *(required)* — End-to-end inference and orchestration latency in milliseconds.
- `suggestions` (array) *(optional)* — Follow-up quick reply suggestions or prompt tips.
- `actions` (array) *(optional)* — Non-mutating project edit recommendations proposed for explicit user review.
  - *Item properties:*
    - `type` (string) *(optional)*, default: `project_edit_suggestion` — Discriminator tag for client-side suggestion handling.
    - `operation` (string) *(required)* — Suggested operation name (e.g., 'update_scene_script', 'adjust_duration', 'suggest_visual').
    - `scene_id` (object) *(optional)* — Scene identifier if suggestion targets a specific scene.
    - `reason` (string) *(required)* — Explanation of why this edit improves the video.
    - `proposed_value` (object) *(required)* — Proposed replacement value or structured parameters.
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---

### 121. `POST` /api/v1/workspaces/{workspace_id}/ask-rhys
**Summary**: Query AskRhys AI Copilot  
**Classification**: B. Protected application API | **Auth Required**: Yes (HTTPBearer)  
**Operation ID**: `ask_rhys_api_v1_workspaces__workspace_id__ask_rhys_post`  

**Purpose**:
Executes truthful conversational inference via the local CPU Qwen 2.5 0.5B ONNX model. Enforces workspace isolation, rate limiting, and returns non-mutating project suggestions.

**Parameters**:
| Name | In | Type | Required | Description |
|---|---|---|---|---|
| `workspace_id` | path | string | Yes | Target Workspace UUID |
| `token` | query | string | No | Access token query parameter for EventSource / SSE |
| `workspace_id` | query | string | No | Optional workspace ID query parameter fallback |
| `X-Request-ID` | header | string | No |  |
| `X-Workspace-ID` | header | string | No | Optional workspace context header (must match workspace_id path parameter if both provided) |
| `X-API-Key` | header | string | No | Developer API key (hz_...) |

**Request Body** (`application/json`): `AskRhysRequest`
- `message` (string) *(required)* — User's prompt or question for AskRhys.
- `project_id` (object) *(optional)* — Optional active project ID for project-aware context.
- `conversation_id` (object) *(optional)* — Optional client conversation tracking identifier.
- `context_mode` (string) *(optional)*, default: `general` — Context modes supported by AskRhys.
- `history` (object) *(optional)* — Bounded conversational history from client (up to 6 previous messages).

**Responses**:
- **HTTP 200** — Model: `AskRhysResponse`: Successful Response
  <details><summary>Response Fields</summary>

- `conversation_id` (string) *(required)* — Conversation session identifier.
- `message` (string) *(required)* — Echo of user's query prompt.
- `response` (string) *(required)* — Truthful response generated by local Qwen 2.5 0.5B ONNX CPU model.
- `context_used` (boolean) *(optional)*, default: `False` — Whether active project context was incorporated into inference.
- `provider` (string) *(optional)*, default: `qwen` — AI provider name that generated the response.
- `model` (string) *(optional)*, default: `llm/qwen-2.5-0.5b-cpu` — Specific model identifier used.
- `latency_ms` (number) *(required)* — End-to-end inference and orchestration latency in milliseconds.
- `suggestions` (array) *(optional)* — Follow-up quick reply suggestions or prompt tips.
- `actions` (array) *(optional)* — Non-mutating project edit recommendations proposed for explicit user review.
  - *Item properties:*
    - `type` (string) *(optional)*, default: `project_edit_suggestion` — Discriminator tag for client-side suggestion handling.
    - `operation` (string) *(required)* — Suggested operation name (e.g., 'update_scene_script', 'adjust_duration', 'suggest_visual').
    - `scene_id` (object) *(optional)* — Scene identifier if suggestion targets a specific scene.
    - `reason` (string) *(required)* — Explanation of why this edit improves the video.
    - `proposed_value` (object) *(required)* — Proposed replacement value or structured parameters.
  </details>
- **HTTP 422** — Model: `HTTPValidationError`: Validation Error

**Possible Error Codes**:
- `HTTP 401`: `AUTH_UNAUTHORIZED`, `AUTH_TOKEN_EXPIRED` (missing or invalid Bearer token)
- `HTTP 403`: `PERMISSION_DENIED` (insufficient workspace role privileges)
- `HTTP 404`: `WORKSPACE_NOT_FOUND` (target workspace does not exist or user has no access)
- `HTTP 422`: `VALIDATION_ERROR` (input payload does not conform to Pydantic schema)
- `HTTP 500`: `INTERNAL_SERVER_ERROR` (unhandled server exception)

---
