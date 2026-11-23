import Link from "next/link";
import { PLANS, yearlySavingPct } from "@/content/plans";

/** The plans grid. Prices and features come from src/content/plans.ts. */
export default function PlansGrid() {
  return (
    <div className="pub-plans">
      {PLANS.map((plan) => {
        const saving = yearlySavingPct(plan);
        return (
          <article key={plan.key} className={`pub-plan${plan.featured ? " pub-plan--featured" : ""}`} id={`plan-${plan.key}`}>
            <p className="pub-label">{plan.name} plan</p>
            <p className="pub-plan__price">
              ${plan.monthly}
              <span>/month</span>
            </p>
            <p className="pub-plan__note">
              {plan.yearly ? `or $${plan.yearly}/month billed yearly (save ${saving}%)` : "Free forever. No card needed."}
            </p>
            <ul className="pub-plan__features">
              {plan.features.map(([feature, included]) => (
                <li key={feature} className={included ? "is-in" : "is-out"}>
                  <span className="pub-plan__mark" aria-hidden="true">
                    {included ? "✓" : "–"}
                  </span>
                  <span>
                    {!included && <span className="pub-sr">Not included: </span>}
                    {feature}
                  </span>
                </li>
              ))}
            </ul>
            <Link
              className={`pub-btn ${plan.featured || plan.key === "free" ? "pub-btn--primary" : "pub-btn--secondary"} pub-plan__cta`}
              href="/signup/"
              data-ga-event="plan_click"
              data-ga-plan={plan.key}
            >
              {plan.cta}
            </Link>
          </article>
        );
      })}
    </div>
  );
}
