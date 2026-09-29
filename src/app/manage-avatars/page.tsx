"use client";

import React from "react";
import { DashboardContent } from "../page";

export default function ManageAvatarsPage() {
  return (
    <DashboardContent
      initialView="avatars"
      initialActiveRailTab="avatar"
      initialAvatarSection="avatars"
    />
  );
}
