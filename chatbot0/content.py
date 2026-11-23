"""chatbot0 public-page content that is likely to change: URLs and the plans.

Pricing is kept here, in one place, so it can be updated without touching the
templates. The owner has not yet confirmed these prices are current (SMA-8).
"""

from __future__ import annotations

from dataclasses import dataclass

SITE_URL = "https://chatbot0.smalltech.in"
# chatbot0's own sign-up page (templates/chatbot0/signup.html). Relative, like every other link, so it works at
# /chatbot0/ and at the root of chatbot0.smalltech.in.
SIGNUP_URL = "signup"
# The chat widget (embed.js + the /embed iframe) is served by the Zer0 app. The backend picks the
# prompts by the page origin: chatbot0.smalltech.in maps to the CHATBOT0 domain key in the prompts table.
WIDGET_URL = "https://zer0.smalltech.in"
ZER0_URL = "https://zer0.smalltech.in"
CONTACT_EMAIL = "contact@smalltech.in"
GITHUB_URL = "https://github.com/smallTechOrg"
LINKEDIN_URL = "https://www.linkedin.com/company/madhyamakist"


@dataclass(frozen=True)
class Plan:
    key: str
    name: str
    monthly: int  # USD per month, billed monthly
    yearly: int | None  # USD per month, billed yearly; None for the free plan
    features: tuple[tuple[str, bool], ...]  # (feature, included)
    cta: str
    featured: bool = False

    @property
    def yearly_saving_pct(self) -> int | None:
        """Whole-percent saving of yearly over monthly billing, computed from the prices."""
        if not self.yearly or not self.monthly:
            return None
        return round((self.monthly - self.yearly) * 100 / self.monthly)


# Free / Basic / Pro, ported from the original zero.smalltech.in pricing.
PLANS: tuple[Plan, ...] = (
    Plan(
        "free",
        "Free",
        0,
        None,
        (
            ("200 conversations a month", True),
            ("Built-in lead dashboard", True),
            ("Priority support", False),
            ("Free customisations", False),
            ("Free backend integration", False),
        ),
        "Start free",
    ),
    Plan(
        "basic",
        "Basic",
        4,
        3,
        (
            ("1,000 conversations a month", True),
            ("Built-in lead dashboard", True),
            ("Priority support", True),
            ("Free customisations", True),
            ("Free backend integration", False),
        ),
        "Choose Basic",
    ),
    Plan(
        "pro",
        "Pro",
        12,
        10,
        (
            ("Unlimited conversations", True),
            ("Built-in lead dashboard", True),
            ("Priority support", True),
            ("Free customisations", True),
            ("Free backend integration", True),
        ),
        "Choose Pro",
        featured=True,
    ),
)

FREE_CONVERSATIONS = "200"
MAX_YEARLY_SAVING_PCT = max((p.yearly_saving_pct or 0) for p in PLANS)
LOWEST_PAID_MONTHLY = min(p.monthly for p in PLANS if p.monthly)


# Sign-up: the widget colour the form starts with and the preset swatches (ported from the old sign-up page).
# These are the visitor's widget colours, not the page palette.
DEFAULT_WIDGET_COLOUR = "#219EBC"
WIDGET_COLOURS = ("#219EBC", "#023047", "#FB8500", "#FFB703", "#E63946", "#2D6A4F", "#7209B7", "#000000")


@dataclass(frozen=True)
class Industry:
    slug: str  # anchor id on /industries
    name: str  # as in the old ?industry=<name> links
    feature: str
    desc: str
    pitch: str  # one line for the top of /industries when ?industry= picks this one


# Ported from INDUSTRY_CONFIGS on the old zer0 site. Claims chatbot0 cannot back (third-party integrations,
# compliance certifications, calendar booking) were dropped; "Small Business" was dropped.
INDUSTRIES: tuple[Industry, ...] = (
    Industry(
        "e-commerce",
        "E-Commerce",
        "Product questions",
        "Answers questions about products, shipping and returns, and points shoppers to what fits, "
        "from what you tell it about your catalogue.",
        "Turn shoppers' questions into orders, with answers on products, shipping and returns at any hour.",
    ),
    Industry(
        "customer-service",
        "Customer Service",
        "Answers from your business",
        "Learns your services, policies and FAQs from the description you give it, so every visitor gets "
        "the same clear answer.",
        "Give every customer a fast, consistent answer, and pass the ones that need a person to your team.",
    ),
    Industry(
        "education",
        "Education",
        "Enrolment assistant",
        "Guides prospective students through your courses, answers admissions questions and captures their details.",
        "Take prospective students from first question to enquiry, around the clock.",
    ),
    Industry(
        "enterprises",
        "Enterprises",
        "Custom setup",
        "Free customisations and backend integration on the Pro plan, and a person at smallTech to work "
        "with on what you need.",
        "Shape the agent to your brand and connect it to your own systems.",
    ),
    Industry(
        "healthcare",
        "Healthcare",
        "Patient enquiries",
        "Answers questions about your services, timings and locations, and captures details for appointment requests.",
        "Answer patients' questions at any hour and capture appointment requests for your front desk.",
    ),
    Industry(
        "insurance",
        "Insurance",
        "Policy explainer",
        "Explains policy terms in plain language and takes the first details of a quote or claim enquiry.",
        "Make policies easier to understand and capture quote and claim enquiries as they come in.",
    ),
    Industry(
        "it-support",
        "IT Support",
        "First-line answers",
        "Answers common questions and captures the details of an issue, so your team picks it up with the "
        "whole conversation.",
        "Handle routine questions on the spot and hand the rest to your team with the context.",
    ),
    Industry(
        "real-estate",
        "Real Estate",
        "Buyer pre-qualification",
        "Asks about budget and location, answers questions about your listings and captures buyers' details "
        "for a viewing.",
        "Capture property enquiries around the clock and know what each buyer is looking for.",
    ),
    Industry(
        "recruitment",
        "Recruitment",
        "Candidate pre-screening",
        "Answers candidates' questions about your roles and collects their details and experience for your "
        "team to review.",
        "Answer candidates' questions and collect their details, so your team starts with what it needs.",
    ),
    Industry(
        "sales",
        "Sales",
        "Lead qualification",
        "Asks the qualifying questions while it answers, and sends warm leads to your dashboard.",
        "Qualify visitors while they browse and hand your team the warm conversations.",
    ),
)


def find_industry(value: str | None) -> Industry | None:
    """The industry an old ?industry=<name> link (or a slug) points at; None if it matches none."""
    key = (value or "").strip().lower()
    if not key:
        return None
    for industry in INDUSTRIES:
        if key in (industry.slug, industry.name.lower()):
            return industry
    return None
