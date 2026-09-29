"use client";

import React, { useRef } from "react";
import { Component, Square, Star, Plus, Lock, Pencil, Trash2 } from "lucide-react";
import { StudioScene } from "./VidoAIStudio";
import {
  useTimelineClipDrag,
  getScenePlayheadTime,
  MIN_CLIP_DURATION,
  getClipToClipSnapTargets,
} from "../../lib/timelineUtils";

interface ElementsTimelineTrackProps {
  scenes: StudioScene[];
  totalDuration: number;
  activeSceneIndex: number;
  playbackTime: number;
  selectedElementLayerId: string | null;
  selectedLayerIds?: string[];
  onSelectScene: (index: number) => void;
  onSelectElementLayer: (id: string | null, isAdditive?: boolean) => void;
  onOpenElementsPanel: () => void;
  onDeleteLayer?: (layerId: string) => void;
  onUpdateTiming?: (
    sceneIdx: number,
    layerId: string,
    start: number,
    end: number
  ) => void;
  onCommitTiming?: () => void;
}

function ElementsTimelineClipItem({
  layer,
  sceneDuration,
  sceneIdx,
  isLayerSelected,
  isLayerActiveAtPlayhead,
  containerRef,
  snapTargets,
  onSnapChange,
  onSelectScene,
  onSelectElementLayer,
  onOpenElementsPanel,
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
  onSelectElementLayer: (id: string | null) => void;
  onOpenElementsPanel: () => void;
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
        onSelectElementLayer(layer.id);
        onOpenElementsPanel();
      },
      onUpdateTiming: (id, start, end) => {
        onUpdateTiming?.(sceneIdx, id, start, end);
      },
      onCommitTiming: () => {
        onCommitTiming?.();
      },
    });

  const isShape = layer.type === "shape";
  const elementPreview = layer.name || (isShape ? "Shape" : "Sticker");

  return (
    <div
      {...getClipProps()}
      style={{
        left: `${Math.max(0, Math.min(96, leftPct))}%`,
        width: `${Math.max(4, Math.min(100, widthPct))}%`,
      }}
      className={`absolute h-4 rounded text-[9px] px-1 flex items-center gap-1 truncate border select-none group transition-shadow ${
        isDragging
          ? "cursor-grabbing ring-2 ring-amber-400 z-30 shadow-lg"
          : layer.locked
          ? "cursor-default"
          : "cursor-grab"
      } ${
        isLayerSelected
          ? "bg-amber-500 border-white text-white font-bold z-10 shadow-xs"
          : isLayerActiveAtPlayhead
          ? "bg-amber-600/90 border-amber-300 text-white font-semibold shadow-xs"
          : "bg-amber-900/60 border-amber-700/60 text-amber-200 hover:border-amber-400"
      }`}
      title={`${startTime.toFixed(1)}s - ${endTime.toFixed(
        1
      )}s: "${elementPreview}" (Drag to move, drag edges to trim)`}
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

      {isShape ? (
        <Square size={9} className="flex-shrink-0 pointer-events-none" />
      ) : (
        <Star size={9} className="flex-shrink-0 pointer-events-none" />
      )}
      <span className="truncate pointer-events-none">{elementPreview}</span>
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
            onSelectElementLayer(layer.id);
            onOpenElementsPanel();
          }}
          className="p-0.5 rounded hover:bg-white/20 text-slate-300 hover:text-white cursor-pointer"
          title="Edit Element"
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
            title="Delete Element"
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

function ElementsTimelineSceneLane({
  sc,
  sceneIdx,
  sceneDuration,
  isSelectedScene,
  playbackTime,
  scenes,
  selectedElementLayerId,
  selectedLayerIds,
  onSelectScene,
  onSelectElementLayer,
  onOpenElementsPanel,
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
  selectedElementLayerId: string | null;
  selectedLayerIds?: string[];
  onSelectScene: (index: number) => void;
  onSelectElementLayer: (id: string | null, isAdditive?: boolean) => void;
  onOpenElementsPanel: () => void;
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
  const elementLayers = (sc.layers || []).filter(
    (l: any) =>
      (l.type === "shape" || l.type === "sticker" || l.type === "element") &&
      l.enabled !== false
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
      {elementLayers.length === 0 ? (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onSelectScene(sceneIdx);
            onOpenElementsPanel();
          }}
          className="w-full h-full flex items-center justify-center gap-1 text-[9px] text-amber-400/70 hover:text-amber-200 transition-colors cursor-pointer"
          title={`Add Shape or Sticker for Scene ${sceneIdx + 1}`}
        >
          <Plus size={10} />
          <span className="truncate">Element</span>
        </button>
      ) : (
        <div
          ref={containerRef}
          className="w-full h-full relative flex items-center overflow-hidden"
        >
          {elementLayers.map((layer: any, layerIdx: number) => {
            const startTime = Math.max(0, Number(layer.start_time ?? 0));
            const endTime = Math.max(
              startTime + MIN_CLIP_DURATION,
              Number(layer.end_time ?? sceneDuration)
            );
            const isLayerSelected =
              selectedLayerIds && selectedLayerIds.length > 0
                ? selectedLayerIds.includes(layer.id)
                : layer.id === selectedElementLayerId;
            const isLayerActiveAtPlayhead =
              isSelectedScene &&
              playbackTime >= startTime &&
              playbackTime <= endTime;

            const snapTargets = getClipToClipSnapTargets(
              elementLayers,
              layer.id,
              baseSnapTargets
            );

            return (
              <ElementsTimelineClipItem
                key={layer.id || `element_lane_${layerIdx}`}
                layer={layer}
                sceneDuration={sceneDuration}
                sceneIdx={sceneIdx}
                isLayerSelected={isLayerSelected}
                isLayerActiveAtPlayhead={isLayerActiveAtPlayhead}
                containerRef={containerRef}
                snapTargets={snapTargets}
                onSnapChange={setActiveSnapTime}
                onSelectScene={onSelectScene}
                onSelectElementLayer={onSelectElementLayer}
                onOpenElementsPanel={onOpenElementsPanel}
                onDeleteLayer={onDeleteLayer}
                onUpdateTiming={onUpdateTiming}
                onCommitTiming={onCommitTiming}
              />
            );
          })}

          {activeSnapTime !== null && (
            <div
              className="absolute top-0 bottom-0 w-[2px] bg-amber-400 z-50 pointer-events-none shadow-[0_0_6px_rgba(251,191,36,0.9)]"
              style={{
                left: `${Math.max(
                  0,
                  Math.min(100, (activeSnapTime / sceneDuration) * 100)
                )}%`,
              }}
            >
              <div className="absolute top-0 -left-1 w-2.5 h-1 bg-amber-300 rounded-xs" />
              <div className="absolute bottom-0 -left-1 w-2.5 h-1 bg-amber-300 rounded-xs" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ElementsTimelineTrack({
  scenes,
  totalDuration,
  activeSceneIndex,
  playbackTime,
  selectedElementLayerId,
  selectedLayerIds,
  onSelectScene,
  onSelectElementLayer,
  onOpenElementsPanel,
  onDeleteLayer,
  onUpdateTiming,
  onCommitTiming,
}: ElementsTimelineTrackProps) {
  return (
    <div className="h-7 px-2 flex items-center gap-1.5 border-t border-[#131929] bg-[#070b14]">
      {scenes.map((sc, sceneIdx) => {
        const sceneDuration = sc.duration || 5.0;
        const sceneWidthPct =
          totalDuration > 0 ? (sceneDuration / totalDuration) * 100 : 100;
        const isSelectedScene = activeSceneIndex === sceneIdx;

        return (
          <div
            key={sc.id || `scene_elements_${sceneIdx}`}
            style={{ width: `${Math.max(12, sceneWidthPct)}%` }}
            className={`h-5.5 rounded relative flex items-center px-1 truncate transition-all border ${
              isSelectedScene
                ? "bg-amber-950/40 border-amber-600/60"
                : "bg-amber-950/20 border-amber-900/30 hover:border-amber-800/60"
            }`}
          >
            <ElementsTimelineSceneLane
              sc={sc}
              sceneIdx={sceneIdx}
              sceneDuration={sceneDuration}
              isSelectedScene={isSelectedScene}
              playbackTime={playbackTime}
              scenes={scenes}
              selectedElementLayerId={selectedElementLayerId}
              selectedLayerIds={selectedLayerIds}
              onSelectScene={onSelectScene}
              onSelectElementLayer={onSelectElementLayer}
              onOpenElementsPanel={onOpenElementsPanel}
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
