import { Link } from "@tanstack/react-router";
import { Button } from "@/shared/ui/button";

const navLinks = [
    { label: "Product", href: "#product" },
    { label: "How it works", href: "#how-it-works" },
    { label: "TikTok Score & Fix", href: "#tiktok-score" },
    { label: "For Sellers", href: "#sellers" },
    { label: "For Agencies", href: "#agencies" },
    { label: "Pricing", href: "#pricing" },
    { label: "Resources", href: "#faq" },
];

export function LandingNav() {
    return (
        <header className="sticky top-0 z-50 border-b border-hairline bg-background/80 backdrop-blur-md">
            <nav className="mx-auto flex h-16 max-w-[1200px] items-center justify-between px-4 sm:px-6 lg:px-10">
                <a href="#" className="text-lg font-bold text-text-primary">
                    VIRALDY
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
                    <Link to="/login">Try Viraldy</Link>
                </Button>
            </nav>
        </header>
    );
}
