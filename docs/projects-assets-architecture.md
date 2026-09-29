# HeyZen Content Layer Architecture: Projects, Folders & Assets

This document defines the technical architecture, data contracts, optimistic concurrency rules, and object storage upload/download flows for the HeyZen content subsystem implemented in Phase 5.

---

## 1. Domain Models & Relational Architecture

The content layer provides a multi-tenant hierarchy strictly isolated by Workspace:

```text
Workspace (Tenant Boundary)
  ├── Folders (Hierarchical Organization)
  │     └── Folders (Subfolders)
  ├── Projects (Editable Video State)
  │     └── ProjectVersions (Immutable JSONB Snapshots)
  └── Assets (Binary Media in MinIO/S3)
```

### Folders (`folders`)
* **Purpose**: Scopes and organizes projects into arbitrary tree hierarchies within a single workspace.
* **Fields**:
  * `id`: UUID (Primary Key)
  * `workspace_id`: UUID (FK to `workspaces.id`, ON DELETE CASCADE)
  * `parent_id`: UUID (Nullable self-referencing FK to `folders.id`, ON DELETE RESTRICT)
  * `name`: VARCHAR(128)
  * `created_by`: UUID (FK to `users.id`, ON DELETE RESTRICT)
  * `created_at`, `updated_at`: TIMESTAMPTZ (UTC)
  * `deleted_at`: TIMESTAMPTZ (Soft-delete timestamp)
* **Invariants**:
  * **Workspace Scoping**: Parent folder must belong to the same workspace as child folder.
  * **Cycle Prevention**: A folder cannot be its own parent, nor can it be moved into any of its own descendants.
  * **Sibling Uniqueness**: Sibling folders sharing the same parent (including root level) must have unique names (case-insensitive).
  * **Non-Empty Deletion Guard**: Soft-deleting a folder that contains active child folders or active projects is rejected with HTTP 409 (`FOLDER_NOT_EMPTY`).

### Projects (`projects`)
* **Purpose**: Represents an editable video project. The Project is *not* an MP4; it is structured canvas data.
* **Fields**:
  * `id`: UUID (Primary Key)
  * `workspace_id`: UUID (FK to `workspaces.id`, ON DELETE CASCADE)
  * `folder_id`: UUID (Nullable FK to `folders.id`, ON DELETE SET NULL)
  * `created_by`: UUID (FK to `users.id`, ON DELETE RESTRICT)
  * `title`: VARCHAR(255)
  * `project_type`: VARCHAR(64) (`standard`, `avatar_video`, `agent`, `translation`, `template_based`)
  * `status`: VARCHAR(32) (`draft`, `processing`, `ready`, `archived`)
  * `aspect_ratio`: VARCHAR(16) (`16:9`, `9:16`, `1:1`)
  * `width`, `height`: INTEGER (e.g. 1920x1080)
  * `fps`: INTEGER (e.g. 30, 60)
  * `duration_ms`: INTEGER (Calculated timeline runtime in milliseconds)
  * `thumbnail_asset_id`: UUID (Nullable FK to `assets.id`, ON DELETE SET NULL)
  * `current_version_id`: UUID (FK to active `project_versions.id`)
  * `revision`: INTEGER (Monotonically increasing version counter for optimistic locking)
  * `created_at`, `updated_at`, `deleted_at`

### Project Versions (`project_versions`)
* **Purpose**: Immutable historical snapshots storing the full `ProjectDocumentV1` document in PostgreSQL `JSONB`.
* **Fields**:
  * `id`: UUID (Primary Key)
  * `project_id`: UUID (FK to `projects.id`, ON DELETE CASCADE)
  * `revision`: INTEGER (1-indexed, immutable)
  * `document`: JSONB (Complete validated canvas document)
  * `created_by`: UUID (FK to `users.id`, ON DELETE RESTRICT)
  * `source`: VARCHAR(32) (`manual`, `autosave`, `template`, `agent`, `import`, `initial`)
  * `created_at`: TIMESTAMPTZ (UTC)
* **Constraints**:
  * `UNIQUE(project_id, revision)`: Guarantees no two versions can claim the same revision number.

---

## 2. Structured Project JSON Contract (`ProjectDocumentV1`)

All editable canvas state is validated against Pydantic V2 and persisted in `ProjectVersion.document`.

### Canonical Envelope Schema

```json
{
  "schema_version": 1,
  "settings": {
    "aspect_ratio": "16:9",
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "total_duration": 15.0
  },
  "scenes": [
    {
      "id": "scene-uuid-1",
      "sequence": 1,
      "duration": 5.0,
      "transition": {
        "type": "fade",
        "duration": 0.5
      },
      "background": {
        "type": "color",
        "value": "#0F172A"
      },
      "avatar": {
        "avatar_id": "avatar-preset-1",
        "look_id": "outfit-business-casual",
        "position": {
          "x": 0.5,
          "y": 0.65,
          "scale": 1.0,
          "rotation": 0.0
        },
        "view_mode": "half_body"
      },
      "speech": {
        "voice_id": "voice-en-us-1",
        "script": "Welcome to HeyZen, the next generation video platform.",
        "audio_asset_id": null,
        "speed": 1.0,
        "pitch": 0.0
      },
      "layers": [
        {
          "id": "layer-1",
          "type": "text",
          "name": "Title Heading",
          "start_time": 0.0,
          "end_time": 5.0,
          "transform": {
            "x": 0.5,
            "y": 0.2,
            "scale": 1.0
          },
          "content": {
            "text": "Welcome to HeyZen",
            "fontSize": 48,
            "color": "#FFFFFF"
          }
        }
      ]
    }
  ],
  "audio_tracks": [
    {
      "id": "bg-music-track-1",
      "asset_id": "asset-uuid-1",
      "name": "Upbeat Ambient",
      "volume": 0.25,
      "start_time": 0.0,
      "duration": 15.0,
      "fade_in_duration": 1.0,
      "fade_out_duration": 2.0,
      "loop": true
    }
  ],
  "assets": [
    {
      "asset_id": "asset-uuid-1",
      "asset_type": "audio",
      "storage_key": "workspaces/.../audio.mp3"
    }
  ],
  "metadata": {
    "tags": ["marketing", "onboarding"],
    "notes": "Draft version for stakeholder review"
  }
}
```

---

## 3. Optimistic Concurrency & Revision Protection

To prevent lost updates when multiple users or browser tabs edit the same project simultaneously, the backend enforces optimistic concurrency control:

### Concurrency Protocol

```text
Client (Editor)                                FastAPI Backend                             PostgreSQL
       │                                               │                                        │
       │─── GET /projects/{id} ───────────────────────>│                                        │
       │<── Project (revision: 5) ─────────────────────│                                        │
       │                                               │                                        │
[User edits timeline]                                  │                                        │
       │                                               │                                        │
       │─── POST /projects/{id}/versions ─────────────>│                                        │
       │    { expected_revision: 5, document: {...} }  │                                        │
       │                                               │─── SELECT * FOR UPDATE ───────────────>│
       │                                               │<── project (revision: 5) ──────────────│
       │                                               │    (Lock acquired)                     │
       │                                               │                                        │
       │                                               │─── INSERT ProjectVersion (rev: 6) ────>│
       │                                               │─── UPDATE project (rev: 6) ───────────>│
       │                                               │─── COMMIT ────────────────────────────>│
       │<── Version 6 (HTTP 201 Created) ──────────────│                                        │
```

### Conflict Handling (Stale Revision)
If Client B attempts to save with `expected_revision: 5` after Client A has already advanced the project to revision 6:
1. The backend locks the project row inside the transaction.
2. Compares `project.revision (6)` with `expected_revision (5)`.
3. Detects mismatch and rolls back immediately.
4. Returns HTTP 409 Conflict:
   ```json
   {
     "error": {
       "code": "CONCURRENCY_CONFLICT",
       "message": "Revision conflict: current project revision is 6, but update expected revision 5.",
       "request_id": "...",
       "details": null
     }
   }
   ```
5. Client B's editor prompts the user to reload the latest changes or merge.

---

## 4. Asset Object Storage Architecture

Binary media files (images, audio, video, fonts) are **never** proxied through FastAPI to ensure low latency and horizontal scalability.

### Upload Flow (Pre-Signed PUT)

```text
Browser Client                                FastAPI Backend                             MinIO / S3
       │                                             │                                         │
       │─── POST /assets/upload-intents ────────────>│                                         │
       │    { filename: "clip.mp4", mime: "video/mp4" }                                        │
       │                                             │─── generate_presigned_url(PUT) ────────>│
       │                                             │    key: workspaces/{ws}/assets/{id}/... │
       │                                             │─── INSERT Asset (pending_upload) ──────>│
       │<── { asset_id, signed_upload_url } ─────────│                                         │
       │                                                                                       │
       │─── PUT binary payload directly to signed_upload_url ─────────────────────────────────>│
       │<── HTTP 200 OK ───────────────────────────────────────────────────────────────────────│
       │                                             │                                         │
       │─── POST /assets/{id}/confirm ──────────────>│                                         │
       │                                             │─── head_object(storage_key) ───────────>│
       │                                             │<── { ContentLength, ContentType } ──────│
       │                                             │    (Verifies object exists & size)      │
       │                                             │─── UPDATE Asset (status: "ready") ─────>│
       │<── { asset_id, status: "ready" } ───────────│                                         │
```

### Download Flow (Pre-Signed GET)
1. Client requests `GET /api/v1/workspaces/{workspace_id}/assets/{asset_id}/download`.
2. Backend authenticates caller, verifies workspace membership and `asset.read` permission.
3. Backend generates short-lived pre-signed GET URL (default expiry: 1 hour).
4. Returns `{ "download_url": "...", "expires_in_seconds": 3600 }`.
5. Browser directly streams media from MinIO/S3 without loading the API server.

---

## 5. Workspace Isolation Guarantees

Every database query and storage key incorporates the workspace boundary:
1. **API Routes**: Scoped under `/api/v1/workspaces/{workspace_id}/...`.
2. **Object Storage**: Keys strictly prefixed with `workspaces/{workspace_id}/assets/{asset_id}/{filename}`.
3. **Foreign Keys**: Folders, projects, and assets all maintain non-nullable foreign keys to `workspaces.id`.
4. **Relationship Validation**: When assigning a folder or asset to a project, the service layer verifies that both entities share the exact same `workspace_id`. Cross-workspace attachments return HTTP 404.
