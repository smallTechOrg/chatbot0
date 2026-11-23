import Link from "next/link";
import CtaPanel from "@/components/site/CtaPanel";
import { INDUSTRIES, type Industry } from "@/content/industries";
import { mailto } from "@/content/site";

/** Where an industry card links to besides its text, if anywhere. */
function MoreLink({ slug }: { slug: string }) {
  if (slug === "sales")
    return (
      <Link className="pub-link pub-card__more" href="/sales/">
        The AI sales agent
      </Link>
    );
  if (slug === "customer-service")
    return (
      <Link className="pub-link pub-card__more" href="/support/">
        The AI support agent
      </Link>
    );
  if (slug === "enterprises")
    return (
      <a className="pub-link pub-card__more" href={mailto("chatbot0 custom setup")}>
        Talk to us
      </a>
    );
  return null;
}

/** The industries page, with one entry highlighted when `selected` is given. */
export default function IndustriesView({ selected }: { selected?: Industry }) {
  return (
    <>
      <section className="pub-hero pub-hero--short">
        <div className="pub-wrap">
          <div className="pub-section__head">
            <p className="pub-label">Industries</p>
            {selected ? (
              <>
                <h1 className="pub-title">
                  chatbot0 for <span className="pub-accent">{selected.name}.</span>
                </h1>
                <p className="pub-lead">
                  {selected.pitch}{" "}
                  <a className="pub-link" href={`#${selected.slug}`}>
                    See how
                  </a>
                  .
                </p>
              </>
            ) : (
              <>
                <h1 className="pub-title">
                  One agent, shaped to <span className="pub-accent">your business.</span>
                </h1>
                <p className="pub-lead">
                  chatbot0 learns your business from the description you give it, so it speaks your customers&apos; language,
                  whatever you do.
                </p>
              </>
            )}
            <div className="pub-actions pub-actions--flush">
              <Link className="pub-btn pub-btn--primary" href="/signup/">
                Sign up for free
              </Link>
              <Link className="pub-btn pub-btn--secondary" href="/pricing/">
                See pricing
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="pub-section pub-section--flush" id="industries">
        <div className="pub-wrap">
          <div className="pub-cards pub-cards--3">
            {INDUSTRIES.map((industry) => {
              const current = industry === selected;
              return (
                <article
                  key={industry.slug}
                  className={`pub-card${current ? " pub-card--current" : ""}`}
                  id={industry.slug}
                  aria-current={current ? "true" : undefined}
                >
                  <p className="pub-label">{industry.name}</p>
                  <h2 className="pub-subheading">{industry.feature}</h2>
                  <p className="pub-body">{industry.desc}</p>
                  <MoreLink slug={industry.slug} />
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <CtaPanel heading="Don't see your industry?" subject="chatbot0 for my industry">
        If your customers ask questions, chatbot0 can answer them. Describe your business when you sign up and it takes it from
        there.
      </CtaPanel>
    </>
  );
}
