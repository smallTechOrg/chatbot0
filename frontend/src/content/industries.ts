// Industries, ported from chatbot0/content.py (which ported INDUSTRY_CONFIGS from the old zer0 site).
// Claims chatbot0 cannot back (third-party integrations, compliance certifications, calendar booking)
// were dropped; "Small Business" was dropped.

export interface Industry {
  /** Anchor id on /industries. */
  slug: string;
  /** As in the old ?industry=<name> links. */
  name: string;
  feature: string;
  desc: string;
  /** One line for the top of /industries when ?industry= picks this one. */
  pitch: string;
}

export const INDUSTRIES: readonly Industry[] = [
  {
    slug: "e-commerce",
    name: "E-Commerce",
    feature: "Product questions",
    desc: "Answers questions about products, shipping and returns, and points shoppers to what fits, from what you tell it about your catalogue.",
    pitch: "Turn shoppers' questions into orders, with answers on products, shipping and returns at any hour.",
  },
  {
    slug: "customer-service",
    name: "Customer Service",
    feature: "Answers from your business",
    desc: "Learns your services, policies and FAQs from the description you give it, so every visitor gets the same clear answer.",
    pitch: "Give every customer a fast, consistent answer, and pass the ones that need a person to your team.",
  },
  {
    slug: "education",
    name: "Education",
    feature: "Enrolment assistant",
    desc: "Guides prospective students through your courses, answers admissions questions and captures their details.",
    pitch: "Take prospective students from first question to enquiry, around the clock.",
  },
  {
    slug: "enterprises",
    name: "Enterprises",
    feature: "Custom setup",
    desc: "Free customisations and backend integration on the Pro plan, and a person at smallTech to work with on what you need.",
    pitch: "Shape the agent to your brand and connect it to your own systems.",
  },
  {
    slug: "healthcare",
    name: "Healthcare",
    feature: "Patient enquiries",
    desc: "Answers questions about your services, timings and locations, and captures details for appointment requests.",
    pitch: "Answer patients' questions at any hour and capture appointment requests for your front desk.",
  },
  {
    slug: "insurance",
    name: "Insurance",
    feature: "Policy explainer",
    desc: "Explains policy terms in plain language and takes the first details of a quote or claim enquiry.",
    pitch: "Make policies easier to understand and capture quote and claim enquiries as they come in.",
  },
  {
    slug: "it-support",
    name: "IT Support",
    feature: "First-line answers",
    desc: "Answers common questions and captures the details of an issue, so your team picks it up with the whole conversation.",
    pitch: "Handle routine questions on the spot and hand the rest to your team with the context.",
  },
  {
    slug: "real-estate",
    name: "Real Estate",
    feature: "Buyer pre-qualification",
    desc: "Asks about budget and location, answers questions about your listings and captures buyers' details for a viewing.",
    pitch: "Capture property enquiries around the clock and know what each buyer is looking for.",
  },
  {
    slug: "recruitment",
    name: "Recruitment",
    feature: "Candidate pre-screening",
    desc: "Answers candidates' questions about your roles and collects their details and experience for your team to review.",
    pitch: "Answer candidates' questions and collect their details, so your team starts with what it needs.",
  },
  {
    slug: "sales",
    name: "Sales",
    feature: "Lead qualification",
    desc: "Asks the qualifying questions while it answers, and sends warm leads to your dashboard.",
    pitch: "Qualify visitors while they browse and hand your team the warm conversations.",
  },
];

/** The industry an old ?industry=<name> link (or a slug) points at; undefined if it matches none. */
export function findIndustry(value: string | null | undefined): Industry | undefined {
  const key = (value ?? "").trim().toLowerCase();
  if (!key) return undefined;
  return INDUSTRIES.find((i) => key === i.slug || key === i.name.toLowerCase());
}
