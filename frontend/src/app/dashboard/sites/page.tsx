import type { Metadata } from "next";
import AppShell from "@/components/app/AppShell";
import SitesPage from "@/components/app/SitesPage";

export const metadata: Metadata = { title: { absolute: "Websites, chatbot0" }, robots: { index: false } };

export default function Page() {
  return (
    <AppShell>
      <SitesPage />
    </AppShell>
  );
}
