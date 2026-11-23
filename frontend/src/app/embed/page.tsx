import { Suspense } from "react";
import Widget from "@/components/widget/Widget";

// Shown inside the iframe that embed.js adds to a customer's page.
export default function Page() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <Widget />
    </Suspense>
  );
}
