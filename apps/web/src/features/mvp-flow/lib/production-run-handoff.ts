type ImportedProductCandidate = {
    name: string;
    external_source?: string | null;
    external_id?: string | null;
    metadata_json?: Record<string, unknown>;
};

type SeedProductIdentity = {
    id: string;
    name: string;
};

type ImportedReferenceCandidate = {
    source_url?: string | null;
};

export function findImportedProduct<T extends ImportedProductCandidate>(
    products: T[],
    seed: SeedProductIdentity,
) {
    return (
        products.find(
            (product) =>
                product.external_source === "frontend_demo" && product.external_id === seed.id,
        ) ??
        products.find((product) => product.metadata_json?.frontend_seed_id === seed.id) ??
        products.find((product) => product.name === seed.name)
    );
}

export function demoCreativeSourceUrl(creativeId: string) {
    return `viraldy://creative-library/${creativeId}`;
}

export function findImportedReference<T extends ImportedReferenceCandidate>(
    references: T[],
    creativeId: string,
) {
    const sourceUrl = demoCreativeSourceUrl(creativeId);
    return references.find((reference) => reference.source_url === sourceUrl);
}
