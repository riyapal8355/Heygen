"use client";

import React from "react";
import VideoAgentWorkspace, {
  VideoAgentGenerationContext,
  VideoAgentWorkspaceProps,
} from "./VideoAgentWorkspace";

export type { VideoAgentGenerationContext };

export interface VideoAgentProps extends VideoAgentWorkspaceProps {}

export default function VideoAgent(props: VideoAgentProps) {
  return <VideoAgentWorkspace {...props} />;
}
