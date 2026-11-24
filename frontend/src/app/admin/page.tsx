import type { Metadata } from "next";
import AdminPage from "@/components/app/AdminPage";
import AppShell from "@/components/app/AppShell";

export const metadata: Metadata = { title: { absolute: "Admin, chatbot0" }, robots: { index: false } };

export default function Page() {
  return (
    <AppShell adminOnly>
      <AdminPage />
    </AppShell>
  );
}
