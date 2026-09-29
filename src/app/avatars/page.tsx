"use client";

import React from "react";
import { DashboardContent } from "../page";

export default function AvatarsPage() {
  return (
    <DashboardContent
      initialView="avatars"
      initialActiveRailTab="avatar"
      initialAvatarSection="avatars"
    />
  );
}
