import Link from "next/link";
import ChatMock from "@/components/site/ChatMock";
import PlansGrid from "@/components/site/PlansGrid";
import CtaPanel from "@/components/site/CtaPanel";
import { FREE_CONVERSATIONS } from "@/content/plans";
import { CONTACT_EMAIL, SITE_URL, ZER0_URL } from "@/content/site";
import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata({
  path: "/",
  title: "chatbot0, the AI chat agent for business websites",
  description:
    "chatbot0 sits on your website, answers visitors, captures leads and hands you the warm conversation. " +
    "Free plan with 200 conversations a month. No code. By smallTech.",
});

const JSON_LD = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "chatbot0",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web Browser",
  url: `${SITE_URL}/`,
  description:
    "An AI chat agent for business websites: answers visitors, captures leads and hands over the warm conversation. No code required.",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
    description: `Free plan with ${FREE_CONVERSATIONS} conversations a month`,
  },
  author: {
    "@type": "Organization",
    name: "smallTech",
    url: "https://smalltech.in",
    contactPoint: { "@type": "ContactPoint", email: CONTACT_EMAIL, contactType: "customer support" },
  },
};

const FEED = [
  ["Alex Rivera", "alex@rivera.example"],
  ["Sarah Chen", "s.chen@dev.example"],
  ["Marcus Wright", "m.wright@xyz.example"],
  ["Elena Rossi", "elena@rossi.example"],
] as const;

const HOW = [
  ["01", "Answers visitors", "Responds instantly to questions about your products, services and FAQs, in plain, human language."],
  ["02", "Captures leads", "Asks the right questions and captures contact details straight into your lead dashboard, while you sleep."],
  ["03", "Hands over the warm conversation", "When a visitor is ready to buy, you pick it up with the whole conversation in hand."],
] as const;

export default function Page() {
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD) }} />
      <section className="pub-hero">
        <div className="pub-wrap pub-hero__grid">
          <div className="pub-hero__copy">
            <p className="pub-label">chatbot0 by Zer0</p>
            <h1 className="pub-title">
              The AI chat agent for your website, built for the <span className="pub-accent">agentic age.</span>
            </h1>
            <p className="pub-lead">
              Contact forms lose customers. chatbot0 sits on your site, answers visitors&apos; questions, captures their
              details and hands you the warm conversation. You make the calls.
            </p>
            <div className="pub-actions">
              <Link className="pub-btn pub-btn--primary" href="/signup/">
                Sign up for free
              </Link>
              <Link className="pub-btn pub-btn--secondary" href="/pricing/">
                See pricing
              </Link>
            </div>
            <ul className="pub-pills" aria-label="Highlights">
              <li>Free plan: {FREE_CONVERSATIONS} conversations a month</li>
              <li>Live in under 5 minutes</li>
              <li>No code</li>
            </ul>
          </div>
          <ChatMock
            url="yourbusiness.com"
            messages={[
              { from: "visitor", text: "In how many days can I expect the shipment for my order?" },
              {
                from: "agent",
                text: "You should receive your order within 5–7 business days. Can I take your email so we can send you the tracking link?",
              },
              { from: "visitor", text: "Sure, it's priya@example.com. And what is your return policy?" },
            ]}
            lead="New lead captured · sent to your dashboard"
          />
        </div>
      </section>

      <section className="pub-section" id="how">
        <div className="pub-wrap">
          <div className="pub-section__head">
            <p className="pub-label">How it works</p>
            <h2 className="pub-heading">From a static page to a conversation that sells, in minutes.</h2>
            <p className="pub-body">
              chatbot0 works the front of your funnel around the clock, so the conversations that reach you are the ones
              worth having.
            </p>
          </div>
          <div className="pub-cards pub-cards--3">
            {HOW.map(([num, title, body]) => (
              <article key={num} className="pub-card">
                <p className="pub-card__num">{num}</p>
                <h3 className="pub-subheading">{title}</h3>
                <p className="pub-body">{body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="pub-section pub-section--tight">
        <div className="pub-wrap">
          <div className="pub-panel">
            <div className="pub-panel__grid">
              <div>
                <p className="pub-label pub-label--gold">Getting started</p>
                <h2 className="pub-heading pub-heading--on-ink">Live on your site in three steps.</h2>
                <ol className="pub-steps">
                  <li>
                    <span>1</span>
                    <div>
                      <strong>Sign up free.</strong> Tell chatbot0 about your business.
                    </div>
                  </li>
                  <li>
                    <span>2</span>
                    <div>
                      <strong>Paste one line of code.</strong> It goes live on any website.
                    </div>
                  </li>
                  <li>
                    <span>3</span>
                    <div>
                      <strong>Watch the leads arrive.</strong> Every one lands in the built-in dashboard.
                    </div>
                  </li>
                </ol>
                <Link className="pub-btn pub-btn--primary" href="/signup/">
                  Get started free
                </Link>
              </div>
              <div className="pub-feed" aria-label="Example lead dashboard">
                <p className="pub-feed__title">Example: your lead dashboard</p>
                <ul>
                  {FEED.map(([name, mail]) => (
                    <li key={name}>
                      <span className="pub-feed__name">{name}</span>
                      <span className="pub-feed__mail">{mail}</span>
                      <span className="pub-feed__tag">New</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="pub-section">
        <div className="pub-wrap pub-split">
          <div>
            <p className="pub-label">Why businesses use it</p>
            <h2 className="pub-heading">An AI front desk, at a price any business can afford.</h2>
            <p className="pub-body">
              chatbot0 is an embeddable AI chat agent for any business with a website. Enterprise chatbots take months of
              setup. chatbot0 goes live on your website in minutes, with no code.
            </p>
            <p className="pub-body">
              It learns your products, services and FAQs, answers customer questions and captures leads 24 hours a day, 7
              days a week, even when your team is offline.
            </p>
            <p className="pub-body">
              From e-commerce to real estate, healthcare and education (
              <Link className="pub-link" href="/industries/">
                see industries
              </Link>
              ), it gives your visitors a premium experience without an enterprise budget. Start free with{" "}
              {FREE_CONVERSATIONS} conversations a month, or upgrade to Pro for unlimited conversations and backend
              integrations.
            </p>
          </div>
          <div className="pub-stats">
            <div className="pub-stat">
              <p className="pub-stat__value">&lt; 5 min</p>
              <p className="pub-label">Setup time</p>
              <p className="pub-caption">Paste one line of code and you&apos;re live on any website.</p>
            </div>
            <div className="pub-stat">
              <p className="pub-stat__value">Any</p>
              <p className="pub-label">Industry</p>
              <p className="pub-caption">From retail to healthcare, it learns your business.</p>
            </div>
            <div className="pub-stat">
              <p className="pub-stat__value">{FREE_CONVERSATIONS}</p>
              <p className="pub-label">Free conversations</p>
              <p className="pub-caption">Every month, on the free plan. No credit card required.</p>
            </div>
            <div className="pub-stat">
              <p className="pub-stat__value">24/7</p>
              <p className="pub-label">Always on</p>
              <p className="pub-caption">Nights, weekends and holidays.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="pub-section" id="pricing">
        <div className="pub-wrap">
          <div className="pub-section__head">
            <p className="pub-label">Plans</p>
            <h2 className="pub-heading">Flexible plans for every scale.</h2>
            <p className="pub-body">
              Start free and upgrade when the conversations grow.{" "}
              <Link className="pub-link" href="/pricing/">
                See full pricing
              </Link>
              .
            </p>
          </div>
          <PlansGrid />
        </div>
      </section>

      <section className="pub-section" id="zer0">
        <div className="pub-wrap">
          <div className="pub-suite">
            <div>
              <p className="pub-label">Part of the Zer0 suite</p>
              <h2 className="pub-heading">AI for Everyone: agentic AI, put to work.</h2>
              <p className="pub-body">
                chatbot0 is one of the Zer0 agents from smallTech. Agents do the repetitive steps, people make the calls,
                and every business gets the AI tools enterprises use, simply and affordably.
              </p>
            </div>
            <div className="pub-actions pub-actions--flush">
              <a className="pub-btn pub-btn--secondary" href={ZER0_URL}>
                Explore Zer0
              </a>
            </div>
          </div>
        </div>
      </section>

      <CtaPanel heading="Put chatbot0 on your website today." subject="chatbot0">
        Free to start. Live on your site in minutes.
      </CtaPanel>
    </>
  );
}
