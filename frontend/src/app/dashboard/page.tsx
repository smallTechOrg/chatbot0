import type { Metadata } from "next";
import AppShell from "@/components/app/AppShell";
import LeadsDashboard from "@/components/app/LeadsDashboard";

export const metadata: Metadata = { title: { absolute: "Leads, chatbot0" }, robots: { index: false } };

export default function Page() {
  return (
    <AppShell>
      <LeadsDashboard />
    </AppShell>
  );
}
