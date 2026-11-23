import Link from "next/link";
import ChatMock from "@/components/site/ChatMock";
import CtaPanel from "@/components/site/CtaPanel";
import { pageMetadata } from "@/lib/seo";

// AI support agent use case, ported from the old zer0 "support" page (claims chatbot0 cannot back were dropped).
export const metadata = pageMetadata({
  path: "/support",
  title: "AI customer support agent for your website, chatbot0",
  description:
    "chatbot0 answers customers' questions instantly, day and night, from what you tell it about your business, " +
    "and passes the rest to your team. Free to start.",
});

const STATS = [
  ["24/7", "Always on", "Nights, weekends and holidays."],
  ["0", "Time on hold", "Every customer gets a reply straight away. No queue."],
  ["1", "Source of answers", "What you tell it about your business, so answers stay consistent."],
  ["< 5 min", "Setup time", "Paste one line of code and it's live on any website."],
] as const;

export default function Page() {
  return (
    <>
      <section className="pub-hero">
        <div className="pub-wrap pub-hero__grid">
          <div className="pub-hero__copy">
            <p className="pub-label">AI support agent</p>
            <h1 className="pub-title">
              Instant answers for your customers, <span className="pub-accent">24/7.</span>
            </h1>
            <p className="pub-lead">
              chatbot0 answers customers&apos; questions the moment they ask, from what you tell it about your products,
              services and policies. No queue, no hold. The questions that need a person reach your team with the
              conversation attached.
            </p>
            <div className="pub-actions">
              <Link className="pub-btn pub-btn--primary" href="/signup/">
                Sign up for free
              </Link>
              <Link className="pub-btn pub-btn--secondary" href="/pricing/">
                See pricing
              </Link>
            </div>
          </div>
          <ChatMock
            url="yourbusiness.com/help"
            messages={[
              { from: "visitor", text: "What is your return policy?" },
              {
                from: "agent",
                text: "You can return any unused item within 30 days for a full refund. Would you like the team to email you a return label?",
              },
              { from: "visitor", text: "Yes please, it's sam@example.com." },
            ]}
            lead="Request captured · sent to your dashboard"
          />
        </div>
      </section>

      <section className="pub-section" id="what-it-does">
        <div className="pub-wrap">
          <div className="pub-section__head">
            <p className="pub-label">What it does</p>
            <h2 className="pub-heading">The first line of support, always on.</h2>
            <p className="pub-body">
              Customers get an answer straight away. Your team gets fewer repeat questions and a clear handover on the rest.
            </p>
          </div>
          <div className="pub-stats pub-stats--4">
            {STATS.map(([value, label, caption]) => (
              <div key={label} className="pub-stat">
                <p className="pub-stat__value">{value}</p>
                <p className="pub-label">{label}</p>
                <p className="pub-caption">{caption}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="pub-section">
        <div className="pub-wrap pub-split">
          <div>
            <p className="pub-label">Honest by design</p>
            <h2 className="pub-heading">It answers what it knows, and hands over the rest.</h2>
            <p className="pub-body">
              chatbot0 answers from the description of your business you give it when you sign up: products, services,
              opening hours, policies, FAQs. It doesn&apos;t guess.
            </p>
            <p className="pub-body">
              When a customer asks something it can&apos;t answer, it takes their name and contact details so your team can
              follow up, and the request lands in your lead dashboard.
            </p>
          </div>
          <div className="pub-card">
            <h3 className="pub-subheading">Make it yours</h3>
            <p className="pub-body">
              Pick the widget colour when you sign up. Paid plans add priority support and free customisations; Pro adds free
              backend integration.
            </p>
            <div className="pub-actions pub-actions--flush">
              <Link className="pub-btn pub-btn--secondary" href="/pricing/">
                Compare plans
              </Link>
            </div>
          </div>
        </div>
      </section>

      <CtaPanel heading="Give your customers an answer in seconds." subject="chatbot0 support agent">
        Free to start. Live on your site in minutes. Also works as an{" "}
        <Link className="pub-link pub-link--on-ink" href="/sales/">
          AI sales agent
        </Link>
        .
      </CtaPanel>
    </>
  );
}
