"use client";

import React, { useRef } from "react";
import { Music, Volume2, VolumeX, Repeat, Plus, Pencil, Trash2 } from "lucide-react";
import { AudioTrackItem } from "./MusicPanel";
import {
  useTimelineClipDrag,
  MIN_CLIP_DURATION,
  getClipToClipSnapTargets,
} from "../../lib/timelineUtils";

interface MusicTimelineTrackProps {
  audioTracks: AudioTrackItem[];
  activeTrackId?: string | null;
  totalDuration: number;
  playbackTime?: number;
  onSelectTrack: (trackId: string) => void;
  onOpenMusicPanel: () => void;
  onDeleteTrack?: (trackId: string) => void;
  onUpdateTiming?: (trackId: string, start: number, duration: number) => void;
  onCommitTiming?: () => void;
}

function MusicTimelineClipItem({
  track,
  totalDuration,
  playbackTime,
  isSelected,
  containerRef,
  snapTargets,
  onSnapChange,
  onSelectTrack,
  onOpenMusicPanel,
  onDeleteTrack,
  onUpdateTiming,
  onCommitTiming,
}: {
  track: AudioTrackItem;
  totalDuration: number;
  playbackTime: number;
  isSelected: boolean;
  containerRef: React.RefObject<HTMLDivElement | null>;
  snapTargets: number[];
  onSnapChange?: (target: number | null) => void;
  onSelectTrack: (trackId: string) => void;
  onOpenMusicPanel: () => void;
  onDeleteTrack?: (trackId: string) => void;
  onUpdateTiming?: (trackId: string, start: number, duration: number) => void;
  onCommitTiming?: () => void;
}) {
  const startTime = Math.max(0, Number(track.start_time ?? 0));
  const rawDuration =
    typeof track.duration === "number" && track.duration > 0
      ? track.duration
      : Math.max(MIN_CLIP_DURATION, totalDuration - startTime);
  const endTime = Math.max(
    startTime + MIN_CLIP_DURATION,
    Math.min(totalDuration, startTime + rawDuration)
  );

  const startPct =
    totalDuration > 0 ? (startTime / totalDuration) * 100 : 0;
  const widthPct =
    totalDuration > 0 ? ((endTime - startTime) / totalDuration) * 100 : 100;

  const { isDragging, getClipProps, getLeftHandleProps, getRightHandleProps } =
    useTimelineClipDrag({
      id: track.id,
      startTime,
      endTime,
      maxDuration: totalDuration,
      snapTargets,
      containerRef,
      onSnapChange,
      onSelect: () => {
        onSelectTrack(track.id);
        onOpenMusicPanel();
      },
      onUpdateTiming: (id, start, end) => {
        onUpdateTiming?.(id, start, end - start);
      },
      onCommitTiming: () => {
        onCommitTiming?.();
      },
    });

  const volPct = Math.round((track.volume || 1.0) * 100);

  return (
    <div
      {...getClipProps()}
      style={{
        left: `${Math.max(0, Math.min(96, startPct))}%`,
        width: `${Math.max(4, Math.min(100, widthPct))}%`,
      }}
      className={`absolute h-5.5 rounded text-[10px] px-2 flex items-center justify-between truncate select-none group transition-all border ${
        isDragging
          ? "cursor-grabbing ring-2 ring-blue-400 z-30 shadow-lg"
          : "cursor-grab"
      } ${
        isSelected
          ? "bg-gradient-to-r from-blue-900/60 to-indigo-900/60 border-blue-400 text-white font-semibold shadow-xs"
          : "bg-blue-950/40 border-blue-900/40 text-blue-200 hover:border-blue-700"
      }`}
      title={`${track.name} (${startTime.toFixed(1)}s - ${endTime.toFixed(
        1
      )}s, ${track.muted ? "Muted" : `${volPct}%`}) (Drag to move, edges to trim)`}
    >
      {/* Left Trim Handle */}
      <div
        {...getLeftHandleProps()}
        className="absolute left-0 top-0 bottom-0 w-2 cursor-ew-resize opacity-0 group-hover:opacity-100 hover:opacity-100 bg-white/40 hover:bg-white rounded-l flex items-center justify-center z-20 transition-opacity"
        title="Trim music start offset"
      >
        <div className="w-[1px] h-2.5 bg-slate-900/80" />
      </div>

      <div className="flex items-center gap-1.5 truncate pointer-events-none">
        <Music size={10} className="text-blue-400 flex-shrink-0" />
        <span className="truncate">{track.name}</span>
      </div>

      <div className="flex items-center gap-1 ml-1.5 flex-shrink-0 pointer-events-none">
        {track.loop && (
          <span className="text-[8px] bg-blue-900/70 text-blue-300 px-1 rounded flex items-center gap-0.5">
            <Repeat size={8} /> Loop
          </span>
        )}
        <span
          className={`text-[8px] px-1 rounded font-mono ${
            track.muted
              ? "bg-red-950/80 text-red-300"
              : "bg-black/50 text-slate-300"
          }`}
        >
          {track.muted ? "MUTED" : `${volPct}%`}
        </span>
      </div>

      {/* Edit / Delete Hover Actions */}
      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 hover:opacity-100 transition-opacity ml-auto mr-2 z-20">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onSelectTrack(track.id);
            onOpenMusicPanel();
          }}
          className="p-0.5 rounded hover:bg-white/20 text-slate-300 hover:text-white cursor-pointer"
          title="Edit Music Track"
        >
          <Pencil size={8} />
        </button>
        {onDeleteTrack && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDeleteTrack(track.id);
            }}
            className="p-0.5 rounded hover:bg-red-500/30 text-slate-300 hover:text-red-300 cursor-pointer"
            title="Delete Music Track"
          >
            <Trash2 size={8} />
          </button>
        )}
      </div>

      {/* Right Trim Handle */}
      <div
        {...getRightHandleProps()}
        className="absolute right-0 top-0 bottom-0 w-2 cursor-ew-resize opacity-0 group-hover:opacity-100 hover:opacity-100 bg-white/40 hover:bg-white rounded-r flex items-center justify-center z-20 transition-opacity"
        title="Trim music duration"
      >
        <div className="w-[1px] h-2.5 bg-slate-900/80" />
      </div>
    </div>
  );
}

export default function MusicTimelineTrack({
  audioTracks,
  activeTrackId,
  totalDuration,
  playbackTime = 0,
  onSelectTrack,
  onOpenMusicPanel,
  onDeleteTrack,
  onUpdateTiming,
  onCommitTiming,
}: MusicTimelineTrackProps) {
  const [activeSnapTime, setActiveSnapTime] = React.useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isAnyMuted = audioTracks.some((t) => t.muted || t.volume === 0);

  const baseSnapTargets = [0.0, totalDuration];
  if (playbackTime >= 0 && playbackTime <= totalDuration) {
    baseSnapTargets.push(playbackTime);
  }

  return (
    <div className="h-7 px-2 flex items-center border-t border-[#131929] select-none bg-[#07090f]">
      {audioTracks.length === 0 ? (
        <button
          onClick={onOpenMusicPanel}
          className="w-full h-5.5 rounded border border-dashed border-[#1c2842] hover:border-blue-500/50 hover:bg-blue-950/20 text-slate-500 hover:text-blue-300 text-[10px] font-medium flex items-center justify-center gap-1.5 transition-all cursor-pointer"
        >
          <Plus size={11} />
          <span>Add Background Music</span>
        </button>
      ) : (
        <div
          ref={containerRef}
          className="w-full h-full relative flex items-center overflow-hidden"
        >
          {audioTracks.map((track) => {
            const isSelected = track.id === activeTrackId;
            const snapTargets = getClipToClipSnapTargets(
              audioTracks,
              track.id,
              baseSnapTargets
            );

            return (
              <MusicTimelineClipItem
                key={track.id}
                track={track}
                totalDuration={totalDuration}
                playbackTime={playbackTime}
                isSelected={isSelected}
                containerRef={containerRef}
                snapTargets={snapTargets}
                onSnapChange={setActiveSnapTime}
                onSelectTrack={onSelectTrack}
                onOpenMusicPanel={onOpenMusicPanel}
                onDeleteTrack={onDeleteTrack}
                onUpdateTiming={onUpdateTiming}
                onCommitTiming={onCommitTiming}
              />
            );
          })}

          {activeSnapTime !== null && totalDuration > 0 && (
            <div
              className="absolute top-0 bottom-0 w-[2px] bg-blue-400 z-50 pointer-events-none shadow-[0_0_6px_rgba(96,165,250,0.9)]"
              style={{
                left: `${Math.max(
                  0,
                  Math.min(100, (activeSnapTime / totalDuration) * 100)
                )}%`,
              }}
            >
              <div className="absolute top-0 -left-1 w-2.5 h-1 bg-blue-300 rounded-xs" />
              <div className="absolute bottom-0 -left-1 w-2.5 h-1 bg-blue-300 rounded-xs" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
