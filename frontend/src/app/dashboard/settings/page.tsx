import type { Metadata } from "next";
import AppShell from "@/components/app/AppShell";
import SlackSettings from "@/components/app/SlackSettings";

export const metadata: Metadata = { title: { absolute: "Settings, chatbot0" }, robots: { index: false } };

export default function Page() {
  return (
    <AppShell>
      <h1 className="mb-6 text-2xl font-semibold">Settings</h1>
      <SlackSettings />
    </AppShell>
  );
}
