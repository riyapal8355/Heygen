"use client";

import React, { useRef } from "react";
import { Subtitles, Plus, Pencil, Trash2 } from "lucide-react";
import { StudioScene } from "./VidoAIStudio";
import {
  useTimelineClipDrag,
  getScenePlayheadTime,
  MIN_CLIP_DURATION,
  getClipToClipSnapTargets,
} from "../../lib/timelineUtils";

interface CaptionTimelineTrackProps {
  scenes: StudioScene[];
  totalDuration: number;
  activeSceneIndex: number;
  playbackTime: number;
  selectedCueId: string | number | null;
  onSelectScene: (index: number) => void;
  onSelectCue: (id: string | number | null) => void;
  onOpenCaptionsPanel: () => void;
  onDeleteCue?: (sceneIdx: number, cueId: string | number) => void;
  onUpdateCueTiming?: (
    sceneIdx: number,
    cueId: string | number,
    start: number,
    end: number
  ) => void;
  onCommitCueTiming?: () => void;
}

function CaptionTimelineClipItem({
  cue,
  sceneDuration,
  sceneIdx,
  isCueSelected,
  isCueActiveAtPlayhead,
  containerRef,
  snapTargets,
  onSnapChange,
  onSelectScene,
  onSelectCue,
  onOpenCaptionsPanel,
  onDeleteCue,
  onUpdateCueTiming,
  onCommitCueTiming,
}: {
  cue: any;
  sceneDuration: number;
  sceneIdx: number;
  isCueSelected: boolean;
  isCueActiveAtPlayhead: boolean;
  containerRef: React.RefObject<HTMLDivElement | null>;
  snapTargets: number[];
  onSnapChange?: (target: number | null) => void;
  onSelectScene: (index: number) => void;
  onSelectCue: (id: string | number | null) => void;
  onOpenCaptionsPanel: () => void;
  onDeleteCue?: (sceneIdx: number, cueId: string | number) => void;
  onUpdateCueTiming?: (
    sceneIdx: number,
    cueId: string | number,
    start: number,
    end: number
  ) => void;
  onCommitCueTiming?: () => void;
}) {
  const cueStart = Math.max(0, Number(cue.start ?? cue.start_time ?? 0));
  const cueEnd = Math.max(
    cueStart + MIN_CLIP_DURATION,
    Number(cue.end ?? cue.end_time ?? (cueStart + 1.0))
  );
  const leftPct = (cueStart / sceneDuration) * 100;
  const widthPct = Math.max(4, ((cueEnd - cueStart) / sceneDuration) * 100);

  const { isDragging, getClipProps, getLeftHandleProps, getRightHandleProps } =
    useTimelineClipDrag({
      id: cue.id,
      startTime: cueStart,
      endTime: cueEnd,
      maxDuration: sceneDuration,
      snapTargets,
      containerRef,
      onSnapChange,
      onSelect: () => {
        onSelectScene(sceneIdx);
        onSelectCue(cue.id);
        onOpenCaptionsPanel();
      },
      onUpdateTiming: (id, start, end) => {
        onUpdateCueTiming?.(sceneIdx, id, start, end);
      },
      onCommitTiming: () => {
        onCommitCueTiming?.();
      },
    });

  return (
    <div
      {...getClipProps()}
      style={{
        left: `${Math.max(0, Math.min(96, leftPct))}%`,
        width: `${Math.max(4, Math.min(100, widthPct))}%`,
      }}
      className={`absolute h-4 rounded text-[9px] px-1 flex items-center truncate border select-none group transition-shadow ${
        isDragging
          ? "cursor-grabbing ring-2 ring-sky-400 z-30 shadow-lg"
          : "cursor-grab"
      } ${
        isCueSelected
          ? "bg-sky-500 border-white text-black font-bold z-10 shadow-xs"
          : isCueActiveAtPlayhead
          ? "bg-sky-600/90 border-sky-300 text-white font-semibold shadow-xs"
          : "bg-sky-900/60 border-sky-700/60 text-sky-200 hover:border-sky-400"
      }`}
      title={`${cueStart.toFixed(1)}s - ${cueEnd.toFixed(
        1
      )}s: "${cue.text}" (Drag to move, drag edges to trim)`}
    >
      {/* Left Trim Handle */}
      <div
        {...getLeftHandleProps()}
        className="absolute left-0 top-0 bottom-0 w-2 cursor-ew-resize opacity-0 group-hover:opacity-100 hover:opacity-100 bg-white/40 hover:bg-white rounded-l flex items-center justify-center z-20 transition-opacity"
        title="Trim start time"
      >
        <div className="w-[1px] h-2 bg-slate-900/80" />
      </div>

      <span className="truncate pointer-events-none">{cue.text}</span>

      {/* Edit / Delete Hover Actions */}
      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 hover:opacity-100 transition-opacity ml-auto mr-2 z-20">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onSelectScene(sceneIdx);
            onSelectCue(cue.id);
            onOpenCaptionsPanel();
          }}
          className="p-0.5 rounded hover:bg-white/20 text-slate-300 hover:text-white cursor-pointer"
          title="Edit Caption"
        >
          <Pencil size={8} />
        </button>
        {onDeleteCue && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDeleteCue(sceneIdx, cue.id);
            }}
            className="p-0.5 rounded hover:bg-red-500/30 text-slate-300 hover:text-red-300 cursor-pointer"
            title="Delete Caption"
          >
            <Trash2 size={8} />
          </button>
        )}
      </div>

      {/* Right Trim Handle */}
      <div
        {...getRightHandleProps()}
        className="absolute right-0 top-0 bottom-0 w-2 cursor-ew-resize opacity-0 group-hover:opacity-100 hover:opacity-100 bg-white/40 hover:bg-white rounded-r flex items-center justify-center z-20 transition-opacity"
        title="Trim end time"
      >
        <div className="w-[1px] h-2 bg-slate-900/80" />
      </div>
    </div>
  );
}

function CaptionTimelineSceneLane({
  sc,
  sceneIdx,
  sceneDuration,
  isSelectedScene,
  playbackTime,
  scenes,
  selectedCueId,
  onSelectScene,
  onSelectCue,
  onOpenCaptionsPanel,
  onDeleteCue,
  onUpdateCueTiming,
  onCommitCueTiming,
}: {
  sc: StudioScene;
  sceneIdx: number;
  sceneDuration: number;
  isSelectedScene: boolean;
  playbackTime: number;
  scenes: StudioScene[];
  selectedCueId: string | number | null;
  onSelectScene: (index: number) => void;
  onSelectCue: (id: string | number | null) => void;
  onOpenCaptionsPanel: () => void;
  onDeleteCue?: (sceneIdx: number, cueId: string | number) => void;
  onUpdateCueTiming?: (
    sceneIdx: number,
    cueId: string | number,
    start: number,
    end: number
  ) => void;
  onCommitCueTiming?: () => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cues = (sc.subtitles || []).filter((c: any) => c.enabled !== false);

  const localPlayhead = getScenePlayheadTime(scenes, sceneIdx, playbackTime);
  const snapTargets: number[] = [0.0, sceneDuration];
  if (isSelectedScene && localPlayhead >= 0) {
    snapTargets.push(localPlayhead);
  }

  const [activeSnapTime, setActiveSnapTime] = React.useState<number | null>(null);
  const baseSnapTargets = [0.0, sceneDuration];
  if (isSelectedScene && localPlayhead >= 0) {
    baseSnapTargets.push(localPlayhead);
  }

  const normalizedCues = cues.map((c: any) => ({
    id: c.id,
    start_time: Number(c.start ?? c.start_time ?? 0),
    end_time: Number(c.end ?? c.end_time ?? 1.0),
  }));

  return (
    <div
      onClick={() => onSelectScene(sceneIdx)}
      className="w-full h-full relative"
    >
      {cues.length === 0 ? (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onSelectScene(sceneIdx);
            onOpenCaptionsPanel();
          }}
          className="w-full h-full flex items-center justify-center gap-1 text-[9px] text-sky-400/70 hover:text-sky-200 transition-colors cursor-pointer"
          title={`Add Captions for Scene ${sceneIdx + 1}`}
        >
          <Plus size={10} />
          <span className="truncate">Captions</span>
        </button>
      ) : (
        <div
          ref={containerRef}
          className="w-full h-full relative flex items-center overflow-hidden"
        >
          {cues.map((cue: any, cueIdx: number) => {
            const cueStart = Math.max(0, Number(cue.start || 0));
            const cueEnd = Math.max(
              cueStart + MIN_CLIP_DURATION,
              Number(cue.end || cueStart + 1.0)
            );
            const isCueSelected = cue.id === selectedCueId;
            const isCueActiveAtPlayhead =
              isSelectedScene &&
              playbackTime >= cueStart &&
              playbackTime <= cueEnd;

            const snapTargets = getClipToClipSnapTargets(
              normalizedCues,
              cue.id,
              baseSnapTargets
            );

            return (
              <CaptionTimelineClipItem
                key={cue.id || `cue_${cueIdx}`}
                cue={cue}
                sceneDuration={sceneDuration}
                sceneIdx={sceneIdx}
                isCueSelected={isCueSelected}
                isCueActiveAtPlayhead={isCueActiveAtPlayhead}
                containerRef={containerRef}
                snapTargets={snapTargets}
                onSnapChange={setActiveSnapTime}
                onSelectScene={onSelectScene}
                onSelectCue={onSelectCue}
                onOpenCaptionsPanel={onOpenCaptionsPanel}
                onDeleteCue={onDeleteCue}
                onUpdateCueTiming={onUpdateCueTiming}
                onCommitCueTiming={onCommitCueTiming}
              />
            );
          })}

          {activeSnapTime !== null && (
            <div
              className="absolute top-0 bottom-0 w-[2px] bg-sky-400 z-50 pointer-events-none shadow-[0_0_6px_rgba(56,189,248,0.9)]"
              style={{
                left: `${Math.max(
                  0,
                  Math.min(100, (activeSnapTime / sceneDuration) * 100)
                )}%`,
              }}
            >
              <div className="absolute top-0 -left-1 w-2.5 h-1 bg-sky-300 rounded-xs" />
              <div className="absolute bottom-0 -left-1 w-2.5 h-1 bg-sky-300 rounded-xs" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function CaptionTimelineTrack({
  scenes,
  totalDuration,
  activeSceneIndex,
  playbackTime,
  selectedCueId,
  onSelectScene,
  onSelectCue,
  onOpenCaptionsPanel,
  onDeleteCue,
  onUpdateCueTiming,
  onCommitCueTiming,
}: CaptionTimelineTrackProps) {
  return (
    <div className="h-7 px-2 flex items-center gap-1.5 border-t border-[#131929] bg-[#080c16]">
      {scenes.map((sc, sceneIdx) => {
        const sceneDuration = sc.duration || 5.0;
        const sceneWidthPct =
          totalDuration > 0 ? (sceneDuration / totalDuration) * 100 : 100;
        const isSelectedScene = activeSceneIndex === sceneIdx;

        return (
          <div
            key={sc.id || `scene_cap_${sceneIdx}`}
            style={{ width: `${Math.max(12, sceneWidthPct)}%` }}
            className={`h-5.5 rounded relative flex items-center px-1 truncate transition-all border ${
              isSelectedScene
                ? "bg-sky-950/40 border-sky-600/60"
                : "bg-sky-950/20 border-sky-900/30 hover:border-sky-800/60"
            }`}
          >
            <CaptionTimelineSceneLane
              sc={sc}
              sceneIdx={sceneIdx}
              sceneDuration={sceneDuration}
              isSelectedScene={isSelectedScene}
              playbackTime={playbackTime}
              scenes={scenes}
              selectedCueId={selectedCueId}
              onSelectScene={onSelectScene}
              onSelectCue={onSelectCue}
              onOpenCaptionsPanel={onOpenCaptionsPanel}
              onDeleteCue={onDeleteCue}
              onUpdateCueTiming={onUpdateCueTiming}
              onCommitCueTiming={onCommitCueTiming}
            />
          </div>
        );
      })}
    </div>
  );
}
