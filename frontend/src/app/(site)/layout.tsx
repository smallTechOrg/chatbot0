import SiteFooter from "@/components/site/SiteFooter";
import SiteHeader from "@/components/site/SiteHeader";
import SiteWidget from "@/components/site/SiteWidget";

// The shell of every public page. The `.pub` wrapper scopes the page styles (src/styles/site.css).
export default function SiteLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="pub">
      <a className="pub-skip" href="#main">
        Skip to content
      </a>
      <SiteHeader />
      <main id="main">{children}</main>
      <SiteFooter />
      <SiteWidget />
    </div>
  );
}
