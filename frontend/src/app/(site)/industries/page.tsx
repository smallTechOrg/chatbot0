import { Suspense } from "react";
import IndustriesFromQuery from "@/components/site/IndustriesFromQuery";
import IndustriesView from "@/components/site/IndustriesView";
import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata({
  path: "/industries",
  title: "chatbot0 for your industry",
  description:
    "How businesses in e-commerce, education, healthcare, insurance, real estate, recruitment and more use " +
    "chatbot0 to answer visitors and capture leads.",
});

export default function Page() {
  // useSearchParams needs a Suspense boundary in a static export, where the page is built without a query
  // string. The fallback is the full page, so the exported HTML carries the content for crawlers.
  return (
    <Suspense fallback={<IndustriesView />}>
      <IndustriesFromQuery />
    </Suspense>
  );
}
