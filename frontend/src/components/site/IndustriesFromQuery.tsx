"use client";

import { useSearchParams } from "next/navigation";
import { findIndustry } from "@/content/industries";
import IndustriesView from "./IndustriesView";

/** ?industry=<name> (old zer0 links) highlights one entry, client-side. */
export default function IndustriesFromQuery() {
  return <IndustriesView selected={findIndustry(useSearchParams().get("industry"))} />;
}
