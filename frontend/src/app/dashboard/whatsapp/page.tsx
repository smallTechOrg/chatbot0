import type { Metadata } from "next";
import AppShell from "@/components/app/AppShell";
import WhatsAppPage from "@/components/app/WhatsAppPage";

export const metadata: Metadata = { title: { absolute: "WhatsApp, chatbot0" }, robots: { index: false } };

export default function Page() {
  return (
    <AppShell>
      <WhatsAppPage />
    </AppShell>
  );
}
