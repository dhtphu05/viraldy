# VIRALDY — RESEARCH-BACKED GOLDEN OUTPUT & SEMANTIC ACCEPTANCE BASELINE

**Version:** 1.0  
**Research cutoff:** 2026-07-31  
**Status:** Authoritative semantic baseline for supervised private beta, showcase fixtures, prompt evaluation, and regression testing  
**Supersedes:** `VIRALDY_GOLDEN_OUTPUT_REFERENCE_AND_ACCEPTANCE_EXAMPLES_V0_9.md`

## Authority statement

This document defines what a high-quality Viraldy intelligence output must mean, not merely how it should sound.

It is authoritative for:

- product-aware personalization;
- evidence-grounded Creative DNA;
- PatternKit abstraction;
- ViralKit composition;
- Creative Campaign Pack quality;
- exact UGC Preflight behavior;
- seller-facing decisions;
- creator-friendly revision requests;
- ambiguous and insufficient-evidence handling;
- domain-specific behavior for TikTok Shop US, POD/personalization, and dropshipping;
- golden fixtures and semantic regression tests.

This document is **not** proof that any creative pattern is viral, causal, or commercially successful. A pattern becomes performance-supported only when linked campaign data meets the evidence and sample-size rules defined below.

When this document conflicts with a shortened example embedded in another goal file, this document wins.

---

# R1. Research method and evidence hierarchy

## R1.1 Research scope

The baseline combines five evidence classes:

1. **Official platform and regulator guidance** — TikTok for Business, TikTok Shop Academy, FTC, Etsy, Shopify.
2. **Operational creator-workflow guidance** — Insense campaign and revision rules.
3. **Creative-strategy frameworks** — Motion and Foreplay taxonomies for hooks, mechanics, formats, fatigue, and research-to-brief workflows.
4. **POD and fulfillment guidance** — Etsy, Printful, Printify.
5. **Community observations** — seller discussions used only as low-confidence failure signals, never as normative truth.

## R1.2 Source-confidence tiers

| Tier | Meaning | Allowed use in Viraldy |
|---|---|---|
| `A_OFFICIAL` | Official platform, regulator, or policy source | Hard rules, compliance checks, platform-specific requirements |
| `B_CORROBORATED` | Reputable practitioner/vendor pattern supported by multiple examples | Pattern hypotheses, creator workflow, testing guidance |
| `C_COMMUNITY_SIGNAL` | Seller/creator anecdote or discussion | Error discovery, diagnostic questions, qualitative hypotheses only |
| `D_INTERNAL_HYPOTHESIS` | Viraldy inference not yet validated externally | Test hypothesis only; must be labeled and measured |

No `C_COMMUNITY_SIGNAL` or `D_INTERNAL_HYPOTHESIS` may create a hard blocker unless an independent rule, Product Context constraint, or Campaign Pack requirement supports it.

## R1.3 Normative research findings

The following findings shape this baseline:

- TikTok-native creative should be vertical, readable inside safe zones, visually stimulating, sound-aware, and structured around a hook, body, and close. `[SRC-TT-01]`
- Shoppable videos commonly use a clear beginning, body, and CTA; product demonstrations, product tests, tutorials, real-life sharing, varied scenes, and ordering guidance are recognized content structures. `[SRC-TT-02]`
- Creator content should preserve the creator's natural voice and typical style. Forced scripts, forced trends, and mismatched communities can reduce authenticity. A product may appear later when the story genuinely needs setup; early reveal is not a universal law. `[SRC-TT-03]`
- Product, visual demo, verbal description, listing, price, promotion, shipping, and claims must stay consistent. False demonstrations, unsupported comparisons, misleading delivery promises, and product-listing mismatch are prohibited. `[SRC-TT-04]` `[SRC-TT-05]`
- Commercial relationships and material connections require clear disclosure. Platform disclosure tools may not always replace clear, conspicuous disclosure in the content itself. `[SRC-FTC-01]` `[SRC-FTC-02]`
- Revision requests should be specific and tied to the original brief; creator collaboration should not turn into unlimited scope expansion. `[SRC-INS-01]` `[SRC-INS-02]`
- Creative analysis should distinguish the message angle, creative mechanic, hook tactic, psychological trigger, visual format, and narrative sequence. Treating all of them as “the hook” produces generic outputs. `[SRC-MOT-01]` `[SRC-MOT-02]`
- Creative fatigue usually calls for refreshing high-impact elements such as the hook or angle before declaring the product dead. `[SRC-MOT-03]`
- Swipe-file and competitor research create value only when references become structured, searchable inputs to briefs and experiments rather than surface-level copies. `[SRC-FOR-01]` `[SRC-FOR-02]`
- Personalized products must be represented accurately, with a real finished customized item where required, readable personalization, and clear collection of each customization detail. `[SRC-ETSY-01]` `[SRC-ETSY-02]`
- POD sellers should verify samples, print quality, sizing, materials, photos, shipping estimates, and supplier reliability rather than relying only on mockups. `[SRC-POD-01]` `[SRC-POD-02]` `[SRC-POD-03]`
- Dropshipping sellers remain responsible for product safety, supplier quality, truthful shipping information, refunds, and customer expectations even when fulfillment is outsourced. `[SRC-SHOP-01]`

---

# R2. Viraldy semantic architecture

## R2.1 The intelligence chain

```text
Product Context
+ Authorized media
+ Transcript / OCR / frame observations
        ↓
Creative DNA
        ↓
PatternKit candidate
        ↓
Product-specific PatternKit match
        ↓
ViralKit: exactly three testable concepts
        ↓
Creative Campaign Pack
        ↓
Compiled exact requirements
        ↓
UGC Preflight
        ↓
SellerActionPlan
        ↓
Seller action + revision + outcome
        ↓
Pattern performance update
```

## R2.2 What each artifact means

| Artifact | Question answered | Must not claim |
|---|---|---|
| Creative DNA | What is observed in this asset? | Why it will perform |
| PatternKit | What reusable structure is supported by the source evidence? | That the pattern is winning without performance evidence |
| ViralKit | How should one or more patterns be adapted into three product-specific tests? | That any concept will go viral or generate GMV |
| Creative Campaign Pack | What exactly should the creator produce? | That it is a TikTok Ads/Meta campaign object |
| Preflight | Did the draft satisfy the exact brief and structural requirements? | Guaranteed conversion or legal approval |
| SellerActionPlan | What should the seller do next, under which conditions, and what should be learned? | Invented budget, threshold, rights, or economics |

## R2.3 Separation of semantic layers

Viraldy must not collapse these concepts:

```text
Message angle
≠ Creative mechanic
≠ Hook tactic
≠ Psychological trigger
≠ Visual format
≠ Narrative sequence
≠ Product proof
≠ CTA
```

### Message angle

The product-specific strategic claim or framing, for example:

- save space in a small dorm;
- turn a pet identity into a gift;
- prevent an opened snack bag from spilling in a backpack.

### Creative mechanic

The cognitive or emotional mechanism that makes the story work, for example:

- implied answer;
- social witness;
- contrast;
- reframe;
- overheard conversation;
- objection breaker;
- story/Trojan-horse.

### Hook tactic

The opening frame used to earn attention, for example:

- problem callout;
- result first;
- identity callout;
- confession;
- contrarian statement;
- question;
- warning;
- price anchor;
- novelty/newness;
- comment reply.

### Psychological trigger

The emotional mechanism inside the hook, for example:

- curiosity gap;
- identity and belonging;
- pain agitation;
- surprise;
- social proof;
- urgency/stakes;
- credibility;
- relief;
- loss aversion.

### Visual format

The surface production format, for example:

- selfie review;
- hands-only demo;
- before/after split screen;
- unboxing;
- street interview;
- comment reply;
- screen recording;
- reaction;
- creator POV;
- montage.

### Narrative sequence

The ordered beats, for example:

```text
problem → product reveal → demo → observable proof → CTA
```

## R2.4 Source observation versus adapted requirement

PatternKit records what source assets showed. ViralKit decides what the target product should require.

Unacceptable:

```json
{
  "source_product_first_appearance_ms": 900,
  "mandatory_target_product_first_appearance_ms": 900
}
```

Correct:

```json
{
  "observed_source_range_ms": {
    "min": 900,
    "max": 2200,
    "source_asset_count": 2
  },
  "adaptation_status": "requires_product_specific_compilation",
  "recommended_target_range_ms": null
}
```

Then ViralKit may compile:

```json
{
  "requirement_type": "product_visibility_timing",
  "instruction": "Show the target product clearly before 2000 ms.",
  "expected_before_ms": 2000,
  "reason": "The selected result-first concept needs the product to ground the promise immediately.",
  "source": "viral_kit_concept_requirement"
}
```

A story-led or reaction-led concept may intentionally allow a later reveal when the setup is necessary. The decision must be explicit and concept-specific.

---

# R3. Research-backed social creative pattern catalog

The catalog below is not a list of guaranteed winners. It is a library of testable pattern families that PatternKit may recognize and ViralKit may adapt.

## P01 — Problem → Solution / Lifehack

- **Evidence tier:** `A_OFFICIAL + B_CORROBORATED`
- **Mechanism:** Mirrors a recognizable problem, introduces the product naturally, then demonstrates a practical resolution.
- **Use when:** Products with a visible, common pain and a short, safe demonstration.
- **Avoid when:** Products whose outcome is delayed, invisible, highly subjective, or requires unsupported claims.
- **Minimum evidence:** Problem scene, product appearance, mechanism-in-use, result or benefit cue.
- **Common failure:** The problem is exaggerated, the product appears unrelated, or the “solution” is only spoken rather than shown.
- **Viraldy domain use:** TikTok Shop home/beauty/gadgets; dropshipping demonstration products; POD only when the pain is ordering or gifting confusion.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P02 — Result First → Explanation

- **Evidence tier:** `A_OFFICIAL + B_CORROBORATED`
- **Mechanism:** Leads with the visible effect or final state, then explains how the product produced it.
- **Use when:** Strong observable transformations or highly visual end states.
- **Avoid when:** Manipulated before/after, lighting changes, or results that cannot be substantiated.
- **Minimum evidence:** Result frame, continuity evidence, product use, same-object proof.
- **Common failure:** The first frame overpromises, the result is unrelated to the product, or the explanation never proves causality.
- **Viraldy domain use:** Beauty, cleaning, organization, apparel styling, compact tools.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P03 — Tutorial / How-To

- **Evidence tier:** `A_OFFICIAL`
- **Mechanism:** Reduces uncertainty through a clear sequence of steps and shows the product being used.
- **Use when:** Products where usage knowledge or setup is a major objection.
- **Avoid when:** Long, over-scripted instructions or steps that are unsafe or not in the product documentation.
- **Minimum evidence:** Ordered demo steps, product visibility, voiceover or captions, final state.
- **Common failure:** Steps are skipped, the product leaves frame, or the tutorial contradicts the listing.
- **Viraldy domain use:** Electronics, tools, personalization ordering, beauty routines, home products.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P04 — Product Test / Proof

- **Evidence tier:** `A_OFFICIAL + B_CORROBORATED`
- **Mechanism:** Creates trust by testing one clear product promise under visible conditions.
- **Use when:** Products with a safe and representative test that viewers can verify.
- **Avoid when:** Universal guarantees, staged tests, unsupported materials, or tests that imply safety/certification.
- **Minimum evidence:** Test setup, product action, result, conditions, compatibility.
- **Common failure:** The test condition is hidden, the result is edited, or the test is not representative of normal use.
- **Viraldy domain use:** Gadgets, cleaning, packaging tools, apparel fit, print quality.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P05 — Before / After

- **Evidence tier:** `A_OFFICIAL`
- **Mechanism:** Uses contrast to make change visible and easy to understand.
- **Use when:** Observable changes that can be filmed on the same item, area, or subject.
- **Avoid when:** Different lighting, camera distance, objects, styling, or unverified long-term outcomes.
- **Minimum evidence:** Before and after frames, same-object continuity, timing, no deceptive editing.
- **Common failure:** The before and after cannot be compared or the transformation is implied rather than visible.
- **Viraldy domain use:** Garment care, organization, cleaning, beauty with careful claims, POD mockup-versus-finished-item comparison.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P06 — Unboxing / First Impression

- **Evidence tier:** `A_OFFICIAL`
- **Mechanism:** Uses novelty, packaging, and authentic initial reaction to create curiosity and trust.
- **Use when:** Giftable products, visually distinctive packaging, products with setup or reveal value.
- **Avoid when:** Fake first reactions, undisclosed gifting, or packaging that differs from what buyers receive.
- **Minimum evidence:** Package, opening sequence, actual product, reaction, disclosure.
- **Common failure:** The product is never demonstrated, the reaction is over-scripted, or the package hides quality issues.
- **Viraldy domain use:** POD gifts, beauty, fashion, home products.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P07 — Creator-Native Personal Review

- **Evidence tier:** `A_OFFICIAL`
- **Mechanism:** Builds credibility through the creator’s normal voice, style, and community language.
- **Use when:** Creator has genuine category fit and enough product knowledge to speak naturally.
- **Avoid when:** Word-for-word scripts, unfamiliar creator formats, or claims the creator cannot support.
- **Minimum evidence:** Creator style history, natural delivery, product use, disclosure.
- **Common failure:** The brand voice replaces creator voice; creator sounds like reading a brief.
- **Viraldy domain use:** All creator-commerce categories.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P08 — Real-Life Scenario / POV

- **Evidence tier:** `A_OFFICIAL + B_CORROBORATED`
- **Mechanism:** Places the product in a recognizable moment so the viewer self-identifies with the use case.
- **Use when:** Buyer pain is situational and the product naturally belongs in the scene.
- **Avoid when:** Convoluted setups, forced dialogue, or scenarios disconnected from actual use.
- **Minimum evidence:** Context cue, buyer pain, product integration, outcome.
- **Common failure:** The scenario consumes the whole video and the product never becomes clear.
- **Viraldy domain use:** Dorm, travel, family routine, gifting, workday, small-space living.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P09 — Comparison / Old Way vs New Way

- **Evidence tier:** `B_CORROBORATED`
- **Mechanism:** Creates contrast between an existing workaround and the proposed product method.
- **Use when:** The alternative is familiar and the comparison can be objective.
- **Avoid when:** Disparaging competitors, vague “better” claims, or unsupported price/performance comparison.
- **Minimum evidence:** Both methods, comparable conditions, factual dimensions.
- **Common failure:** Cherry-picked comparison, hidden tradeoffs, or negative brand references.
- **Viraldy domain use:** Tools, organization, POD gift-versus-generic-gift framing, compact alternatives.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P10 — Comment Reply / FAQ

- **Evidence tier:** `A_OFFICIAL + B_CORROBORATED`
- **Mechanism:** Turns real objections or questions into a creator-native answer and demonstration.
- **Use when:** The comment is real or clearly presented as a common question, and the answer can be shown.
- **Avoid when:** Fabricated social proof or pretending a generated comment is real.
- **Minimum evidence:** Comment source, spoken/visual answer, product demonstration.
- **Common failure:** The answer dodges the question or invents compatibility, shipping, or product facts.
- **Viraldy domain use:** Personalization ordering, sizing, compatibility, shipping, product use.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P11 — Social Witness / Reaction

- **Evidence tier:** `B_CORROBORATED`
- **Mechanism:** Uses another person’s visible reaction or social observation to add credibility and emotional payoff.
- **Use when:** Reaction is genuine, consented, and the product payoff is visible.
- **Avoid when:** Staged testimonials, hidden incentives, or using a person’s likeness without permission.
- **Minimum evidence:** Reaction moment, product reveal, relationship/context, disclosure.
- **Common failure:** Reaction replaces product proof or becomes exaggerated theater.
- **Viraldy domain use:** POD gifts, surprise products, family/home products.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P12 — Identity Callout / Community Language

- **Evidence tier:** `A_OFFICIAL + B_CORROBORATED`
- **Mechanism:** Allows the right audience to self-select through a specific identity, community, role, or life stage.
- **Use when:** Identity is relevant to the product and the creator genuinely understands the community.
- **Avoid when:** Stereotyping, forced slang, sensitive targeting, or identity unrelated to the offer.
- **Minimum evidence:** Buyer persona, community context, creator fit, product relevance.
- **Common failure:** Generic “for everyone” copy or community language copied from another niche.
- **Viraldy domain use:** Dog moms, nurses, teachers, gamers, dorm students, travelers, parents.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P13 — Gift Reaction / Personalization Reveal

- **Evidence tier:** `A_OFFICIAL + B_CORROBORATED`
- **Mechanism:** Combines recipient identity, a personalized reveal, and emotional payoff.
- **Use when:** A finished personalized item exists and the exact customization is verified.
- **Avoid when:** Placeholder mockups, wrong name/breed/date, private customer data, or delivery promises not backed by fulfillment.
- **Minimum evidence:** Finished product, readable customization, recipient/occasion, ordering clarity.
- **Common failure:** Emotional reaction is strong but the personalized product is wrong or unreadable.
- **Viraldy domain use:** POD apparel, mugs, ornaments, jewelry, personalized home decor.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P14 — Objection Handling / Skepticism Breaker

- **Evidence tier:** `B_CORROBORATED`
- **Mechanism:** Names a believable objection and resolves it with evidence rather than reassurance alone.
- **Use when:** Objection is real and answerable from product facts or demonstration.
- **Avoid when:** Invented objections, fake authority, or unsupported guarantees.
- **Minimum evidence:** Objection source, product fact, proof, caveat.
- **Common failure:** “Trust me” language with no evidence or hiding product limitations.
- **Viraldy domain use:** Compatibility, size/fit, personalization process, shipping, setup, durability.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P15 — Confession / Contrarian Reframe

- **Evidence tier:** `B_CORROBORATED`
- **Mechanism:** Breaks expectation with a candid admission or counterintuitive frame.
- **Use when:** The statement is truthful and leads naturally to product relevance.
- **Avoid when:** Manufactured controversy, dangerous advice, or false expert claims.
- **Minimum evidence:** Claim basis, personal context, product connection.
- **Common failure:** Clickbait is stronger than the actual product story.
- **Viraldy domain use:** Ad-fatigued audiences, comparison contexts, creator reviews.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P16 — Story / Trojan-Horse Integration

- **Evidence tier:** `A_OFFICIAL + B_CORROBORATED`
- **Mechanism:** Begins with an entertaining or emotionally relevant story, then integrates the product as part of the resolution.
- **Use when:** Creator is a strong storyteller and delayed integration improves coherence.
- **Avoid when:** Treating late product reveal as automatically wrong or letting the story hide the product entirely.
- **Minimum evidence:** Story setup, natural product integration, creator style fit, final action.
- **Common failure:** Brand interruption feels forced, or the product is irrelevant to the story.
- **Viraldy domain use:** Lifestyle, travel, gift stories, day-in-the-life, comedic creator formats.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P17 — Trend / Community Remix

- **Evidence tier:** `A_OFFICIAL`
- **Mechanism:** Uses a relevant trend, sound, meme, or community convention to make the product feel native.
- **Use when:** Creator has used similar formats and the trend genuinely supports the product story.
- **Avoid when:** Forcing a dance, sound, or meme that the creator/community would not normally use.
- **Minimum evidence:** Trend relevance, creator history, community match, product integration.
- **Common failure:** Trend becomes the only idea and the product feels pasted on.
- **Viraldy domain use:** All categories, but only when relevance is explicit.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.

## P18 — Offer / Value Anchor

- **Evidence tier:** `A_OFFICIAL + B_CORROBORATED`
- **Mechanism:** Makes the commercial reason to act clear through price, bundle, discount, or value comparison.
- **Use when:** Offer is current, authorized, and consistent with the product listing.
- **Avoid when:** Expired discounts, fake scarcity, inconsistent price, unsupported “cheapest” or savings claims.
- **Minimum evidence:** Current listing price, offer terms, timing, CTA.
- **Common failure:** Offer overwhelms product proof or becomes misleading.
- **Viraldy domain use:** TikTok Shop conversion content, bundle tests, seasonal promotions.

PatternKit must store this as a hypothesis with provenance. ViralKit must adapt it to the current product rather than copy wording, creator identity, or scene execution.


---

# R4. Real-world mistake taxonomy

Each mistake code must map to one or more of:

- evidence finding;
- confidence;
- hard blocker or priority;
- seller-facing explanation;
- creator-facing revision;
- required input or next action.

A mistake must not be inferred without evidence. The same symptom may have different root causes.

| Code | Real mistake | Detection basis | Required Viraldy action |
|---|---|---|---|
| `STRATEGY_GENERIC_ANGLE` | Angle could apply to any product | Product name/mechanism/buyer absent from concept | Rewrite using Product Context; do not approve showcase output. |
| `STRATEGY_SURFACE_COPY` | Reference wording or scene identity is copied | High semantic/visual similarity to source | Keep mechanism; change buyer, wording, creator, setting, proof, and execution. |
| `STRATEGY_FORCED_TREND` | Trend does not fit creator or product | Creator history and current format mismatch | Remove trend or choose a creator-native format. |
| `STRATEGY_FORCED_HOOK` | Opening is convoluted or disconnected | Hook and product narrative do not converge | Use a natural hook or allow necessary story setup. |
| `STRATEGY_ONE_VARIABLE_NOT_CONTROLLED` | Test changes many factors without a learning plan | No held-constant list | Compile a test matrix with changed axes and controlled variables. |
| `CREATOR_OVER_SCRIPTED` | Creator sounds like reading brand copy | Delivery mismatch, unnatural pacing | Preserve facts and constraints; rewrite as talking points. |
| `CREATOR_WRONG_COMMUNITY` | Creator language/style does not fit target community | Persona/community mismatch | Select a creator or framing with credible community fit. |
| `CREATOR_SCOPE_CREEP` | Revision requests add new deliverables outside brief | Requested change has no source_path in brief | Create a new paid scope/version rather than treating it as a revision. |
| `CREATOR_VAGUE_FEEDBACK` | Feedback says “catchier” or “more viral” | No expected/observed/action detail | Return timecoded, requirement-linked revision instructions. |
| `OPENING_NO_CLEAR_CONTEXT` | First seconds lack problem, result, identity, or product context | Opening observations incomplete | Choose one clear opening function instead of adding random motion. |
| `PRODUCT_LATE_FOR_SELECTED_CONCEPT` | Product timing violates concept requirement | first_appearance_ms > expected_before_ms | Move product earlier only for the selected concept requirement. |
| `PRODUCT_FORCED_TOO_EARLY` | Brand insertion harms natural story setup | Story mechanic requires setup and product is rushed | Allow a later reveal with an explicit maximum window. |
| `PRODUCT_MISMATCH` | Shown product/variant does not match Product Context | Product match confidence below threshold | Reject or reshoot with the correct SKU/variant. |
| `PRODUCT_OBSCURED` | Text/sticker/hand blocks critical product detail | Frame evidence shows obstruction | Reshoot or reposition overlay/product. |
| `DEMO_NO_MECHANISM` | Product appears but mechanism is not visible | Demo step lacks action/result | Add a clear in-use step. |
| `DEMO_UNSUPPORTED_MATERIAL` | Demo uses an unverified material or compatibility | Product governance conflict | Reshoot with seller-authorized compatible material. |
| `DEMO_FALSE_OR_STAGED` | Demonstration is misleading or edited to imply unsupported result | Continuity or product facts conflict | Reject; request representative demonstration. |
| `PROOF_SPOKEN_ONLY` | Creator states a result without observable evidence | Claim exists but proof evidence absent | Add verifiable proof or soften to personal experience. |
| `PROOF_BEFORE_AFTER_INCOMPARABLE` | Before and after differ in lighting/object/camera | Continuity check fails | Reshoot on the same object/area under comparable conditions. |
| `PROOF_TOO_BRIEF` | Evidence appears too briefly to verify | Visible duration below readability/viewability requirement | Extend proof shot; do not mark satisfied. |
| `CTA_MISSING` | No actionable close | CTA evidence absent where required | Add product-tag/order guidance appropriate to objective. |
| `CTA_WRONG_TYPE` | CTA does not match objective or platform | Expected CTA type differs from observed | Replace with the selected Campaign Pack CTA. |
| `CTA_NO_PRODUCT_TAG` | TikTok Shop product tag cue is required but absent | product_tag_visible=false | Add product tag and clear ordering cue. |
| `OFFER_INCONSISTENT` | Price/discount differs from listing | OCR/ASR conflicts with Product Context | Remove or update the offer before posting. |
| `OFFER_FAKE_SCARCITY` | Scarcity/urgency has no seller-authorized basis | No offer evidence or expiry | Remove invented urgency. |
| `CLAIM_UNSUPPORTED` | Objective product claim lacks support | Claim candidate + no governance support | Remove, qualify, or add authorized substantiation. |
| `CLAIM_UNIVERSAL_GUARANTEE` | Claim applies to every user/material/result | Universal language detected | Rewrite to supported use and scope. |
| `DISCLOSURE_COMMERCIAL_MISSING` | Paid/gifted relationship not disclosed | Commercial relationship known; disclosure absent | Add clear disclosure and platform branded-content setting. |
| `DISCLOSURE_PRODUCT_MISSING` | Required product qualification absent | Required disclosure matcher missing | Add readable/spoken disclosure close to the claim. |
| `DISCLOSURE_NOT_READABLE` | Disclosure exists but is too brief/small/obscured | OCR duration/visibility insufficient | Increase duration, contrast, size, or spoken support. |
| `SHIPPING_UNAUTHORIZED` | Creator promises unverified delivery speed | Spoken/OCR claim conflicts with Product Context | Remove or use seller-authorized estimate. |
| `SHIPPING_PRODUCT_MISMATCH` | Shipped or shown item differs from listing | Asset/product mismatch | Block publication and investigate supplier/fulfillment. |
| `RIGHTS_INCOMPLETE` | Paid-use rights or Spark authorization missing | Rights record incomplete | Hold paid use; request authorization/terms. |
| `POD_WRONG_PERSONALIZATION` | Name/date/breed/image differs from approved order | OCR/vision mismatch | Reject current asset; use correct finished product. |
| `POD_MOCKUP_ONLY` | Only a digital mockup is shown where finished item is required | No physical-item evidence | Show an actual finished sample. |
| `POD_TEXT_UNREADABLE` | Personalization cannot be verified | OCR confidence/duration insufficient | Reshoot close-up with readable contrast. |
| `POD_PRIVACY_EXPOSURE` | Customer address/order details visible | Sensitive text detected | Remove/redact and reshoot. |
| `POD_SIZE_OR_VARIANT_AMBIGUOUS` | Garment size/color/style unclear or wrong | Product variant mismatch | Show and state approved variant only. |
| `POD_IP_RISK` | Unauthorized trademark, celebrity, or copied design | Governance/IP flag | Do not generate or publish; require authorization/original design. |
| `POD_SAMPLE_NOT_VERIFIED` | Creative relies on mockup without sample QA | No sample/actual-product confirmation | Mark proof confidence low and request sample verification. |
| `DROP_SUPPLIER_NOT_VERIFIED` | Seller has not verified supplier/product quality | Product Context completeness gap | Hold strong quality claims; request sample/supplier evidence. |
| `DROP_COMPATIBILITY_OVERCLAIM` | Works-with-all claim exceeds verified compatibility | Governance conflict | List supported materials/models only. |
| `DROP_TRUST_CUE_GENERIC` | Fake badges/countdowns/templates create scam cues | Generic template signals | Replace with real product use, support, returns, and transparent facts. |
| `DROP_FUNNEL_DIAGNOSIS_REQUIRED` | Strong clicks but weak orders may be downstream | Metrics pattern; no creative blocker explains gap | Inspect page speed, offer, shipping, reviews, checkout, and economics before rewriting hook. |
| `DROP_ECONOMICS_INVALID` | CPA/test economics cannot work at current margin/AOV | Commercial data shows negative unit economics | Do not recommend scaling; require offer/margin decision. |
| `EVIDENCE_LOW_COVERAGE` | Audio/OCR/visual coverage is incomplete | Coverage below threshold | Return unknown and request better media; do not approve hard requirements. |
| `EVIDENCE_MULTIPLE_PRODUCTS` | More than one product appears and mapping is uncertain | Multiple product candidates | Require seller confirmation or product tracking. |
| `EVIDENCE_DARK_OR_BLURRY` | Product/proof cannot be verified | Visual quality low | Request better-lit or higher-resolution footage. |
| `DATA_SCORE_OVERFIT` | Test asserts exact demo score rather than semantic band | Fixture expectation too brittle | Assert action band, blocker set, evidence validity, and relative improvement. |
| `DATA_PATTERN_CALLED_WINNER_TOO_EARLY` | Pattern labeled winning without performance support | performance_summary=none/directional | Rename to candidate/directional pattern. |
| `DATA_CAUSAL_OVERCLAIM` | Correlation framed as causal truth | No experimental control | Use directional language and caveats. |


---

# R5. Mapping the research taxonomy to current PatternKitV1 and ViralKitV1

This baseline must work with the current backend contracts rather than inventing a disconnected schema.

## R5.1 PatternKitV1 mapping

| Research concept | Current contract location |
|---|---|
| Hook tactic | `opening.primary_hook_types` |
| Hook mechanism | `opening.hook_mechanism` |
| Psychological trigger | `narrative.emotional_drivers` |
| Message angle | `narrative.angle_family` |
| Narrative sequence | `sequence` and `narrative.narrative_progression` |
| Product reveal | `product_reveal` |
| Demo | `demo` |
| Proof | `proof` |
| Creator-native style | `creator` |
| Visual/editing format | `editing` plus sequence and creator fields |
| Offer and CTA | `offer`, `cta` |
| POD applicability | `applicability.pod_context` |
| Dropshipping applicability | `applicability.dropshipping_context` |
| Keep/change/avoid | `adaptation_instructions` |
| Performance support | `performance_summary` |
| Source facts | `PatternEvidenceRefV1` |

Do not add a new field merely because a blog uses a different name. Add a schema version only when the current contract cannot preserve a material distinction.

## R5.2 ViralKitV1 mapping

| Research concept | Current contract location |
|---|---|
| Product snapshot | `product.snapshot_json` |
| Buyer pain/desired outcome | `buyer_context`, concept fields |
| Pattern applicability/conflict | `pattern_matches` |
| Product-specific adaptation | `adaptation_plan` |
| Exactly three concepts | `concepts` validator |
| Different hook/mechanic/proof | `diversity_axes` and concept fields |
| Exact production requirements | `must_show`, `overlays`, `spoken_lines`, disclosures |
| Test plan | `test_matrix` |
| Generation instructions | `generation_briefs` |
| Campaign Pack linkage | `campaign_pack_links` |
| Preflight requirement classes | `preflight_requirement_links` |

## R5.3 Separate recommendation payload

`SellerActionPlanV1` is a separate seller-decision object. It must not be buried inside ViralKit or a prose summary.

---

# R6. Category-specific TikTok Shop creative guidance

## R6.1 Beauty and personal care

- Show the product and result clearly, especially when the claim depends on visible application.
- Treat before/after as sensitive evidence: same area, comparable lighting, truthful timing, and required qualifications.
- Do not let dramatic visual editing imply a result the product cannot substantiate.

## R6.2 Fashion and POD apparel

- Show fit, full-body or relevant garment area, size/variant, print placement, and readable personalization.
- A mockup may support option education, but a finished actual item is required when the brief or marketplace rule requires it.
- Separate buyer identity from creator identity: “dog mom buyer” is not automatically “dog mom creator.”

## R6.3 Electronics and tools

- Show the effect or function, then explain the product; keep technical claims within documented capabilities.
- Product tests must state or show relevant conditions and compatible materials.

## R6.4 Home and living

- Strong patterns include unboxing, lifehack, real-life pain→solution, and visible result.
- Avoid generic “must-have” framing without a specific use context.

## R6.5 Comment-led iteration

Comments and seller questions may create new PatternKit candidates, but generated or fabricated comments must never be presented as real social proof.

---

# R7. Golden-output precedence rules

1. Product facts beat pattern suggestions.
2. Governance beats creative optimization.
3. Exact Campaign Pack requirements beat generic best practices.
4. Evidence uncertainty beats confident prose.
5. Creator authenticity beats a word-for-word script, provided mandatory facts and disclosures remain intact.
6. A later product reveal may be valid for a story/reaction mechanic; timing is concept-specific.
7. A high structural score cannot override product mismatch, missing disclosure, deceptive proof, missing rights, or negative economics.
8. A strong click signal does not prove the creative caused low conversion; downstream funnel and economics must be diagnosed.
9. PatternKit stores observed ranges; ViralKit compiles target requirements.
10. PatternKit and ViralKit are hypotheses until seller actions and outcomes support them.

---

# PART II — CORE GOLDEN OUTPUTS

The following full-flow scenario remains the primary TikTok Shop reference, now governed by the research rules above.

# 1. Viraldy output philosophy

Every meaningful Viraldy output must satisfy four grounding layers.

## 1.1 Product-grounded

The response must use the actual product context:

- product mechanism;
- buyer persona;
- buyer pain;
- desired outcome;
- price and offer;
- market;
- shipping and fulfillment;
- claims allowed;
- claims prohibited;
- required disclosures;
- product assets;
- seller constraints.

When a value is unavailable, return `unknown`, `null`, or a typed missing state.

Never fill gaps with a plausible-sounding product claim.

## 1.2 Evidence-grounded

Every observation about a video must identify:

- what was observed;
- evidence source;
- timestamp or time range when available;
- evidence ID;
- confidence;
- uncertainty.

A seller must be able to click a finding and inspect the corresponding moment.

## 1.3 Decision-grounded

Every score or diagnosis must lead to a practical action:

- approve;
- revise;
- reject;
- reshoot;
- organic-only;
- small paid test;
- Spark-ready pending rights;
- create Campaign Pack;
- select concept;
- stop using a pattern;
- collect more evidence.

Never end with generic advice such as:

> Make the hook stronger and add a clearer CTA.

## 1.4 Learning-grounded

The system must preserve:

```text
AI output
→ human correction
→ seller decision
→ revision or execution
→ performance outcome
```

The AI output must not be overwritten when the user corrects it.

---

# 2. Quality bar: generic vs Viraldy-grade output

## 2.1 Unacceptable generic output

```text
The hook is weak.
Show the product earlier.
Add social proof.
Use a stronger CTA.
```

Problems:

- no product context;
- no evidence;
- no exact expected timing;
- no reason why the proof is weak;
- no differentiation between blocker and optional improvement;
- no creator-ready revision;
- no action label.

## 2.2 Viraldy-grade output

```text
Action: Revise before paid use
Confidence: Medium

Product: SwiftPress Mini Garment Steamer
Buyer: US college students who need quick clothing care in small spaces
Objective: TikTok Shop affiliate test

Hard blocker
- The Campaign Pack requires the product to appear by 00:02.000.
- The first clear product appearance is at 00:04.200.
- Evidence: product_appearance_17, frames 126–149.

Missing execution
- The brief requires an observable same-fabric before/after result.
- The draft shows steam output but never returns to the original wrinkled section.
- Evidence: demo_action_22 and proof_summary_31.

What is already strong
- The creator delivery feels natural and matches the requested student-review style.
- The product-tag CTA is visible from 00:18.800 to 00:21.100.

Revision request
1. Move the product close-up into the first two seconds.
2. Keep the same shirt section visible before and after steaming.
3. Add the required disclosure: “Results vary by fabric type.”
4. Preserve the current creator delivery and product-tag CTA.
```

---

# 3. Golden end-to-end scenario A — TikTok Shop US home/travel product

## 3.1 Seller context

```text
Seller type: Cross-border TikTok Shop US operator
Team location: Vietnam
Target market: United States
Team size: 4
Creative volume: 20–40 short videos per month
Current workflow: TikTok Favorites + Drive + Sheets + creator chat
Objective: Produce creator UGC for organic affiliate testing and limited Spark testing
```

## 3.2 Product

```text
Product name: SwiftPress Mini Garment Steamer
Category: Home / travel apparel care
Selling price: $29.99
COGS: $8.40
Shipping promise authorized by seller: 4–6 business days
Primary buyer: US college students and frequent travelers
Primary pain: Wrinkled clothing when there is no room or time for a full-size iron
Desired outcome: Presentable clothing with a compact tool
Observable mechanism: Steam is applied directly to wrinkled fabric
Observable proof: Same fabric area before and after use
Offer: 15% launch discount
Objective: TikTok Shop affiliate test
```

## 3.3 Product claim governance

Allowed:

- helps reduce visible wrinkles;
- compact for dorm rooms and travel;
- heats and produces steam according to verified product instructions;
- convenient alternative for quick touch-ups.

Allowed with qualification:

- visible wrinkle reduction, when accompanied by an actual same-fabric demonstration;
- “quick” when not represented as instant and when tied to the observed clip.

Prohibited:

- removes every wrinkle instantly;
- professional dry-cleaning results;
- sanitizes or kills bacteria unless separately verified;
- safe for every fabric;
- guaranteed result.

Required disclosure:

- Results vary by fabric type.

---

# 4. Golden ProductContextV1 output

```json
{
  "schema_version": "product_context_v1",
  "identity": {
    "name": "SwiftPress Mini Garment Steamer",
    "brand": "SwiftPress",
    "category": "home_travel_apparel_care",
    "market": "US",
    "product_type": "portable_garment_steamer"
  },
  "buyer_personas": [
    {
      "id": "college_student",
      "label": "College student in a dorm or shared apartment",
      "pains": [
        "Wrinkled clothes before class or an event",
        "Limited storage space",
        "No full-size ironing setup"
      ],
      "desired_outcomes": [
        "Look presentable quickly",
        "Keep clothing care compact and convenient"
      ],
      "objections": [
        "Will it actually show a visible difference?",
        "Is it safe for my fabric?",
        "Is it worth carrying or storing?"
      ]
    },
    {
      "id": "frequent_traveler",
      "label": "Frequent traveler with carry-on luggage",
      "pains": [
        "Clothes become wrinkled in luggage",
        "Hotel ironing tools may be unavailable"
      ],
      "desired_outcomes": [
        "Refresh clothing without a full ironing board"
      ],
      "objections": [
        "Will it fit in luggage?",
        "How quickly can it be used?"
      ]
    }
  ],
  "benefits": [
    {
      "id": "visible_wrinkle_reduction",
      "statement": "Helps reduce visible wrinkles when used on supported fabrics.",
      "evidence_status": "seller_provided",
      "claim_policy": "allowed_with_qualification"
    },
    {
      "id": "compact_storage",
      "statement": "Compact format for dorm rooms and travel.",
      "evidence_status": "product_spec",
      "claim_policy": "allowed"
    }
  ],
  "commercial": {
    "currency": "USD",
    "selling_price": 29.99,
    "cogs": 8.40,
    "offer": {
      "type": "percentage_discount",
      "value": 15,
      "label": "15% launch discount"
    },
    "shipping": {
      "market": "US",
      "authorized_promise": "4–6 business days",
      "unverified_promises": []
    }
  },
  "creative_context": {
    "visual_demo_potential": "high",
    "recommended_proof": [
      "same_fabric_before_after",
      "close_up_wrinkle_change"
    ],
    "risky_execution": [
      "steam-only shot without visible result",
      "claiming instant results",
      "switching garments between before and after"
    ],
    "platform_cues": [
      "TikTok Shop product tag",
      "vertical 9:16 framing",
      "natural creator delivery"
    ]
  },
  "governance": {
    "allowed_claims": [
      "Helps reduce visible wrinkles",
      "Compact for quick touch-ups"
    ],
    "allowed_with_qualification": [
      {
        "claim": "Quick wrinkle reduction",
        "qualification": "Show the actual result and avoid instant-result language."
      }
    ],
    "prohibited_claims": [
      "Removes every wrinkle instantly",
      "Professional dry-cleaning results",
      "Kills bacteria",
      "Safe for every fabric",
      "Guaranteed result"
    ],
    "required_disclosures": [
      "Results vary by fabric type."
    ]
  },
  "completeness": {
    "status": "usable",
    "missing_fields": [
      "verified_supported_fabric_list"
    ]
  }
}
```

Acceptance requirements:

- Product projections must match `identity.name` and `identity.market`.
- Missing supported-fabric information remains missing.
- Downstream outputs must not claim universal fabric compatibility.

---

# 5. Golden Creative DNA output for a reference video

## 5.1 Reference asset description

```text
Duration: 23.4 seconds
Reference product: competing portable steamer
Creator: student/lifestyle creator
Observed flow:
wrinkled shirt problem → product reveal → steaming demo → same-shirt result → product-tag CTA
```

## 5.2 CreativeDnaV1 target output

```json
{
  "schema_version": "creative_dna_v1",
  "asset_version_id": "ref-steamer-asset-v1",
  "opening": {
    "hook_type": {
      "value": "situational_problem",
      "evidence_ids": ["ev-hook-01", "ev-asr-01"],
      "confidence": 0.93
    },
    "hook_text": {
      "value": "I was already late and this shirt was still wrinkled.",
      "evidence_ids": ["ev-asr-01"],
      "confidence": 0.98
    },
    "opening_visual": {
      "value": "Creator holds a visibly wrinkled shirt close to camera.",
      "evidence_ids": ["ev-frame-01"],
      "confidence": 0.95
    },
    "first_three_second_structure": {
      "value": [
        "show_problem",
        "state_time_pressure",
        "reveal_product"
      ],
      "evidence_ids": ["ev-scene-01", "ev-scene-02"],
      "confidence": 0.91
    }
  },
  "product": {
    "first_appearance_ms": {
      "value": 1300,
      "evidence_ids": ["ev-product-first-01"],
      "confidence": 0.96
    },
    "shot_types": {
      "value": ["handheld_close_up", "in_use"],
      "evidence_ids": ["ev-product-appearance-01", "ev-product-appearance-02"],
      "confidence": 0.89
    },
    "product_match_confidence": {
      "value": null,
      "unknown_reason": "No target Product Context was attached to this reference analysis.",
      "evidence_ids": [],
      "confidence": 0.0
    }
  },
  "narrative": {
    "structure": {
      "value": "problem_solution_transformation",
      "evidence_ids": ["ev-scene-sequence-01"],
      "confidence": 0.92
    },
    "angle": {
      "value": "last_minute_clothing_rescue",
      "evidence_ids": ["ev-asr-01", "ev-scene-sequence-01"],
      "confidence": 0.87
    },
    "buyer_pain": {
      "value": "Wrinkled clothing immediately before leaving.",
      "evidence_ids": ["ev-asr-01", "ev-frame-01"],
      "confidence": 0.94
    },
    "desired_outcome": {
      "value": "Make clothing look presentable with minimal setup.",
      "evidence_ids": ["ev-result-01"],
      "confidence": 0.81
    }
  },
  "demo": {
    "detected": {
      "value": true,
      "evidence_ids": ["ev-demo-01"],
      "confidence": 0.98
    },
    "demo_type": {
      "value": "same_item_in_use_transformation",
      "evidence_ids": ["ev-demo-01", "ev-proof-01"],
      "confidence": 0.94
    },
    "steps": {
      "value": [
        "show_wrinkled_fabric",
        "apply_steam_to_same_area",
        "show_same_area_after_use"
      ],
      "evidence_ids": ["ev-demo-01", "ev-proof-01"],
      "confidence": 0.93
    },
    "mechanism_clarity": {
      "value": "clear",
      "evidence_ids": ["ev-demo-01"],
      "confidence": 0.90
    },
    "result_visibility": {
      "value": "clear",
      "evidence_ids": ["ev-proof-01"],
      "confidence": 0.88
    }
  },
  "proof": {
    "proof_types": {
      "value": ["same_item_before_after", "observable_visual_result"],
      "evidence_ids": ["ev-proof-01"],
      "confidence": 0.91
    },
    "verifiability": {
      "value": "medium_high",
      "evidence_ids": ["ev-proof-01"],
      "confidence": 0.82,
      "uncertainty": "Lighting changes slightly between the before and after views."
    }
  },
  "creator": {
    "persona": {
      "value": "college_lifestyle_creator",
      "evidence_ids": ["ev-creator-01"],
      "confidence": 0.75
    },
    "delivery_style": {
      "value": "casual_first_person_review",
      "evidence_ids": ["ev-asr-full-01"],
      "confidence": 0.90
    },
    "authenticity_cues": {
      "value": [
        "situational context",
        "natural speech",
        "hands-on demonstration"
      ],
      "evidence_ids": ["ev-creator-01", "ev-demo-01"],
      "confidence": 0.86
    }
  },
  "editing": {
    "pacing": {
      "value": "fast_but_readable",
      "evidence_ids": ["ev-editing-01"],
      "confidence": 0.87
    },
    "first_three_second_cut_count": {
      "value": 2,
      "evidence_ids": ["ev-editing-01"],
      "confidence": 0.99
    },
    "pattern_interrupts": {
      "value": [
        "wrinkled-shirt close-up",
        "fast product hand-entry"
      ],
      "evidence_ids": ["ev-editing-02"],
      "confidence": 0.85
    },
    "dead_air_ranges": {
      "value": [],
      "evidence_ids": ["ev-editing-03"],
      "confidence": 0.82
    }
  },
  "offer": {
    "present": {
      "value": false,
      "evidence_ids": [],
      "confidence": 0.66,
      "uncertainty": "No clear price or discount was observed in transcript or OCR evidence."
    }
  },
  "cta": {
    "present": {
      "value": true,
      "evidence_ids": ["ev-cta-01"],
      "confidence": 0.98
    },
    "cta_type": {
      "value": "tiktok_shop_product_tag",
      "evidence_ids": ["ev-cta-01"],
      "confidence": 0.95
    },
    "start_ms": {
      "value": 20100,
      "evidence_ids": ["ev-cta-01"],
      "confidence": 0.98
    },
    "spoken_text": {
      "value": "It is linked right here.",
      "evidence_ids": ["ev-asr-cta-01"],
      "confidence": 0.97
    },
    "overlay_text": {
      "value": "Shop now",
      "evidence_ids": ["ev-ocr-cta-01"],
      "confidence": 0.91
    }
  },
  "claims": {
    "observed_claims": [
      {
        "text": "It fixed the wrinkles so fast.",
        "risk": "medium",
        "reason": "The claim is supported directionally by the visible result but uses broad speed language.",
        "evidence_ids": ["ev-asr-claim-01", "ev-proof-01"],
        "confidence": 0.79
      }
    ]
  },
  "reusable_mechanisms": [
    {
      "mechanism": "situational urgency before product reveal",
      "evidence_ids": ["ev-hook-01", "ev-product-first-01"],
      "confidence": 0.88
    },
    {
      "mechanism": "same-item demonstration followed by visible result",
      "evidence_ids": ["ev-demo-01", "ev-proof-01"],
      "confidence": 0.92
    }
  ],
  "risks": [
    {
      "code": "REFERENCE_SPEED_CLAIM",
      "severity": "medium",
      "message": "Do not copy broad speed language without product-specific evidence.",
      "evidence_ids": ["ev-asr-claim-01"]
    }
  ],
  "overall_confidence": "high",
  "uncertainties": [
    "The creator persona is inferred from content style, not verified profile data.",
    "No performance data is attached, so this analysis does not prove that the structure caused sales."
  ]
}
```

Acceptance requirements:

- Product match remains unknown because no target product was attached.
- The reference is described, not declared a winning ad.
- CTA spoken text and overlay text remain separate.
- Offer is not invented.
- Every positive observation has evidence.

---

# 6. Golden PatternKit output

## 6.1 PatternKit name

```text
Deadline Pressure → Fast Product Reveal → Same-Fabric Proof
```

## 6.2 Intended use

This PatternKit abstracts a reusable structure from two reference videos. It does not copy either script.

## 6.3 PatternKitV1 target output

```json
{
  "schema_version": "pattern_kit_v1",
  "id": "pk-deadline-fast-reveal-proof",
  "version": 1,
  "name": "Deadline Pressure → Fast Product Reveal → Same-Fabric Proof",
  "summary": "A situation-led structure that creates urgency, reveals the product early, demonstrates use on the same item, and closes with observable proof and a commerce CTA.",
  "kind": "multi_asset_cluster",
  "scope": "workspace_private",
  "status": "candidate",
  "source": {
    "creative_dna_version_ids": [
      "dna-steamer-reference-v1",
      "dna-lint-remover-reference-v1"
    ],
    "source_asset_count": 2,
    "source_category_count": 2,
    "extraction_mode": "ai_assisted"
  },
  "sequence": [
    {
      "beat_id": "beat_1_problem_hook",
      "order": 1,
      "beat_type": "hook",
      "purpose": "Make the buyer recognize a time-sensitive or socially uncomfortable problem.",
      "recommended_start_ms_min": 0,
      "recommended_start_ms_max": 300,
      "recommended_duration_ms_min": 900,
      "recommended_duration_ms_max": 1800,
      "requiredness": "required",
      "evidence_refs": ["pattern-ev-hook-a", "pattern-ev-hook-b"],
      "confidence": 0.90
    },
    {
      "beat_id": "beat_2_product_reveal",
      "order": 2,
      "beat_type": "product_reveal",
      "purpose": "Connect the product directly to the problem before attention decays.",
      "recommended_start_ms_min": 900,
      "recommended_start_ms_max": 2200,
      "recommended_duration_ms_min": 800,
      "recommended_duration_ms_max": 1800,
      "requiredness": "required",
      "evidence_refs": ["pattern-ev-product-a", "pattern-ev-product-b"],
      "confidence": 0.92
    },
    {
      "beat_id": "beat_3_in_use_demo",
      "order": 3,
      "beat_type": "demo",
      "purpose": "Show the mechanism on the actual problem object.",
      "recommended_start_ms_min": 2000,
      "recommended_start_ms_max": 4500,
      "recommended_duration_ms_min": 3500,
      "recommended_duration_ms_max": 7000,
      "requiredness": "required",
      "evidence_refs": ["pattern-ev-demo-a", "pattern-ev-demo-b"],
      "confidence": 0.91
    },
    {
      "beat_id": "beat_4_observable_proof",
      "order": 4,
      "beat_type": "proof",
      "purpose": "Return to the same item or area and show an observable result.",
      "recommended_start_ms_min": 7000,
      "recommended_start_ms_max": 13000,
      "recommended_duration_ms_min": 1800,
      "recommended_duration_ms_max": 4000,
      "requiredness": "required",
      "evidence_refs": ["pattern-ev-proof-a", "pattern-ev-proof-b"],
      "confidence": 0.89
    },
    {
      "beat_id": "beat_5_commerce_cta",
      "order": 5,
      "beat_type": "cta",
      "purpose": "Make the next commerce action explicit without replacing proof with sales language.",
      "recommended_start_ms_min": 15000,
      "recommended_start_ms_max": 22000,
      "recommended_duration_ms_min": 1500,
      "recommended_duration_ms_max": 3500,
      "requiredness": "recommended",
      "evidence_refs": ["pattern-ev-cta-a"],
      "confidence": 0.72
    }
  ],
  "opening": {
    "primary_hook_types": [
      "situational_problem",
      "time_pressure"
    ],
    "hook_mechanism": "Show a recognizable problem and state why it matters now.",
    "opening_visual_pattern": "Problem object fills the frame before or while the first line is spoken.",
    "first_three_second_structure": [
      "problem_visual",
      "situational_context",
      "product_reveal"
    ],
    "face_presence_preference": "optional",
    "product_presence_preference": "before_2200ms",
    "pattern_interrupt_strategy": [
      "macro problem close-up",
      "fast hand-entry with product"
    ],
    "evidence_refs": ["pattern-ev-hook-a", "pattern-ev-hook-b"],
    "confidence": 0.90,
    "uncertainties": []
  },
  "product_reveal": {
    "first_appearance_window_ms": {
      "min": 900,
      "max": 2200
    },
    "preferred_shot_types": [
      "handheld_close_up",
      "in_use"
    ],
    "close_up_expectation": "required",
    "usage_visibility_expectation": "required",
    "screen_time_guidance": "The product should remain identifiable through the core demo.",
    "reveal_role": "solution_connection",
    "product_match_requirement": "Target product identity must be verified when Product Context is attached.",
    "evidence_refs": ["pattern-ev-product-a", "pattern-ev-product-b"],
    "confidence": 0.92,
    "uncertainties": []
  },
  "narrative": {
    "structures": [
      "problem_solution_transformation"
    ],
    "angle_family": "urgent_practical_rescue",
    "buyer_pain_pattern": "A visible problem appears immediately before a socially or practically important moment.",
    "desired_outcome_pattern": "Resolve the visible problem with minimal setup.",
    "emotional_drivers": [
      "relief",
      "preparedness",
      "convenience"
    ],
    "awareness_stage": "problem_aware",
    "narrative_progression": [
      "recognize problem",
      "introduce product",
      "demonstrate mechanism",
      "show result",
      "invite next action"
    ],
    "evidence_refs": ["pattern-ev-narrative-a", "pattern-ev-narrative-b"],
    "confidence": 0.88,
    "uncertainties": []
  },
  "demo": {
    "demo_types": [
      "same_item_in_use_transformation"
    ],
    "mechanism_pattern": "Use the product on the original problem object while preserving visual continuity.",
    "required_steps": [
      "show initial state",
      "show product contacting or affecting the same object",
      "show result on the same object or area"
    ],
    "before_state_expectation": "Clearly visible and retained long enough for comparison.",
    "after_state_expectation": "Same item, same area, or an unmistakably equivalent comparison.",
    "result_visibility_expectation": "Observable without relying only on spoken claims.",
    "continuity_expectation": "medium_high",
    "demo_failure_modes": [
      "showing the tool without showing its effect",
      "changing objects between before and after",
      "cutting before the result becomes visible",
      "using text claims as a substitute for proof"
    ],
    "evidence_refs": ["pattern-ev-demo-a", "pattern-ev-demo-b"],
    "confidence": 0.91,
    "uncertainties": []
  },
  "proof": {
    "proof_types": [
      "same_item_before_after",
      "observable_visual_result"
    ],
    "proof_mechanism": "Return to the original problem area and show a visible change.",
    "verifiability_requirement": "The viewer should be able to compare before and after without trusting narration alone.",
    "proof_timing_guidance": "Immediately after the main demo and before the final CTA.",
    "proof_strength_conditions": [
      "same object or area",
      "similar framing",
      "similar lighting",
      "no hidden product substitution"
    ],
    "unsupported_proof_risks": [
      "universal result claims",
      "instant-result language",
      "edited comparison that hides continuity"
    ],
    "evidence_refs": ["pattern-ev-proof-a", "pattern-ev-proof-b"],
    "confidence": 0.89,
    "uncertainties": []
  },
  "creator": {
    "creator_personas": [
      "student_lifestyle_creator",
      "practical_home_creator",
      "travel_lifestyle_creator"
    ],
    "delivery_styles": [
      "casual_first_person_review",
      "situational_demonstration"
    ],
    "face_presence_preference": "optional",
    "speaking_preference": "recommended",
    "emotion_range": [
      "mild frustration",
      "relief",
      "practical satisfaction"
    ],
    "pacing_preference": "conversational_fast",
    "authenticity_cues": [
      "specific situation",
      "natural wording",
      "hands-on use",
      "observable proof"
    ],
    "sales_language_intensity": "low_to_medium",
    "creator_constraints": [
      "Do not perform exaggerated surprise.",
      "Do not claim universal results."
    ],
    "evidence_refs": ["pattern-ev-creator-a", "pattern-ev-creator-b"],
    "confidence": 0.79,
    "uncertainties": [
      "Creator persona fit has not been validated by performance data."
    ]
  },
  "editing": {
    "pacing": "fast_but_readable",
    "cut_density": "medium_high",
    "first_three_second_cut_guidance": "One or two purposeful cuts; do not hide the product reveal.",
    "caption_density": "medium",
    "transition_types": [
      "direct_cut",
      "match_cut_to_result"
    ],
    "pattern_interrupt_guidance": [
      "macro problem close-up",
      "quick product hand-entry"
    ],
    "dead_air_tolerance": "low",
    "visual_safe_zone_guidance": [
      "Keep product-tag and key overlay clear of TikTok UI zones."
    ],
    "evidence_refs": ["pattern-ev-editing-a", "pattern-ev-editing-b"],
    "confidence": 0.82,
    "uncertainties": []
  },
  "offer": {
    "offer_required": false,
    "offer_types": [
      "optional_launch_discount",
      "value_without_discount"
    ],
    "offer_positioning_pattern": "Proof must appear before offer language.",
    "offer_timing_guidance": "After observable proof and before CTA.",
    "urgency_policy": "Use only seller-authorized urgency.",
    "price_display_policy": "Display only verified price or discount.",
    "commerce_constraints": [
      "Do not invent stock scarcity.",
      "Do not invent shipping speed."
    ],
    "evidence_refs": [],
    "confidence": 0.43,
    "uncertainties": [
      "The source cluster does not contain consistent offer evidence."
    ]
  },
  "cta": {
    "cta_required": true,
    "cta_types": [
      "tiktok_shop_product_tag",
      "low_pressure_shop_prompt"
    ],
    "modalities": [
      "spoken",
      "platform_product_tag"
    ],
    "product_tag_expectation": "required_for_tiktok_shop_objective",
    "cta_timing_guidance": "After proof, before the final two seconds when possible.",
    "cta_language_pattern": "Reference the product tag naturally; avoid unrelated urgency.",
    "cta_failure_modes": [
      "generic 'check it out' without product-tag cue",
      "CTA before the result is visible",
      "unsupported discount claim"
    ],
    "evidence_refs": ["pattern-ev-cta-a"],
    "confidence": 0.72,
    "uncertainties": [
      "CTA evidence comes from one of two source assets."
    ]
  },
  "applicability": {
    "suitable_categories": [
      "portable_garment_care",
      "lint_removal",
      "home_organization",
      "cleaning_tools",
      "visual_transformation_gadgets"
    ],
    "unsuitable_categories": [
      "products_without_observable_use",
      "services",
      "products_requiring_long_term_outcomes"
    ],
    "required_product_traits": [
      "visible problem",
      "safe in-use demonstration",
      "observable short-form result"
    ],
    "preferred_product_traits": [
      "compact form factor",
      "low setup time",
      "clear product handling"
    ],
    "buyer_contexts": [
      "time pressure",
      "small space",
      "travel",
      "practical convenience"
    ],
    "markets": ["US"],
    "platforms": ["tiktok_shop"],
    "objectives": [
      "organic_test",
      "affiliate_test",
      "small_paid_test"
    ],
    "fulfillment_constraints": [
      "Use only seller-authorized shipping language."
    ],
    "compliance_sensitivities": [
      "speed claims",
      "universal result claims",
      "safety claims"
    ],
    "pod_context": null,
    "dropshipping_context": {
      "visual_demo_required": true,
      "trust_mechanisms": [
        "same-item proof",
        "creator hands-on use"
      ],
      "shipping_promise_constraints": [
        "Do not imply immediate delivery."
      ],
      "quality_proof_requirements": [
        "Show actual product operation."
      ],
      "margin_or_offer_constraints": [
        "Use only verified price and seller-authorized discount."
      ],
      "claim_risks": [
        "instant result",
        "universal compatibility"
      ]
    }
  },
  "adaptation_instructions": [
    {
      "element_path": "narrative.progression",
      "instruction_type": "keep",
      "instruction": "Keep the problem → early reveal → in-use demo → observable result sequence.",
      "rationale": "This is the reusable structural mechanism supported by both source assets.",
      "severity": "high"
    },
    {
      "element_path": "opening.hook_text",
      "instruction_type": "change",
      "instruction": "Write a new product- and buyer-specific opening line.",
      "rationale": "Exact wording belongs to the source creative and is not the reusable mechanism.",
      "severity": "hard"
    },
    {
      "element_path": "proof.execution",
      "instruction_type": "keep",
      "instruction": "Preserve same-item continuity and visible comparison.",
      "rationale": "The pattern depends on observable proof rather than narration alone.",
      "severity": "hard"
    },
    {
      "element_path": "claims.speed",
      "instruction_type": "avoid",
      "instruction": "Avoid instant-result or universal-result language.",
      "rationale": "The source evidence does not support universal timing claims.",
      "severity": "hard"
    }
  ],
  "performance_summary": {
    "evidence_status": "none",
    "asset_count": 0,
    "campaign_count": 0,
    "metrics": [],
    "caveats": [
      "No seller performance data is linked.",
      "This PatternKit represents a reusable structural hypothesis, not a winning pattern."
    ],
    "confidence": "low"
  },
  "overall_confidence": "medium",
  "uncertainties": [
    "Offer strategy is weakly supported by the source cluster.",
    "Creator persona performance is not validated."
  ]
}
```

## 6.4 Required visual presentation

PatternKit UI should show:

```text
SOURCE EVIDENCE
2 reference assets · 11 evidence moments · no linked performance data

REUSABLE STRUCTURE
Problem → Reveal → Demo → Proof → CTA

KEEP
✓ situational problem
✓ product before 2.2s
✓ same-item proof

CHANGE
↻ buyer situation
↻ exact hook wording
↻ creator persona
↻ offer framing

AVOID
✕ competitor script
✕ instant-result claim
✕ unrelated shipping urgency

APPLICABILITY
Best fit: compact products with visible short-form transformation
Not suitable: products with no observable demo
```

---

# 7. Golden ViralKit output

## 7.1 ViralKit objective

```text
Product: SwiftPress Mini Garment Steamer
Platform: TikTok Shop US
Objective: Affiliate test
Primary buyer groups: college student, frequent traveler
Pattern source: Deadline Pressure → Fast Product Reveal → Same-Fabric Proof
```

## 7.2 Pattern match result

```json
{
  "pattern_kit_version_id": "pk-deadline-fast-reveal-proof-v1",
  "match_score": 0.88,
  "applicability_status": "applicable_with_constraints",
  "matched_product_traits": [
    "visible problem",
    "short-form in-use demo",
    "observable result",
    "compact product"
  ],
  "conflicts": [],
  "constraints": [
    "Avoid universal fabric compatibility.",
    "Include seller-required fabric disclosure.",
    "Use authorized 4–6 business day shipping language only if shipping is mentioned."
  ],
  "selection_reason": "The product supports the core same-item transformation mechanism and an early reveal without requiring long-term proof."
}
```

## 7.3 Adaptation plan

### Keep

- visible problem in the opening;
- product reveal before two seconds;
- same-shirt demo and result continuity;
- proof before CTA;
- low-pressure product-tag CTA.

### Change

- reference creator context → US college student/traveler context;
- reference script → new product-specific language;
- reference product → SwiftPress product assets and verified mechanism;
- offer → verified 15% launch discount;
- disclosure → “Results vary by fabric type.”

### Avoid

- copying the competitor sentence;
- “instantly removes every wrinkle”;
- fake countdown or stock scarcity;
- using a different shirt for the after shot;
- claiming sanitation benefits.

## 7.4 Exactly three strategically different concepts

### Concept A — Late for Class Rescue

```json
{
  "id": "late_for_class",
  "name": "Late for Class Rescue",
  "strategic_axis": "time_pressure_for_college_student",
  "diversity_axes": [
    "buyer_persona",
    "hook_mechanism",
    "creator_persona",
    "narrative_structure"
  ],
  "buyer_persona_id": "college_student",
  "buyer_persona_label": "College student in a dorm",
  "buyer_pain": "A wrinkled shirt immediately before class or an event",
  "desired_outcome": "Look presentable without setting up an ironing board",
  "awareness_stage": "problem_aware",
  "creative_angle": "A compact last-minute clothing rescue for dorm life",
  "hook": {
    "hook_type": "situational_problem",
    "spoken_text": "I had ten minutes before class and this shirt looked like it came straight out of my backpack.",
    "overlay_text": null,
    "opening_visual": "Macro close-up of the wrinkled shirt while a phone clock is visible in the background.",
    "target_time_ms": 0,
    "product_present": false,
    "buyer_pain": "last-minute wrinkled clothing"
  },
  "opening_visual": "Wrinkled shirt close-up, then product enters frame before 1.8 seconds.",
  "narrative_structure": "situational_problem_solution_proof",
  "creator_persona": "US college lifestyle creator",
  "delivery_style": "casual first-person demonstration",
  "demo_mechanism": "Steam the same shirt section while keeping the camera close enough to see the fabric.",
  "proof_mechanism": "Return to the same shirt section using similar framing and lighting.",
  "offer_framing": "Mention the verified 15% launch discount only after the result is shown.",
  "cta_strategy": "Natural TikTok Shop product-tag CTA after proof.",
  "claims_to_avoid": [
    "instant result",
    "safe for every fabric",
    "professional dry-cleaning result"
  ],
  "required_disclosures": [
    "Results vary by fabric type."
  ],
  "test_hypothesis": "A time-pressure student scenario will increase relevance and product clicks among college-age viewers without requiring high-pressure sales language.",
  "expected_learning": "Whether urgency from a real dorm situation creates stronger intent than travel or comparison positioning.",
  "feasibility": "high",
  "confidence": "medium"
}
```

### Concept B — Carry-On Clothing Rescue

```json
{
  "id": "carry_on_rescue",
  "name": "Carry-On Clothing Rescue",
  "strategic_axis": "travel_convenience",
  "diversity_axes": [
    "buyer_persona",
    "hook_mechanism",
    "creator_persona",
    "demo_mechanism",
    "narrative_structure"
  ],
  "buyer_persona_id": "frequent_traveler",
  "buyer_persona_label": "Frequent traveler using carry-on luggage",
  "buyer_pain": "Clothing becomes wrinkled inside packed luggage",
  "desired_outcome": "Refresh an outfit in a hotel room with a compact tool",
  "awareness_stage": "solution_aware",
  "creative_angle": "A carry-on-friendly clothing-care backup",
  "hook": {
    "hook_type": "reveal_from_context",
    "spoken_text": "This is why I stopped trusting hotel irons.",
    "overlay_text": "Carry-on clothing rescue",
    "opening_visual": "Open a suitcase and pull out a visibly wrinkled outfit.",
    "target_time_ms": 0,
    "product_present": false,
    "buyer_pain": "wrinkled travel outfit"
  },
  "opening_visual": "Suitcase reveal followed by the product placed beside travel items.",
  "narrative_structure": "travel_problem_tool_demo_result",
  "creator_persona": "US travel creator",
  "delivery_style": "practical travel tip",
  "demo_mechanism": "Use the steamer on one half of a packed shirt in a hotel-room setting.",
  "proof_mechanism": "Show treated and untreated halves in the same frame.",
  "offer_framing": "Optional; value and portability are primary.",
  "cta_strategy": "Product-tag CTA framed as a travel packing recommendation.",
  "claims_to_avoid": [
    "works on every fabric",
    "hotel-safe guarantee",
    "instant result"
  ],
  "required_disclosures": [
    "Results vary by fabric type."
  ],
  "test_hypothesis": "Travel context and side-by-side proof will create stronger saves and comments among frequent travelers than a general convenience demo.",
  "expected_learning": "Whether portability is a stronger purchase driver than time pressure.",
  "feasibility": "medium",
  "confidence": "medium"
}
```

### Concept C — Small-Space Iron Alternative

```json
{
  "id": "small_space_alternative",
  "name": "Small-Space Iron Alternative",
  "strategic_axis": "comparison_and_space_saving",
  "diversity_axes": [
    "hook_mechanism",
    "narrative_structure",
    "demo_mechanism",
    "proof_mechanism",
    "offer_framing"
  ],
  "buyer_persona_id": "small_space_renter",
  "buyer_persona_label": "Apartment renter with limited storage",
  "buyer_pain": "A full-size iron and board take up too much space",
  "desired_outcome": "Keep a compact clothing-care option in a drawer",
  "awareness_stage": "solution_aware",
  "creative_angle": "A compact alternative for quick touch-ups in small spaces",
  "hook": {
    "hook_type": "comparison",
    "spoken_text": "I do not have space for an ironing board, so this lives in my desk drawer.",
    "overlay_text": "No ironing board setup",
    "opening_visual": "Show a crowded closet, then open a drawer containing the compact steamer.",
    "target_time_ms": 0,
    "product_present": true,
    "buyer_pain": "limited storage"
  },
  "opening_visual": "Product is visible immediately inside the drawer.",
  "narrative_structure": "comparison_space_problem_demo_proof",
  "creator_persona": "small-apartment lifestyle creator",
  "delivery_style": "practical comparison review",
  "demo_mechanism": "Show setup time and steam a shirt while the ironing board remains folded away.",
  "proof_mechanism": "Close-up of the treated area plus visual comparison of storage footprint.",
  "offer_framing": "15% launch discount as a secondary value cue.",
  "cta_strategy": "Product-tag CTA after the compact-storage proof.",
  "claims_to_avoid": [
    "replaces professional ironing for every use",
    "instant result",
    "safe for every fabric"
  ],
  "required_disclosures": [
    "Results vary by fabric type."
  ],
  "test_hypothesis": "Immediate product visibility and space-saving comparison will improve product clicks among apartment renters even without a time-pressure story.",
  "expected_learning": "Whether product visibility and storage benefit outperform situational urgency.",
  "feasibility": "high",
  "confidence": "medium"
}
```

## 7.5 Concept comparison visual

```text
                         A: Late for Class   B: Carry-On Rescue   C: Small-Space Alternative
Buyer                    College student     Traveler             Apartment renter
Primary pain             Time pressure       Packed wrinkles      Storage/setup
Hook                     Situational problem Travel reveal        Comparison
Product first seen       <1.8s               <2.2s                0s
Creator                   Student             Travel creator       Home/lifestyle
Demo                      Same-shirt section  Half-shirt compare   Setup + in-use
Proof                     Same-area result    Treated vs untreated Result + footprint
Main metric hypothesis   Product clicks      Saves/comments       Product clicks
```

Acceptance requirements:

- The concepts differ across meaningful axes.
- Buyer persona and creator persona are not merged.
- The same PatternKit mechanism is adapted, not copied.
- Claims and disclosure requirements remain consistent.
- No concept claims predicted GMV or virality.

---

# 8. Golden ViralKit test matrix

```json
{
  "primary_hypothesis": "The same early-reveal and same-item proof pattern will perform differently depending on buyer situation and hook mechanism.",
  "controlled_variables": [
    "product",
    "selling_price",
    "15% launch discount",
    "video length target 18–24 seconds",
    "product-tag CTA",
    "required fabric disclosure"
  ],
  "intentionally_changed_variables": [
    "buyer persona",
    "hook mechanism",
    "creator persona",
    "demo framing",
    "proof framing"
  ],
  "recommended_test_order": [
    "late_for_class",
    "small_space_alternative",
    "carry_on_rescue"
  ],
  "concepts": [
    {
      "concept_id": "late_for_class",
      "hypothesis": "Time pressure creates the strongest immediate purchase intent.",
      "changed_axes": [
        "buyer_persona",
        "hook_mechanism",
        "creator_persona"
      ],
      "held_constant": [
        "product",
        "offer",
        "same-item proof requirement",
        "product tag"
      ],
      "minimum_execution_requirements": [
        "product before 2000ms",
        "same-shirt before and after",
        "required disclosure",
        "product-tag CTA"
      ],
      "metrics_to_observe": [
        "3-second hold rate",
        "product clicks",
        "orders",
        "comments mentioning time or dorm use"
      ]
    },
    {
      "concept_id": "carry_on_rescue",
      "hypothesis": "Travel context creates stronger saves and high-intent comments.",
      "changed_axes": [
        "buyer_persona",
        "hook_mechanism",
        "demo_mechanism"
      ],
      "held_constant": [
        "product",
        "offer",
        "same-item proof requirement",
        "product tag"
      ],
      "minimum_execution_requirements": [
        "suitcase context visible",
        "product before 2300ms",
        "treated vs untreated proof",
        "required disclosure"
      ],
      "metrics_to_observe": [
        "saves",
        "product clicks",
        "comments mentioning travel",
        "orders"
      ]
    },
    {
      "concept_id": "small_space_alternative",
      "hypothesis": "Immediate product visibility and comparison positioning create the strongest click intent.",
      "changed_axes": [
        "hook_mechanism",
        "narrative_structure",
        "proof_mechanism"
      ],
      "held_constant": [
        "product",
        "offer",
        "product tag",
        "required disclosure"
      ],
      "minimum_execution_requirements": [
        "product visible at opening",
        "storage comparison",
        "in-use result",
        "required disclosure"
      ],
      "metrics_to_observe": [
        "product clicks",
        "CTR when paid-tested",
        "orders",
        "comments mentioning storage"
      ]
    }
  ],
  "decision_criteria": [
    {
      "criterion": "Do not compare commercial outcomes unless each concept satisfies its minimum execution requirements.",
      "signal_type": "structural",
      "comparison": "Campaign Pack and Preflight compliance",
      "caveat": "A weak execution cannot fairly test the strategic concept."
    },
    {
      "criterion": "Use product clicks and orders as stronger commerce signals than views alone.",
      "signal_type": "commercial",
      "comparison": "Concept-level rate normalized by exposure and test window",
      "caveat": "Private beta reporting is directional and not a causal claim."
    }
  ]
}
```

---

# 9. Golden Creative Campaign Pack

The selected concept is `late_for_class`.

## 9.1 Human-readable creator view

```text
CREATIVE CAMPAIGN PACK
Product: SwiftPress Mini Garment Steamer
Concept: Late for Class Rescue
Objective: TikTok Shop affiliate test
Target duration: 18–24 seconds

WHO THIS IS FOR
US college students living in dorms or shared apartments who want a compact way to handle wrinkled clothing before class or an event.

CORE ANGLE
A last-minute dorm-room clothing rescue with clear same-shirt proof.

CREATOR STYLE
Casual student lifestyle creator.
Natural first-person delivery.
Do not sound like a commercial voice-over.

MANDATORY OPENING
Start on a visibly wrinkled shirt.
The product must be clearly visible by 00:02.000.

HOOK OPTIONS
1. Spoken: “I had ten minutes before class and this shirt looked like it came straight out of my backpack.”
   Opening visual: wrinkled shirt close-up with a phone clock in the background.
   Mandatory: yes

2. Spoken: “Dorm-room problem: no ironing board and a shirt I cannot wear like this.”
   Opening visual: show the small dorm space before revealing the product.
   Mandatory: no

3. Overlay: “Last-minute outfit rescue”
   Opening visual: shirt first, product enters frame quickly.
   Mandatory: no

Important: A spoken hook does not need to appear as an overlay unless the selected hook explicitly includes overlay text.

REQUIRED STORY
1. Show the wrinkled shirt problem.
2. Reveal the product before two seconds.
3. Steam one clearly visible section of the same shirt.
4. Return to that same section and show the result.
5. Mention or display: “Results vary by fabric type.”
6. End with a natural TikTok Shop product-tag CTA.

MUST SHOW
- Clear product close-up.
- Product operating on the shirt.
- Same-shirt before and after.
- TikTok Shop product tag.
- Required disclosure.

DO
- Keep the same shirt and similar lighting for proof.
- Speak naturally from personal experience.
- Keep the product visible during the main demo.
- Show the result before mentioning the discount.

DO NOT
- Say it removes every wrinkle instantly.
- Say it is safe for every fabric.
- Claim sanitation or bacteria removal.
- Use a different shirt in the result shot.
- Invent stock scarcity or faster shipping.

OFFER
Verified 15% launch discount.
Mention only after the result is visible.

CTA
Spoken direction: “I linked the one I use in the product tag.”
Product tag: required.
Target CTA window: 00:16.000–00:22.000.

RIGHTS REQUEST
Please confirm permission for TikTok organic use, Spark Ads testing, and editing of the submitted cut. Raw footage is preferred but not required for this test.

REVISION CHECKLIST
- Product appears by two seconds.
- Same-shirt proof is visible.
- Disclosure is present.
- Product tag is present.
- No prohibited claim is used.
```

## 9.2 Typed brief highlights

```json
{
  "objective": "tiktok_shop_affiliate_test",
  "audience": {
    "buyer_persona_id": "college_student",
    "persona_label": "US college student in a dorm or shared apartment",
    "pain_points": [
      "last-minute wrinkled clothing",
      "limited space for ironing equipment"
    ],
    "desired_outcomes": [
      "look presentable quickly",
      "use a compact clothing-care tool"
    ]
  },
  "creator_direction": {
    "persona": "US college lifestyle creator",
    "delivery_style": "casual first-person demonstration",
    "tone": ["natural", "specific", "practical"],
    "avoid_tones": ["overhyped", "commercial announcer", "guaranteed result"]
  },
  "cta": {
    "spoken": "I linked the one I use in the product tag.",
    "overlay": null,
    "cta_type": "product_tag",
    "product_tag_required": true,
    "required_before_ms": 22000
  },
  "claim_guardrails": {
    "allowed": [
      "Helps reduce visible wrinkles",
      "Compact for quick touch-ups"
    ],
    "allowed_with_qualification": [
      {
        "claim": "Quick wrinkle reduction",
        "qualification": "Show actual same-shirt proof and avoid instant wording."
      }
    ],
    "prohibited": [
      "Removes every wrinkle instantly",
      "Safe for every fabric",
      "Kills bacteria",
      "Professional dry-cleaning results"
    ],
    "required_disclosures": [
      "Results vary by fabric type."
    ]
  }
}
```

---

# 10. Golden compiled Preflight requirements

```json
[
  {
    "id": "product_visible_by_2s",
    "requirement_type": "product",
    "source_path": "storyboard[1].product_visibility_required",
    "description": "The target product must be clearly visible by 00:02.000.",
    "severity": "hard",
    "matcher_type": "product_visibility_timing",
    "matcher_config": {
      "before_ms": 2000
    },
    "expected_semantics": "timing"
  },
  {
    "id": "target_product_match",
    "requirement_type": "product",
    "source_path": "product_snapshot.identity",
    "description": "The UGC must show the SwiftPress Mini Garment Steamer, not a different steamer.",
    "severity": "hard",
    "matcher_type": "product_match",
    "matcher_config": {
      "minimum_confidence": 0.70
    },
    "expected_semantics": "type_match"
  },
  {
    "id": "same_shirt_demo",
    "requirement_type": "demo",
    "source_path": "storyboard[2]",
    "description": "The creator must steam the same shirt section shown in the problem opening.",
    "severity": "high",
    "matcher_type": "demo_mechanism_match",
    "matcher_config": {
      "text": "same-shirt section steamed in use"
    },
    "expected_semantics": "semantic_match"
  },
  {
    "id": "same_shirt_proof",
    "requirement_type": "proof",
    "source_path": "proof_direction[0]",
    "description": "The same shirt section must be shown after use with an observable visible result.",
    "severity": "high",
    "matcher_type": "proof_type_match",
    "matcher_config": {
      "proof_type": "same_item_before_after"
    },
    "expected_semantics": "type_match"
  },
  {
    "id": "fabric_disclosure",
    "requirement_type": "claim_governance",
    "source_path": "claim_guardrails.required_disclosures[0]",
    "description": "The disclosure 'Results vary by fabric type.' must appear in spoken or on-screen text.",
    "severity": "hard",
    "matcher_type": "required_disclosure_presence",
    "matcher_config": {
      "text": "Results vary by fabric type."
    },
    "expected_semantics": "presence"
  },
  {
    "id": "no_instant_claim",
    "requirement_type": "claim_governance",
    "source_path": "claim_guardrails.prohibited[0]",
    "description": "The UGC must not claim that every wrinkle is removed instantly.",
    "severity": "hard",
    "matcher_type": "prohibited_claim_absence",
    "matcher_config": {
      "text": "removes every wrinkle instantly"
    },
    "expected_semantics": "absence"
  },
  {
    "id": "product_tag_required",
    "requirement_type": "cta",
    "source_path": "cta.product_tag_required",
    "description": "A TikTok Shop product tag must be present.",
    "severity": "hard",
    "matcher_type": "product_tag_presence",
    "matcher_config": {},
    "expected_semantics": "presence"
  },
  {
    "id": "cta_by_22s",
    "requirement_type": "cta",
    "source_path": "cta.required_before_ms",
    "description": "The CTA must begin no later than 00:22.000.",
    "severity": "high",
    "matcher_type": "cta_timing",
    "matcher_config": {
      "before_ms": 22000
    },
    "expected_semantics": "timing"
  }
]
```

---

# 11. Golden UGC Preflight — first draft

## 11.1 Observed draft

```text
Duration: 22.7 seconds
Product first clearly appears: 4.2 seconds
Creator delivery: natural
Demo: product is used, but the original shirt area is not shown again
Proof: steam is visible; wrinkle result is unclear
CTA: product tag appears at 18.8 seconds
Disclosure: missing
Claims: no prohibited instant claim detected
```

## 11.2 Structural score

```json
{
  "overall_score": 74,
  "band": "revise",
  "dimensions": [
    {
      "name": "hook_clarity",
      "score": 82,
      "reason": "The creator states a specific last-minute clothing problem immediately.",
      "confidence": "high",
      "evidence_ids": ["draft-hook-01"]
    },
    {
      "name": "product_visibility",
      "score": 55,
      "reason": "The product is clearly shown, but its first appearance at 4.2 seconds is late for this brief.",
      "confidence": "high",
      "evidence_ids": ["draft-product-01"]
    },
    {
      "name": "demo_clarity",
      "score": 76,
      "reason": "The product is shown in use on the shirt, but continuity with the opening problem area is incomplete.",
      "confidence": "medium",
      "evidence_ids": ["draft-demo-01"]
    },
    {
      "name": "proof_strength",
      "score": 42,
      "reason": "Steam is visible, but the draft does not show an observable same-shirt result.",
      "confidence": "high",
      "evidence_ids": ["draft-proof-summary-01"]
    },
    {
      "name": "creator_authenticity",
      "score": 88,
      "reason": "The delivery is natural, specific, and consistent with the requested student persona.",
      "confidence": "medium",
      "evidence_ids": ["draft-creator-01"]
    },
    {
      "name": "offer_clarity",
      "score": 68,
      "reason": "The 15% discount is stated after the demonstration, but the result is not yet strong enough to support the offer sequence.",
      "confidence": "medium",
      "evidence_ids": ["draft-offer-01"]
    },
    {
      "name": "cta_readiness",
      "score": 92,
      "reason": "The product-tag CTA is present at 18.8 seconds and clearly tied to the product.",
      "confidence": "high",
      "evidence_ids": ["draft-cta-01"]
    },
    {
      "name": "tiktok_native_fit",
      "score": 84,
      "reason": "Vertical framing, creator-led delivery, and pacing fit the platform context.",
      "confidence": "medium",
      "evidence_ids": ["draft-platform-01"]
    },
    {
      "name": "claim_safety",
      "score": 72,
      "reason": "No prohibited instant-result claim was observed, but required disclosure coverage is missing.",
      "confidence": "medium",
      "evidence_ids": ["draft-text-coverage-01"]
    }
  ]
}
```

## 11.3 Exact alignment evaluations

```json
[
  {
    "requirement_id": "product_visible_by_2s",
    "status": "missing",
    "score": 0,
    "confidence": "high",
    "reason": "The first clear product appearance occurs after the required deadline.",
    "expected": {
      "before_ms": 2000
    },
    "observed": {
      "first_appearance_ms": 4200
    },
    "evidence_ids": ["draft-product-01"]
  },
  {
    "requirement_id": "target_product_match",
    "status": "satisfied",
    "score": 100,
    "confidence": "high",
    "reason": "The observed product matches the attached SwiftPress product assets.",
    "expected": {
      "minimum_confidence": 0.70
    },
    "observed": {
      "product_match_confidence": 0.93
    },
    "evidence_ids": ["draft-product-match-01"]
  },
  {
    "requirement_id": "same_shirt_demo",
    "status": "partial",
    "score": 65,
    "confidence": "medium",
    "reason": "The product is used on the shirt, but the system cannot verify that the exact opening section is preserved through the demo.",
    "expected": {
      "mechanism": "same-shirt section steamed in use"
    },
    "observed": {
      "product_in_use": true,
      "same_section_continuity": "uncertain"
    },
    "evidence_ids": ["draft-demo-01"]
  },
  {
    "requirement_id": "same_shirt_proof",
    "status": "missing",
    "score": 0,
    "confidence": "high",
    "reason": "No same-item before/after proof is observed after the demonstration.",
    "expected": {
      "proof_type": "same_item_before_after"
    },
    "observed": {
      "proof_types": ["steam_visibility_only"]
    },
    "evidence_ids": ["draft-proof-summary-01"]
  },
  {
    "requirement_id": "fabric_disclosure",
    "status": "missing",
    "score": 0,
    "confidence": "high",
    "reason": "The required disclosure was not found in transcript or OCR evidence.",
    "expected": {
      "text": "Results vary by fabric type."
    },
    "observed": {
      "eligible_text_sources": 9,
      "matched": false
    },
    "evidence_ids": []
  },
  {
    "requirement_id": "no_instant_claim",
    "status": "satisfied",
    "score": 100,
    "confidence": "medium",
    "reason": "The prohibited instant-result claim was not observed in available transcript and OCR evidence.",
    "expected": {
      "semantics": "absence",
      "text": "removes every wrinkle instantly"
    },
    "observed": {
      "available_text_sources": 9,
      "coverage": "medium"
    },
    "evidence_ids": []
  },
  {
    "requirement_id": "product_tag_required",
    "status": "satisfied",
    "score": 100,
    "confidence": "high",
    "reason": "A product tag is visible during the CTA window.",
    "expected": {
      "product_tag_required": true
    },
    "observed": {
      "product_tag_present": true,
      "start_ms": 18800
    },
    "evidence_ids": ["draft-cta-01"]
  },
  {
    "requirement_id": "cta_by_22s",
    "status": "satisfied",
    "score": 100,
    "confidence": "high",
    "reason": "The CTA begins before the 22-second deadline.",
    "expected": {
      "before_ms": 22000
    },
    "observed": {
      "cta_start_ms": 18800
    },
    "evidence_ids": ["draft-cta-01"]
  }
]
```

## 11.4 Final Preflight output

```json
{
  "structural_score": 74,
  "brief_alignment_score": 57,
  "final_score": 71,
  "action": "revise",
  "confidence": "high",
  "hard_blockers": [
    {
      "code": "PRODUCT_REVEAL_LATE",
      "message": "Product appears at 4.2 seconds; the Campaign Pack requires visibility by 2.0 seconds.",
      "evidence_ids": ["draft-product-01"]
    },
    {
      "code": "REQUIRED_DISCLOSURE_MISSING",
      "message": "The required fabric-result disclosure is missing.",
      "evidence_ids": []
    }
  ],
  "high_priority_fixes": [
    {
      "code": "SAME_ITEM_PROOF_MISSING",
      "instruction": "Return to the exact shirt section shown in the opening and hold the result long enough for comparison.",
      "evidence_ids": ["draft-proof-summary-01"]
    }
  ],
  "strengths": [
    "Natural student-creator delivery",
    "Clear product-tag CTA",
    "Platform-native pacing"
  ],
  "creator_revision_message": "The student setup and delivery feel natural, and the product-tag ending works well. Please move the product close-up into the first two seconds, return to the exact shirt section after steaming so the result is visible, and add the on-screen or spoken disclosure: ‘Results vary by fabric type.’ Keep the current tone and CTA.",
  "next_action": "Upload a revised version and rerun Preflight before paid use."
}
```

---

# 12. Golden revision comparison

## 12.1 Revised observations

```text
Draft 1 product reveal: 4.2s
Draft 2 product reveal: 1.4s

Draft 1 proof: steam only
Draft 2 proof: same-shirt result held for 2.6s

Draft 1 disclosure: missing
Draft 2 disclosure: OCR text from 15.2s to 18.0s

CTA: preserved in both versions
Creator style: preserved
```

## 12.2 Revision diff output

```json
{
  "from_asset_version_id": "ugc-draft-v1",
  "to_asset_version_id": "ugc-draft-v2",
  "resolved": [
    {
      "issue": "PRODUCT_REVEAL_LATE",
      "before": {
        "first_appearance_ms": 4200
      },
      "after": {
        "first_appearance_ms": 1400
      }
    },
    {
      "issue": "SAME_ITEM_PROOF_MISSING",
      "before": {
        "proof_type": "steam_visibility_only"
      },
      "after": {
        "proof_type": "same_item_before_after",
        "proof_duration_ms": 2600
      }
    },
    {
      "issue": "REQUIRED_DISCLOSURE_MISSING",
      "before": {
        "present": false
      },
      "after": {
        "present": true,
        "text": "Results vary by fabric type.",
        "start_ms": 15200,
        "end_ms": 18000
      }
    }
  ],
  "preserved_strengths": [
    "creator authenticity",
    "product-tag CTA",
    "platform-native pacing"
  ],
  "new_issues": [],
  "summary": "All mandatory revision blockers were resolved without removing the strongest creator and CTA signals."
}
```

## 12.3 Revised Preflight

```json
{
  "structural_score": 86,
  "brief_alignment_score": 93,
  "final_score": 87,
  "action": "small_paid_test",
  "confidence": "high",
  "hard_blockers": [],
  "strengths": [
    "Product appears at 1.4 seconds",
    "Same-shirt proof is observable",
    "Required disclosure is present",
    "Product-tag CTA is clear",
    "Creator delivery remains natural"
  ],
  "remaining_caveats": [
    "Structural readiness does not guarantee sales performance.",
    "Confirm Spark and editing rights before paid amplification."
  ],
  "next_action": "Approve for organic posting and a limited paid test after rights confirmation."
}
```

---

# 13. Golden recommendation output

```json
{
  "schema_version": "recommendation_v2",
  "action": "small_paid_test",
  "title": "Approve structure; confirm rights before Spark testing",
  "reason": "The revised video satisfies all hard Campaign Pack requirements and resolves the original product-timing, proof, and disclosure blockers.",
  "confidence": "high",
  "evidence": [
    {
      "statement": "Product appears at 1.4 seconds.",
      "evidence_ids": ["v2-product-first-01"]
    },
    {
      "statement": "Same-shirt before/after proof is visible.",
      "evidence_ids": ["v2-proof-01"]
    },
    {
      "statement": "Required disclosure is present.",
      "evidence_ids": ["v2-disclosure-01"]
    },
    {
      "statement": "Product-tag CTA begins before the deadline.",
      "evidence_ids": ["v2-cta-01"]
    }
  ],
  "blockers": [],
  "conditions": [
    "Confirm TikTok organic usage rights.",
    "Confirm Spark Ads authorization.",
    "Confirm editing permission for the approved cut."
  ],
  "next_steps": [
    "Publish organically or through the planned affiliate workflow.",
    "Run a limited paid test only after rights are complete.",
    "Attach views, product clicks, orders, GMV, and test dates to this asset after the test."
  ],
  "disclaimer": "This recommendation evaluates structural and brief readiness. It is not a guarantee of virality, GMV, ROAS, or sales."
}
```

---

# 14. Seller action and feedback capture

## 14.1 Seller action

```json
{
  "recommendation_id": "rec-steamer-v2",
  "action": "accepted",
  "reason": "The team agrees the required revisions are complete and will use the video for organic affiliate posting first.",
  "created_by": "seller-user-id",
  "created_at": "2026-08-12T09:00:00Z"
}
```

## 14.2 Field-level correction example

```json
{
  "subject_type": "creative_dna",
  "subject_id": "dna-ugc-v2",
  "field_path": "creator.persona",
  "feedback_type": "partial",
  "ai_value_json": {
    "value": "college_lifestyle_creator"
  },
  "user_value_json": {
    "value": "general_lifestyle_creator_with_student_setting"
  },
  "comment": "The setting is student-focused, but the creator's channel is not primarily college content.",
  "model_run_id": "model-run-v2",
  "created_by": "seller-user-id"
}
```

Learning rule:

- preserve the original inference;
- store the correction separately;
- use the corrected label in evaluation and future workspace-private learning only when appropriate.

---

# 15. Golden performance-learning response after testing

Assume the seller later imports directional performance data.

```text
Concept A — Late for Class
Views: 31,400
Product clicks: 1,180
Orders: 42
GMV: $1,259.58

Concept C — Small-Space Alternative
Views: 28,900
Product clicks: 1,460
Orders: 37
GMV: $1,109.63
```

Viraldy-grade response:

```json
{
  "analysis_status": "directional",
  "summary": "Late for Class generated more orders, while Small-Space Alternative generated more product clicks relative to views. The available sample is not sufficient to declare a universally winning pattern.",
  "observations": [
    {
      "finding": "Late for Class produced the higher observed order count and GMV in this test window.",
      "evidence": {
        "concept_id": "late_for_class",
        "orders": 42,
        "gmv": 1259.58
      },
      "confidence": "medium"
    },
    {
      "finding": "Small-Space Alternative produced the higher observed product-click rate.",
      "evidence": {
        "concept_id": "small_space_alternative",
        "product_clicks": 1460,
        "views": 28900
      },
      "confidence": "medium"
    }
  ],
  "diagnosis": [
    "Time-pressure positioning may be stronger for immediate order intent in this sample.",
    "Space-saving comparison may create strong curiosity and product exploration but needs offer or page validation before concluding it is weaker commercially."
  ],
  "recommended_actions": [
    {
      "action": "create_variant",
      "instruction": "Create a second Late for Class variant with a different student creator while preserving the same proof mechanism.",
      "reason": "Test whether the observed order signal is tied to the angle rather than one creator execution."
    },
    {
      "action": "fix_and_retest",
      "instruction": "Retest Small-Space Alternative with clearer price-value framing after the proof.",
      "reason": "The concept generated strong product-click behavior but fewer observed orders."
    }
  ],
  "pattern_update": {
    "pattern_kit_version_id": "pk-deadline-fast-reveal-proof-v1",
    "performance_evidence_status": "directional",
    "do_not_promote_to_supported": true,
    "reason": "The sample contains too few independent campaign executions."
  },
  "caveats": [
    "The test is observational and may be affected by creator, posting time, distribution, product page, and audience differences.",
    "Do not interpret the result as causal proof."
  ]
}
```

---

---

# 16. Golden scenario B — POD personalization, full authoritative flow

## 16.1 Fixture facts

All values below are explicit fixture facts. Runtime outputs must never reuse them for another product.

```text
Product: Personalized Dog Mom Crewneck
Market: United States
Channel: TikTok Shop affiliate / organic test
Selling price: USD 42.00
Authorized offer: 10% off during the current fixture campaign only
Buyer segments:
- dog owner buying for herself
- partner/friend buying a personalized gift
Personalization fields:
- pet_name: Milo
- breed_style: Golden Retriever
- garment_color: Sand
- garment_size: M
Production estimate: 2–5 business days
Shipping estimate after production: 4–8 business days
Actual physical sample: available and approved
Commercial relationship: gifted product + affiliate commission
```

## 16.2 ProductContextV1 quality target

```json
{
  "schema_version": "product_context_v1",
  "identity": {
    "name": "Personalized Dog Mom Crewneck",
    "brand": "Pawline Studio",
    "category": "personalized_apparel",
    "subcategory": "crewneck_sweatshirt",
    "variant": "Sand / M / Golden Retriever / Milo",
    "market": "US",
    "currency": "USD"
  },
  "personas": [
    {
      "id": "self_purchase_dog_mom",
      "label": "Dog owner buying an identity product for herself",
      "pain_points": [
        "generic dog apparel does not feel personal",
        "online mockups make print quality hard to judge"
      ],
      "desired_outcomes": [
        "wear something recognizably connected to her pet",
        "see exactly how the finished personalization looks"
      ],
      "objections": [
        "the pet name may be misspelled",
        "the breed illustration may not match",
        "the garment may not fit or arrive in time"
      ],
      "awareness_stage": "product_aware"
    },
    {
      "id": "gift_buyer",
      "label": "Friend or partner buying a personalized gift",
      "pain_points": [
        "generic gifts feel impersonal",
        "ordering customization feels error-prone"
      ],
      "desired_outcomes": [
        "create a recognizable emotional reaction",
        "submit personalization correctly"
      ],
      "objections": [
        "delivery timing is uncertain",
        "the finished item may differ from the preview"
      ],
      "awareness_stage": "solution_aware"
    }
  ],
  "benefits": [
    {
      "id": "identity_expression",
      "label": "Pet identity expression",
      "description": "The approved product displays the buyer's pet name and selected breed illustration.",
      "proof_available": ["approved physical sample", "readable finished embroidery/print close-up"],
      "claim_strength": "supported"
    }
  ],
  "features": [
    {
      "id": "personalized_name",
      "label": "Pet name personalization",
      "description": "Fixture value: Milo",
      "visual_demo_possible": true,
      "visual_cues": ["readable name close-up"]
    },
    {
      "id": "breed_illustration",
      "label": "Approved breed illustration",
      "description": "Fixture value: Golden Retriever",
      "visual_demo_possible": true,
      "visual_cues": ["breed artwork close-up"]
    }
  ],
  "commercial": {
    "price": 42.0,
    "compare_at_price": null,
    "discount_text": "10% off during the current fixture campaign",
    "bundle_text": null,
    "shipping_text": "2–5 business days production plus 4–8 business days shipping",
    "commission_percent": null,
    "margin_band": "unknown",
    "offer_notes": ["Do not promise an arrival date without seller confirmation."]
  },
  "creative": {
    "primary_angles": ["dog mom identity", "personalized gift reaction", "ordering clarity"],
    "demonstration_mechanisms": ["show finished sample", "reveal exact name and breed", "show ordering inputs"],
    "visual_differentiators": ["actual finished crewneck", "readable Milo personalization", "approved Golden Retriever illustration"],
    "available_proof": ["approved physical sample", "input-to-finished-item comparison"],
    "creator_personas": ["dog-owner lifestyle creator", "gift creator", "practical tutorial creator"],
    "preferred_delivery_styles": ["authentic review", "gift reaction", "ordering walkthrough"],
    "brand_voice": ["warm", "specific", "not over-scripted"],
    "prohibited_visuals": ["blank garment as final proof", "placeholder text", "customer address or order ID"]
  },
  "governance": {
    "claims": [
      {
        "id": "allowed_personalization",
        "text": "Personalized with the approved pet name and breed illustration.",
        "rule_type": "allowed",
        "qualification": null,
        "severity": "low"
      },
      {
        "id": "prohibited_delivery_guarantee",
        "text": "Guaranteed to arrive before a specific holiday or date.",
        "rule_type": "prohibited",
        "qualification": null,
        "severity": "high"
      },
      {
        "id": "required_material_connection",
        "text": "Gifted product / affiliate relationship disclosure.",
        "rule_type": "required_disclosure",
        "qualification": null,
        "severity": "high"
      }
    ],
    "required_disclosures": ["Gifted product and affiliate relationship"],
    "prohibited_content": ["unauthorized trademark or celebrity image", "private customer data"],
    "rights_notes": ["Seller confirms rights to the original design and approved product assets."]
  }
}
```

## 16.3 Reference Creative DNA

Reference: a personalized necklace gift-reaction video. The target product is a crewneck, so Viraldy may reuse the identity/reveal/reaction structure but not the necklace execution.

```json
{
  "opening": {
    "primary_hook_type": {
      "value": "reaction_first",
      "status": "observed",
      "confidence": 0.91,
      "evidence_ids": ["pod_ev_hook_01"]
    },
    "opening_visual": {
      "value": "recipient sees a wrapped personalized gift",
      "status": "observed",
      "confidence": 0.9,
      "evidence_ids": ["pod_ev_opening_01"]
    },
    "buyer_pain": {
      "value": "generic gifts feel impersonal",
      "status": "inferred",
      "confidence": 0.68,
      "evidence_ids": ["pod_ev_hook_01", "pod_ev_reaction_01"]
    }
  },
  "product": {
    "first_appearance_ms": {
      "value": 3200,
      "status": "observed",
      "confidence": 0.96,
      "evidence_ids": ["pod_ev_product_01"]
    },
    "usage_present": {
      "value": true,
      "status": "observed",
      "confidence": 0.87,
      "evidence_ids": ["pod_ev_wear_01"]
    }
  },
  "narrative": {
    "structure": {
      "value": "gift_setup -> personalization_reveal -> reaction -> ordering_context -> CTA",
      "status": "observed",
      "confidence": 0.88,
      "evidence_ids": ["pod_ev_hook_01", "pod_ev_product_01", "pod_ev_reaction_01"]
    },
    "angle": {
      "value": "recognition through personalization",
      "status": "inferred",
      "confidence": 0.77,
      "evidence_ids": ["pod_ev_personalization_01", "pod_ev_reaction_01"]
    }
  },
  "proof": {
    "proof_types": {
      "value": ["finished_item_closeup", "recipient_verification"],
      "status": "observed",
      "confidence": 0.9,
      "evidence_ids": ["pod_ev_personalization_01", "pod_ev_reaction_01"]
    }
  },
  "creator": {
    "delivery_style": {
      "value": "gift_reaction_story",
      "status": "observed",
      "confidence": 0.89,
      "evidence_ids": ["pod_ev_creator_01"]
    }
  },
  "risks": [
    {
      "code": "REFERENCE_PRODUCT_EXECUTION_MUST_CHANGE",
      "severity": "medium",
      "message": "The source uses jewelry; target execution must be redesigned for apparel.",
      "evidence_ids": ["pod_ev_product_01"],
      "remediation_hint": "Keep the personalization reveal and reaction structure, not the source product or exact shots."
    }
  ]
}
```

## 16.4 PatternKitV1

### Pattern name

`Identity Recognition → Finished Personalization Reveal → Emotional Payoff → Ordering Clarity`

### Observed source pattern

```json
{
  "schema_version": "pattern_kit_v1",
  "name": "Identity Recognition to Personalization Payoff",
  "summary": "A reaction-led personalization structure that builds emotional relevance, verifies the finished customized detail, and reduces ordering uncertainty.",
  "kind": "single_asset_abstraction",
  "scope": "workspace_private",
  "status": "candidate",
  "source": {
    "source_asset_count": 1,
    "source_category_count": 1,
    "extraction_mode": "ai_assisted"
  },
  "sequence": [
    {
      "beat_id": "identity_or_recipient_setup",
      "order": 1,
      "beat_type": "hook",
      "purpose": "Make the recipient or identity context immediately recognizable.",
      "recommended_start_ms_min": 0,
      "recommended_start_ms_max": 1800,
      "requiredness": "required",
      "evidence_refs": ["pod_ev_hook_01"],
      "confidence": 0.91
    },
    {
      "beat_id": "finished_personalization_reveal",
      "order": 2,
      "beat_type": "product_reveal",
      "purpose": "Show the finished personalized detail clearly enough to verify it.",
      "recommended_start_ms_min": 2500,
      "recommended_start_ms_max": 5000,
      "requiredness": "required",
      "evidence_refs": ["pod_ev_personalization_01"],
      "confidence": 0.92
    },
    {
      "beat_id": "emotional_payoff",
      "order": 3,
      "beat_type": "reaction",
      "purpose": "Show why the specific personalization matters to the recipient or buyer.",
      "requiredness": "recommended",
      "evidence_refs": ["pod_ev_reaction_01"],
      "confidence": 0.87
    },
    {
      "beat_id": "ordering_clarity",
      "order": 4,
      "beat_type": "demo",
      "purpose": "Explain the minimum inputs needed to order correctly.",
      "requiredness": "recommended",
      "evidence_refs": ["pod_ev_ordering_01"],
      "confidence": 0.74
    },
    {
      "beat_id": "cta",
      "order": 5,
      "beat_type": "cta",
      "purpose": "Direct the viewer to the product tag without inventing delivery urgency.",
      "requiredness": "recommended",
      "evidence_refs": ["pod_ev_cta_01"],
      "confidence": 0.81
    }
  ],
  "applicability": {
    "suitable_categories": ["personalized_apparel", "personalized_gifts", "custom_home_decor"],
    "unsuitable_categories": ["non_personalized_commodity", "products_without_finished_sample"],
    "required_product_traits": ["visible personalization", "approved finished item", "clear ordering inputs"],
    "preferred_product_traits": ["identity or occasion relevance", "giftable format"],
    "buyer_contexts": ["self identity", "gift buyer", "recipient reaction"],
    "markets": ["US"],
    "platforms": ["tiktok_shop"],
    "objectives": ["pod_gift_campaign", "tiktok_shop_affiliate_test"],
    "fulfillment_constraints": ["Do not promise a delivery date without seller-authorized production and shipping data."],
    "compliance_sensitivities": ["material connection disclosure", "privacy", "IP rights"],
    "pod_context": {
      "recipient_types": ["self purchaser", "friend", "partner", "family recipient"],
      "occasions": ["birthday", "holiday", "Mother's Day", "everyday identity"],
      "personalization_requirements": ["exact spelling", "approved artwork", "finished-item proof"],
      "identity_cues": ["pet name", "breed", "relationship"],
      "emotional_payoff_patterns": ["recognition", "surprise", "belonging"],
      "mockup_accuracy_risks": ["placeholder text", "wrong garment color", "different print placement"]
    },
    "dropshipping_context": null
  },
  "adaptation_instructions": [
    {
      "element_path": "narrative.structure",
      "instruction_type": "keep",
      "instruction": "Keep the identity/reveal/payoff progression.",
      "rationale": "The reusable value is the recognition structure, not the source product.",
      "severity": "medium",
      "evidence_refs": ["pod_ev_hook_01", "pod_ev_reaction_01"]
    },
    {
      "element_path": "product.execution",
      "instruction_type": "change",
      "instruction": "Replace jewelry execution with an actual finished crewneck close-up and fit/wear context.",
      "rationale": "The target product is apparel and requires product-specific proof.",
      "severity": "hard",
      "evidence_refs": ["pod_ev_product_01"]
    },
    {
      "element_path": "creative.wording",
      "instruction_type": "avoid",
      "instruction": "Do not reuse the source recipient, name, exact reaction line, or exact scene staging.",
      "rationale": "Avoid surface copying and private-data reuse.",
      "severity": "hard",
      "evidence_refs": ["pod_ev_reaction_01"]
    }
  ],
  "performance_summary": {
    "evidence_status": "none",
    "asset_count": 0,
    "campaign_count": 0,
    "date_range_start": null,
    "date_range_end": null,
    "metrics": [],
    "caveats": ["No seller performance is linked; this is a structural hypothesis."],
    "confidence": "low"
  },
  "overall_confidence": "medium",
  "uncertainties": ["Reaction-led structure may require a later product reveal than a direct product demo."]
}
```

## 16.5 ViralKitV1 — exactly three concepts

### Concept A — Dog Mom Uniform

- **Buyer:** self-purchase dog owner.
- **Creator:** dog-owner lifestyle creator.
- **Hook tactic:** identity callout.
- **Psychological trigger:** belonging/recognition.
- **Narrative:** identity statement → actual crewneck reveal → close-up personalization → wear context → product tag.
- **Demo/proof:** actual finished garment; readable `Milo`; approved Golden Retriever art; fit shot.
- **Expected learning:** Does self-identity framing produce more product clicks than gift framing?

### Concept B — The Gift She Recognized Immediately

- **Buyer:** partner/friend gift buyer.
- **Creator:** gifting/lifestyle creator filming a consented recipient reaction.
- **Hook tactic:** reaction-first story.
- **Psychological trigger:** emotional payoff/social witness.
- **Narrative:** gift setup → partial reaction → finished personalization reveal → recipient verification → ordering clarity → CTA.
- **Demo/proof:** recipient reads `Milo`; physical sample visible; no private order details.
- **Expected learning:** Does recipient recognition increase shares and qualified comments?

### Concept C — How to Order Yours Correctly

- **Buyer:** product-aware shopper worried about personalization errors.
- **Creator:** practical tutorial creator.
- **Hook tactic:** objection handling / FAQ.
- **Psychological trigger:** risk reduction and clarity.
- **Narrative:** show required fields → approved preview → finished item → fit/quality close-up → CTA.
- **Demo/proof:** input values match finished item exactly.
- **Expected learning:** Does ordering clarity increase product-tag clicks and reduce personalization questions?

### ViralKit test matrix

```json
{
  "primary_hypothesis": "Different buyer intents require different creative mechanics even when product and offer remain fixed.",
  "controlled_variables": [
    "product variant: Sand / M / Milo / Golden Retriever",
    "selling price: USD 42",
    "authorized 10% offer",
    "actual finished physical sample",
    "product tag",
    "commercial disclosure",
    "production and shipping wording"
  ],
  "intentionally_changed_variables": [
    "buyer persona",
    "hook tactic",
    "creator persona",
    "narrative structure",
    "proof framing"
  ],
  "recommended_test_order": [
    "concept_c_ordering_clarity",
    "concept_a_identity",
    "concept_b_gift_reaction"
  ],
  "decision_criteria": [
    {
      "criterion": "All personalization and disclosure blockers are resolved before publication.",
      "signal_type": "structural",
      "comparison": "required",
      "caveat": "Structural readiness does not prove sales performance."
    },
    {
      "criterion": "Compare product-tag click rate and qualified personalization questions by concept.",
      "signal_type": "behavioral",
      "comparison": "directional cohort comparison",
      "caveat": "Creator and distribution differences remain confounders."
    },
    {
      "criterion": "Do not recommend paid scaling until gross-profit and rights data are complete.",
      "signal_type": "commercial",
      "comparison": "precondition",
      "caveat": "Viraldy must not invent a budget or threshold."
    }
  ]
}
```

## 16.6 Selected Creative Campaign Pack — Concept B

### Creator-facing brief

```text
CONCEPT
The Gift She Recognized Immediately

PRODUCT
Personalized Dog Mom Crewneck — Sand / M
Approved personalization: Milo + Golden Retriever illustration

CREATOR DIRECTION
Use your natural gift-reaction style. Do not read a word-for-word script.
The recipient must consent to being filmed.

MANDATORY PRODUCT TRUTH
- Film the actual finished crewneck, not only a mockup.
- The close-up must clearly read “Milo”.
- The approved breed illustration must be visible.
- Do not show an address, order number, or private customer message.

OPENING
Open with the gift setup and a natural reaction cue.
The package or crewneck may appear immediately; the exact personalization reveal may occur after the reaction setup.

REQUIRED BEATS
1. Gift/recipient context within the first 2 seconds.
2. Finished crewneck visible before 4 seconds.
3. Readable Milo + Golden Retriever close-up held for at least 1.5 seconds.
4. Recipient verifies the personalization naturally.
5. One concise explanation of what buyers submit.
6. Product-tag CTA.

DISCLOSURE
Clearly disclose gifted product and affiliate relationship.

DO NOT SAY
- Guaranteed to arrive before a holiday/date.
- Handmade, hand-painted, or embroidered unless Product Context confirms it.
- Perfect for every dog mom.

DELIVERY WORDING
Use only: “Check the current production and delivery estimate on the product page.”
```

## 16.7 Compiled Preflight requirements

```json
[
  {
    "id": "pod_actual_finished_item",
    "matcher_type": "product_match",
    "severity": "hard",
    "expected": {"physical_finished_item": true},
    "description": "Show the approved finished personalized crewneck, not only a mockup."
  },
  {
    "id": "pod_name_exact",
    "matcher_type": "overlay_or_visual_text_exact",
    "severity": "hard",
    "expected": {"text": "Milo", "case_sensitive": false},
    "description": "Visible personalization must match the approved pet name."
  },
  {
    "id": "pod_breed_art_match",
    "matcher_type": "product_variant_match",
    "severity": "hard",
    "expected": {"breed_style": "Golden Retriever"},
    "description": "Breed illustration must match the approved variant."
  },
  {
    "id": "pod_personalization_readable",
    "matcher_type": "overlay_text_presence",
    "severity": "high",
    "expected": {"minimum_visible_ms": 1500, "not_occluded": true},
    "description": "Hold the personalization close-up long enough to verify."
  },
  {
    "id": "pod_material_connection",
    "matcher_type": "required_disclosure_presence",
    "severity": "hard",
    "expected": {"meaning": "gifted product and affiliate relationship", "readable": true},
    "description": "Commercial relationship must be clearly disclosed."
  },
  {
    "id": "pod_no_delivery_guarantee",
    "matcher_type": "prohibited_claim_absence",
    "severity": "hard",
    "expected": {"prohibited_meaning": "guaranteed arrival date"},
    "description": "Do not promise an unverified arrival date."
  },
  {
    "id": "pod_privacy",
    "matcher_type": "prohibited_text_or_visual_absence",
    "severity": "hard",
    "expected": {"private_data": false},
    "description": "Do not reveal address, order ID, or private customer data."
  },
  {
    "id": "pod_product_tag",
    "matcher_type": "product_tag_presence",
    "severity": "high",
    "expected": {"present": true},
    "description": "Use a TikTok Shop product-tag CTA."
  }
]
```

## 16.8 First-draft Preflight

### Observed draft

```text
00:00.000–00:02.800  Recipient opens package; natural reaction is strong.
00:02.900–00:05.300  Crewneck shown; physical item is real.
00:05.400–00:07.100  Close-up reads “Miles,” not “Milo.”
00:07.200–00:08.000  Breed illustration is partially covered by a hand.
00:09.500–00:11.000  Creator says: “It arrived in three days, so yours will too.”
00:12.000–00:13.000  Affiliate disclosure appears in small low-contrast text for ~1 second.
00:15.000–00:17.000  Product tag CTA is present.
```

### Expected versus observed

```json
{
  "final_action": "reject_or_reshoot",
  "hard_blockers": [
    {
      "code": "POD_WRONG_PERSONALIZATION",
      "requirement_id": "pod_name_exact",
      "expected": {"pet_name": "Milo"},
      "observed": {"ocr_text": "Miles", "start_ms": 5400, "end_ms": 7100},
      "evidence_ids": ["pod_draft_ocr_name_01"],
      "seller_message": "The finished product shows the wrong pet name. Do not publish or ask the creator to hide it with editing.",
      "creator_fix": "Please reshoot with the approved Milo sample."
    },
    {
      "code": "SHIPPING_UNAUTHORIZED",
      "requirement_id": "pod_no_delivery_guarantee",
      "expected": {"no_guaranteed_arrival_claim": true},
      "observed": {"spoken_text": "It arrived in three days, so yours will too."},
      "evidence_ids": ["pod_draft_asr_shipping_01"],
      "seller_message": "A personal delivery experience cannot be turned into a guarantee for every buyer.",
      "creator_fix": "Replace with: Check the current production and delivery estimate on the product page."
    },
    {
      "code": "DISCLOSURE_NOT_READABLE",
      "requirement_id": "pod_material_connection",
      "expected": {"clear_and_conspicuous": true},
      "observed": {"visible_ms": 1000, "contrast": "low"},
      "evidence_ids": ["pod_draft_ocr_disclosure_01"],
      "seller_message": "The disclosure exists but is not readable enough to satisfy the brief.",
      "creator_fix": "Use a clear spoken or on-screen gifted/affiliate disclosure with readable size and duration."
    }
  ],
  "strengths_to_preserve": [
    "Natural recipient reaction",
    "Actual physical product shown",
    "Product-tag CTA"
  ],
  "high_priority_fixes": [
    {
      "code": "POD_TEXT_UNREADABLE",
      "expected": "Golden Retriever illustration fully visible",
      "observed": "Illustration partly covered by hand",
      "evidence_ids": ["pod_draft_visual_breed_01"]
    }
  ],
  "confidence": "high",
  "disclaimer": "This is a product-truth and brief-alignment decision, not a performance prediction."
}
```

## 16.9 Creator-friendly revision request

```text
The recipient reaction feels genuine, and the product-tag ending works well.

We need a reshoot because the visible name on the current sample reads “Miles,” while the approved personalization is “Milo.” Please use the correct finished sample, hold a clear close-up of “Milo” and the Golden Retriever illustration for at least 1.5 seconds, and keep your hand away from the artwork.

Please also remove the line that promises three-day delivery. Use: “Check the current production and delivery estimate on the product page.” Add a clear gifted/affiliate disclosure that is easy to read or hear.

Please keep the natural reaction and CTA. These are already strong.
```

## 16.10 Revised draft and seller action

```text
Revised result:
- Correct Milo sample: satisfied
- Golden Retriever art visible: satisfied
- Disclosure readable/spoken: satisfied
- Delivery guarantee removed: satisfied
- Product tag: satisfied

Action: approve_organic_hold_paid
Reason: Creative and product truth are ready; paid use still requires rights and gross-profit/test-budget confirmation.
```

---

# 17. Golden scenario C — Dropshipping visual-demo product, full authoritative flow

## 17.1 Fixture facts

```text
Product: Rechargeable Mini Bag Sealer
Market: United States
Channel: TikTok Shop organic/affiliate test
Selling price: USD 18.99
Authorized offer: none
Verified supported materials in fixture: selected PP/PE snack bags listed by seller
Unsupported/unknown: foil-lined bags, thick freezer bags, every plastic material
Verified function: applies heat to reseal supported opened snack bags
Seller-authorized shipping wording: 7–10 business days
Supplier sample: received and inspected
Commercial relationship: gifted product + affiliate commission
```

## 17.2 ProductContextV1 quality target

```json
{
  "schema_version": "product_context_v1",
  "identity": {
    "name": "Rechargeable Mini Bag Sealer",
    "brand": "SealMate",
    "category": "kitchen_gadget",
    "subcategory": "portable_bag_sealer",
    "variant": "rechargeable_standard",
    "market": "US",
    "currency": "USD"
  },
  "personas": [
    {
      "id": "dorm_snacker",
      "label": "College student carrying opened snack bags",
      "pain_points": ["clips open in backpacks", "opened snacks spill"],
      "desired_outcomes": ["compact resealing method", "less mess while carrying snacks"],
      "objections": ["uncertain compatibility", "product may look gimmicky"],
      "awareness_stage": "problem_aware"
    },
    {
      "id": "family_pantry",
      "label": "Parent organizing opened pantry snacks",
      "pain_points": ["many clips and rolled bags", "hard to keep opened bags organized"],
      "desired_outcomes": ["simple pantry routine", "visible seal line"],
      "objections": ["works only on some bags", "quality may be inconsistent"],
      "awareness_stage": "solution_aware"
    }
  ],
  "benefits": [
    {
      "id": "supported_bag_reseal",
      "label": "Reseal supported snack bags",
      "description": "The verified fixture sample creates a visible heat seal on selected seller-approved PP/PE snack bags.",
      "proof_available": ["approved sample demo", "close-up seal line"],
      "claim_strength": "supported"
    }
  ],
  "features": [
    {
      "id": "rechargeable",
      "label": "Rechargeable design",
      "description": "Verified fixture feature",
      "visual_demo_possible": true,
      "visual_cues": ["charging port", "device power state"]
    },
    {
      "id": "compact_form",
      "label": "Compact handheld form",
      "description": "Fits in a drawer or travel bag in the fixture scenario",
      "visual_demo_possible": true,
      "visual_cues": ["hand scale", "storage context"]
    }
  ],
  "commercial": {
    "price": 18.99,
    "compare_at_price": null,
    "discount_text": null,
    "bundle_text": null,
    "shipping_text": "7–10 business days",
    "commission_percent": null,
    "margin_band": "unknown",
    "offer_notes": ["Paid-test economics cannot be evaluated until gross profit and budget are supplied."]
  },
  "creative": {
    "primary_angles": ["dorm snack spill prevention", "pantry routine", "travel packing"],
    "demonstration_mechanisms": ["supported bag reseal", "close-up seal line", "storage/portability"],
    "visual_differentiators": ["one-handed use", "compact size", "visible seal line"],
    "available_proof": ["seller-approved sample demo"],
    "creator_personas": ["college lifestyle creator", "family organization creator", "travel creator"],
    "preferred_delivery_styles": ["hands-on demo", "real-life scenario", "FAQ"],
    "brand_voice": ["practical", "specific", "not miraculous"],
    "prohibited_visuals": ["unsupported bag material presented as compatible", "unsafe or deceptive leak test"]
  },
  "governance": {
    "claims": [
      {
        "id": "allowed_reseal",
        "text": "I use it to reseal supported snack bags after opening.",
        "rule_type": "allowed",
        "qualification": null,
        "severity": "low"
      },
      {
        "id": "prohibited_airtight",
        "text": "Makes every bag completely airtight.",
        "rule_type": "prohibited",
        "qualification": null,
        "severity": "critical"
      },
      {
        "id": "prohibited_fresh_forever",
        "text": "Keeps food fresh forever or guarantees food safety.",
        "rule_type": "prohibited",
        "qualification": null,
        "severity": "critical"
      },
      {
        "id": "prohibited_universal_compatibility",
        "text": "Works on every bag or every plastic material.",
        "rule_type": "prohibited",
        "qualification": null,
        "severity": "high"
      },
      {
        "id": "required_material_connection",
        "text": "Gifted product / affiliate relationship disclosure.",
        "rule_type": "required_disclosure",
        "qualification": null,
        "severity": "high"
      }
    ],
    "required_disclosures": ["Gifted product and affiliate relationship"],
    "prohibited_content": ["unsupported safety certification", "false shipping promise"],
    "rights_notes": ["Creator content requires authorized usage before paid amplification."]
  }
}
```

## 17.3 Reference Creative DNA

Reference: a hands-only mini tool demo showing a visible problem, product use, and close-up result.

```json
{
  "opening": {
    "primary_hook_type": {
      "value": "mess_interruption",
      "status": "observed",
      "confidence": 0.93,
      "evidence_ids": ["drop_ev_hook_01"]
    },
    "opening_visual": {
      "value": "opened snack bag spills inside a backpack",
      "status": "observed",
      "confidence": 0.94,
      "evidence_ids": ["drop_ev_problem_01"]
    }
  },
  "product": {
    "first_appearance_ms": {
      "value": 1100,
      "status": "observed",
      "confidence": 0.98,
      "evidence_ids": ["drop_ev_product_01"]
    },
    "usage_present": {
      "value": true,
      "status": "observed",
      "confidence": 0.95,
      "evidence_ids": ["drop_ev_demo_01"]
    }
  },
  "demo": {
    "detected": {
      "value": true,
      "status": "observed",
      "confidence": 0.97,
      "evidence_ids": ["drop_ev_demo_01"]
    },
    "demo_type": {
      "value": "one_handed_usage",
      "status": "observed",
      "confidence": 0.92,
      "evidence_ids": ["drop_ev_demo_01"]
    },
    "result_clarity": {
      "value": "clear_seal_line",
      "status": "observed",
      "confidence": 0.89,
      "evidence_ids": ["drop_ev_proof_01"]
    }
  },
  "proof": {
    "proof_types": {
      "value": ["visible_seal_line", "bag_remains_closed_during_normal_handling"],
      "status": "observed",
      "confidence": 0.84,
      "evidence_ids": ["drop_ev_proof_01", "drop_ev_handling_01"]
    },
    "verifiability": {
      "value": "observable_with_conditions",
      "status": "observed",
      "confidence": 0.82,
      "evidence_ids": ["drop_ev_material_01", "drop_ev_proof_01"]
    }
  },
  "risks": [
    {
      "code": "COMPATIBILITY_CONDITIONS_MUST_BE_PRESERVED",
      "severity": "high",
      "message": "The source demonstrates one bag material and does not support universal compatibility.",
      "evidence_ids": ["drop_ev_material_01"],
      "remediation_hint": "ViralKit must use only seller-approved supported bags."
    }
  ]
}
```

## 17.4 PatternKitV1

### Pattern name

`Visible Mess → Early Tool Reveal → One-Handed Mechanism → Close-Up Proof → Context CTA`

```json
{
  "schema_version": "pattern_kit_v1",
  "name": "Visible Mess to Verifiable Tool Proof",
  "summary": "A compact demo pattern that makes a practical problem visible, shows the tool early, demonstrates one representative use, and closes with condition-aware proof.",
  "kind": "single_asset_abstraction",
  "scope": "workspace_private",
  "status": "candidate",
  "sequence": [
    {
      "beat_id": "visible_problem",
      "order": 1,
      "beat_type": "problem",
      "purpose": "Show a recognizable mess or failure state.",
      "recommended_start_ms_min": 0,
      "recommended_start_ms_max": 1000,
      "requiredness": "required",
      "evidence_refs": ["drop_ev_problem_01"],
      "confidence": 0.94
    },
    {
      "beat_id": "product_reveal",
      "order": 2,
      "beat_type": "product_reveal",
      "purpose": "Ground the demonstration in the actual tool.",
      "recommended_start_ms_min": 800,
      "recommended_start_ms_max": 1800,
      "requiredness": "required",
      "evidence_refs": ["drop_ev_product_01"],
      "confidence": 0.98
    },
    {
      "beat_id": "representative_demo",
      "order": 3,
      "beat_type": "demo",
      "purpose": "Demonstrate the mechanism on an approved material.",
      "requiredness": "required",
      "evidence_refs": ["drop_ev_demo_01", "drop_ev_material_01"],
      "confidence": 0.93
    },
    {
      "beat_id": "observable_proof",
      "order": 4,
      "beat_type": "proof",
      "purpose": "Show the seal line and normal-handling result without universal claims.",
      "requiredness": "required",
      "evidence_refs": ["drop_ev_proof_01"],
      "confidence": 0.89
    },
    {
      "beat_id": "cta",
      "order": 5,
      "beat_type": "cta",
      "purpose": "Give a product-tag CTA consistent with the listing.",
      "requiredness": "recommended",
      "evidence_refs": ["drop_ev_cta_01"],
      "confidence": 0.79
    }
  ],
  "applicability": {
    "suitable_categories": ["visually_demonstrable_gadget", "small_kitchen_tool", "organization_tool"],
    "unsuitable_categories": ["products_without_observable_mechanism", "products_requiring_unsafe_tests"],
    "required_product_traits": ["approved demo material", "visible mechanism", "observable result"],
    "preferred_product_traits": ["compact form", "one-handed use", "real-life context"],
    "buyer_contexts": ["dorm", "pantry", "travel"],
    "markets": ["US"],
    "platforms": ["tiktok_shop"],
    "objectives": ["dropshipping_demo_test", "tiktok_shop_affiliate_test"],
    "fulfillment_constraints": ["Use only seller-authorized shipping wording."],
    "compliance_sensitivities": ["universal compatibility", "food safety", "false demonstration"],
    "pod_context": null,
    "dropshipping_context": {
      "visual_demo_required": true,
      "trust_mechanisms": ["actual sample", "supported-material close-up", "visible seal line"],
      "shipping_promise_constraints": ["7–10 business days only in this fixture"],
      "quality_proof_requirements": ["approved supplier sample", "representative normal use"],
      "margin_or_offer_constraints": ["paid-test action requires gross-profit and budget data"],
      "claim_risks": ["completely airtight", "fresh forever", "works on every bag"]
    }
  },
  "adaptation_instructions": [
    {
      "element_path": "demo.material",
      "instruction_type": "keep",
      "instruction": "Keep the representative approved-material demo and close-up proof.",
      "rationale": "Trust comes from visible, condition-aware proof.",
      "severity": "hard",
      "evidence_refs": ["drop_ev_material_01", "drop_ev_proof_01"]
    },
    {
      "element_path": "buyer_context",
      "instruction_type": "change",
      "instruction": "Change dorm, pantry, and travel contexts across concepts while keeping product facts fixed.",
      "rationale": "The ViralKit should learn which context produces qualified interest.",
      "severity": "medium",
      "evidence_refs": ["drop_ev_problem_01"]
    },
    {
      "element_path": "claims",
      "instruction_type": "avoid",
      "instruction": "Do not generalize one demonstration into universal compatibility, airtightness, freshness, or food-safety claims.",
      "rationale": "The source proves one representative use only.",
      "severity": "hard",
      "evidence_refs": ["drop_ev_material_01", "drop_ev_proof_01"]
    }
  ],
  "performance_summary": {
    "evidence_status": "none",
    "asset_count": 0,
    "campaign_count": 0,
    "date_range_start": null,
    "date_range_end": null,
    "metrics": [],
    "caveats": ["No seller performance is linked; do not call this a winning pattern."],
    "confidence": "low"
  },
  "overall_confidence": "medium",
  "uncertainties": ["Compatibility beyond approved materials is unknown."]
}
```

## 17.5 ViralKitV1 — exactly three concepts

### Concept A — Dorm Backpack Spill

- **Buyer:** college student.
- **Creator:** student lifestyle creator.
- **Hook tactic:** problem interruption.
- **Mechanic:** real-life scenario.
- **Demo:** approved snack bag reseal before returning it to backpack.
- **Proof:** visible seal line and normal handling; no extreme leak claim.
- **Expected learning:** Does a concrete spill scenario create qualified product-tag clicks?

### Concept B — Pantry Clip Replacement Routine

- **Buyer:** parent/household organizer.
- **Creator:** home organization creator.
- **Hook tactic:** old way vs new way.
- **Mechanic:** comparison under factual conditions.
- **Demo:** clips/rolled bags versus sealing one approved bag type at a time.
- **Proof:** close-up seal line on each verified material.
- **Expected learning:** Does organization framing outperform mess prevention?

### Concept C — What Bags Does It Actually Work On?

- **Buyer:** skeptical product-aware shopper.
- **Creator:** practical FAQ/test creator.
- **Hook tactic:** objection handling/comment reply.
- **Mechanic:** skepticism breaker.
- **Demo:** seller-approved supported materials and one explicit unsupported/unknown material note.
- **Proof:** each test labeled; no universal claim.
- **Expected learning:** Does transparent compatibility increase trust and reduce misleading comments?

## 17.6 Selected Campaign Pack — Concept A

```text
CONCEPT
Dorm Backpack Spill

CREATOR DIRECTION
Use your normal dorm/student routine style. Keep it practical and unscripted.

MANDATORY PRODUCT TRUTH
- Use only the seller-approved supported snack bag supplied with the product.
- Show the actual mini bag sealer and visible seal line.
- Do not say airtight, food-safe, fresh forever, or works on every bag.

OPENING
Show the opened snack bag spilling or threatening to spill in a backpack.
Show the product clearly before 1.8 seconds.

REQUIRED BEATS
1. Real backpack/snack context.
2. Product visible before 1.8 seconds.
3. One complete supported-material demo.
4. Seal line close-up held long enough to verify.
5. Normal handling proof — no extreme or deceptive test.
6. Product-tag CTA.

DISCLOSURE
Clearly disclose gifted product and affiliate relationship.

SHIPPING
Use only: “Current delivery estimate is 7–10 business days.”
```

## 17.7 Compiled requirements

```json
[
  {
    "id": "drop_product_before_1800",
    "matcher_type": "product_visibility_timing",
    "severity": "hard",
    "expected": {"before_ms": 1800}
  },
  {
    "id": "drop_supported_material",
    "matcher_type": "demo_material_match",
    "severity": "hard",
    "expected": {"material_in": ["seller_approved_pp_bag", "seller_approved_pe_bag"]}
  },
  {
    "id": "drop_complete_demo",
    "matcher_type": "demo_mechanism_match",
    "severity": "hard",
    "expected": {"mechanism": "complete_supported_bag_reseal"}
  },
  {
    "id": "drop_visible_seal",
    "matcher_type": "proof_type_match",
    "severity": "high",
    "expected": {"proof_type": "visible_seal_line", "minimum_visible_ms": 1200}
  },
  {
    "id": "drop_no_airtight",
    "matcher_type": "prohibited_claim_absence",
    "severity": "hard",
    "expected": {"prohibited_meaning": "universal airtight guarantee"}
  },
  {
    "id": "drop_no_universal_compatibility",
    "matcher_type": "prohibited_claim_absence",
    "severity": "hard",
    "expected": {"prohibited_meaning": "works on every bag or material"}
  },
  {
    "id": "drop_shipping_exact",
    "matcher_type": "shipping_claim_match",
    "severity": "hard",
    "expected": {"allowed_text_meaning": "7–10 business days or no shipping statement"}
  },
  {
    "id": "drop_material_connection",
    "matcher_type": "required_disclosure_presence",
    "severity": "hard",
    "expected": {"meaning": "gifted product and affiliate relationship", "readable": true}
  },
  {
    "id": "drop_product_tag",
    "matcher_type": "product_tag_presence",
    "severity": "high",
    "expected": {"present": true}
  }
]
```

## 17.8 First-draft Preflight

### Observed draft

```text
00:00.000–00:01.100  Backpack spill context is clear.
00:01.100–00:02.000  Product appears clearly.
00:02.200–00:07.000  Creator demonstrates on a foil-lined bag not listed as supported.
00:07.100–00:08.900  Seal line looks visible, but material compatibility is unverified.
00:08.900–00:10.200  Creator says: “This makes every bag completely airtight.”
00:10.300–00:11.500  Creator says: “And it arrives in two days.”
00:12.000–00:13.500  Gifted/affiliate disclosure is absent.
00:14.000–00:16.000  Product tag CTA is present.
```

### Expected versus observed

```json
{
  "final_action": "reject_or_reshoot",
  "hard_blockers": [
    {
      "code": "DEMO_UNSUPPORTED_MATERIAL",
      "requirement_id": "drop_supported_material",
      "expected": {"approved_material": true},
      "observed": {"material": "foil_lined_unknown"},
      "evidence_ids": ["drop_draft_visual_material_01"],
      "seller_message": "A clear demo on an unverified material is still not usable proof.",
      "creator_fix": "Reshoot with the seller-approved snack bag supplied for the campaign."
    },
    {
      "code": "CLAIM_UNIVERSAL_GUARANTEE",
      "requirement_id": "drop_no_airtight",
      "expected": {"universal_airtight_claim": false},
      "observed": {"spoken_text": "This makes every bag completely airtight."},
      "evidence_ids": ["drop_draft_asr_claim_01"],
      "seller_message": "The fixture supports a visible reseal on selected bags, not universal airtightness.",
      "creator_fix": "Use: I use it to reseal supported snack bags after opening."
    },
    {
      "code": "SHIPPING_UNAUTHORIZED",
      "requirement_id": "drop_shipping_exact",
      "expected": {"allowed": "7–10 business days or no claim"},
      "observed": {"spoken_text": "It arrives in two days."},
      "evidence_ids": ["drop_draft_asr_shipping_01"],
      "seller_message": "The shipping promise conflicts with Product Context.",
      "creator_fix": "Remove it or use the authorized 7–10 business day wording."
    },
    {
      "code": "DISCLOSURE_COMMERCIAL_MISSING",
      "requirement_id": "drop_material_connection",
      "expected": {"disclosure_present": true},
      "observed": {"disclosure_present": false},
      "evidence_ids": [],
      "seller_message": "The gifted/affiliate relationship is not disclosed.",
      "creator_fix": "Add a clear spoken or on-screen disclosure and use the platform setting."
    }
  ],
  "strengths_to_preserve": [
    "Strong real-life backpack problem",
    "Product appears at 1.1 seconds",
    "Product-tag CTA"
  ],
  "confidence": "high"
}
```

## 17.9 Revision request

```text
The backpack setup and early product reveal are strong, and the product-tag ending already works.

Please reshoot the demo using only the seller-approved snack bag supplied for this campaign. The current foil-lined bag is not verified. Replace “every bag completely airtight” with: “I use it to reseal supported snack bags after opening.” Remove the two-day delivery claim or use the authorized 7–10 business day wording.

Please add a clear gifted/affiliate disclosure. Keep the current opening and CTA.
```

## 17.10 Revised result and diagnosis boundary

```text
Revised structural result: ready for organic test
Paid-test decision: blocked pending economics and rights

Do not infer:
- that the product keeps food fresh longer;
- that the product works on all materials;
- that good product-tag clicks guarantee orders.

If clicks are strong but orders remain weak, Viraldy must inspect product-page speed, trust, price, shipping, reviews, checkout, and unit economics before blaming the hook.
```

---

# 18. SellerActionPlanV1 — making recommendations executable

A seller-facing action must contain more than `small_paid_test`, `revise`, or `approve`.

## 18.1 Contract

```json
{
  "schema_version": "seller_action_plan_v1",
  "decision": "approve_organic_hold_paid",
  "decision_scope": {
    "subject_type": "ugc_asset_version",
    "subject_id": "uuid",
    "subject_version": 2
  },
  "why_now": "Mandatory creative blockers are resolved, but paid-use rights and unit economics are incomplete.",
  "confidence": "high",
  "preconditions": [
    {
      "code": "RIGHTS_CONFIRMATION_REQUIRED",
      "status": "missing",
      "owner_role": "seller_operator",
      "required_input": "Spark/paid usage authorization"
    },
    {
      "code": "ECONOMICS_REQUIRED",
      "status": "missing",
      "owner_role": "seller_operator",
      "required_input": "gross profit per order and test budget cap"
    }
  ],
  "execution_plan": {
    "owner_role": "seller_operator",
    "next_artifact_type": "approved_organic_asset",
    "steps": [
      "Publish or schedule the approved organic asset",
      "Collect initial product-tag click and comment signals",
      "Confirm rights and economics before any paid amplification"
    ],
    "due_at": null
  },
  "economic_context": {
    "completeness": "incomplete",
    "selling_price": 18.99,
    "gross_profit_per_order": null,
    "test_budget_cap": null,
    "economic_decision": "not_evaluated",
    "missing_required_inputs": ["gross_profit_per_order", "test_budget_cap"]
  },
  "measurement_plan": {
    "measurement_window_hours": null,
    "primary_metric": "product_tag_click_rate",
    "secondary_metrics": ["orders", "gross_profit", "qualified_comments"],
    "success_criterion_source": "seller_defined_or_workspace_benchmark",
    "success_threshold": null,
    "stop_conditions": [
      "rights remain incomplete",
      "critical claim or product mismatch is discovered",
      "seller-defined budget cap is reached",
      "unit economics are negative"
    ]
  },
  "expected_learning": "Determine whether the selected buyer context creates qualified product interest without relying on unsupported claims.",
  "review_gate": {
    "trigger": "seller-defined measurement window completed",
    "next_decisions": ["iterate", "hold", "limited_paid_test", "stop"]
  },
  "evidence_ids": ["uuid"],
  "disclaimer": "Viraldy does not invent budget, success thresholds, rights, or commercial outcomes."
}
```

## 18.2 Action-value rules

- `revise` must identify exact blockers, owner, source requirement, evidence, and revision scope.
- `reshoot` must explain why editing cannot fix the issue.
- `approve_organic` must state which paid-use preconditions remain.
- `small_paid_test` is invalid when budget, rights, gross profit, or success criterion source is absent.
- A missing commercial input becomes `missing_required_input`, not an invented estimate.
- Every action must define an expected learning, not only a score.
- Seller actions and AI recommendations remain separate records.

---

# 19. Insufficient-evidence and ambiguous-case baseline

Viraldy must be willing to say `unknown`, `insufficient_evidence`, or `request_better_media`.

| Case | Correct behavior | Forbidden behavior |
|---|---|---|
| Video is dark or blurry | Mark affected visual fields unknown; request better footage | Guess product/proof from context |
| No audio stream | Continue visual/OCR pipeline; transcript empty | Fail the whole workflow or invent speech |
| Audio exists but ASR confidence is low | Mark claim/disclosure status unknown; do not approve hard requirement | Treat missing transcript as claim absence |
| Two products appear | Ask seller to confirm target SKU or use product tracking | Choose the more likely product silently |
| Product Context missing | Allow generic structural analysis with low confidence; block product-aware action | Invent buyer, price, shipping, or claims |
| OCR text partly hidden | Mark exact text verification unknown | Fuzzy-match a name and approve POD personalization |
| Disclosure appears for 0.4 seconds | Mark not readable / not satisfied | Count keyword presence as satisfaction |
| Before/after lighting changes | Mark proof partial or unreliable | Score it as strong transformation proof |
| POD sample shows correct name but wrong garment color | Product variant mismatch blocker | Approve because personalization text is correct |
| Dropshipping demo uses unknown bag material | Compatibility unknown/hard blocker if brief required approved material | Generalize from visual result |
| Creator says a shipping claim not in Product Context | Prohibited/unauthorized claim | Treat it as harmless personal experience without review |
| Strong CTR but weak conversion | Diagnose downstream funnel/economics as a separate branch | Automatically rewrite the hook |
| Reference uses product later for story setup | Preserve observed timing and mechanic; ViralKit decides target timing | Apply a universal “product under 2 seconds” rule |
| Pattern has one or two source assets | Candidate with medium/low confidence | “Winning pattern” label |
| Performance is correlated but uncontrolled | Directional evidence with non-causal caveat | Causal claim |

## 19.1 Insufficient-evidence output

```json
{
  "decision": "request_better_media",
  "confidence": "low",
  "reason": "The product label and required disclosure are not readable in the supplied footage.",
  "affected_requirements": ["product_match", "required_disclosure_presence"],
  "verified_strengths": ["Creator delivery appears natural"],
  "unverified_fields": ["product_variant", "disclosure_text", "proof_result"],
  "next_action": {
    "owner_role": "creator",
    "request": "Provide a well-lit close-up of the product label and disclosure held on screen long enough to read."
  }
}
```

---

# 20. Presentation-layer contract

The same finding must have three representations.

## 20.1 Machine code

```text
POD_WRONG_PERSONALIZATION
```

## 20.2 Reviewer copy

```text
Expected pet_name=Milo; OCR observed Miles at 00:05.400–00:07.100.
```

## 20.3 Seller-friendly copy

```text
The finished product shows the wrong pet name, so this asset cannot be approved.
```

## 20.4 Creator-friendly copy

```text
Please reshoot with the approved Milo sample and hold the name close-up long enough to read.
```

UI must not expose raw matcher names as the primary seller experience.

---

# 21. Research-backed semantic acceptance gates

## 21.1 Contract and evidence

- 100% outputs validate against the declared schema.
- 100% evidence IDs exist in the same workspace and source lineage.
- 100% timestamps are within media duration.
- No hard requirement may be satisfied by unknown evidence.
- No claim absence may be high-confidence when transcript/OCR/visual coverage is incomplete.

## 21.2 Product truth and personalization

- Zero invented price, shipping, offer, material, compatibility, personalization, or rights facts.
- POD exact-name/date/image/variant mismatches create blockers.
- Physical-item requirements cannot be satisfied by a placeholder mockup.
- Dropshipping compatibility cannot be generalized beyond approved data.

## 21.3 PatternKit

- Required beats have evidence refs.
- Observed ranges remain source observations, not automatic target requirements.
- `performance_summary.evidence_status=none` forbids “winner,” “proven,” or performance claims.
- Directional evidence includes sample-size and non-causal caveats.
- Keep/change/avoid instructions preserve mechanisms while preventing surface copying.

## 21.4 ViralKit

- Exactly three concepts.
- Every pair differs on at least two meaningful axes.
- At least one concept changes hook mechanism.
- At least one concept changes demo, proof, or narrative mechanism.
- Buyer persona and creator persona remain separate.
- Each concept states expected learning and minimum execution requirements.
- Test matrix states held constants and intentionally changed variables.

## 21.5 Preflight

- Tests assert blocker/action bands, not a single exact score.
- Product match, required disclosure, prohibited claim, timing, demo mechanism, and exact personalization use requirement-specific matchers.
- Strong creative signals are preserved in revision messages.
- Reshoot is used when editing cannot correct product truth or physical proof.

## 21.6 Seller action

- Every action has scope, owner, preconditions, next artifact, expected learning, and review gate.
- No budget, measurement window, or success threshold is invented.
- Paid action cannot pass without rights and economics completeness.

## 21.7 Friendly output

- Generic-output rate ≤ 5% in the golden set.
- Every seller summary names the actual product and product-specific issue when data exists.
- Creator message usefulness target ≥ 4/5 in human review.
- Technical codes are available for audit but not used as the primary customer copy.

---

# 22. Runtime and cost guardrails

This golden file is an evaluation and implementation reference. It must **not** be sent in full on every model request.

Runtime rules:

1. Use a canonical system prompt plus one operation prompt.
2. Retrieve only the Product Context, evidence, PatternKit sections, and 1–2 few-shot examples relevant to the operation and domain.
3. Score timing, exact text, product match thresholds, claims, and hard blockers in deterministic code.
4. Cache immutable source artifacts and reuse input hashes.
5. Cap output tokens by operation.
6. Escalate to a stronger model only for low-confidence adjudication or failed schema repair.
7. Record token/usage, latency, prompt version, schema version, model, and cost estimate.
8. Do not retry because prose is “not impressive”; retry only on provider/contract failure.

Recommended evaluation budgets must be configured in code, not treated as universal prices:

```json
{
  "media_observation": {"max_output_tokens": 5000},
  "creative_dna": {"max_output_tokens": 5000},
  "pattern_kit": {"max_output_tokens": 7000},
  "viral_kit": {"max_output_tokens": 9000},
  "campaign_pack": {"max_output_tokens": 7000},
  "revision_message": {"max_output_tokens": 1200}
}
```

These are starting caps for qualification, not guaranteed optimal production settings.

---

# 23. Source registry

## Official TikTok and TikTok Shop

- `[SRC-TT-01]` TikTok for Business, Creative Codes — https://ads.tiktok.com/business/es-LA/creative-codes
- `[SRC-TT-02]` TikTok Shop Academy, Creating Shoppable Video — https://seller-us.tiktok.com/university/course?content_id=7319548693186306&lang=en&learning_id=84434503026433
- `[SRC-TT-03]` TikTok for Business, 4 Things Effective Creator Campaigns Have in Common — https://ads.tiktok.com/business/en-US/blog/creator-marketplace-engaging-content-tips
- `[SRC-TT-04]` TikTok Shop Content Policy — https://seller-us.tiktok.com/university/essay?course_type=1&identity=1&knowledge_id=6837891779151617&role=1
- `[SRC-TT-05]` TikTok Shop, Suggestions for High-Quality Shoppable Videos — https://seller-us.tiktok.com/university/essay?knowledge_id=2816204956665642
- `[SRC-TT-06]` TikTok Shop Seller Terms — https://seller-us.tiktok.com/university/essay?course_type=1&from=search%7BcontentIdParams%7D&identity=1&knowledge_id=8331959022847790&role=1
- `[SRC-TT-07]` TikTok Shop Fulfillment Best Practices — https://seller-us.tiktok.com/university/essay?from=policy&identity=1&knowledge_id=6179821974439723&role=1
- `[SRC-TT-08]` TikTok Video Insights — https://ads.tiktok.com/business/en-US/blog/video-insights-ad-creative-data
- `[SRC-TT-09]` TikTok Spark Ads Creative Playbook — https://ads.tiktok.com/business/creativecenter/quicktok/online/Spark-Ads-Creative-Playbook/pc/en

## FTC

- `[SRC-FTC-01]` FTC Updated Endorsement Guides — https://www.ftc.gov/news-events/news/press-releases/2023/06/federal-trade-commission-announces-updated-advertising-guides-combat-deceptive-reviews-endorsements
- `[SRC-FTC-02]` FTC Disclosures 101 for Social Media Influencers — https://www.ftc.gov/news-events/news/press-releases/2019/11/ftc-releases-advertising-disclosures-guidance-online-influencers
- `[SRC-FTC-03]` FTC Lord & Taylor disclosure guidance — https://www.ftc.gov/business-guidance/blog/2016/03/ftcs-lord-taylor-case-native-advertising-clear-disclosure-always-style

## Creator operations

- `[SRC-INS-01]` Insense Content Feedback and Revisions Guidelines — https://help-creators.insense.pro/4587
- `[SRC-INS-02]` Insense Pricing/Revision FAQ — https://insense.pro/pricing

## Creative strategy and research workflow

- `[SRC-MOT-01]` Motion Hook Tactics Library — https://motionapp.com/library/hooks/tactics/
- `[SRC-MOT-02]` Motion Hook Writing and Psychological Triggers — https://motionapp.com/library/frameworks/hook-writing
- `[SRC-MOT-03]` Motion Creative Fatigue Guidance — https://motionapp.com/blog/ad-fatigue
- `[SRC-MOT-04]` Motion Creative Strategy Engine — https://go.motionapp.com/creative-strategy-engine
- `[SRC-FOR-01]` Foreplay Winning Ad Workflow — https://www.foreplay.co/
- `[SRC-FOR-02]` Foreplay Swipe File — https://www.foreplay.co/swipe-file

## POD and personalization

- `[SRC-ETSY-01]` Etsy Policy Best Practices for Accurate Listings — https://www.etsy.com/seller-handbook/article/1075628311049
- `[SRC-ETSY-02]` Etsy Personalized Listing Guidance — https://help.etsy.com/hc/en-us/articles/360000344528-How-to-Offer-Personalized-Listings
- `[SRC-POD-01]` Printful POD Mistakes — https://www.printful.com/uk/blog/print-on-demand-mistakes
- `[SRC-POD-02]` Printful Samples Before Selling — https://www.printful.com/ca/blog/print-on-demand-tips
- `[SRC-POD-03]` Printful Production/Shipping and Size Guidance — https://www.printful.com/ca/blog/customer-service-for-print-on-demand
- `[SRC-POD-04]` Printify Common POD Mistakes — https://printify.com/blog/how-to-make-money-with-print-on-demand/

## Dropshipping and fulfillment

- `[SRC-SHOP-01]` Shopify Legal/Compliance Guidance for Dropshipping — https://help.shopify.com/en/manual/compliance/legal/dropshipping

## Community signals — hypothesis only

- `[SRC-COMM-01]` Dropshipping discussion: strong CTR with weak conversion and slow mobile page — https://tr.reddit.com/r/dropshipping/comments/1uk1qji/wildly_streaky_sales_56_in_a_couple_days_then/
- `[SRC-COMM-02]` Dropshipping discussion: inconsistent product photos and generic templates as trust risks — https://hr.reddit.com/r/dropshipping/comments/1t63i3q/why_your_shopify_store_looks_scammy_in_2026_even/

---

# 24. Change log from v0.9

Version 1.0 adds:

- official-policy and practitioner source hierarchy;
- clear separation of angle, mechanic, hook tactic, trigger, format, and sequence;
- 18 research-backed pattern families;
- 50+ real-world mistake codes;
- observed-source range versus product-specific requirement rules;
- full-depth POD and dropshipping golden flows equal to the TikTok product scenario;
- material-connection disclosure and creator-authenticity rules;
- SellerActionPlanV1 with economics, owner, preconditions, measurement, stop rules, and expected learning;
- insufficient-evidence and ambiguous cases;
- seller/reviewer/creator presentation layers;
- cost/runtime guardrails;
- research-backed acceptance gates that avoid exact-score overfitting.

# Appendix A. UI output hierarchy

Viraldy should not display one giant AI paragraph.

## 18.1 Top decision card

```text
REVISE BEFORE PAID USE
Final score: 71
Confidence: High
2 hard blockers · 1 high-priority fix
```

## 18.2 Evidence timeline

```text
0s        2s        5s        10s       15s       20s
| Hook | late product | demo | no proof | offer | CTA |
```

Clicking a segment opens:

- video frame;
- transcript/OCR;
- observed value;
- expected value;
- evidence confidence.

## 18.3 Expected vs observed

```text
Requirement             Expected             Observed             Status
Product reveal          ≤2.0s                4.2s                 Missing
Same-item proof         Required             Not observed         Missing
Disclosure              Required             Not found            Missing
Product tag              Required             18.8s                Satisfied
```

## 18.4 Revision priority

```text
MUST FIX
1. Product timing
2. Required disclosure

SHOULD FIX
3. Same-shirt proof

KEEP
- Creator delivery
- Product-tag CTA
- Pacing
```

## 18.5 PatternKit visual

- source assets;
- evidence-backed sequence;
- keep/change/avoid;
- applicability;
- performance evidence state;
- confidence and uncertainty.

## 18.6 ViralKit visual

- three concept cards;
- differences highlighted by strategic axis;
- controlled vs changed variables;
- concept selection action;
- Campaign Pack status;
- Preflight requirement readiness.

---

# Appendix B. Codex fixture and automated acceptance requirements

Codex must create deterministic fixture data that produces outputs equivalent in meaning to the golden examples.

Required fixture scenarios:

```text
home_travel_steamer
pod_dog_mom_crewneck
dropshipping_bag_sealer
```

Required test assets:

```text
reference_good_structure
ugc_missing_product_timing
ugc_missing_proof
ugc_missing_disclosure
ugc_prohibited_claim
ugc_revision_resolves_all
no_audio_video
```

Required assertions:

## Product Context

- missing facts remain unknown;
- projection fields stay synchronized;
- claim guardrails survive snapshots.

## Creative DNA

- no product-match result without attached Product Context;
- no offer is invented;
- spoken and overlay CTA remain separate;
- every observed field has evidence;
- category-specific observations do not leak across fixtures.

## PatternKit

- at least one source DNA version is required;
- multi-asset cluster requires at least two sources;
- sequence is contiguous;
- exact competitor wording is not emitted as a keep instruction;
- no `winning` label without performance evidence;
- POD and dropshipping applicability fields remain distinct;
- version and provenance are immutable.

## ViralKit

- exactly three concepts;
- each concept differs from every other concept across at least two axes;
- buyer and creator personas remain separate;
- all claims and disclosures are preserved;
- concepts violating product constraints are rejected;
- selected concept action is stored separately;
- Campaign Pack is produced through the Campaign Pack public service.

## Campaign Pack

- spoken hook does not automatically become overlay;
- product timing compiles to exact matcher;
- required disclosure compiles to presence matcher;
- prohibited claim compiles to absence matcher;
- product-tag and CTA timing compile separately;
- buyer audience and creator direction are not mixed.

## Scorer

- no LLM-generated scores;
- timing points only apply when timing is satisfied;
- claim absence confidence reflects evidence coverage;
- hard blockers override score bands.

## Preflight

- product at 4.2s fails a 2.0s requirement;
- generic demo score cannot satisfy an exact same-item proof requirement;
- missing disclosure is a hard blocker;
- prohibited claim detection returns violated;
- unknown hard requirement cannot approve;
- revision resolves exact blockers and preserves strengths.

## Recommendation

- action, reason, evidence, confidence, conditions, and next steps are present;
- seller action is stored separately;
- structural readiness disclaimer is present.

---

# Appendix C. Final product quality statement

The desired Viraldy experience is:

```text
The system understands the seller's actual product,
shows exactly what it observed,
explains the mismatch between brief and execution,
produces a creator-ready action,
and stores what the seller decided and what happened next.
```

Viraldy is not successful because the response sounds intelligent.

Viraldy is successful when:

- a seller can use the Campaign Pack without rewriting it;
- a creator can execute the revision without another clarification call;
- a reviewer agrees with the main blockers;
- the seller changes or confirms a real decision;
- the next test is informed by stored evidence and outcomes.
