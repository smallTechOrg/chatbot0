import Link from "next/link";
import ChatMock from "@/components/site/ChatMock";
import CtaPanel from "@/components/site/CtaPanel";
import { pageMetadata } from "@/lib/seo";

// AI sales agent use case, ported from the old zer0 "sales" page (claims chatbot0 cannot back were dropped).
export const metadata = pageMetadata({
  path: "/sales",
  title: "AI sales agent for your website, chatbot0",
  description:
    "chatbot0 talks to every visitor, answers questions about what you sell, asks the qualifying questions " +
    "and sends warm leads to your dashboard. Free to start.",
});

const WHAT = [
  [
    "01",
    "Qualifies as it talks",
    "Works out what each visitor needs, matches it to what you offer and asks the follow-up questions, so you know who is worth a call.",
  ],
  [
    "02",
    "Captures every lead",
    "Collects name, email or phone as part of the conversation, and every lead lands in your built-in lead dashboard.",
  ],
  [
    "03",
    "Hands over the warm conversation",
    "Asked for a meeting or a quote, it takes the visitor's details so your team can follow up with the whole conversation in hand.",
  ],
] as const;

export default function Page() {
  return (
    <>
      <section className="pub-hero">
        <div className="pub-wrap pub-hero__grid">
          <div className="pub-hero__copy">
            <p className="pub-label">AI sales agent</p>
            <h1 className="pub-title">
              Close more deals from the visitors <span className="pub-accent">you already have.</span>
            </h1>
            <p className="pub-lead">
              chatbot0 talks to every visitor, answers questions about what you sell, asks the questions your sales team
              would ask and captures contact details. Your team picks up the warm leads, day or night.
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
            url="yourbusiness.com/pricing"
            messages={[
              { from: "visitor", text: "Do you do installations for offices, or only homes?" },
              {
                from: "agent",
                text: "We do both. How many rooms are you looking to fit out, and when would you like to start?",
              },
              { from: "visitor", text: "About 12, ideally next month. Can someone call me? I'm Dev, 98765 43210." },
            ]}
            lead="Qualified lead · sent to your dashboard"
          />
        </div>
      </section>

      <section className="pub-section" id="what-it-does">
        <div className="pub-wrap">
          <div className="pub-section__head">
            <p className="pub-label">What it does</p>
            <h2 className="pub-heading">A salesperson on every page, who never takes a day off.</h2>
            <p className="pub-body">
              Contact forms wait for visitors to come back. chatbot0 starts the conversation while they&apos;re still
              interested.
            </p>
          </div>
          <div className="pub-cards pub-cards--3">
            {WHAT.map(([num, title, body]) => (
              <article key={num} className="pub-card">
                <p className="pub-card__num">{num}</p>
                <h3 className="pub-subheading">{title}</h3>
                <p className="pub-body">{body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="pub-section">
        <div className="pub-wrap pub-split">
          <div>
            <p className="pub-label">Your pitch, not a script</p>
            <h2 className="pub-heading">It sells what you sell.</h2>
            <p className="pub-body">
              When you sign up, describe your business: what you offer, who it&apos;s for, and what makes you different.
              chatbot0 uses it in every conversation. The more detail you give, the better it sells.
            </p>
            <p className="pub-body">
              It doesn&apos;t make things up. When a visitor asks something you haven&apos;t covered, it takes their details
              so a person can answer.
            </p>
          </div>
          <div className="pub-card">
            <h3 className="pub-subheading">Leads in your own systems</h3>
            <p className="pub-body">
              Every plan includes the lead dashboard. The Pro plan adds free backend integration, so leads can go where your
              team already works.
            </p>
            <div className="pub-actions pub-actions--flush">
              <Link className="pub-btn pub-btn--secondary" href="/pricing/#plan-pro">
                See the Pro plan
              </Link>
            </div>
          </div>
        </div>
      </section>

      <CtaPanel heading="Put an AI sales agent on your website today." subject="chatbot0 sales agent">
        Free to start. Live on your site in minutes. Also handles{" "}
        <Link className="pub-link pub-link--on-ink" href="/support/">
          customer support
        </Link>
        .
      </CtaPanel>
    </>
  );
}
