import { Link } from "@tanstack/react-router";
import { BrandLogo } from "@/shared/ui/brand-logo";
import { Button } from "@/shared/ui/button";

export function LandingFooter() {
    return (
        <footer className="border-t border-hairline bg-surface">
            <div className="mx-auto max-w-[1200px] px-4 py-12 sm:px-6 lg:px-10">
                <div className="flex flex-col gap-8 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                        <BrandLogo className="h-11 w-[164px]" />
                        <p className="mt-2 max-w-xs text-sm text-text-secondary">
                            Creative Intelligence for creator-led commerce.
                        </p>
                    </div>

                    <div className="flex flex-wrap gap-x-12 gap-y-6">
                        <div>
                            <p className="text-xs font-semibold uppercase text-text-tertiary">
                                Product
                            </p>
                            <div className="mt-3 flex flex-col gap-2">
                                <a
                                    href="#features"
                                    className="text-sm text-text-secondary hover:text-text-primary"
                                >
                                    Features
                                </a>
                                <a
                                    href="#how-it-works"
                                    className="text-sm text-text-secondary hover:text-text-primary"
                                >
                                    How it works
                                </a>
                                <a
                                    href="#use-cases"
                                    className="text-sm text-text-secondary hover:text-text-primary"
                                >
                                    Use Cases
                                </a>
                            </div>
                        </div>
                        <div>
                            <p className="text-xs font-semibold uppercase text-text-tertiary">
                                Resources
                            </p>
                            <div className="mt-3 flex flex-col gap-2">
                                <a
                                    href="#faq"
                                    className="text-sm text-text-secondary hover:text-text-primary"
                                >
                                    FAQ
                                </a>
                            </div>
                        </div>
                        <div>
                            <p className="text-xs font-semibold uppercase text-text-tertiary">
                                Company
                            </p>
                            <div className="mt-3 flex flex-col gap-2">
                                <Button
                                    asChild
                                    variant="link"
                                    size="sm"
                                    className="h-auto p-0 text-sm text-text-secondary hover:text-text-primary"
                                >
                                    <Link to="/login">Log in</Link>
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>

                <p className="mt-12 text-center text-xs text-text-tertiary">
                    &copy; {new Date().getFullYear()} Viraldy. All rights reserved.
                </p>
            </div>
        </footer>
    );
}
