import Link from "next/link";
import { CONTACT_EMAIL, mailto } from "@/content/site";

interface Props {
  heading: string;
  /** Body text; may contain links. */
  children: React.ReactNode;
  /** Subject of the "Email" button's message. */
  subject: string;
}

/** The dark call-to-action panel that closes most pages. */
export default function CtaPanel({ heading, children, subject }: Props) {
  return (
    <section className="pub-section pub-section--tight">
      <div className="pub-wrap">
        <div className="pub-panel pub-cta">
          <h2 className="pub-heading pub-heading--on-ink">{heading}</h2>
          <p className="pub-body pub-body--on-ink">{children}</p>
          <div className="pub-actions pub-actions--center">
            <Link className="pub-btn pub-btn--primary" href="/signup/">
              Sign up for free
            </Link>
            <a className="pub-btn pub-btn--secondary-on-ink" href={mailto(subject)}>
              Email {CONTACT_EMAIL}
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
