import SignupForm from "@/components/signup/SignupForm";
import { FREE_CONVERSATIONS } from "@/content/plans";
import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata({
  path: "/signup",
  title: "Sign up free, chatbot0",
  description:
    "Create your free chatbot0 agent and get the one-line embed script for your website. " +
    `${FREE_CONVERSATIONS} conversations a month free, no card needed.`,
});

export default function Page() {
  return (
    <section className="pub-hero pub-hero--short">
      <div className="pub-wrap pub-signup">
        <SignupForm />
      </div>
    </section>
  );
}
