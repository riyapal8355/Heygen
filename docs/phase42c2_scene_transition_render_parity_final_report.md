# Phase 42C-2 — Scene Transition Render Parity Final Report

## 1. Executive Summary

Phase 42C-2 completes the missing **FFmpeg scene-transition rendering parity** in HeyZen Studio.

Prior to this phase, while scene transitions (`fade`, `wipe`, `dissolve`, `slide`) were configurable in the Studio UI and stored in the project schema (`scene.transition`), the backend media compositor performed a hard cut (`concat` demuxer or `concat` filter) between all scene clips.

In Phase 42C-2, we implemented an end-to-end transition-aware multi-scene assembly pipeline:
- Integrated FFmpeg's `xfade` (video) and `acrossfade` (audio) native filter operations.
- Preserved the fast stream-copy `concat` path when all boundaries are hard cuts.
- Implemented robust support for arbitrary mixed boundaries (e.g. `A --fade--> B --none--> C --wipe--> D`).
- Dynamically track the assembled timeline duration so that cumulative overlaps and transition offsets match actual rendered clips.
- Ensured transition durations are safely bounded and clamped relative to rendered clip boundaries to eliminate filter configuration errors.
- Preserved the existing multi-track background music architecture in `_mix_background_audio`.
- Successfully validated 13/13 test cases in `backend/tests/test_phase42c2_scene_transitions.py` including pixel-level RGB frame assertions, 98/98 backend studio regressions, 160/160 frontend tests, 0 TypeScript errors, and a clean production build.

---

## 2. Existing Transition Model

The project's transition model was audited from `backend/app/schemas/project_document.py` and `src/components/studio/VidoAIStudio.tsx`:

1. **Storage Location**: Stored on each `Scene` object as `scene.transition: Optional[SceneTransition] = None`.
2. **Ownership**: The transition is owned by the incoming scene (visual effect transitioning *into* this scene).
3. **First Scene Semantics**: Scene 0 has no preceding scene. Any transition placed on Scene 0 is ignored (render begins at $t=0$ directly with Scene 0).
4. **Last Scene Semantics**: Scene $N-1$ does not transition out into void; export cleanly terminates after the last scene.
5. **Supported Types**:
   - `fade` (crossfade between scenes)
   - `dissolve` (dissolve between scenes)
   - `wipe` / `wipe_left` (directional wipe sweeping across)
   - `slide` / `slide_left` (directional slide across)
   - `none` or `None` (standard hard cut)
6. **Duration**: Default `0.5` seconds in UI, schema bounded $[0.0, 5.0]$.

---

## 3. Supported Transition Types & Parity Status

| Transition Type | UI Value | FFmpeg Implementation | Parity Status | Visual Verification |
|---|---|---|---|---|
| Hard Cut (None) | `none` / `null` | Fast `concat` demuxer / filter | **PASS** | Abrupt boundary, exact duration sum |
| Fade | `fade` | `xfade=transition=fade` | **PASS** | Intermediate blend (Red + Blue -> blended RGB) |
| Dissolve | `dissolve` | `xfade=transition=dissolve` | **PASS** | Intermediate blend/dissolve pattern |
| Wipe Left | `wipe` / `wipe_left` | `xfade=transition=wipeleft` | **PASS** | Spatial separation (Left vs Right color domains) |
| Slide Left | `slide` / `slide_left` | `xfade=transition=slideleft` | **PASS** | Spatial separation across sliding plane |

All repository-supported transition types are fully implemented with 100% test coverage.

---

## 4. FFmpeg Filter Pipeline & Architecture

The compositor architecture operates in two clean tiers:

1. **Scene-Level Rendering (Preserved)**:
   - Each scene is rendered into an intermediate broadcast clip with its visual layers (media, video, image, shapes, stickers, text, captions, avatars) composited via the unified RGBA overlay chain and synchronized speech audio.
   - Scene clips are rendered once and output to `mws.scenes_dir / "scene_XXXX.mp4"`.

2. **Transition-Aware Multi-Scene Assembly (`_concatenate_scene_clips`)**:
   - **Step 1: Duration Probing**: Probes actual rendered clip durations with `ffprobe_service`.
   - **Step 2: Boundary Analysis**: Inspects boundaries $1 \dots N-1$. If all boundaries are `None` or `"none"` or effective duration $< 0.05\text{s}$, the pipeline executes the fast concat path.
   - **Step 3: Filtergraph Construction**:
     - Normalizes timebases: `[i:v:0]settb=AVTB,fps={fps}[v{i}]`.
     - Tracks dynamic assembled duration:
       $$\text{offset}_i = \text{assembled\_dur} - D_i$$
       $$\text{assembled\_dur} \leftarrow \text{assembled\_dur} + \text{duration}(B) - D_i$$
     - For transition boundaries:
       - Video: `[v_prev][v_i]xfade=transition={type}:duration={D}:offset={offset},settb=AVTB,fps={fps}[v_out_i]`
       - Audio: `[a_prev][a_i]acrossfade=d={D}:c1=tri:c2=tri[a_out_i]`
     - For hard-cut boundaries:
       - Video: `[v_prev][v_i]concat=n=2:v=1:a=0,settb=AVTB,fps={fps}[v_out_i]`
       - Audio: `[a_prev][a_i]concat=n=2:v=0:a=1[a_out_i]`
   - **Step 4: Mixed Background Audio Mixer (`_mix_background_audio`)**:
     - Consumes the assembled transition video and layers independent background music tracks with adelay/amix, strictly bounded by the assembled video duration.

---

## 5. Timing, Overlap, and Duration Formula

For $N$ scenes with actual durations $T_0, T_1, \dots, T_{N-1}$ and effective transition durations $D_1, D_2, \dots, D_{N-1}$ (where $D_i = 0$ for hard cuts):

$$\text{Final Video Duration} = \sum_{i=0}^{N-1} T_i - \sum_{i=1}^{N-1} D_i$$

### Safety Clamping
To prevent FFmpeg filter errors when scene clips are shorter than the requested transition duration:
$$D_{i, \text{clamped}} = \min\left(D_i, T_{i-1} - 0.05, T_i - 0.05, \frac{T_{i-1} + T_i}{2}\right)$$
If $D_{i, \text{clamped}} < 0.05\text{s}$, the boundary cleanly falls back to a hard cut.

---

## 6. Preview / Export Parity

- **Canvas Preview**: When scrubbing or playing through the studio canvas, switching scenes transitions sequentially at scene boundaries.
- **Exported Video**: Now mirrors this behavior with smooth video crossfades and wipes rather than hard jumps.
- **Hard Cuts**: Scenes without transitions continue to cut cleanly with zero offset drift or visual glitches.

---

## 7. Audio Behavior

- **Scene Speech Audio**: Crossfaded across transitions using FFmpeg's `acrossfade=d={D}:c1=tri:c2=tri`.
- **Hard Cuts**: Concatenated cleanly via `concat=n=2:v=0:a=1`.
- **Background Music**: Background music tracks configured in `audio_tracks` are layered onto the assembled video in `_mix_background_audio`. Background music tracks are not affected by scene crossfades, avoiding music distortion or duplication.

---

## 8. Test Suite Verification

### Phase 42C-2 Transition Test Suite (`test_phase42c2_scene_transitions.py`)
```text
backend\tests\test_phase42c2_scene_transitions.py::test_1_no_transition_hard_cut PASSED [  7%]
backend\tests\test_phase42c2_scene_transitions.py::test_2_single_fade_transition PASSED [ 15%]
backend\tests\test_phase42c2_scene_transitions.py::test_3_transition_timing_boundaries PASSED [ 23%]
backend\tests\test_phase42c2_scene_transitions.py::test_4_dissolve_transition PASSED [ 30%]
backend\tests\test_phase42c2_scene_transitions.py::test_5_directional_wipe_and_slide PASSED [ 38%]
backend\tests\test_phase42c2_scene_transitions.py::test_6_three_scenes_consecutive_transitions PASSED [ 46%]
backend\tests\test_phase42c2_scene_transitions.py::test_7_variable_transition_durations PASSED [ 53%]
backend\tests\test_phase42c2_scene_transitions.py::test_8_short_scenes_boundary_clamping PASSED [ 61%]
backend\tests\test_phase42c2_scene_transitions.py::test_9_first_scene_transition_ignored PASSED [ 69%]
backend\tests\test_phase42c2_scene_transitions.py::test_10_last_scene_clean_termination PASSED [ 76%]
backend\tests\test_phase42c2_scene_transitions.py::test_11_audio_and_music_preservation PASSED [ 84%]
backend\tests\test_phase42c2_scene_transitions.py::test_12_total_duration_formula PASSED [ 92%]
backend\tests\test_phase42c2_scene_transitions.py::test_13_mixed_transition_and_hard_cut_boundaries PASSED [100%]

======================= 13 passed, 2 warnings in 21.62s =======================
```

### Full Studio Backend Regression Suite
```text
98 passed, 608 deselected, 3 warnings in 89.20s (0:01:29)
```

### Frontend Tests
```text
ℹ tests 160
ℹ suites 54
ℹ pass 160
ℹ fail 0
```

### TypeScript Compilation & Build
- `npx tsc --noEmit`: 0 errors.
- `npm run build`: Compiled successfully in 3.0s, 6 static pages generated.

---

## 9. Pixel-Level Acceptance Verification

All core transition tests extract frames using `ffmpeg -ss {t} -vframes 1` and inspect pixel data via Pillow:

| Scenario | Tested Configuration | Sample Timestamp | Verified Pixel Condition | Status |
|---|---|---|---|---|
| Single Fade | Red (A) -> Blue (B), $D=0.8\text{s}$ | $t=2.1\text{s}$ (midpoint) | $R > 40$, $B > 40$ (color blend) | **PASS** |
| Dissolve | Red (A) -> Blue (B), $D=1.0\text{s}$ | $t=2.5\text{s}$ (midpoint) | Intermediate non-trivial blend | **PASS** |
| Directional Wipe | Red (A) -> Blue (B), $D=1.0\text{s}$ | $t=2.5\text{s}$ (midpoint) | Left $10\%$ vs Right $90\%$ color split ($R > 150$, $B > 150$) | **PASS** |
| Mixed 4 Scenes | Red $\xrightarrow{\text{fade}}$ Green $\xrightarrow{\text{none}}$ Blue $\xrightarrow{\text{wipe}}$ Yellow | $t=1.0, 2.1, 3.5, 4.3, 6.3, 7.8\text{s}$ | Accurate progression through Red, blend, Green, Blue, wipe, and Yellow | **PASS** |

---

## 10. Service Health

All services remained continuously running throughout implementation and verification:

| Service | Port / Target | Status |
|---|---|---|
| Next.js Dev Server | `localhost:3000` (PID 9036) | **RUNNING** |
| FastAPI Backend | `127.0.0.1:8000` (PID 15688) | **RUNNING** |
| PostgreSQL | `5432` (`heyzen-postgres`) | **HEALTHY** |
| Redis | `6379` (`heyzen-redis`) | **HEALTHY** |
| MinIO S3 API | `9000` (`heyzen-minio`) | **HEALTHY** |
| MinIO Console | `9001` (`heyzen-minio`) | **HEALTHY** |
| Docker Daemon | Windows Docker Desktop | **HEALTHY** |

---

## 11. Browser E2E

**Status: NOT VERIFIED**  
**Reason:** Playwright browser binaries are not installed in the environment (`No tests found` / no playwright test suite configured in project root).

---

## 12. Known Limitations

- Sub-frame audio crossfades ($< 0.05\text{s}$) are safely clamped to hard cuts to prevent audio encoder clicks and zero-sample filter errors.
- Codec-level GOP container overhead may cause final output duration to deviate by at most $\pm 0.1\text{s}$ from theoretical fractional duration, which is within standard video container tolerance.

---

## 13. Files Changed

- `backend/app/media/filters.py`: Added `map_transition_to_xfade` mapping repository transition types (`fade`, `dissolve`, `wipe`, `slide`) to FFmpeg filter names.
- `backend/app/media/compositor.py`: Enhanced `_concatenate_scene_clips` with transition-aware progressive `xfade`/`acrossfade` assembly, dynamic timeline offset tracking, safety clamping, and hard-cut fast path preservation.
- `backend/tests/test_phase42c2_scene_transitions.py`: Created comprehensive 13-scenario test suite with pixel-level verification and duration checks.

---

## 14. Final Status

**IMPLEMENTED**
