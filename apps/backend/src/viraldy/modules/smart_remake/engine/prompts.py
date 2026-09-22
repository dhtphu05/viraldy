from typing import Any


def _join(parts: list[str]) -> str:
    return "\n".join(part for part in parts if part)


def build_reference_analysis_prompt(
    *,
    target_duration: int,
    mime_type: str | None = None,
    prompt: str | None = None,
    description: str | None = None,
    has_video: bool,
) -> tuple[str, str]:
    system = _join(
        [
            "The uploaded reference video is provided only to extract abstract creative DNA."
            if has_video
            else "No reference video was supplied. Infer abstract creative DNA only from the provided text and product context.",
            "Analyze format, opening composition, scene structure, shot rhythm, camera style, framing, movement, setting type, generic background elements, generic actor behavior, expression, gestures, hook logic, pacing, motion beats, audio energy, and product reveal logic when evidence is available.",
            "Treat any product, tool, package, logo, or object visible in the reference video as source-role context only. It will be replaced by the user's uploaded target product during rendering.",
            "This is a source-faithful ad remake, not a new ad concept. Preserve the reference video's demo use-case, demo logic, environment realism, surface/problem context, result reveal, human presence/framing, and pacing.",
            "Do not identify, reproduce, or describe a real person identity.",
            "Do not copy face identity, brand names, logos, original captions, exact spoken wording, or copyrighted wording.",
            "Do not produce instructions that use the uploaded video as a generation reference.",
            "Do not return URLs, paths, file names, storage keys, video-generation payloads, or render request types.",
            "Output JSON only.",
            "Return strict valid JSON parseable by JSON.parse with no markdown or prose.",
            "Do not include raw newline, tab, or control characters inside string values; escape them as \\n, \\t, or unicode escapes.",
            "Every object property and every array element must be comma-separated.",
            "Avoid nested quotation marks in dialogue; when quotation marks are necessary, escape them.",
        ]
    )
    user = _join(
        [
            f"Analyze the uploaded {mime_type} reference video for a {target_duration}s Smart Remake."
            if has_video
            else f"Create a concept-only reference analysis for a {target_duration}s Smart Remake.",
            f"User prompt: {prompt}" if prompt else "",
            f"Description: {description}" if description else "",
            "Analyze the full uploaded reference video from beginning to end, even when the output target is 8 seconds. Do not analyze only the first 8 seconds.",
            f"The {target_duration}s output should condense the full reference video's hook, demo action, result/payoff, and pacing into the target duration while preserving the source order.",
            "Determine whether the video contains no person, hands only, or a visible person.",
            "Analyze the actual reference video pacing. Count meaningful shot changes or angle changes, estimate average shot duration, identify transition/cut style, action speed, camera movement energy, audio energy, important action beats, and any unnecessary lingering or static sections."
            if has_video
            else "Infer pacingPlan from text and product context only. Do not assume every concept should be fast-paced; choose slow, medium, or fast based on the requested style.",
            "When describing sourceShots and motionBeats, preserve the role and physical action pattern, but write actions so the source object/tool role can be replaced by the uploaded target product.",
            "Do not let the reference video's original product/tool identity become a required generated object. Use generic terms like target product, product tool, handheld item, package, or hero product where possible.",
            "For each sourceShot action, include the visible environment, working surface, hand/body framing, product contact/action, problem state, result state, and camera energy when visible.",
            "Write each sourceShot action as a concrete, concise physical sequence: hand/body interaction, target surface, contact point, movement direction, and visible result when present. Do not use vague labels such as demonstrate product, show use, or product action.",
            "For every sourceShot and motionBeat that shows product use, include physicalAction with visible-only fields: operator (hand/body grip or pose), targetSurface, contactPoint, movement, and visibleEffect. This per-shot execution contract must describe what the reference visibly does, not hidden product features or a new use-case.",
            "If the reference shows hands or a person, preserve the same human-presence category, crop/framing, pose direction, and interaction mechanics using generic non-identifiable people or hands.",
            "Preserve the original demo sequence and use-case closely. Do not invent a different use-case, different surface, or different way of using the product.",
            "Only swap visual product identity, color, material, or allowed product details. The source demo action remains the authority for how the product is used.",
            "Detect sourceShots from real visual shot boundaries or meaningful composition changes. Do not treat every semantic action as a separate shot unless the video actually cuts, changes angle, changes framing, or changes composition."
            if has_video
            else "Infer sourceShots from the requested structure only when no video is supplied. Keep inferred shots conservative and concrete.",
            "sourceShots are the authority for exact remake shot planning. If one continuous source shot contains several actions, return one sourceShot with one combined action; do not split it into touch/slide/lift/reveal shots unless there are real visual shot boundaries.",
            "Do not invent sourceShots to satisfy pacingPlan.shotCount. motionBeats may describe semantic actions, but sourceShots must stay one-to-one with actual visual shots.",
            'Default shotPreservationMode to "exact". Use "adaptive" only if the user explicitly asks to simplify or compress the source structure.',
            "sourceShotCount must equal sourceShots.length. sourceDurationSeconds must represent the full visual source duration covered by sourceShots.",
            "Each sourceShots item must include shotIndex, startSecond, endSecond, durationSeconds, role, priority, framing, cameraAngle, cameraMovement, subjectPresence, action, optional physicalAction, optional productState, optional transitionOut, and stateBefore/stateAfter whenever the source visibly changes state; leave those fields null only when no visible state transition occurs.",
            "Classify the ad before any scene timeline is compiled. Use only generic ad structure, hook logic, visual structure, product cardinality, motion-beat roles, state transitions, and renderability warnings from the actual video."
            if has_video
            else "Infer creative routing fields from the supplied text and product context only. Keep them generic and mark uncertain renderability as warnings.",
            "creativeArchetype must be one of product_demo, problem_solution, before_after, transformation, unboxing, testimonial, comparison, lifestyle_showcase, offer_led, product_reveal, tutorial, visual_meme, continuous_one_take, fast_montage, or other.",
            "visualStructure must be one of continuous, sequential_shots, before_after, split_screen, slideshow, screen_recording, or mixed_media.",
            "primaryHookType must be one of visual_action, visual_surprise, problem, transformation, reaction, text, spoken_line, offer, or product_result.",
            "productCardinality must be single or multiple.",
            "Each motionBeats item must include role and priority. Roles: hook, setup, problem, action, demonstration, transition, reveal, proof, reaction, payoff, hero, cta. Priorities: mandatory, supporting, optional.",
            "Motion beats with meaningful product or subject state changes must include stateBefore and stateAfter, such as closed to opened, messy to organized, hidden to revealed, folded to expanded, or problem state to resolved state.",
            'A motion beat with a meaningful stateBefore and stateAfter should normally be priority "mandatory". Do not replace state-changing beats with generic beauty shots.',
            "renderability must include supported, selectedStrategy, and warnings. selectedStrategy must be one of continuous_action, sequential_demo, problem_to_solution, before_to_after, transformation_sequence, unboxing_sequence, testimonial_structure, comparison_sequence, offer_structure, reveal_sequence, or simplified_sequential.",
            "Detect difficult structures such as split screen, screen recording, exact on-screen text, copyrighted dialogue, complex multi-product comparison, very high shot counts, mixed media, or UI-specific interactions.",
            "Use renderability warnings with non-empty code and message. Useful codes include REFERENCE_STRUCTURE_SIMPLIFIED, TEXT_DEPENDENT_HOOK, VOICE_DEPENDENT_HOOK, SCREEN_RECORDING_UNSUPPORTED, MULTI_PRODUCT_COMPLEXITY, SHOT_COUNT_REDUCED, and COMPARISON_CLAIMS_RESTRICTED.",
            "Do not silently turn difficult structures into a generic lifestyle demo. Choose the closest safe strategy and explain simplifications in renderability warnings.",
            "Do not include product-specific router rules, real-person identity, brand names, URLs, file paths, storage keys, render payloads, or reference-video fields in creative routing data.",
            "Analyze the first 2 seconds separately as openingShot. Describe the exact first-frame composition, product position and state, subject position, initial pose, first visible action, camera angle, framing, camera movement, first cut time, and actions that must not replace the original opening."
            if has_video
            else "Infer openingShot from text and product context. Keep it concrete enough to define the first frame and first visible product action.",
            "openingForbiddenSubstitutions must list opening replacements to avoid, such as generic smoothing, macro texture shots, or starting after the hook action already happened, only when supported by the source.",
            'Analyze audio intent as a separate audioPlan. Default audioPlan.mode to "native" unless the user clearly requests silence.',
            'If the reference has mostly music or music-only audio, set audioPlan.referenceMusic.mode to "extract" and describe the music style, mood, energy, and tempo in audioPlan.music.',
            "If the reference contains speech/voiceover mixed with music, do not set referenceMusic.mode to extract; describe the music and create native dialogue/voice guidance instead.",
            "For UGC review, plan native dialogue plus room ambience and light background music when appropriate.",
            "For product showcase, plan product sound effects and subtle music when appropriate.",
            "For cinematic video, plan ambience, cinematic music, and scene sound effects when appropriate.",
            "Do not request subtitles unless explicitly requested by the user.",
            'For pacingPlan, use pace "slow", "medium", or "fast"; cutStyle "continuous", "soft_cut", "hard_cut", "jump_cut", or "mixed"; motionIntensity "low", "medium", or "high"; cameraEnergy "static", "smooth", or "dynamic"; audioEnergy "low", "medium", or "high".',
            "pacingPlan.actionBeats should include only important actions, with estimated durationSeconds and a plain shotType such as close-up, medium shot, product insert, hands close-up, or hero shot.",
            "Do not hard-code fast pacing. Slow cinematic references should remain slow; calm product showcases may be medium or slow; energetic montage references may be fast.",
            "Return JSON compatible with this TypeScript shape:",
            '{ analysisOnly: true, subjectPresence: "none" | "hands_only" | "person", shotPreservationMode: "exact" | "adaptive", sourceShotCount: number, sourceDurationSeconds: number, sourceShots: [{ shotIndex, startSecond, endSecond, durationSeconds, role, priority, framing, cameraAngle, cameraMovement, subjectPresence, action, physicalAction?: { operator?: string, targetSurface?: string, contactPoint?: string, movement?: string, visibleEffect?: string }, productState?: string, stateBefore?: string, stateAfter?: string, transitionOut?: string }], format, sceneCount, creativeArchetype, visualStructure, primaryHookType, productCardinality: "single" | "multiple", renderability: { supported: boolean, selectedStrategy: string, warnings: [{ code: string, message: string, originalStructure?: string, selectedStrategy?: string }] }, cameraStyle: { angle, framing, movement }, setting: { locationType, backgroundElements }, actorBehavior?: { expression: string | null, gestures: string[] }, creativeConcept: { hook, adType, productMoment }, motionBeats: [{ startSecond, endSecond, action, physicalAction?: { operator?: string, targetSurface?: string, contactPoint?: string, movement?: string, visibleEffect?: string }, role, priority, stateBefore?: string, stateAfter?: string }], forbiddenReuse, audioPlan: { mode: "native" | "silent", language: string | null, dialogue: string | null, ambience: string | null, soundEffects: string[], music: string | null, warnings: string[], referenceMusic: { mode: "none" | "extract", reason?: string } }, pacingPlan: { pace: "slow" | "medium" | "fast", shotCount: number, averageShotDuration: number, cutStyle: "continuous" | "soft_cut" | "hard_cut" | "jump_cut" | "mixed", motionIntensity: "low" | "medium" | "high", cameraEnergy: "static" | "smooth" | "dynamic", audioEnergy: "low" | "medium" | "high", actionBeats: [{ action: string, durationSeconds: number, shotType: string }] }, openingShot: { durationSeconds: number, framing: string, cameraAngle: string, cameraMovement: string, subjectPresence: "none" | "hands_only" | "person", subjectPosition: string, productPosition: string, productState: string, initialPose: string, firstAction: string, gazeDirection?: string, backgroundLayout: string[], cutAtSecond?: number }, openingForbiddenSubstitutions: string[] }',
            "Return the object directly, not wrapped in another key.",
            "Use the boolean true for analysisOnly.",
            "All string fields must be non-empty.",
            "backgroundElements, gestures, and motionBeats must be non-empty arrays.",
            "forbiddenReuse may be an empty array when there is no identity, brand, caption, logo, or wording that must be blocked from reuse.",
            'Use subjectPresence "none" when no person appears; do not invent a person when none is present.',
            'Use subjectPresence "hands_only" when only hands appear; describe generic hands only with no face or identity.',
            'Use subjectPresence "person" only when a visible person appears; describe an original generic presenter without identity.',
            'Use generic actor and scene descriptions only when subjectPresence is "person".',
        ]
    )
    return system, user


def build_product_lock_prompt(
    *,
    metadata: Any | None = None,
    prompt: str | None = None,
    description: str | None = None,
    product_lock_mode: str | None = None,
    must_preserve: list[str] | None = None,
    can_change: list[str] | None = None,
    visual_colors: list[str] | None = None,
) -> tuple[str, str]:
    def meta(key: str) -> Any:
        if metadata is None:
            return None
        if isinstance(metadata, dict):
            return metadata.get(key)
        return getattr(metadata, key, None)

    metadata_lines = [
        f"Title: {meta('title')}" if meta("title") else "",
        f"Description: {meta('description')}" if meta("description") else "",
        f"Specs: {meta('specsText')}" if meta("specsText") else "",
        f"Price: {meta('price')}" if meta("price") else "",
        f"Original price: {meta('originalPrice')}" if meta("originalPrice") else "",
        f"Discount percent: {meta('discountPercent')}" if meta("discountPercent") is not None else "",
        f"Platform: {meta('platform')}" if meta("platform") else "",
        f"Source URL: {meta('sourceUrl')}" if meta("sourceUrl") else "",
    ]
    if not any(metadata_lines):
        metadata_lines = ["No product metadata was supplied. Derive product identity from the prompt, description, image, or generic product context."]

    system = _join(
        [
            "Use supplied product image, prompt, description, and metadata as available.",
            "When a product image is present, it is the visual source of truth.",
            "The product image is the source of truth for target product identity, color, components, and physical affordances. It must not create a new video use-case by itself.",
            "Do not invent hidden product features, materials, brand, price, discount, coupon, deadline, certifications, or performance claims.",
            "Identify must-preserve visual attributes and common generation errors when evidence supports them.",
            "Identify realistic product usage constraints from the supplied image, description, and metadata only as guardrails for contact point, scale, grip, and impossible motions.",
            "Infer physical affordances from the product image: which part is held, which part touches the surface, expected scale, reachable surfaces, and motions that are mechanically plausible.",
            "Do not invent alternate video use-cases. If the product function is uncertain, keep usage constraints conservative and based on visible physical affordances.",
            "The productReference.entityType must be visual_asset.",
            "Do not include mediaId; it is assigned later by FlowKit after upload.",
            "Output JSON only.",
            "Return strict valid JSON parseable by JSON.parse with no markdown or prose.",
            "Do not include raw newline, tab, or control characters inside string values; escape them as \\n, \\t, or unicode escapes.",
            "Every object property and every array element must be comma-separated.",
            "Avoid nested quotation marks; when quotation marks are necessary, escape them.",
        ]
    )
    user = _join(
        [
            "Create a ProductLock JSON object for Smart Remake generation.",
            "Return: productName, productType, visualIdentity, productUsage, mustPreserve, canChange, forbiddenErrors, productReference.",
            "mustPreserve, canChange, visualIdentity.colors, and productReference.characterName may be empty or omitted when unsupported.",
            "productUsage must include realisticUseCases, suitableSurfaces, contactPoints, handlingInstructions, usageConstraints, and forbiddenUsageErrors arrays.",
            f"Product lock mode: {product_lock_mode}." if product_lock_mode else "",
            f"User prompt: {prompt}" if prompt else "",
            f"Description: {description}" if description else "",
            f"User must preserve: {'; '.join(must_preserve or [])}" if must_preserve else "",
            f"User can change: {'; '.join(can_change or [])}" if can_change else "",
            f"Known visual colors: {', '.join(visual_colors or [])}" if visual_colors else "",
            "Use practical mustPreserve constraints like color palette, silhouette, texture, component layout, and functional structure only when supported.",
            "Use practical forbiddenErrors like changed colors, invented logos, missing components, duplicated components, altered proportions, or flat catalog mockup appearance when supported.",
            "Use practical productUsage constraints like how the hand should hold the item, which end touches the surface, realistic pressure, scale, and actions that would be physically wrong.",
            "ProductUsage is a guardrail, not a new creative brief. It must not replace the reference video's demo use-case in render prompts.",
            "Make forbiddenUsageErrors concrete enough to block likely wrong substitutions such as using the wrong end, wrong surface, wrong scale, or replacing a task-specific item with a generic tool.",
            "Available metadata:",
            *metadata_lines,
        ]
    )
    return system, user


def build_compile_summary_prompt(input_data: dict[str, Any]) -> str:
    return _join(
        [
            f"Compile target: {input_data.get('targetDuration')}s vertical {input_data.get('aspectRatio')}.",
            f"Language: {input_data.get('language')}." if input_data.get("language") else "",
            f"Reference format: {input_data.get('referenceAnalysis', {}).get('format')}.",
            f"Product: {input_data.get('productLock', {}).get('productName')}.",
        ]
    )
