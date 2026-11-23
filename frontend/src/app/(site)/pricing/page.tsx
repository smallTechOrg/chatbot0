import Link from "next/link";
import PlansGrid from "@/components/site/PlansGrid";
import { FREE_CONVERSATIONS, LOWEST_PAID_MONTHLY, MAX_YEARLY_SAVING_PCT } from "@/content/plans";
import { mailto } from "@/content/site";
import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata({
  path: "/pricing",
  title: "Pricing, chatbot0",
  description:
    `Simple pricing for chatbot0. Start free with ${FREE_CONVERSATIONS} conversations a month, ` +
    `upgrade from $${LOWEST_PAID_MONTHLY} a month. No hidden fees.`,
});

export default function Page() {
  return (
    <>
      <section className="pub-hero pub-hero--short">
        <div className="pub-wrap">
          <div className="pub-section__head">
            <p className="pub-label">Pricing</p>
            <h1 className="pub-title">
              Flexible plans for <span className="pub-accent">every scale.</span>
            </h1>
            <p className="pub-lead">
              Start free and upgrade as the conversations grow. Save up to {MAX_YEARLY_SAVING_PCT}% when you pay yearly. No
              hidden fees.
            </p>
          </div>
        </div>
      </section>

      <section className="pub-section pub-section--flush">
        <div className="pub-wrap">
          <PlansGrid />
        </div>
      </section>

      <section className="pub-section">
        <div className="pub-wrap pub-split">
          <div>
            <p className="pub-label">Every plan includes</p>
            <h2 className="pub-heading">One agent, ready for your site.</h2>
            <p className="pub-body">
              An embeddable chat agent that answers visitors and captures leads, a built-in dashboard where every lead
              lands, and setup in minutes with one line of code.
            </p>
          </div>
          <div className="pub-card">
            <h3 className="pub-subheading">Questions about plans</h3>
            <p className="pub-body">
              Need a custom setup, a backend integration or help choosing a plan? Write to us and a person will reply.
            </p>
            <div className="pub-actions pub-actions--flush">
              <Link className="pub-btn pub-btn--primary" href="/signup/">
                Sign up for free
              </Link>
              <a className="pub-btn pub-btn--secondary" href={mailto("chatbot0 pricing")}>
                Email us
              </a>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
