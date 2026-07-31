import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link2, Loader2, Search } from "lucide-react";
import { useState, type ComponentProps } from "react";
import { toast } from "sonner";

import {
    crawlProductPreview,
    createProduct,
    type CreateProductInput,
    type Product,
    type ProductCrawlPreview,
} from "@/shared/api/products";
import { queryKeys } from "@/shared/api/query-keys";
import { Button } from "@/shared/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/shared/ui/dialog";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Textarea } from "@/shared/ui/textarea";

type ProductDraftForm = {
    name: string;
    brand: string;
    category: string;
    market: string;
    currency: string;
    price: string;
    compareAtPrice: string;
    description: string;
};

export function ImportProductDialog({
    workspaceId,
    onImported,
}: {
    workspaceId?: string;
    onImported: (product: Product) => void;
}) {
    const queryClient = useQueryClient();
    const [open, setOpen] = useState(false);
    const [url, setUrl] = useState("");
    const [preview, setPreview] = useState<ProductCrawlPreview | null>(null);
    const [form, setForm] = useState<ProductDraftForm | null>(null);

    const previewMutation = useMutation({
        mutationFn: (productUrl: string) => {
            if (!workspaceId) throw new Error("No backend workspace is available.");
            return crawlProductPreview(workspaceId, productUrl);
        },
        onSuccess: (result) => {
            setPreview(result);
            setForm(formFromPreview(result));
        },
    });
    const saveMutation = useMutation({
        mutationFn: () => {
            if (!workspaceId || !preview || !form) {
                throw new Error("Analyze a product link before saving.");
            }
            return createProduct(workspaceId, createInputFromForm(preview.product_draft, form));
        },
        onSuccess: (product) => {
            queryClient.setQueryData<Product[]>(
                queryKeys.products.list(workspaceId),
                (current = []) =>
                    current.some((item) => item.id === product.id)
                        ? current
                        : [...current, product],
            );
            void queryClient.invalidateQueries({
                queryKey: queryKeys.products.list(workspaceId),
            });
            setOpen(false);
            setUrl("");
            setPreview(null);
            setForm(null);
            onImported(product);
            toast.success("Product imported", {
                description: `${product.name} is now available in the catalog.`,
            });
        },
        onError: (error) => {
            toast.error("Product could not be saved", {
                description:
                    error instanceof Error ? error.message : "Try saving the product again.",
            });
        },
    });

    const imageUrl = preview ? previewImage(preview) : "";
    const previewError =
        previewMutation.error instanceof Error
            ? previewMutation.error.message
            : previewMutation.error
              ? "The product link could not be analyzed."
              : "";

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button
                    variant="secondary"
                    disabled={!workspaceId}
                    title={
                        workspaceId
                            ? "Import a product from a public link"
                            : "Connect the backend and create a workspace to import products"
                    }
                >
                    <Link2 className="h-4 w-4" />
                    Import product link
                </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
                <DialogHeader>
                    <DialogTitle>Import product from link</DialogTitle>
                    <DialogDescription>
                        Paste a public product URL, review the observed fields, then save it to this
                        workspace.
                    </DialogDescription>
                </DialogHeader>

                <form
                    className="space-y-5"
                    onSubmit={(event) => {
                        event.preventDefault();
                        if (form) {
                            saveMutation.mutate();
                        } else if (url.trim()) {
                            previewMutation.mutate(url.trim());
                        }
                    }}
                >
                    <div className="space-y-2">
                        <Label htmlFor="product-import-url">Product URL</Label>
                        <div className="flex gap-2">
                            <Input
                                id="product-import-url"
                                type="url"
                                placeholder="https://www.amazon.com/dp/..."
                                value={url}
                                onChange={(event) => {
                                    setUrl(event.target.value);
                                    setPreview(null);
                                    setForm(null);
                                    previewMutation.reset();
                                }}
                                required
                                disabled={previewMutation.isPending || saveMutation.isPending}
                            />
                            <Button
                                type="button"
                                variant="secondary"
                                disabled={
                                    !url.trim() ||
                                    previewMutation.isPending ||
                                    saveMutation.isPending
                                }
                                onClick={() => previewMutation.mutate(url.trim())}
                            >
                                {previewMutation.isPending ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <Search className="h-4 w-4" />
                                )}
                                {previewMutation.isPending ? "Crawling…" : "Analyze"}
                            </Button>
                        </div>
                        {previewError ? (
                            <p role="alert" className="text-sm text-destructive">
                                {previewError}
                            </p>
                        ) : null}
                    </div>

                    {preview && form ? (
                        <div className="space-y-4 border-t border-hairline pt-5">
                            <div className="grid gap-4 sm:grid-cols-[128px_minmax(0,1fr)]">
                                <div className="flex aspect-square items-center justify-center overflow-hidden rounded-xl border border-hairline bg-surface-soft">
                                    {imageUrl ? (
                                        <img
                                            src={imageUrl}
                                            alt=""
                                            className="h-full w-full object-contain"
                                        />
                                    ) : (
                                        <Link2 className="h-8 w-8 text-text-tertiary" />
                                    )}
                                </div>
                                <div className="grid gap-3 sm:grid-cols-2">
                                    <Field
                                        id="product-import-name"
                                        label="Name"
                                        value={form.name}
                                        onChange={(name) =>
                                            setForm((current) =>
                                                current ? { ...current, name } : current,
                                            )
                                        }
                                        className="sm:col-span-2"
                                        required
                                    />
                                    <Field
                                        id="product-import-brand"
                                        label="Brand"
                                        value={form.brand}
                                        onChange={(brand) =>
                                            setForm((current) =>
                                                current ? { ...current, brand } : current,
                                            )
                                        }
                                    />
                                    <Field
                                        id="product-import-category"
                                        label="Category"
                                        value={form.category}
                                        onChange={(category) =>
                                            setForm((current) =>
                                                current ? { ...current, category } : current,
                                            )
                                        }
                                        required
                                    />
                                </div>
                            </div>

                            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                                <Field
                                    id="product-import-market"
                                    label="Market"
                                    value={form.market}
                                    onChange={(market) =>
                                        setForm((current) =>
                                            current ? { ...current, market } : current,
                                        )
                                    }
                                    required
                                />
                                <Field
                                    id="product-import-currency"
                                    label="Currency"
                                    value={form.currency}
                                    onChange={(currency) =>
                                        setForm((current) =>
                                            current ? { ...current, currency } : current,
                                        )
                                    }
                                    placeholder="USD"
                                />
                                <Field
                                    id="product-import-price"
                                    label="Price"
                                    value={form.price}
                                    onChange={(price) =>
                                        setForm((current) =>
                                            current ? { ...current, price } : current,
                                        )
                                    }
                                    inputMode="decimal"
                                />
                                <Field
                                    id="product-import-compare-price"
                                    label="Original price"
                                    value={form.compareAtPrice}
                                    onChange={(compareAtPrice) =>
                                        setForm((current) =>
                                            current ? { ...current, compareAtPrice } : current,
                                        )
                                    }
                                    inputMode="decimal"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="product-import-description">Description</Label>
                                <Textarea
                                    id="product-import-description"
                                    rows={5}
                                    value={form.description}
                                    onChange={(event) =>
                                        setForm((current) =>
                                            current
                                                ? {
                                                      ...current,
                                                      description: event.target.value,
                                                  }
                                                : current,
                                        )
                                    }
                                />
                            </div>

                            <p className="text-xs text-text-tertiary">
                                Source: {preview.source_url} · Confidence:{" "}
                                {confidenceText(preview.crawl.confidence)}
                            </p>
                        </div>
                    ) : null}

                    <DialogFooter>
                        <Button
                            type="button"
                            variant="ghost"
                            onClick={() => setOpen(false)}
                            disabled={saveMutation.isPending}
                        >
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            disabled={
                                !form?.name.trim() ||
                                previewMutation.isPending ||
                                saveMutation.isPending
                            }
                        >
                            {saveMutation.isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : null}
                            {saveMutation.isPending ? "Saving…" : "Save product"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}

function Field({
    id,
    label,
    value,
    onChange,
    className,
    ...inputProps
}: {
    id: string;
    label: string;
    value: string;
    onChange: (value: string) => void;
    className?: string;
} & Pick<ComponentProps<typeof Input>, "placeholder" | "required" | "inputMode">) {
    return (
        <div className={`space-y-2 ${className ?? ""}`}>
            <Label htmlFor={id}>{label}</Label>
            <Input
                id={id}
                value={value}
                onChange={(event) => onChange(event.target.value)}
                {...inputProps}
            />
        </div>
    );
}

function formFromPreview(preview: ProductCrawlPreview): ProductDraftForm {
    const draft = preview.product_draft;
    const identity = draft.product_context.identity;
    const commercial = draft.product_context.commercial;
    return {
        name: draft.name,
        brand: identity.brand ?? "",
        category: identity.category || "unknown",
        market: identity.market || draft.market || "unknown",
        currency: identity.currency ?? "",
        price: fieldNumber(commercial.price),
        compareAtPrice: fieldNumber(commercial.compare_at_price),
        description: draft.description ?? "",
    };
}

function createInputFromForm(
    draft: CreateProductInput,
    form: ProductDraftForm,
): CreateProductInput {
    const price = decimalOrNull(form.price);
    const compareAtPrice = decimalOrNull(form.compareAtPrice);
    const category = form.category.trim() || "unknown";
    const market = form.market.trim() || "unknown";
    const currency = form.currency.trim().toUpperCase() || null;
    return {
        ...draft,
        name: form.name.trim(),
        description: form.description.trim() || null,
        market,
        metadata_json: {
            ...draft.metadata_json,
            brand: form.brand.trim(),
            category,
            currency: currency ?? "",
            current_price_text: form.price.trim(),
            original_price_text: form.compareAtPrice.trim(),
        },
        product_context: {
            ...draft.product_context,
            identity: {
                ...draft.product_context.identity,
                name: form.name.trim(),
                brand: form.brand.trim() || null,
                category,
                market,
                currency,
            },
            commercial: {
                ...draft.product_context.commercial,
                price,
                compare_at_price: compareAtPrice,
            },
        },
    };
}

function previewImage(preview: ProductCrawlPreview): string {
    const metadataImage = preview.product_draft.metadata_json.image_url;
    if (typeof metadataImage === "string" && metadataImage) return metadataImage;
    const crawlImage = preview.crawl.image;
    return typeof crawlImage === "string" ? crawlImage : "";
}

function fieldNumber(value: string | number | null | undefined): string {
    return value === null || value === undefined ? "" : String(value);
}

function decimalOrNull(value: string): number | null {
    if (!value.trim()) return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

function confidenceText(value: unknown): string {
    return typeof value === "number" ? `${Math.round(value * 100)}%` : "Unknown";
}
