import CtaPanel from "@/components/site/CtaPanel";
import { ZER0_URL } from "@/content/site";
import { pageMetadata } from "@/lib/seo";

export const metadata = pageMetadata({
  path: "/about",
  title: "About chatbot0, by smallTech",
  description:
    "chatbot0 is the AI chat agent from smallTech, the company behind Zer0. AI for Everyone: the tools large " +
    "companies use, simple and affordable for any business.",
});

export default function Page() {
  return (
    <>
      <section className="pub-hero pub-hero--short">
        <div className="pub-wrap">
          <div className="pub-section__head">
            <p className="pub-label">About</p>
            <h1 className="pub-title">
              chatbot0 is built by smallTech. <span className="pub-accent">AI for Everyone.</span>
            </h1>
            <p className="pub-lead">
              smallTech builds AI agents that put the tools large companies use within reach of any business: simple to set
              up, affordable to run, with people making the calls.
            </p>
          </div>
        </div>
      </section>

      <section className="pub-section pub-section--flush">
        <div className="pub-wrap">
          <div className="pub-cards pub-cards--3">
            <article className="pub-card">
              <p className="pub-card__num">chatbot0</p>
              <h2 className="pub-subheading">The AI chat agent</h2>
              <p className="pub-body">
                Sits on your website, answers visitors, captures leads and hands you the warm conversation. Free to start,
                live in minutes, no code.
              </p>
            </article>
            <a className="pub-card pub-card--link" href={ZER0_URL}>
              <p className="pub-card__num">Zer0</p>
              <h2 className="pub-subheading">The agent suite</h2>
              <p className="pub-body">
                chatbot0 is one of the Zer0 agents. Agents do the repetitive steps; people make the calls.
              </p>
              <span className="pub-link">zer0.smalltech.in</span>
            </a>
            <a className="pub-card pub-card--link" href="https://smalltech.in">
              <p className="pub-card__num">smallTech</p>
              <h2 className="pub-subheading">The company</h2>
              <p className="pub-body">The team behind Zer0 and chatbot0, building AI for Everyone.</p>
              <span className="pub-link">smalltech.in</span>
            </a>
          </div>
        </div>
      </section>

      <CtaPanel heading="Talk to a person." subject="chatbot0">
        Questions, custom setups or partnerships: write to us and someone from the team will reply.
      </CtaPanel>
    </>
  );
}
