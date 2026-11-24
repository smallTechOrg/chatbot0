import type { Metadata } from "next";
import { Suspense } from "react";
import AcceptForm from "@/components/app/AcceptForm";

export const metadata: Metadata = { title: { absolute: "Choose your password, chatbot0" }, robots: { index: false }, referrer: "no-referrer" };

export default function Page() {
  // useSearchParams needs a Suspense boundary in a static export.
  return (
    <Suspense>
      <AcceptForm />
    </Suspense>
  );
}
