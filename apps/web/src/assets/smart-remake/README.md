# Smart Remake illustrations

Generated with the built-in `image_gen` tool. Transparent alpha was verified on the source PNGs and preserved in the WebP copies. Intake assets are 480 × 480; the loading asset is 960 × 640. The three new assets total approximately 100 KiB. CSS provides motion and respects `prefers-reduced-motion`.

## reference-video.webp

```text
Use case: stylized-concept
Asset type: decorative empty-state illustration for the video-reference upload panel of Viraldy's Smart Remake web app.
Primary request: one cohesive polished 3D miniature, a rounded ivory vertical video card with a large translucent raspberry-pink play triangle in its center, a short charcoal filmstrip curving behind the card. Two tiny pink four-point sparkle accents.
Style/medium: premium soft 3D clay and translucent pink glass, rounded bevels, fine material rendering, soft studio shadows. Match a light app with rose #e00b41, blush pink, ivory cream and restrained charcoal.
Composition/framing: isolated centered compact object group, square canvas, generous clean margin, fully visible silhouette, slight isometric view, readable at 160px.
Constraints: genuinely transparent alpha background; no background plane, no text, no letters, no watermark, no logo, no humans, no border around the entire image.
```

## product-reference.webp

```text
Use case: stylized-concept
Asset type: decorative empty-state illustration for the product-photo upload panel of Viraldy's Smart Remake web app.
Primary request: one cohesive polished 3D miniature, two softly overlapping rounded ivory photo cards, the front card displaying a simple unbranded blush-pink cosmetic pump bottle on a small ivory pedestal, a tiny raspberry-pink plus badge at the lower corner. One small four-point sparkle.
Style/medium: premium soft 3D clay and translucent pink glass, rounded bevels, fine material rendering, soft studio shadows. Match a light app with rose #e00b41, blush pink, ivory cream and restrained charcoal.
Composition/framing: isolated centered compact object group, square canvas, generous clean margin, fully visible silhouette, slight isometric view, readable at 160px. Friendly and refined, a UI illustration rather than a real product photo.
Constraints: genuinely transparent alpha background; no background plane, no text, no letters, no watermark, no logo, no humans, no border around the entire image.
```

## render-studio.webp

```text
Use case: stylized-concept
Asset type: wide decorative loading illustration for AI video generation in Viraldy's Smart Remake app.
Primary request: a small polished 3D video studio metaphor: three rounded ivory storyboard cards flowing from the left into a translucent raspberry-pink circular camera lens, with an elegant charcoal-and-ivory striped clapperboard and a luminous pink play symbol emerging on the right. Keep a single cohesive object group, two small four-point pink sparkles, calm and precise.
Style/medium: premium soft 3D clay combined with translucent rose glass, rounded bevels, tactile materials, studio lighting and delicate ambient shadow. Palette rose #e00b41, blush pink, ivory cream and restrained charcoal, made for a clean white productivity UI.
Composition/framing: landscape 3:2 canvas, centered horizontal arrangement, all objects fully visible with generous transparent margins. Clear silhouette at 400px wide. No scene environment.
Constraints: genuinely transparent alpha background; no text, no letters, no numbers, no watermark, no logo, no humans, no background plane.
```

Final cleanup prompt for `render-studio.webp` (built-in image edit with the generated studio image as the edit target):

```text
Use case: background-extraction
Asset type: transparent loading illustration for a white app UI.
Primary request: remove ONLY the gray/white/black backdrop and background haze from this illustration. Keep the entire camera lens, storyboard cards, clapperboard, play symbol, and pink sparkles precisely intact, with the same composition, shape, materials and colors. Clean object cutout with genuinely transparent alpha to all edges. Preserve translucent pink parts of the objects, remove background outside their silhouettes. No added background plane, no gray checkerboard, no new objects, no text. Output an actual transparent image.
```
