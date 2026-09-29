"use client";

import React, { useRef } from "react";
import { Type, Plus, Lock, Pencil, Trash2 } from "lucide-react";
import { StudioScene } from "./VidoAIStudio";
import {
  useTimelineClipDrag,
  getScenePlayheadTime,
  MIN_CLIP_DURATION,
  getClipToClipSnapTargets,
} from "../../lib/timelineUtils";

interface TextTimelineTrackProps {
  scenes: StudioScene[];
  totalDuration: number;
  activeSceneIndex: number;
  playbackTime: number;
  selectedTextLayerId: string | null;
  selectedLayerIds?: string[];
  onSelectScene: (index: number) => void;
  onSelectTextLayer: (id: string | null, isAdditive?: boolean) => void;
  onOpenTextPanel: () => void;
  onDeleteLayer?: (layerId: string) => void;
  onUpdateTiming?: (
    sceneIdx: number,
    layerId: string,
    start: number,
    end: number
  ) => void;
  onCommitTiming?: () => void;
}

function TextTimelineClipItem({
  layer,
  sceneDuration,
  sceneIdx,
  isLayerSelected,
  isLayerActiveAtPlayhead,
  containerRef,
  snapTargets,
  onSnapChange,
  onSelectScene,
  onSelectTextLayer,
  onOpenTextPanel,
  onDeleteLayer,
  onUpdateTiming,
  onCommitTiming,
}: {
  layer: any;
  sceneDuration: number;
  sceneIdx: number;
  isLayerSelected: boolean;
  isLayerActiveAtPlayhead: boolean;
  containerRef: React.RefObject<HTMLDivElement | null>;
  snapTargets: number[];
  onSnapChange?: (target: number | null) => void;
  onSelectScene: (index: number) => void;
  onSelectTextLayer: (id: string | null) => void;
  onOpenTextPanel: () => void;
  onDeleteLayer?: (layerId: string) => void;
  onUpdateTiming?: (
    sceneIdx: number,
    layerId: string,
    start: number,
    end: number
  ) => void;
  onCommitTiming?: () => void;
}) {
  const startTime = Math.max(0, Number(layer.start_time ?? 0));
  const endTime = Math.max(
    startTime + MIN_CLIP_DURATION,
    Number(layer.end_time ?? sceneDuration)
  );
  const leftPct = (startTime / sceneDuration) * 100;
  const widthPct = Math.max(4, ((endTime - startTime) / sceneDuration) * 100);

  const { isDragging, getClipProps, getLeftHandleProps, getRightHandleProps } =
    useTimelineClipDrag({
      id: layer.id,
      startTime,
      endTime,
      maxDuration: sceneDuration,
      snapTargets,
      containerRef,
      locked: layer.locked === true,
      onSnapChange,
      onSelect: () => {
        onSelectScene(sceneIdx);
        onSelectTextLayer(layer.id);
        onOpenTextPanel();
      },
      onUpdateTiming: (id, start, end) => {
        onUpdateTiming?.(sceneIdx, id, start, end);
      },
      onCommitTiming: () => {
        onCommitTiming?.();
      },
    });

  const textPreview = layer.content?.text || layer.name || "Text";

  return (
    <div
      {...getClipProps()}
      style={{
        left: `${Math.max(0, Math.min(96, leftPct))}%`,
        width: `${Math.max(4, Math.min(100, widthPct))}%`,
      }}
      className={`absolute h-4 rounded text-[9px] px-1 flex items-center gap-1 truncate border select-none group transition-shadow ${
        isDragging
          ? "cursor-grabbing ring-2 ring-purple-400 z-30 shadow-lg"
          : layer.locked
          ? "cursor-default"
          : "cursor-grab"
      } ${
        isLayerSelected
          ? "bg-purple-500 border-white text-white font-bold z-10 shadow-xs"
          : isLayerActiveAtPlayhead
          ? "bg-purple-600/90 border-purple-300 text-white font-semibold shadow-xs"
          : "bg-purple-900/60 border-purple-700/60 text-purple-200 hover:border-purple-400"
      }`}
      title={`${startTime.toFixed(1)}s - ${endTime.toFixed(
        1
      )}s: "${textPreview}" (Drag to move, drag edges to trim)`}
    >
      {/* Left Trim Handle */}
      {!layer.locked && (
        <div
          {...getLeftHandleProps()}
          className="absolute left-0 top-0 bottom-0 w-2 cursor-ew-resize opacity-0 group-hover:opacity-100 hover:opacity-100 bg-white/40 hover:bg-white rounded-l flex items-center justify-center z-20 transition-opacity"
          title="Trim start time"
        >
          <div className="w-[1px] h-2 bg-slate-900/80" />
        </div>
      )}

      <Type size={9} className="flex-shrink-0 pointer-events-none text-purple-300" />
      <span className="truncate pointer-events-none">{textPreview}</span>
      {layer.locked && (
        <span title="Locked" className="flex-shrink-0 ml-auto pointer-events-none">
          <Lock size={8} className="text-amber-300" />
        </span>
      )}

      {/* Edit / Delete Hover Actions */}
      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 hover:opacity-100 transition-opacity ml-auto mr-2 z-20">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onSelectScene(sceneIdx);
            onSelectTextLayer(layer.id);
            onOpenTextPanel();
          }}
          className="p-0.5 rounded hover:bg-white/20 text-slate-300 hover:text-white cursor-pointer"
          title="Edit Text"
        >
          <Pencil size={8} />
        </button>
        {onDeleteLayer && !layer.locked && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDeleteLayer(layer.id);
            }}
            className="p-0.5 rounded hover:bg-red-500/30 text-slate-300 hover:text-red-300 cursor-pointer"
            title="Delete Text"
          >
            <Trash2 size={8} />
          </button>
        )}
      </div>

      {/* Right Trim Handle */}
      {!layer.locked && (
        <div
          {...getRightHandleProps()}
          className="absolute right-0 top-0 bottom-0 w-2 cursor-ew-resize opacity-0 group-hover:opacity-100 hover:opacity-100 bg-white/40 hover:bg-white rounded-r flex items-center justify-center z-20 transition-opacity"
          title="Trim end time"
        >
          <div className="w-[1px] h-2 bg-slate-900/80" />
        </div>
      )}
    </div>
  );
}

function TextTimelineSceneLane({
  sc,
  sceneIdx,
  sceneDuration,
  isSelectedScene,
  playbackTime,
  scenes,
  selectedTextLayerId,
  selectedLayerIds,
  onSelectScene,
  onSelectTextLayer,
  onOpenTextPanel,
  onDeleteLayer,
  onUpdateTiming,
  onCommitTiming,
}: {
  sc: StudioScene;
  sceneIdx: number;
  sceneDuration: number;
  isSelectedScene: boolean;
  playbackTime: number;
  scenes: StudioScene[];
  selectedTextLayerId: string | null;
  selectedLayerIds?: string[];
  onSelectScene: (index: number) => void;
  onSelectTextLayer: (id: string | null, isAdditive?: boolean) => void;
  onOpenTextPanel: () => void;
  onDeleteLayer?: (layerId: string) => void;
  onUpdateTiming?: (
    sceneIdx: number,
    layerId: string,
    start: number,
    end: number
  ) => void;
  onCommitTiming?: () => void;
}) {
  const [activeSnapTime, setActiveSnapTime] = React.useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const textLayers = (sc.layers || []).filter(
    (l: any) => l.type === "text" && l.enabled !== false
  );

  const localPlayhead = getScenePlayheadTime(scenes, sceneIdx, playbackTime);
  const baseSnapTargets: number[] = [0.0, sceneDuration];
  if (isSelectedScene && localPlayhead >= 0) {
    baseSnapTargets.push(localPlayhead);
  }

  return (
    <div
      onClick={() => onSelectScene(sceneIdx)}
      className="w-full h-full relative"
    >
      {textLayers.length === 0 ? (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onSelectScene(sceneIdx);
            onOpenTextPanel();
          }}
          className="w-full h-full flex items-center justify-center gap-1 text-[9px] text-purple-400/70 hover:text-purple-200 transition-colors cursor-pointer"
          title={`Add Text for Scene ${sceneIdx + 1}`}
        >
          <Plus size={10} />
          <span className="truncate">Text</span>
        </button>
      ) : (
        <div
          ref={containerRef}
          className="w-full h-full relative flex items-center overflow-hidden"
        >
          {textLayers.map((layer: any, layerIdx: number) => {
            const startTime = Math.max(0, Number(layer.start_time ?? 0));
            const endTime = Math.max(
              startTime + MIN_CLIP_DURATION,
              Number(layer.end_time ?? sceneDuration)
            );
            const isLayerSelected =
              selectedLayerIds && selectedLayerIds.length > 0
                ? selectedLayerIds.includes(layer.id)
                : layer.id === selectedTextLayerId;
            const isLayerActiveAtPlayhead =
              isSelectedScene &&
              playbackTime >= startTime &&
              playbackTime <= endTime;

            const snapTargets = getClipToClipSnapTargets(
              textLayers,
              layer.id,
              baseSnapTargets
            );

            return (
              <TextTimelineClipItem
                key={layer.id || `txt_lane_${layerIdx}`}
                layer={layer}
                sceneDuration={sceneDuration}
                sceneIdx={sceneIdx}
                isLayerSelected={isLayerSelected}
                isLayerActiveAtPlayhead={isLayerActiveAtPlayhead}
                containerRef={containerRef}
                snapTargets={snapTargets}
                onSnapChange={setActiveSnapTime}
                onSelectScene={onSelectScene}
                onSelectTextLayer={onSelectTextLayer}
                onOpenTextPanel={onOpenTextPanel}
                onDeleteLayer={onDeleteLayer}
                onUpdateTiming={onUpdateTiming}
                onCommitTiming={onCommitTiming}
              />
            );
          })}

          {activeSnapTime !== null && (
            <div
              className="absolute top-0 bottom-0 w-[2px] bg-purple-400 z-50 pointer-events-none shadow-[0_0_6px_rgba(192,132,252,0.9)]"
              style={{
                left: `${Math.max(
                  0,
                  Math.min(100, (activeSnapTime / sceneDuration) * 100)
                )}%`,
              }}
            >
              <div className="absolute top-0 -left-1 w-2.5 h-1 bg-purple-300 rounded-xs" />
              <div className="absolute bottom-0 -left-1 w-2.5 h-1 bg-purple-300 rounded-xs" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function TextTimelineTrack({
  scenes,
  totalDuration,
  activeSceneIndex,
  playbackTime,
  selectedTextLayerId,
  selectedLayerIds,
  onSelectScene,
  onSelectTextLayer,
  onOpenTextPanel,
  onDeleteLayer,
  onUpdateTiming,
  onCommitTiming,
}: TextTimelineTrackProps) {
  return (
    <div className="h-7 px-2 flex items-center gap-1.5 border-t border-[#131929] bg-[#080c16]">
      {scenes.map((sc, sceneIdx) => {
        const sceneDuration = sc.duration || 5.0;
        const sceneWidthPct =
          totalDuration > 0 ? (sceneDuration / totalDuration) * 100 : 100;
        const isSelectedScene = activeSceneIndex === sceneIdx;

        return (
          <div
            key={sc.id || `scene_txt_${sceneIdx}`}
            style={{ width: `${Math.max(12, sceneWidthPct)}%` }}
            className={`h-5.5 rounded relative flex items-center px-1 truncate transition-all border ${
              isSelectedScene
                ? "bg-purple-950/40 border-purple-600/60"
                : "bg-purple-950/20 border-purple-900/30 hover:border-purple-800/60"
            }`}
          >
            <TextTimelineSceneLane
              sc={sc}
              sceneIdx={sceneIdx}
              sceneDuration={sceneDuration}
              isSelectedScene={isSelectedScene}
              playbackTime={playbackTime}
              scenes={scenes}
              selectedTextLayerId={selectedTextLayerId}
              selectedLayerIds={selectedLayerIds}
              onSelectScene={onSelectScene}
              onSelectTextLayer={onSelectTextLayer}
              onOpenTextPanel={onOpenTextPanel}
              onDeleteLayer={onDeleteLayer}
              onUpdateTiming={onUpdateTiming}
              onCommitTiming={onCommitTiming}
            />
          </div>
        );
      })}
    </div>
  );
}
