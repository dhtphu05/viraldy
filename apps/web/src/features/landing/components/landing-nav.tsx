import { Link } from "@tanstack/react-router";
import { BrandLogo } from "@/shared/ui/brand-logo";
import { Button } from "@/shared/ui/button";

const navLinks = [
    { label: "How it works", href: "#how-it-works" },
    { label: "Quality QA", href: "#tiktok-score" },
    { label: "Use Cases", href: "#use-cases" },
    { label: "Why Viraldy", href: "#why-viraldy" },
    { label: "Trust Proof", href: "#trust" },
    { label: "FAQ", href: "#faq" },
];

export function LandingNav() {
    return (
        <header className="sticky top-0 z-50 border-b border-hairline bg-background/80 backdrop-blur-md">
            <nav className="mx-auto flex h-16 max-w-[1200px] items-center justify-between px-4 sm:px-6 lg:px-10">
                <a href="#" className="inline-flex items-center" aria-label="Viraldy home">
                    <BrandLogo className="h-10 w-[150px]" />
                </a>

                <div className="hidden items-center gap-6 lg:flex">
                    {navLinks.map((link) => (
                        <a
                            key={link.href}
                            href={link.href}
                            className="text-sm font-medium text-text-secondary transition-colors hover:text-text-primary"
                        >
                            {link.label}
                        </a>
                    ))}
                </div>

                <Button asChild size="sm">
                    <Link to="/login">Get Creative Directions</Link>
                </Button>
            </nav>
        </header>
    );
}
