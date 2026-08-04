# Viraldy Domain, Creative and Workflow Research Pack v1
**Research access date:** 2026-07-31  
**Purpose:** Implementation-ready policy, pattern, mistake, workflow and Golden Case data for Viraldy.
## Executive conclusions
1. Viraldy should separate hard platform/regulatory gates from operational constraints, best practices, directional patterns and anecdotes. The same sentence must never be treated as both a policy violation and a creative optimization.
2. Product truth is the first gate: exact SKU/variant, listing, offer, shipping, physical sample, personalization and supplier route must be versioned. Missing material facts return typed unknowns.
3. A popular or long-running social creative is a research candidate, not a proven winner. “Winning” requires linked outcome evidence and context.
4. UGC approval and paid readiness are separate decisions. Rights, audio, disclosure, product tag and Spark authorization can block paid use even when the creative itself is structurally strong.
5. POD requires a separate overlay for buyer input, preview/template, physical sample, mockup limitations, made-to-order handling and IP. Dropshipping requires an overlay for exact supplier SKU, stock/cost freshness, customer route and compatibility.
6. Preflight should output expected versus observed, evidence, severity, editability, seller action and creator message. A score alone is not a decision product.
7. Performance learning must preserve asset/product/creator/campaign mapping, outcome definitions, economics and test design. Offline scoring filters structural risk; the market still validates performance.
8. Public software pricing and community pain indicate a plausible paid category, but Viraldy willingness-to-pay, price and retention remain unvalidated until paid pilots.
## Evidence model and source priority
| Strength | Meaning |
|---:|---|
| 5 | Official platform/regulator/government rule or current operational documentation; strongest source for a hard rule. |
| 4 | Official guidance, established provider documentation, or primary research/preprint; strong but context may limit transfer. |
| 3 | Established product documentation, vendor first-party report, conference/expert interview; useful best practice or directional evidence. |
| 2 | Seller/creator community anecdote; pain evidence only, never prevalence or causality. |
| 1 | Unverified opinion; excluded from deterministic rules. |

**Source priority:** official platform/regulator → provider/product documentation and primary research → agency/operator examples → seller/creator communities → clearly labelled anecdote/opinion.

**Non-causality rule:** social popularity, views, estimated spend, longevity, follower count and engagement never prove commercial causality by themselves.
## Alignment with Viraldy internal architecture
- **VIRALDY — FULL PRODUCT & BUSINESS BLUEPRINT.pdf** — Decision system spanning creative research, product adaptation, UGC quality gate, creator/sample, rights/Spark, performance and next action.
- **Viraldy_Full_Product_Business_Technical_Blueprint.pdf** — Manual-first/API-later architecture; structured objects, stable IDs, provenance and outcome graph.
- **Pipeline và model lưu trữ.txt** — CreativeDNA is observed asset truth; PatternKit is reusable knowledge; ViralKit is product/campaign-specific compiled hypothesis; models extract/match/score rather than store knowledge.
- **Vòng đời creative Viraldy.txt** — Every feature follows input → evidence → diagnosis → action → outcome; P0 creative loop before integrations.
- **ViralScore Current-State Audit.txt** — Product-grounded, evidence-grounded, decision-grounded and learning-grounded outputs; unknowns must not be invented.
- **viraldy_vidmob_report_planning.docx** — Creative intelligence and element-level analysis patterns adapted to Viraldy niche.
- **viraldy_alison_report_planning.docx** — AI-assisted creative analytics, iteration and domain adaptation research.
- **viraldy_foreplay_report_planning.docx** — Research-to-brief workflow, swipe/reference memory and creative operations.
- **viraldy_pencil_report_planning_final.docx** — Generation/testing workflow and adaptation into product-aware creative decisions.

The research pack is designed for the Viraldy object chain: **Product Context → CreativeDNA → PatternKit candidate → ViralKit → Campaign Pack → immutable UGC draft → Preflight → SellerActionPlan → creator revision → rights/Spark → performance outcome → PatternKit evidence update.**

# A. Domain Expert Policy Catalog
**Count:** 58 policies. Classification counts: `{'official_hard_rule': 25, 'unresolved_disagreement': 1, 'operational_hard_constraint': 16, 'established_best_practice': 13, 'contextual_guideline': 3}`.

## TT-CONTENT-001 — Promoted content must match the actual product
- **Domain:** `tiktok_shop_us`
- **Rule type:** `official_hard_rule`
- **Severity:** `blocker`

**Applicability**
- TikTok Shop shoppable video
- LIVE
- affiliate content
- paid ads

**Required conditions**
- A specific listing/SKU/variant is promoted

**Expected behavior**
- Show and describe the same product, variant, bundle, price and included items the shopper receives
- Keep visual, spoken, caption, product tag and landing page consistent

**Prohibited behavior**
- Material product/variant/bundle/price mismatch
- Supplier footage that creates a false impression

**Unknown behavior**
- If exact SKU, variant or included items cannot be verified, return unknown and require seller confirmation

**Exceptions**
- Minor non-material appearance differences require contextual review

**Common failure modes**
- Old video after listing changed
- Wrong product tag
- Similar supplier model substituted

**Expert-review trigger**
- Product cannot be matched confidently
- Variant/bundle is ambiguous
- Supplier substitution suspected

**Seller-facing explanation**  
The video, product tag and listing must describe the same item. Confirm the exact SKU and current offer before posting.

**Creator-facing correction**  
Please replace shots or lines that show a different model, color, included item, price or function from the linked product.

**Implementation**
```json
{
  "rule": "block when material_product_mismatch=true or tagged_product_id!=campaign.product_id",
  "required_fields": [
    "product_id",
    "variant_id",
    "listing_snapshot_id",
    "asset_version_id"
  ]
}
```
**Sources:** [TT08] TikTok Shop Content Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837891779151617); [TT10] Misleading and false content — TikTok Advertising Policies (https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content); [TT11] Common Reasons Ads Fail Review — TikTok Advertising Policies (https://ads.tiktok.com/help/article/common-reasons-ads-fail-review?lang=en)

## TT-LISTING-001 — Listing images must accurately represent the physical product
- **Domain:** `tiktok_shop_us`
- **Rule type:** `official_hard_rule`
- **Severity:** `blocker`

**Applicability**
- TikTok Shop US product listings

**Required conditions**
- Seller creates or updates listing imagery

**Expected behavior**
- Use images that accurately represent the physical item and only what the buyer receives
- Preserve current platform image requirements in a versioned policy table

**Prohibited behavior**
- Placeholder or materially misleading render
- Props presented as included
- Digitally altered features

**Unknown behavior**
- When image type or physical accuracy cannot be determined, return seller_confirmation_required

**Exceptions**
- Channel rules differ; this applies to TikTok Shop listing assets

**Common failure modes**
- POD mockup used as proof
- AI image changes texture or shape
- Accessories appear included

**Expert-review trigger**
- No physical sample exists
- Mockup and sample materially differ
- Low-resolution evidence

**Seller-facing explanation**  
Use the real physical product in the TikTok Shop listing when the policy requires it; a render cannot change buyer expectations.

**Creator-facing correction**  
Please provide a physical-product image and avoid showing props or digitally altered features as part of the purchase.

**Implementation**
```json
{
  "rule": "block listing_ready when asset_type in [placeholder,materially_inaccurate_render]",
  "policy_version_required": true
}
```
**Sources:** [TT07] Product Listing Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=3196690250417921); [TT18] Product Quality Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=5203348292765486)

## TT-AIGC-001 — AI-generated or edited product content must not mislead
- **Domain:** `tiktok_shop_us`
- **Rule type:** `official_hard_rule`
- **Severity:** `blocker`

**Applicability**
- Listing media
- TikTok Shop content
- paid ads

**Required conditions**
- AI generation, compositing or material enhancement is used

**Expected behavior**
- Keep synthetic content faithful to real product appearance, function and context
- Store provenance and seller confirmation

**Prohibited behavior**
- Invented product capability, result, accessory, endorsement or physical detail

**Unknown behavior**
- If an effect cannot be verified, mark unverified_visual_claim and block proof language

**Exceptions**
- Non-material crop, exposure and captions may be acceptable

**Common failure modes**
- Synthetic before/after
- AI adds feature
- Upscaling changes print texture

**Expert-review trigger**
- Synthetic human endorsement
- Health/safety result
- Material feature only exists in generated image

**Seller-facing explanation**  
AI can help production, but it cannot invent what the product looks like or does.

**Creator-facing correction**  
Please replace the synthetic result with real footage or remove the unsupported claim.

**Implementation**
```json
{
  "rule": "block when synthetic_content=true and material_fact_verification!=verified"
}
```
**Sources:** [TT08] TikTok Shop Content Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837891779151617); [TT18] Product Quality Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=5203348292765486)

## TT-CLAIM-001 — No false, exaggerated or absolute product-effect claims
- **Domain:** `claims_disclosures`
- **Rule type:** `official_hard_rule`
- **Severity:** `blocker`

**Applicability**
- TikTok Shop content
- TikTok ads
- creator scripts
- captions
- landing pages

**Required conditions**
- Creative makes an objective or product-effect claim

**Expected behavior**
- Use specific supportable language tied to evidence
- Keep personal experience no broader than the creator actually observed

**Prohibited behavior**
- Guaranteed outcomes
- Impossible effects
- Unsupported superlatives
- Edited demonstration that materially exaggerates results

**Unknown behavior**
- Absent evidence returns insufficient_evidence; do not rewrite uncertainty as fact

**Exceptions**
- Puffery and borderline opinion require contextual review

**Common failure modes**
- Works instantly
- Best ever as objective proof
- Supplier copy repeated without evidence

**Expert-review trigger**
- Health/safety/financial/environmental/comparative claim
- Before/after manipulation
- Evidence is for another model

**Seller-facing explanation**  
A strong claim needs evidence for this exact product, condition and buyer context.

**Creator-facing correction**  
Please replace the absolute promise with an accurate personal observation or seller-approved evidence-backed wording.

**Implementation**
```json
{
  "rule": "hard_block claim_risk in [prohibited,unsubstantiated_high_risk]",
  "evidence_object_required": true
}
```
**Sources:** [TT10] Misleading and false content — TikTok Advertising Policies (https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content); [TT11] Common Reasons Ads Fail Review — TikTok Advertising Policies (https://ads.tiktok.com/help/article/common-reasons-ads-fail-review?lang=en); [FTC04] Health Products Compliance Guidance — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance)

## TT-OFFER-001 — Creative offer must match current price, discount, bundle and landing page
- **Domain:** `claims_disclosures`
- **Rule type:** `official_hard_rule`
- **Severity:** `blocker`

**Applicability**
- TikTok Shop content
- TikTok ads
- affiliate UGC

**Required conditions**
- Creative presents price, discount, bundle, coupon, free item or shipping offer

**Expected behavior**
- Compare against a timestamped listing/offer snapshot
- State material conditions

**Prohibited behavior**
- Mismatched price/discount
- Unavailable offer
- Hidden qualification
- Wrong bundle

**Unknown behavior**
- If live offer cannot be retrieved or confirmed, return offer_unverified

**Exceptions**
- Dynamic prices require versioned approval and expiry

**Common failure modes**
- Old sale overlay
- Different variant price
- Free shipping not available

**Expert-review trigger**
- Geo-specific pricing
- Coupon condition unclear
- Offer expires before post

**Seller-facing explanation**  
The offer in the video must still match the exact linked product when the content runs.

**Creator-facing correction**  
Please update or remove the price, discount, bundle or shipping line to match the seller-approved current offer.

**Implementation**
```json
{
  "rule": "block when creative_offer materially differs from listing_snapshot_offer",
  "version_fields": [
    "offer_snapshot_at",
    "creative_version_id"
  ]
}
```
**Sources:** [TT10] Misleading and false content — TikTok Advertising Policies (https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content); [TT11] Common Reasons Ads Fail Review — TikTok Advertising Policies (https://ads.tiktok.com/help/article/common-reasons-ads-fail-review?lang=en)

## TT-URGENCY-001 — Urgency and scarcity must be truthful and current
- **Domain:** `claims_disclosures`
- **Rule type:** `official_hard_rule`
- **Severity:** `high`

**Applicability**
- Shop content
- paid ads
- creator CTAs

**Required conditions**
- Creative says limited time, ending soon, low stock or last chance

**Expected behavior**
- Use verified inventory or offer deadline
- Store expiry and source

**Prohibited behavior**
- Fabricated countdown
- Evergreen today-only claim
- Unsupported low-stock statement

**Unknown behavior**
- If stock/expiry is not verifiable, remove urgency and return unknown

**Exceptions**
- Platform-native urgency based on live data may be valid

**Common failure modes**
- Old video after sale
- Supplier stock not synced
- Copied urgency from reference

**Expert-review trigger**
- Evergreen false urgency
- No inventory source
- Potential dark-pattern concern

**Seller-facing explanation**  
Use urgency only when the deadline or inventory signal is real and current.

**Creator-facing correction**  
Please remove the scarcity line or use the exact seller-approved deadline and conditions.

**Implementation**
```json
{
  "rule": "block urgency_claim when verified_expiry=null and verified_inventory_signal=null"
}
```
**Sources:** [TT10] Misleading and false content — TikTok Advertising Policies (https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content); [FTC02] FTC Staff Revises Online Advertising Disclosure Guidelines — Federal Trade Commission (https://www.ftc.gov/news-events/news/press-releases/2013/03/ftc-staff-revises-online-advertising-disclosure-guidelines)

## DISC-001 — Commercial relationship must be clearly disclosed
- **Domain:** `claims_disclosures`
- **Rule type:** `official_hard_rule`
- **Severity:** `blocker`

**Applicability**
- US-facing affiliate, gifted, paid or incentivized content

**Required conditions**
- Fee, commission, free product, discount or other material connection exists

**Expected behavior**
- Use TikTok commercial-content disclosure when required
- Make relationship clear and conspicuous near endorsement

**Prohibited behavior**
- Hidden or ambiguous disclosure
- Assuming product tag alone is disclosure
- Buried hashtag

**Unknown behavior**
- If compensation or relationship is unknown, ask seller/creator and block publish-ready

**Exceptions**
- Pure independent editorial content may not require commercial disclosure after confirmation

**Common failure modes**
- Free product treated as no connection
- Disclosure after more
- Only #collab among many tags

**Expert-review trigger**
- Compensation structure unclear
- Cross-platform reuse
- Creator disputes connection

**Seller-facing explanation**  
A free product, fee or affiliate commission can create a material connection. Confirm it and disclose it clearly.

**Creator-facing correction**  
Please enable the commercial-content disclosure and add plain-language disclosure near the endorsement.

**Implementation**
```json
{
  "rule": "block when material_connection in [yes,unknown] and disclosure_status!=complete"
}
```
**Sources:** [TT13] Commercial Content Disclosure setting for advertisers — TikTok for Business Help Center (https://ads.tiktok.com/help/article/about-the-commercial-content-disclosure-setting-for-advertisers); [FTC01] FTC Endorsement Guides: What People Are Asking — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking); [FTC02] FTC Staff Revises Online Advertising Disclosure Guidelines — Federal Trade Commission (https://www.ftc.gov/news-events/news/press-releases/2013/03/ftc-staff-revises-online-advertising-disclosure-guidelines)

## IP-001 — Do not use unauthorized trademarks, copyright, footage, artwork or counterfeit presentation
- **Domain:** `ip_compliance`
- **Rule type:** `official_hard_rule`
- **Severity:** `blocker`

**Applicability**
- Listings
- ads
- creator content
- POD designs
- reference adaptation

**Required conditions**
- Third-party name, logo, character, artwork, photo, video, music or distinctive branding appears

**Expected behavior**
- Use owned/licensed/public-domain/authorized material and retain proof
- Adapt structure without copying expression

**Prohibited behavior**
- Unauthorized logo/artwork/footage/music
- Counterfeit or confusingly similar branding
- Direct reference cloning

**Unknown behavior**
- If rights are undocumented, return rights_unknown; online availability is not permission

**Exceptions**
- Nominative use, parody and fair use are fact-specific and require expert review

**Common failure modes**
- POD fandom design
- Competitor footage reused
- Trending music used in paid asset

**Expert-review trigger**
- Trademark similarity
- Fan art/parody
- Named comparison
- No licensing proof

**Seller-facing explanation**  
A reference provides pattern evidence, not permission to reuse its script, footage, artwork, logo or music.

**Creator-facing correction**  
Please replace all unapproved third-party elements and provide the license or seller approval.

**Implementation**
```json
{
  "rule": "block when third_party_asset_detected=true and authorization_status not in [verified,approved_after_review]"
}
```
**Sources:** [TT14] TikTok Shop Intellectual Property Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837901778306818); [USPTO02] Likelihood of Confusion — United States Patent and Trademark Office (https://www.uspto.gov/trademarks/search/likelihood-confusion); [USCO01] Visual Artists: Copyright Basics — U.S. Copyright Office (https://www.copyright.gov/engage/visual-artists/)

## CATEGORY-001 — Prohibited and restricted categories require current policy gating
- **Domain:** `seller_governance`
- **Rule type:** `official_hard_rule`
- **Severity:** `blocker`

**Applicability**
- Product onboarding
- Product Scan
- Campaign Pack

**Required conditions**
- Product category is scanned or imported

**Expected behavior**
- Classify against current prohibited/restricted rules
- Require qualification proof where applicable

**Prohibited behavior**
- Generating commerce campaign for prohibited product
- Presenting restricted product as generally eligible

**Unknown behavior**
- If category is uncertain, return expert_review_required and block campaign-ready

**Exceptions**
- Availability varies by qualification, invitation, jurisdiction and version

**Common failure modes**
- Vague seller category
- Supplier relabels item
- Bundle includes restricted component

**Expert-review trigger**
- Regulated/high-risk category
- Policy version changed
- Classification uncertain

**Seller-facing explanation**  
Viraldy must know the exact category and current eligibility before recommending a TikTok Shop launch.

**Creator-facing correction**  
Please pause production until the seller confirms category eligibility and required documentation.

**Implementation**
```json
{
  "rule": "block when category_status in [prohibited,restricted_unqualified,unknown_high_risk]",
  "policy_version_required": true
}
```
**Sources:** [TT19] Prohibited Products Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=1399532709988097); [TT20] Restricted Products Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=3238037484275457)

## QUALITY-001 — Verify exact product quality and listing accuracy before promotion
- **Domain:** `seller_governance`
- **Rule type:** `official_hard_rule`
- **Severity:** `high`

**Applicability**
- TikTok Shop seller
- POD
- dropshipping
- creator seeding

**Required conditions**
- Product will be listed, sampled or promoted

**Expected behavior**
- Verify supplier, materials/specs, condition and listing consistency
- Monitor returns and complaints

**Prohibited behavior**
- Promoting defective or materially inconsistent product as verified

**Unknown behavior**
- No exact sample or supplier evidence means quality_unverified and proof claims stay blocked

**Exceptions**
- Risk-based sampling can be used if uncertainty remains visible

**Common failure modes**
- Sample differs from customer batch
- No QC
- Render hides defect

**Expert-review trigger**
- Complaint/return spike
- Batch mismatch
- Material/safety specification unclear

**Seller-facing explanation**  
Creative quality cannot fix an unverified product. Check the exact item and supplier before scale.

**Creator-facing correction**  
Please avoid quality or durability claims until the seller verifies the physical sample and current batch.

**Implementation**
```json
{
  "rule": "block proof_heavy priority test when exact_sample_status!=verified"
}
```
**Sources:** [TT18] Product Quality Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=5203348292765486); [DS03] Product Sourcing Guide: How To Get Started (2026) — Shopify (https://www.shopify.com/blog/product-sourcing-apps); [DS04] How Does Alibaba Work? Buying and Safety Guide (2026) — Shopify (https://www.shopify.com/blog/16665772-alibaba-101-how-to-safely-source-products-from-the-worlds-biggest-supplier-directory)

## SAMPLE-001 — Free-sample content deadline and product-link obligation
- **Domain:** `tiktok_shop_samples`
- **Rule type:** `official_hard_rule`
- **Severity:** `critical`

**Applicability**
- TikTok Shop US free-sample collaboration

**Required conditions**
- Creator accepted and received a free sample

**Expected behavior**
- Track receipt and current platform due date
- Observed guidance states post within 14 days after receipt
- Include correct product link and qualifying public content

**Prohibited behavior**
- Treating free sample as no obligation
- Missing due date/product link

**Unknown behavior**
- If receipt time is unavailable, deadline_unknown; do not invent

**Exceptions**
- Approved extension/appeal can change deadline

**Common failure modes**
- Wrong delivery timestamp
- Private side agreement ignores platform
- No product link

**Expert-review trigger**
- Delivery dispute
- Defective sample
- Live deadline differs from stored policy

**Seller-facing explanation**  
Track receipt, due date, correct product link and fulfillment status for every free sample.

**Creator-facing correction**  
Please publish qualifying content with the correct product link by the platform deadline or request the supported extension before it expires.

**Implementation**
```json
{
  "rule": "due_date=received_at+14_days unless approved_extension",
  "policy_version_required": true
}
```
**Sources:** [TT01] Guide to Samples: Free and Refundable — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=5764641632306946); [TT02] How to set up and manage samples — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=5694209038927617); [TT03] Sample Integrity Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6118437723506474)

## SAMPLE-002 — Sample extension and defective-sample appeal are limited workflows
- **Domain:** `tiktok_shop_samples`
- **Rule type:** `official_hard_rule`
- **Severity:** `high`

**Applicability**
- TikTok Shop US sample collaboration

**Required conditions**
- Creator cannot meet deadline or sample is defective/unsatisfactory

**Expected behavior**
- Use current in-platform extension/appeal path
- Observed guidance describes one seven-day extension and one defective-sample appeal

**Prohibited behavior**
- Unlimited informal extensions
- Bypassing platform workflow

**Unknown behavior**
- If status cannot be verified, show pending_confirmation

**Exceptions**
- Current policy can change; version the workflow

**Common failure modes**
- Reminder after deadline
- Multiple chat extensions
- Defect not documented

**Expert-review trigger**
- Extension already used
- Disputed defect
- Policy updated

**Seller-facing explanation**  
Use the platform workflow for extension or defect appeal; chat alone may not update platform status.

**Creator-facing correction**  
Please submit the platform extension or defective-sample appeal with evidence before the original deadline.

**Implementation**
```json
{
  "rule": "max_extensions=1; extension_days=7; max_defect_appeals=1",
  "policy_version_required": true
}
```
**Sources:** [TT03] Sample Integrity Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6118437723506474)

## SAMPLE-003 — Refundable-sample window is unresolved across official guidance
- **Domain:** `tiktok_shop_samples`
- **Rule type:** `unresolved_disagreement`
- **Severity:** `critical`

**Applicability**
- TikTok Shop US refundable samples

**Required conditions**
- Refundable sample is created or tracked

**Expected behavior**
- Read deadline and sales goal from live collaboration/order object
- Store source and observed policy version

**Prohibited behavior**
- Hard-coding a universal 90-day or 120-day window

**Unknown behavior**
- Return unknown_policy_conflict when live object is unavailable; observed official pages conflict

**Exceptions**
- Specific Seller Center terms override general documentation

**Common failure modes**
- Stale constant
- Help article treated as contract
- Returns ignored near end

**Expert-review trigger**
- Live campaign terms unavailable
- Official pages continue to conflict

**Seller-facing explanation**  
Do not rely on a fixed refundable-sample window. Use the deadline and goal displayed in the actual collaboration.

**Creator-facing correction**  
Please confirm the deadline shown in your TikTok account before planning the content schedule.

**Implementation**
```json
{
  "rule": "definitive_due_date requires live_platform_object; otherwise unknown_policy_conflict"
}
```
**Sources:** [TT01] Guide to Samples: Free and Refundable — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=5764641632306946); [TT02] How to set up and manage samples — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=5694209038927617)

## SAMPLE-004 — Seller review and shipment windows must be tracked from live platform status
- **Domain:** `tiktok_shop_samples`
- **Rule type:** `operational_hard_constraint`
- **Severity:** `high`

**Applicability**
- TikTok Shop sample request management

**Required conditions**
- Seller receives or approves a sample request

**Expected behavior**
- Track live review and post-approval ship windows
- Observed guidance described seven days for each step

**Prohibited behavior**
- Approving sample without stock/ship feasibility
- Leaving approved sample unshipped

**Unknown behavior**
- If timestamps are not imported, deadline_unknown and ask seller to enter them

**Exceptions**
- Campaign-specific/live terms control

**Common failure modes**
- Request sits only in spreadsheet
- Approval date missing
- Supplier delay found after approval

**Expert-review trigger**
- Supplier cannot meet deadline
- Made-to-order sample
- Live platform differs

**Seller-facing explanation**  
Sample approval creates an operational deadline. Confirm exact inventory and shipping before approval.

**Creator-facing correction**  
Please wait for seller confirmation that the exact sample is in stock and can ship within the platform window.

**Implementation**
```json
{
  "rule": "prefer live platform dates; observed fallback review_days=7 and ship_days=7 with warning"
}
```
**Sources:** [TT02] How to set up and manage samples — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=5694209038927617)

## AFF-001 — Open and Target Collaboration terms must be resolved per creator/product
- **Domain:** `tiktok_shop_affiliate`
- **Rule type:** `official_hard_rule`
- **Severity:** `medium`

**Applicability**
- TikTok Shop Affiliate

**Required conditions**
- Product is in Open and/or Target Collaboration

**Expected behavior**
- Store collaboration type, creator-specific terms, commission, samples and effective dates
- Apply effective Target terms when platform indicates precedence

**Prohibited behavior**
- Assuming one commission/sample policy applies to all creators

**Unknown behavior**
- If effective terms are not imported, ask seller; do not infer from chat

**Exceptions**
- Promotional programs and later changes can alter terms

**Common failure modes**
- Brief shows Open commission while creator has Target offer
- Expired terms

**Expert-review trigger**
- Conflicting screenshots
- Terms changed after brief

**Seller-facing explanation**  
Creator-specific Target terms can differ from the product’s Open Collaboration terms. Verify before outreach.

**Creator-facing correction**  
Please confirm the invitation, commission, sample terms and product before accepting or posting.

**Implementation**
```json
{
  "rule": "effective_terms=active_target_terms else open_terms"
}
```
**Sources:** [TT04] Setting Up Affiliate Collaborations — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837873164896001)

## SPARK-001 — Spark Ads require valid platform authorization and contractual paid-use rights
- **Domain:** `rights_spark`
- **Rule type:** `official_hard_rule`
- **Severity:** `blocker`

**Applicability**
- Spark Ads
- Shop Ads using creator posts

**Required conditions**
- Seller wants to amplify an organic post

**Expected behavior**
- Record supported authorization method, creator/post/advertiser identity, scope, status and expiry
- Confirm separate contractual paid rights

**Prohibited behavior**
- Marking Spark-ready without valid authorization
- Assuming organic post grants paid rights

**Unknown behavior**
- If code/status or contract cannot be validated, authorization_unknown and paid-ready=false

**Exceptions**
- Mass authorization, linked-account and video-code workflows differ

**Common failure modes**
- Expired code
- Wrong post/creator
- Organic rights confused with paid rights

**Expert-review trigger**
- Code invalid/expired
- Creator disputes paid use
- Post/account changed

**Seller-facing explanation**  
A strong post is not automatically a paid asset. Viraldy needs both valid Spark authorization and paid-use rights.

**Creator-facing correction**  
Please provide or approve the supported Spark authorization for this exact post and advertiser, plus the agreed paid-use terms.

**Implementation**
```json
{
  "rule": "spark_ready only when authorization.valid and contract.paid_use=true and asset/post/advertiser match"
}
```
**Sources:** [TT05] Differences between affiliate mass authorization and video code authorization — TikTok for Business Help Center (https://ads.tiktok.com/help/article/differences-between-affiliate-creative-authorization-and-video-code); [TT06] How to create Spark Ads for Manual and Search Campaigns — TikTok for Business Help Center (https://ads.tiktok.com/help/article/spark-ads-creation-guide); [UGC03] TikTok Spark Ads Setup Guide (2026) — Insense (https://insense.pro/blog/tiktok-spark-ads)

## SPARK-002 — Spark workflow can lock caption, change visibility and depend on code lifecycle
- **Domain:** `rights_spark`
- **Rule type:** `official_hard_rule`
- **Severity:** `high`

**Applicability**
- Spark Ads preparation

**Required conditions**
- Creator post is being authorized

**Expected behavior**
- Confirm final caption before authorization
- Acknowledge private-to-public behavior where applicable
- Track code/post lifecycle

**Prohibited behavior**
- Promising edits after authorization when workflow disallows them
- Hiding visibility change
- Deleting code while ads depend on it

**Unknown behavior**
- If chosen method behavior is unknown, expert_review_required

**Exceptions**
- Behavior differs by authorization method and product surface

**Common failure modes**
- Typo discovered after code
- Creator expected private post
- Code cleanup before ad removal

**Expert-review trigger**
- Private-content concern
- Caption contains risky claim
- Active ads depend on code

**Seller-facing explanation**  
Lock the final caption and confirm visibility expectations before requesting authorization.

**Creator-facing correction**  
Please review the final caption and confirm the post may become public while promoted before authorizing it.

**Implementation**
```json
{
  "rule": "require caption_approved_at and visibility_acknowledged_at before authorization_request"
}
```
**Sources:** [TT06] How to create Spark Ads for Manual and Search Campaigns — TikTok for Business Help Center (https://ads.tiktok.com/help/article/spark-ads-creation-guide)

## SPARK-003 — Authorization duration and contractual usage duration must be stored separately
- **Domain:** `rights_spark`
- **Rule type:** `operational_hard_constraint`
- **Severity:** `high`

**Applicability**
- Spark Ads
- creator paid usage

**Required conditions**
- Authorization is granted

**Expected behavior**
- Store platform start/end, contract start/end, channels and renewal
- Use the shorter valid scope for paid use

**Prohibited behavior**
- Assuming one default duration
- Continuing paid use after either permission expires

**Unknown behavior**
- Missing expiry returns duration_unknown and blocks long-running use

**Exceptions**
- Duration options vary across workflows

**Common failure modes**
- Contract/platform durations conflict
- Timezone error
- Renewal not documented

**Expert-review trigger**
- Perpetual/broad usage
- Cross-channel use
- Renewal after expiry

**Seller-facing explanation**  
Track both platform authorization and contract usage term; the shorter valid permission governs.

**Creator-facing correction**  
Please confirm the authorization period and paid-usage term for this exact asset.

**Implementation**
```json
{
  "rule": "paid_use_end=min(platform_authorization_end,contractual_usage_end)",
  "reminders_days": [
    30,
    14,
    7,
    1
  ]
}
```
**Sources:** [TT05] Differences between affiliate mass authorization and video code authorization — TikTok for Business Help Center (https://ads.tiktok.com/help/article/differences-between-affiliate-creative-authorization-and-video-code); [TT06] How to create Spark Ads for Manual and Search Campaigns — TikTok for Business Help Center (https://ads.tiktok.com/help/article/spark-ads-creation-guide); [UGC03] TikTok Spark Ads Setup Guide (2026) — Insense (https://insense.pro/blog/tiktok-spark-ads)

## FULFILL-001 — Regular TikTok Shop orders require timely carrier scan
- **Domain:** `fulfillment`
- **Rule type:** `official_hard_rule`
- **Severity:** `critical`

**Applicability**
- TikTok Shop US regular orders

**Required conditions**
- A regular order is placed

**Expected behavior**
- Use supported logistics and obtain carrier scan within current policy; observed policy states two business days

**Prohibited behavior**
- Promising or operating fulfillment that cannot meet policy
- Marking shipped without real scan

**Unknown behavior**
- Missing order type or scan timestamp returns fulfillment_status_unknown

**Exceptions**
- Made-to-order/backorder/custom orders use separate logic

**Common failure modes**
- Inactive tracking
- Weekend logic wrong
- Order type misclassified

**Expert-review trigger**
- Unsupported carrier
- High late-dispatch rate
- Order type unclear

**Seller-facing explanation**  
Do not approve aggressive shipping language unless the fulfillment process can produce the required scan.

**Creator-facing correction**  
Please avoid dispatch promises the seller has not confirmed for this product and order type.

**Implementation**
```json
{
  "rule": "regular_order_scan_due=order_created_at+2_business_days",
  "policy_version_required": true
}
```
**Sources:** [TT09] TikTok Shop Fulfillment Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=3995852763301633)

## FULFILL-002 — Made-to-order and personalized products require configured handling-time logic
- **Domain:** `fulfillment`
- **Rule type:** `official_hard_rule`
- **Severity:** `critical`

**Applicability**
- Made-to-order
- customized
- personalized
- backorder

**Required conditions**
- Product is not regular in-stock

**Expected behavior**
- Configure accurate handling time
- Observed guidance used handling time +1 business day for dispatch and +5 for delivery

**Prohibited behavior**
- Treating personalized production as regular stock
- Promising faster date without reasonable basis

**Unknown behavior**
- Missing production/handling/carrier evidence returns cannot_promise_delivery

**Exceptions**
- Current Seller Center configuration controls

**Common failure modes**
- POD production omitted
- Personalization review delay omitted
- Peak season ignored

**Expert-review trigger**
- Peak season
- Provider SLA unstable
- Policy version changed

**Seller-facing explanation**  
Personalized and made-to-order products need a separate handling model. Do not use regular-stock promises.

**Creator-facing correction**  
Please avoid a delivery promise until the seller confirms approval, production, handling and carrier time.

**Implementation**
```json
{
  "rule": "block delivery_claim unless handling_time_configured and production_sla_verified and carrier_sla_verified"
}
```
**Sources:** [TT09] TikTok Shop Fulfillment Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=3995852763301633); [FTC05] Mail, Internet, or Telephone Order Merchandise Rule — Federal Trade Commission (https://www.ftc.gov/legal-library/browse/rules/mail-internet-or-telephone-order-merchandise-rule); [POD01] How do I review orders with personalized products? — Printify Help Center (https://help.printify.com/hc/en-us/articles/28903834238097-How-do-I-review-orders-with-personalized-products)

## FULFILL-003 — Account fulfillment health is a launch and scale constraint
- **Domain:** `fulfillment`
- **Rule type:** `operational_hard_constraint`
- **Severity:** `critical`

**Applicability**
- TikTok Shop seller governance

**Required conditions**
- Seller fulfills orders at scale

**Expected behavior**
- Import current LDR, OTDR, seller-fault cancellation and policy thresholds
- Treat rising risk as a scale blocker

**Prohibited behavior**
- Recommending scale while account health is unknown or breached

**Unknown behavior**
- Without account metrics show seller_account_health_unknown

**Exceptions**
- Metric definitions and exclusions may change

**Common failure modes**
- No denominator
- Average shipping days only
- Multiple warehouses hide cause

**Expert-review trigger**
- Metric near enforcement threshold
- Data export incomplete

**Seller-facing explanation**  
Creative scaling is unsafe when fulfillment health is deteriorating. Connect account metrics or keep the recommendation conditional.

**Creator-facing correction**  
Please do not promise fast fulfillment while the seller resolves dispatch or delivery issues.

**Implementation**
```json
{
  "rule": "scale_blocker when current metric breaches current platform threshold",
  "policy_version_required": true
}
```
**Sources:** [TT09] TikTok Shop Fulfillment Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=3995852763301633)

## FTC-CLAIM-001 — Objective advertising claims require a reasonable basis before publication
- **Domain:** `claims_disclosures`
- **Rule type:** `official_hard_rule`
- **Severity:** `blocker`

**Applicability**
- US-facing product advertising
- creator scripts
- landing pages
- listings

**Required conditions**
- Statement is objectively verifiable

**Expected behavior**
- Collect evidence before approval
- Match exact wording, product, population, conditions and outcome

**Prohibited behavior**
- Publishing efficacy, durability, savings, safety or performance claims without adequate substantiation

**Unknown behavior**
- Absent evidence returns insufficient_evidence and suppresses the claim

**Exceptions**
- Subjective opinions/puffery may differ; borderline claims require review

**Common failure modes**
- Supplier claim copied
- Evidence for another model
- Anecdote generalized

**Expert-review trigger**
- High-stakes claim
- Study quality disputed
- Comparative superiority

**Seller-facing explanation**  
Provide the evidence before Viraldy marks an objective claim usable.

**Creator-facing correction**  
Please describe only what you observed and avoid turning it into a universal promise.

**Implementation**
```json
{
  "rule": "block objective_claim unless substantiation adequate_for_exact_claim"
}
```
**Sources:** [FTC04] Health Products Compliance Guidance — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance); [TT10] Misleading and false content — TikTok Advertising Policies (https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content)

## FTC-HEALTH-001 — Health and safety claims require specialized substantiation review
- **Domain:** `claims_disclosures`
- **Rule type:** `official_hard_rule`
- **Severity:** `blocker`

**Applicability**
- Health, beauty physiological, wellness, safety and device claims

**Required conditions**
- Creative states or implies health, disease, physiological or safety outcome

**Expected behavior**
- Route to specialist review and require evidence appropriate to exact claim

**Prohibited behavior**
- Disease/cure/prevention or safety guarantee without adequate evidence
- Using testimonials as clinical proof

**Unknown behavior**
- No vetted evidence returns expert_review_required and claim suppressed

**Exceptions**
- Requirements vary by product and wording

**Common failure modes**
- Before/after used as clinical proof
- Cosmetic benefit drifts to medical claim

**Expert-review trigger**
- Any disease claim
- Child/pregnancy
- Clinical terminology
- Safety guarantee

**Seller-facing explanation**  
Health and safety language is high risk; listing copy or testimonial alone is not enough.

**Creator-facing correction**  
Please remove the medical/safety claim until the seller supplies approved wording and evidence.

**Implementation**
```json
{
  "rule": "always expert_review when health_or_safety_claim=true; default suppress"
}
```
**Sources:** [FTC04] Health Products Compliance Guidance — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance); [TT19] Prohibited Products Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=1399532709988097); [TT20] Restricted Products Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=3238037484275457)

## FTC-REVIEW-001 — Fake, conditioned, insider or suppressed reviews are prohibited
- **Domain:** `seller_governance`
- **Rule type:** `official_hard_rule`
- **Severity:** `blocker`

**Applicability**
- Reviews
- testimonials
- creator seeding
- incentive programs

**Required conditions**
- Seller solicits, imports, generates or highlights reviews

**Expected behavior**
- Use genuine experience
- Disclose insider connection
- Do not condition incentive on sentiment
- Preserve negative reviews absent valid moderation reason

**Prohibited behavior**
- Fake/AI review
- Non-user testimonial
- Paying for positive sentiment
- Undisclosed insider review
- Review suppression

**Unknown behavior**
- Unknown reviewer experience/incentive means review_provenance_unknown and cannot be used as proof

**Exceptions**
- Neutral incentive can be contextual but cannot require positive sentiment

**Common failure modes**
- 5 stars for refund
- AI testimonial
- Employee review without disclosure

**Expert-review trigger**
- Review-program design
- Insider relationship
- Imported source unclear

**Seller-facing explanation**  
Social proof must come from real experiences and cannot be purchased on the condition that it is positive.

**Creator-facing correction**  
Please use only a genuine, disclosed experience and do not imply broader consensus than the evidence supports.

**Implementation**
```json
{
  "rule": "block when review.provenance!=verified or incentive.conditioned_on_sentiment=true"
}
```
**Sources:** [FTC03] Final Rule Banning Fake Reviews and Testimonials — Federal Trade Commission (https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials)

## FTC-SHIP-001 — Shipping promises need a reasonable basis and delay handling
- **Domain:** `fulfillment`
- **Rule type:** `official_hard_rule`
- **Severity:** `blocker`

**Applicability**
- US online orders
- TikTok Shop
- POD
- dropshipping

**Required conditions**
- Seller states or implies shipping/delivery time

**Expected behavior**
- Have a reasonable basis for stated time
- Follow delay consent/refund procedures
- Include production and handling

**Prohibited behavior**
- Invented delivery date
- Ignoring known supplier delay
- Using best-case transit as universal

**Unknown behavior**
- If route/production/carrier evidence is missing, do not generate a delivery promise

**Exceptions**
- Platform fulfillment requirements may be stricter

**Common failure modes**
- Creator sample shipped express
- Production time omitted
- Customs ignored

**Expert-review trigger**
- Peak season
- Cross-border customs
- Backorder/MTO

**Seller-facing explanation**  
Only promise timing that can be supported across production, handling and transit.

**Creator-facing correction**  
Please remove the delivery promise or use seller-approved timing that includes production and handling.

**Implementation**
```json
{
  "rule": "block shipping_claim unless current route evidence and seller confirmation exist"
}
```
**Sources:** [FTC05] Mail, Internet, or Telephone Order Merchandise Rule — Federal Trade Commission (https://www.ftc.gov/legal-library/browse/rules/mail-internet-or-telephone-order-merchandise-rule); [TT09] TikTok Shop Fulfillment Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=3995852763301633)

## POD-PERS-001 — Personalization input must be explicit, preserved and approved before production
- **Domain:** `pod_personalization`
- **Rule type:** `operational_hard_constraint`
- **Severity:** `critical`

**Applicability**
- POD personalized product
- custom gift
- TikTok Shop made-to-order

**Required conditions**
- Buyer supplies name, date, photo, message, size, color, font or layout

**Expected behavior**
- Capture exact input and template version
- Generate final preview
- Require seller/buyer approval before production where workflow requires

**Prohibited behavior**
- Auto-correcting/truncating/substituting personalization without authorization
- Bypassing review

**Unknown behavior**
- Ambiguous character, unsupported symbol or low-resolution image returns personalization_clarification_required

**Exceptions**
- Seller-approved capitalization/layout rules may apply if disclosed

**Common failure modes**
- O/0 ambiguity
- Name clipped
- Unsupported emoji
- Creator demonstrates different checkout flow

**Expert-review trigger**
- Ambiguous input
- Photo rights/quality issue
- Design cannot fit template

**Seller-facing explanation**  
The buyer’s personalization is part of the product. Treat it as production data, not optional copy.

**Creator-facing correction**  
Please show the exact seller-approved personalization flow and do not promise unsupported fonts, symbols or layouts.

**Implementation**
```json
{
  "rule": "production_ready=false until personalization_preview_approved_at exists",
  "required_fields": [
    "buyer_input_snapshot",
    "template_version",
    "preview_asset_id",
    "approval_record"
  ]
}
```
**Sources:** [POD01] How do I review orders with personalized products? — Printify Help Center (https://help.printify.com/hc/en-us/articles/28903834238097-How-do-I-review-orders-with-personalized-products); [POD04] How do I set up product personalization? — Printify Help Center (https://help.printify.com/hc/en-us/articles/29856933892241-How-do-I-set-up-product-personalization); [TT09] TikTok Shop Fulfillment Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=3995852763301633)

## POD-PERS-002 — Creative must distinguish example personalization from the buyer’s final item
- **Domain:** `pod_personalization`
- **Rule type:** `established_best_practice`
- **Severity:** `high`

**Applicability**
- POD listing
- UGC demo
- gift reaction

**Required conditions**
- Sample/mockup displays an example name or message

**Expected behavior**
- Make clear that displayed personalization is an example
- Show ordering limits accurately

**Prohibited behavior**
- Implying every buyer receives the example design
- Hiding material limitations

**Unknown behavior**
- If checkout flow is unverified, personalization_flow_unknown

**Exceptions**
- One example can demonstrate format when custom nature is clear

**Common failure modes**
- Creator says choose anything despite limits
- No example label
- Different font in production

**Expert-review trigger**
- Complex options
- Language support unclear
- No preview

**Seller-facing explanation**  
Show what is customizable, the limits, and which text is only an example.

**Creator-facing correction**  
Please say the displayed name is an example and show the approved customization steps and limits.

**Implementation**
```json
{
  "rule": "flag when personalization_example_present and example_disclosure_missing"
}
```
**Sources:** [POD04] How do I set up product personalization? — Printify Help Center (https://help.printify.com/hc/en-us/articles/29856933892241-How-do-I-set-up-product-personalization); [POD01] How do I review orders with personalized products? — Printify Help Center (https://help.printify.com/hc/en-us/articles/28903834238097-How-do-I-review-orders-with-personalized-products)

## POD-MOCK-001 — Mockups are not proof of exact physical color, texture, placement or quality
- **Domain:** `pod_personalization`
- **Rule type:** `operational_hard_constraint`
- **Severity:** `high`

**Applicability**
- POD listing
- campaign planning
- creator brief
- paid test

**Required conditions**
- Creative relies on generated mockup

**Expected behavior**
- Verify print area, scale, color, texture and production method
- Use physical sample for proof-heavy claims

**Prohibited behavior**
- Treating mockup as conclusive proof
- Using AI mockup to certify physical quality

**Unknown behavior**
- Without sample/provider evidence return mockup_only_unverified

**Exceptions**
- Minor production variation can remain after sampling

**Common failure modes**
- Embroidery texture invented
- Placement perfect digitally but not physically
- AOP seam assumed exact

**Expert-review trigger**
- Paid campaign without sample
- Color-critical design
- Embroidery/AOP

**Seller-facing explanation**  
A mockup explains the concept, but it does not prove exact color, texture, scale or placement.

**Creator-facing correction**  
Please replace mockup close-ups with footage of the physical item before making quality or finish claims.

**Implementation**
```json
{
  "rule": "proof_status=insufficient when only_evidence_type=mockup and claim_dimension in [exact_color,texture,placement,quality]"
}
```
**Sources:** [POD02] How can I create mockups for Early Access Catalog products? — Printify Help Center (https://help.printify.com/hc/en-us/articles/25641196380817-How-can-I-create-mockups-for-Early-Access-Catalog-products); [POD03] Why does my product look different from the mockup? — Printify Help Center (https://help.printify.com/hc/en-us/articles/4483617784721-Why-does-my-product-look-different-from-the-mockup); [COM04] Mockup tool and printed product mismatch — Reddit r/printondemand (https://www.reddit.com/r/printondemand/comments/1t7d1dl/avoid_fourthwall_their_mockup_tool_and_printed/)

## POD-SAMPLE-001 — Physical sample review is default before proof-heavy paid POD creative
- **Domain:** `pod_personalization`
- **Rule type:** `established_best_practice`
- **Severity:** `high`

**Applicability**
- POD paid ad
- Spark
- creator seeding
- new provider/SKU

**Required conditions**
- Creative depends on physical quality, fit, color, print, packaging or reaction

**Expected behavior**
- Inspect exact product/variant where feasible
- Record provider/template/batch and sample evidence

**Prohibited behavior**
- Representing mockup quality as verified
- Large sample seeding before inspecting exact unit

**Unknown behavior**
- No sample permits only concept-level test; keep physical proof blocked

**Exceptions**
- Digital ideation can proceed without sample

**Common failure modes**
- Different sample variant
- Creator receives first unit
- No packaging inspection

**Expert-review trigger**
- High sample cost
- Provider changed factory
- Complaint history

**Seller-facing explanation**  
Before paying to amplify quality or gift-reaction creative, inspect the exact item the customer will receive.

**Creator-facing correction**  
Please wait for the seller-approved physical sample before filming close-up quality or reaction proof.

**Implementation**
```json
{
  "rule": "paid_test_readiness<=structural_only when physical_sample_status!=verified and proof_heavy=true"
}
```
**Sources:** [POD02] How can I create mockups for Early Access Catalog products? — Printify Help Center (https://help.printify.com/hc/en-us/articles/25641196380817-How-can-I-create-mockups-for-Early-Access-Catalog-products); [POD03] Why does my product look different from the mockup? — Printify Help Center (https://help.printify.com/hc/en-us/articles/4483617784721-Why-does-my-product-look-different-from-the-mockup); [COM04] Mockup tool and printed product mismatch — Reddit r/printondemand (https://www.reddit.com/r/printondemand/comments/1t7d1dl/avoid_fourthwall_their_mockup_tool_and_printed/)

## POD-IP-001 — POD artwork requires trademark and copyright clearance
- **Domain:** `pod_personalization`
- **Rule type:** `official_hard_rule`
- **Severity:** `blocker`

**Applicability**
- POD art
- personalized template
- niche/occasion design

**Required conditions**
- Design contains words, logos, characters, art, photos or third-party reference

**Expected behavior**
- Search relevant word/image marks
- Verify ownership/license
- Retain provenance

**Prohibited behavior**
- Unauthorized protected content
- Confusingly similar mark
- Customer upload used without rights

**Unknown behavior**
- Automated image search is supplemental; uncertain result becomes clearance_unknown

**Exceptions**
- Fair use, parody and public domain are fact-specific

**Common failure modes**
- Popular quote assumed free
- Sports/team design
- AI near-copy

**Expert-review trigger**
- Similar mark found
- Fan art/parody
- Customer image rights unclear

**Seller-facing explanation**  
Trend popularity is not permission. Clear the words, images, characters and logos before listing.

**Creator-facing correction**  
Please replace or document authorization for every third-party element.

**Implementation**
```json
{
  "rule": "block listing_ready until ip_clearance_status in [verified_owned,verified_licensed,approved_after_legal_review]"
}
```
**Sources:** [USPTO01] Trademark Search System Updates — United States Patent and Trademark Office (https://www.uspto.gov/trademarks/search/trademark-search-system-updates); [USPTO02] Likelihood of Confusion — United States Patent and Trademark Office (https://www.uspto.gov/trademarks/search/likelihood-confusion); [USCO01] Visual Artists: Copyright Basics — U.S. Copyright Office (https://www.copyright.gov/engage/visual-artists/); [TT14] TikTok Shop Intellectual Property Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837901778306818)

## DROP-SUP-001 — Seller remains accountable for supplier fulfillment and customer experience
- **Domain:** `dropshipping`
- **Rule type:** `operational_hard_constraint`
- **Severity:** `critical`

**Applicability**
- Dropshipping
- supplier-fulfilled TikTok Shop

**Required conditions**
- Third party stores/packs/ships item

**Expected behavior**
- Maintain QC, inventory, tracking, returns and escalation
- Monitor supplier performance

**Prohibited behavior**
- Treating supplier error as outside seller responsibility
- Scaling without recovery process

**Unknown behavior**
- No supplier performance data returns supplier_reliability_unknown

**Exceptions**
- Marketplace-managed fulfillment can change responsibilities

**Common failure modes**
- Wrong item
- Poor packaging
- Inactive tracking
- No refund path

**Expert-review trigger**
- Repeated wrong/missing order
- No return path
- Supplier identity changes

**Seller-facing explanation**  
The customer bought from the seller, so supplier risk is seller risk.

**Creator-facing correction**  
Please avoid certainty about quality or delivery until the seller verifies the exact supplier and route.

**Implementation**
```json
{
  "rule": "priority_scale=false when supplier_score.status in [unknown,failing]"
}
```
**Sources:** [DS01] Dropshipping Fulfillment: The Complete Guide (2026) — Shopify (https://www.shopify.com/blog/dropshipping-fulfillment); [DS02] How To Start an Online Store Without Inventory (2026) — Shopify (https://www.shopify.com/blog/how-to-start-an-online-store-without-inventory); [COM06] Wrong item from dropshipping supplier — Reddit r/dropshipping (https://www.reddit.com/r/dropshipping/comments/1sirqc6/how_do_you_verify_product_quality_before_it_ships/)

## DROP-SUP-002 — Test the exact supplier SKU/variant before proof-led promotion
- **Domain:** `dropshipping`
- **Rule type:** `established_best_practice`
- **Severity:** `critical`

**Applicability**
- Dropshipping demo
- listing
- creator sample

**Required conditions**
- Product is externally sourced with multiple models/variants

**Expected behavior**
- Order and inspect exact model, color, materials, accessories, packaging and function

**Prohibited behavior**
- Assuming supplier image or different sample represents customer unit

**Unknown behavior**
- No exact-variant testing means demo/quality/compatibility unverified

**Exceptions**
- Low-risk commodity may use lighter sampling with uncertainty shown

**Common failure modes**
- Sample from one supplier, fulfillment from another
- Silent model substitution

**Expert-review trigger**
- Electrical/safety product
- High return risk
- Supplier substitution

**Seller-facing explanation**  
Test the exact model and fulfillment source you will sell, not a visually similar listing.

**Creator-facing correction**  
Please film only the seller-approved exact sample and keep claims within what was tested.

**Implementation**
```json
{
  "rule": "block demo_proof when sample.supplier_sku!=listing.supplier_sku or exact_variant_verified!=true"
}
```
**Sources:** [DS03] Product Sourcing Guide: How To Get Started (2026) — Shopify (https://www.shopify.com/blog/product-sourcing-apps); [DS04] How Does Alibaba Work? Buying and Safety Guide (2026) — Shopify (https://www.shopify.com/blog/16665772-alibaba-101-how-to-safely-source-products-from-the-worlds-biggest-supplier-directory); [COM06] Wrong item from dropshipping supplier — Reddit r/dropshipping (https://www.reddit.com/r/dropshipping/comments/1sirqc6/how_do_you_verify_product_quality_before_it_ships/)

## DROP-COMP-001 — Compatibility claims require exact models and conditions
- **Domain:** `dropshipping`
- **Rule type:** `official_hard_rule`
- **Severity:** `blocker`

**Applicability**
- Accessories
- replacement parts
- size/fit
- device/vehicle compatibility

**Required conditions**
- Creative says fits, works with, supports or replaces another product/model

**Expected behavior**
- List exact supported models/conditions from verified evidence
- Demonstrate only verified compatibility

**Prohibited behavior**
- Fits all or implied universal compatibility without evidence

**Unknown behavior**
- Unknown coverage returns compatibility_unknown

**Exceptions**
- Universal product can be described as such only with adequate evidence

**Common failure modes**
- One model generalized
- Variant changes compatibility
- Supplier title overstates coverage

**Expert-review trigger**
- Safety-critical fit
- Electrical voltage/plug
- Vehicle part
- Child/pet safety

**Seller-facing explanation**  
Compatibility is a product fact. Confirm exact models and conditions before using it as a hook.

**Creator-facing correction**  
Please name only verified compatible models or remove the universal-fit statement.

**Implementation**
```json
{
  "rule": "block compatibility_claim unless compatibility_matrix.source_status=verified"
}
```
**Sources:** [TT08] TikTok Shop Content Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837891779151617); [TT10] Misleading and false content — TikTok Advertising Policies (https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content); [DS04] How Does Alibaba Work? Buying and Safety Guide (2026) — Shopify (https://www.shopify.com/blog/16665772-alibaba-101-how-to-safely-source-products-from-the-worlds-biggest-supplier-directory)

## DROP-STOCK-001 — Supplier stock, price and shipping cost must be refreshed before activation/scale
- **Domain:** `dropshipping`
- **Rule type:** `operational_hard_constraint`
- **Severity:** `high`

**Applicability**
- Dropshipping
- supplier marketplace

**Required conditions**
- External supplier controls cost, stock or shipping

**Expected behavior**
- Capture timestamped stock, unit cost, shipping cost, destination and lead time
- Recheck before samples and scale

**Prohibited behavior**
- Treating old supplier snapshot as current
- Approving demand without stock/margin check

**Unknown behavior**
- No feed means stale after seller-defined threshold; no universal interval

**Exceptions**
- Reserved inventory/contract price can reduce volatility

**Common failure modes**
- Stockout after order
- Shipping jump
- Destination cost ignored

**Expert-review trigger**
- No feed
- Single-source dependency
- Material price change

**Seller-facing explanation**  
Supplier data is perishable. Recheck stock and landed cost before approving samples or increasing spend.

**Creator-facing correction**  
Please avoid stock, price, delivery or quality statements until the seller refreshes supplier data.

**Implementation**
```json
{
  "rule": "block scale when supplier_snapshot.age>workspace.supplier_freshness_threshold or landed_cost_current=false"
}
```
**Sources:** [DS05] Product sourcing and supplier monitoring documentation — AutoDS Help Center (https://help.autods.com/); [COM05] Supplier stock and price changes — Reddit r/dropshipping (https://www.reddit.com/r/dropshipping/comments/1u9gt9c/how_do_you_track_supplier_stock_and_price_changes/); [COM07] Unexpected shipping cost and low supplier stock — Reddit r/dropshipping (https://www.reddit.com/r/dropshipping/comments/1q15jg9/unexpected_aliexpress_shipping_costs_and_low/)

## DROP-SHIP-001 — Shipping statements must use the customer route, not the creator sample route
- **Domain:** `dropshipping`
- **Rule type:** `operational_hard_constraint`
- **Severity:** `critical`

**Applicability**
- Dropshipping page
- creator script
- TikTok Shop content

**Required conditions**
- Content mentions arrival, fast shipping, local warehouse or delivery date

**Expected behavior**
- Model production, handling, carrier and customs by destination
- Use seller-approved range

**Prohibited behavior**
- Using express creator sample as proof of customer delivery
- Ignoring production/warehouse difference

**Unknown behavior**
- Unknown route means remove claim and return shipping_route_unknown

**Exceptions**
- Variants/geographies can require separate versions

**Common failure modes**
- US warehouse not reserved
- Transit excludes handling
- Creator got express package

**Expert-review trigger**
- Cross-border customs
- Split shipment
- Warehouse switching

**Seller-facing explanation**  
A creator’s sample delivery is not proof of customer delivery time. Use the actual customer route.

**Creator-facing correction**  
Please remove the sample-arrival statement until the seller confirms customer fulfillment timing.

**Implementation**
```json
{
  "rule": "block shipping_speed_claim when creator_sample_route!=customer_route and customer_route_evidence!=verified"
}
```
**Sources:** [DS01] Dropshipping Fulfillment: The Complete Guide (2026) — Shopify (https://www.shopify.com/blog/dropshipping-fulfillment); [DS02] How To Start an Online Store Without Inventory (2026) — Shopify (https://www.shopify.com/blog/how-to-start-an-online-store-without-inventory); [FTC05] Mail, Internet, or Telephone Order Merchandise Rule — Federal Trade Commission (https://www.ftc.gov/legal-library/browse/rules/mail-internet-or-telephone-order-merchandise-rule); [TT09] TikTok Shop Fulfillment Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=3995852763301633)

## ECON-001 — Paid-test and sample readiness require current contribution economics
- **Domain:** `seller_economics`
- **Rule type:** `operational_hard_constraint`
- **Severity:** `critical`

**Applicability**
- Paid test
- Spark
- sample allocation
- POD
- dropshipping

**Required conditions**
- Viraldy recommends spend, sample, commission or scale

**Expected behavior**
- Calculate price minus COGS, production/personalization, shipping subsidy, fees, commission, expected returns, sample/creator/ad cost
- Show sensitivity and missing inputs

**Prohibited behavior**
- Calling scale-ready from GMV or creative score alone
- Inventing universal margin threshold

**Unknown behavior**
- Missing material cost returns economics_insufficient and withholds recommendation

**Exceptions**
- Seller can choose a capped learning loss if explicitly approved

**Common failure modes**
- GMV mistaken for profit
- Returns omitted
- Supplier cost stale
- Sample cost ignored

**Expert-review trigger**
- Negative/uncertain contribution
- Loss-leader decision
- Inventory financing

**Seller-facing explanation**  
Viraldy cannot recommend paid scale until it knows what one order contributes after major costs.

**Creator-facing correction**  
The creative may be usable, but paid activation remains conditional until the seller confirms economics.

**Implementation**
```json
{
  "rule": "paid_test_readiness=insufficient when required economics missing",
  "required_fields": [
    "price",
    "COGS",
    "fulfillment_cost",
    "fees",
    "commission",
    "expected_refund_cost",
    "sample_cost",
    "creator_fee"
  ]
}
```
**Sources:** [DS01] Dropshipping Fulfillment: The Complete Guide (2026) — Shopify (https://www.shopify.com/blog/dropshipping-fulfillment); [DS02] How To Start an Online Store Without Inventory (2026) — Shopify (https://www.shopify.com/blog/how-to-start-an-online-store-without-inventory); [COM01] 30 samples sent, no sale — Reddit r/TikTokshop (https://www.reddit.com/r/TikTokshop/comments/1ux5rk0/30_samples_sent_no_sale/); [COM02] 1.4M-view affiliate video with weak sales — Reddit r/TikTokshop (https://www.reddit.com/r/TikTokshop/comments/1lgdfzj/our_tiktok_affiliate_video_went_viral_14m_views/)

## UGC-BRIEF-001 — Creator brief must define product truth, objective, deliverables, constraints and approval scope
- **Domain:** `ugc_production`
- **Rule type:** `established_best_practice`
- **Severity:** `high`

**Applicability**
- UGC brief
- affiliate
- paid UGC
- Spark-ready production

**Required conditions**
- Seller requests creator content

**Expected behavior**
- Provide exact product, buyer/problem, approved claims, must-show facts, deliverables, format, deadline, tag/disclosure, rights and revisions
- Version the brief

**Prohibited behavior**
- Vague make-it-viral request
- Leaving rights/claims/deliverables unstated

**Unknown behavior**
- Missing fields stay unknown; ask just-in-time questions

**Exceptions**
- Small organic collaboration can use lighter brief but product truth/disclosure/deliverable/rights remain clear

**Common failure modes**
- No objective
- No exact SKU
- No rights term
- No claim list

**Expert-review trigger**
- High-risk claim
- Personalization incomplete
- Rights/revision dispute

**Seller-facing explanation**  
A usable brief controls product truth and test design while leaving room for creator voice.

**Creator-facing correction**  
Please confirm the exact product, deliverables, approved claims, disclosure, CTA/tag, deadline and usage terms before filming.

**Implementation**
```json
{
  "rule": "brief incomplete if any hard_required field missing",
  "hard_required": [
    "product_id",
    "objective",
    "deliverables",
    "approved_claims",
    "prohibited_claims",
    "disclosure",
    "rights_request",
    "deadline"
  ]
}
```
**Sources:** [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief); [PERF08] Guide to Creating an Effective Creative Brief — Foreplay (https://www.foreplay.co/post/guide-to-creating-an-effective-creative-brief); [PERF09] Creative Strategy Platform Synergies — Foreplay (https://www.foreplay.co/post/creative-strategy-platform-synergies)

## UGC-BRIEF-002 — Guide the outcome without scripting away creator authenticity
- **Domain:** `ugc_production`
- **Rule type:** `contextual_guideline`
- **Severity:** `medium`

**Applicability**
- Creator-led UGC
- affiliate video
- native-style ad

**Required conditions**
- Seller chooses brief precision

**Expected behavior**
- Specify product truths, evidence and hypothesis
- Let creator adapt wording, setting and delivery within flexible zones

**Prohibited behavior**
- Forcing every word/reaction
- Giving no direction

**Unknown behavior**
- Unknown creator capability means use checkpoints, not assumptions

**Exceptions**
- Regulated claims and technical demos can require exact lines

**Common failure modes**
- Robotic readout
- Fake reaction
- Vague brief omits mechanism

**Expert-review trigger**
- Creator repeatedly misses hard requirements
- Legal wording exact
- Brand voice conflict

**Seller-facing explanation**  
The brief should control product truth, not manufacture a fake personality.

**Creator-facing correction**  
Keep required facts and scenes, but use your natural voice unless a line is marked exact.

**Implementation**
```json
{
  "prompt_overlay": "separate exact_requirements from creator_flexible_zones"
}
```
**Sources:** [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief); [UGC05] UGC Brief Template and Production Guidance — Billo (https://billo.app/blog/ugc-brief-template/); [PERF03] How to Make Ads for Meta and TikTok in 2026 — Motion / Savannah Sanchez (https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026)

## UGC-MOD-001 — Modular hooks, raw footage and clean edits are separate contracted deliverables
- **Domain:** `ugc_production`
- **Rule type:** `established_best_practice`
- **Severity:** `medium`

**Applicability**
- Paid UGC
- creative testing
- cross-channel reuse

**Required conditions**
- Seller needs variants or editing flexibility

**Expected behavior**
- Define raw footage, clean base, alternate hooks/CTAs, aspect ratios and captions
- Price and approve each

**Prohibited behavior**
- Assuming one finished video includes unlimited hooks/raw footage/future edits

**Unknown behavior**
- Missing deliverable scope returns deliverable_scope_unknown

**Exceptions**
- Simple affiliate post may need only one deliverable

**Common failure modes**
- Extra hooks requested later
- Music baked into all clips
- No clean CTA

**Expert-review trigger**
- Scope/pricing dispute
- Cross-channel paid use

**Seller-facing explanation**  
One finished video and a modular testing package are different purchases.

**Creator-facing correction**  
Please confirm whether alternate hooks, clean footage, raw clips and CTA versions are included before filming.

**Implementation**
```json
{
  "rule": "requested_item must exist in contracted_deliverables"
}
```
**Sources:** [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief); [UGC04] How to repurpose UGC — Billo (https://billo.app/blog/repurpose-ugc/); [COM08] Brand-side UGC pricing and rights discussion — Reddit r/UGCcreators (https://www.reddit.com/r/UGCcreators/comments/1v6fwqw/im_on_the_brand_side_of_ugc_deals_heres_what/); [COM09] UGC glossary: rights, revisions, raw footage — Reddit r/UGCcreators (https://www.reddit.com/r/UGCcreators/comments/1vat08s/a_glossary_of_common_ugc_terms_for_newer_creators/)

## UGC-REV-001 — Revision rounds and scope must be explicit and tied to approved brief
- **Domain:** `ugc_production`
- **Rule type:** `operational_hard_constraint`
- **Severity:** `high`

**Applicability**
- Paid UGC
- flat-fee collaboration
- agency campaign

**Required conditions**
- Seller can request revisions

**Expected behavior**
- Define included rounds, review windows, fixable issues and reshoot triggers
- Compare each request with approved brief

**Prohibited behavior**
- Unlimited revisions by assumption
- Retroactive brief change treated as creator error

**Unknown behavior**
- Missing contract terms means clarify, not declare entitlement

**Exceptions**
- Platform-specific flat-fee mechanics can differ from private contracts

**Common failure modes**
- New angle requested after draft
- Feedback not timecoded
- Review window lapses

**Expert-review trigger**
- Scope dispute
- Reshoot cost
- More than contracted rounds

**Seller-facing explanation**  
A revision fixes a missed agreed requirement; a new concept or extra deliverable can be new scope.

**Creator-facing correction**  
Please revise the listed brief deviations. New concepts or deliverables should be agreed separately.

**Implementation**
```json
{
  "rule": "classify change as in_scope_fix|optional_optimization|new_scope|reshoot_required"
}
```
**Sources:** [COM08] Brand-side UGC pricing and rights discussion — Reddit r/UGCcreators (https://www.reddit.com/r/UGCcreators/comments/1v6fwqw/im_on_the_brand_side_of_ugc_deals_heres_what/); [COM09] UGC glossary: rights, revisions, raw footage — Reddit r/UGCcreators (https://www.reddit.com/r/UGCcreators/comments/1vat08s/a_glossary_of_common_ugc_terms_for_newer_creators/)

## UGC-REV-002 — Revision feedback must be expected-versus-observed and actionable
- **Domain:** `ugc_production`
- **Rule type:** `established_best_practice`
- **Severity:** `medium`

**Applicability**
- UGC Preflight
- seller-to-creator feedback

**Required conditions**
- Draft needs change

**Expected behavior**
- State expected, observed, evidence/timestamp, why it matters, exact correction and editability

**Prohibited behavior**
- Make it viral/catchier/more authentic without observable correction

**Unknown behavior**
- No reliable evidence means suggestion, not blocker

**Exceptions**
- Subjective preferences remain optional or contract-specific

**Common failure modes**
- Too many equal-priority notes
- Contradictory feedback
- No edit/reshoot distinction

**Expert-review trigger**
- Creator challenges evidence
- No source brief
- Concept would materially change

**Seller-facing explanation**  
Each blocker should show what was expected, what was observed and the smallest useful fix.

**Creator-facing correction**  
Please make the required changes below; optional improvements are separated from blockers.

**Implementation**
```json
{
  "required_output_fields": [
    "requirement_id",
    "expected",
    "observed",
    "evidence_id",
    "severity",
    "editability",
    "correction"
  ]
}
```
**Sources:** [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief); [PERF03] How to Make Ads for Meta and TikTok in 2026 — Motion / Savannah Sanchez (https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026); [PERF09] Creative Strategy Platform Synergies — Foreplay (https://www.foreplay.co/post/creative-strategy-platform-synergies)

## UGC-RIGHTS-001 — Usage rights must specify exact asset, channels, paid use, duration, geography and editing
- **Domain:** `rights_spark`
- **Rule type:** `operational_hard_constraint`
- **Severity:** `blocker`

**Applicability**
- Paid UGC
- Spark
- Meta/website/email reuse
- whitelisting

**Required conditions**
- Seller wants reuse, editing or amplification

**Expected behavior**
- Record channels, organic/paid scope, duration, geography, editing, raw footage, Spark/whitelisting, asset IDs, compensation and proof

**Prohibited behavior**
- Assuming payment or posting transfers all rights
- Using outside agreed scope

**Unknown behavior**
- Missing term returns rights_incomplete and blocks paid/multi-channel readiness

**Exceptions**
- Platform authorization and contract rights are separate

**Common failure modes**
- Usage rights included with no duration
- Raw footage confused with edit rights
- Perpetual use assumed

**Expert-review trigger**
- Perpetual/broad buyout
- Cross-channel
- Creator dispute
- Minor creator

**Seller-facing explanation**  
Viraldy needs a rights record for the exact asset and exact use. A post, file and paid ad are different permissions.

**Creator-facing correction**  
Please confirm channels, duration, paid use, editing, geography and exact assets covered.

**Implementation**
```json
{
  "rule": "paid_ready=false if rights fields missing",
  "required_fields": [
    "asset_ids",
    "channels",
    "paid_use",
    "duration_end",
    "editing_allowed",
    "geography",
    "proof_url"
  ]
}
```
**Sources:** [UGC02] Paid Media UGC: What it is and how to do it — Insense (https://insense.pro/blog/paid-media-ugc); [UGC04] How to repurpose UGC — Billo (https://billo.app/blog/repurpose-ugc/); [COM08] Brand-side UGC pricing and rights discussion — Reddit r/UGCcreators (https://www.reddit.com/r/UGCcreators/comments/1v6fwqw/im_on_the_brand_side_of_ugc_deals_heres_what/); [COM10] Perpetual paid usage requested without compensation — Reddit r/UGCcreators (https://www.reddit.com/r/UGCcreators/comments/1uma3mc/the_amount_of_disrespect/)

## UGC-RIGHTS-002 — Raw footage and derivative editing rights are separate permissions
- **Domain:** `rights_spark`
- **Rule type:** `operational_hard_constraint`
- **Severity:** `high`

**Applicability**
- UGC production
- variant editing

**Required conditions**
- Seller requests raw clips or new edits

**Expected behavior**
- Contract raw delivery and derivative/editing scope explicitly
- Identify creator review for material changes

**Prohibited behavior**
- Assuming file possession grants unlimited editing
- Changing testimonial meaning

**Unknown behavior**
- Unclear edit scope permits storage but blocks publication

**Exceptions**
- Technical edits may be allowed while message changes are not

**Common failure modes**
- New claim inserted
- Creator face paired with unrelated offer
- Raw delivered without edit rights

**Expert-review trigger**
- New claim
- Synthetic voice/face
- Cross-brand use

**Seller-facing explanation**  
Owning a copy of footage is not permission to create any derivative message.

**Creator-facing correction**  
Please confirm what edits are allowed and whether materially changed versions need your approval.

**Implementation**
```json
{
  "rule": "derivative_publish_ready=false unless editing_rights cover requested_transform"
}
```
**Sources:** [UGC02] Paid Media UGC: What it is and how to do it — Insense (https://insense.pro/blog/paid-media-ugc); [UGC04] How to repurpose UGC — Billo (https://billo.app/blog/repurpose-ugc/); [COM09] UGC glossary: rights, revisions, raw footage — Reddit r/UGCcreators (https://www.reddit.com/r/UGCcreators/comments/1vat08s/a_glossary_of_common_ugc_terms_for_newer_creators/)

## UGC-MUSIC-001 — Music/audio rights must cover paid and cross-channel use
- **Domain:** `rights_spark`
- **Rule type:** `official_hard_rule`
- **Severity:** `blocker`

**Applicability**
- Spark
- paid UGC
- cross-platform reuse

**Required conditions**
- Creative contains music or licensed audio

**Expected behavior**
- Use audio authorized for account, paid use, territory and channel
- Maintain clean version when reuse planned

**Prohibited behavior**
- Assuming organic TikTok sound is cleared for paid or off-platform use

**Unknown behavior**
- Unknown audio rights means organic_audio_only or replacement required

**Exceptions**
- Rights differ by platform/account/territory

**Common failure modes**
- Music baked into raw
- No source
- TikTok organic sound reused on Meta

**Expert-review trigger**
- Famous recording
- Remix/sample
- Voice clone
- International paid use

**Seller-facing explanation**  
Organic availability does not automatically clear paid or other-channel use.

**Creator-facing correction**  
Please provide a clean version or seller-approved commercially cleared audio.

**Implementation**
```json
{
  "rule": "cross_channel_paid_ready=false when audio_license does not cover requested channels"
}
```
**Sources:** [UGC04] How to repurpose UGC — Billo (https://billo.app/blog/repurpose-ugc/); [TT14] TikTok Shop Intellectual Property Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837901778306818); [USCO01] Visual Artists: Copyright Basics — U.S. Copyright Office (https://www.copyright.gov/engage/visual-artists/)

## UGC-AUTH-001 — Authentic style does not exempt truth, disclosure or claim rules
- **Domain:** `ugc_production`
- **Rule type:** `contextual_guideline`
- **Severity:** `medium`

**Applicability**
- Creator testimonial
- personal-experience hook

**Required conditions**
- Creative uses personal experience/natural delivery

**Expected behavior**
- Preserve truthful perspective and real use
- Keep all claim/disclosure/product rules

**Prohibited behavior**
- Fabricated experience, reaction or result presented as authentic

**Unknown behavior**
- If creator has not used product, use demonstration/spokesperson format instead of testimonial

**Exceptions**
- Actor/spokesperson can be used if not misleading

**Common failure modes**
- Fake first reaction
- Creator reads seller review as own experience

**Expert-review trigger**
- Testimonial provenance unclear
- Health/financial experience

**Seller-facing explanation**  
Authenticity means the experience is truthful, not merely casual-looking.

**Creator-facing correction**  
Please speak only from your actual experience; use demonstration format when experience is not established.

**Implementation**
```json
{
  "rule": "testimonial_format blocked when creator_product_experience!=verified"
}
```
**Sources:** [FTC01] FTC Endorsement Guides: What People Are Asking — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking); [FTC03] Final Rule Banning Fake Reviews and Testimonials — Federal Trade Commission (https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials); [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief)

## PERF-EVID-001 — Do not label a pattern winning without linked performance evidence
- **Domain:** `performance_creative`
- **Rule type:** `official_hard_rule`
- **Severity:** `high`

**Applicability**
- PatternKit
- Creative DNA
- competitor research
- campaign recommendation

**Required conditions**
- System uses winning/proven/top-performing/causal language

**Expected behavior**
- Link asset IDs, metric definition, date window, spend/distribution, sample size and outcome
- State evidence type

**Prohibited behavior**
- Calling popular, long-running or highly viewed pattern winning without outcomes

**Unknown behavior**
- No evidence means pattern_candidate, observed_structure or test_hypothesis

**Exceptions**
- User opinion can be preserved as opinion

**Common failure modes**
- Views used as sales proof
- One screenshot
- Competitor longevity assumed profitable

**Expert-review trigger**
- Metric provenance missing
- Attribution unclear
- Causal language proposed

**Seller-facing explanation**  
Use “winning” only when linked outcome evidence exists; otherwise it is a candidate worth testing.

**Creator-facing correction**  
This reference is an observed pattern, not proof it will perform for this product.

**Implementation**
```json
{
  "rule": "forbid winning_label unless performance_evidence.status=linked_and_sufficient",
  "fallback_labels": [
    "candidate",
    "observed",
    "directional"
  ]
}
```
**Sources:** [PERF01] Creative Benchmarks 2026 — Motion (https://motionapp.com/library/research/creative-benchmarks-2026/); [PERF07] Offline-to-Online Creative Optimization with Generative Models and Adaptive Testing — Lee et al., arXiv preprint (https://arxiv.org/abs/2607.23696); [COM02] 1.4M-view affiliate video with weak sales — Reddit r/TikTokshop (https://www.reddit.com/r/TikTokshop/comments/1lgdfzj/our_tiktok_affiliate_video_went_viral_14m_views/)

## PERF-CAUSAL-001 — Popularity, spend, longevity and correlation are not causal proof
- **Domain:** `performance_creative`
- **Rule type:** `established_best_practice`
- **Severity:** `high`

**Applicability**
- Competitor watchlist
- benchmark
- Creative DNA

**Required conditions**
- System interprets public or observational signals

**Expected behavior**
- Use signals to prioritize hypotheses
- Separate correlation from causality
- Recommend controlled/sequential test

**Prohibited behavior**
- Claiming an element caused performance because ad was viral/long-running/high-spend

**Unknown behavior**
- Confounded evidence returns directional_pattern with uncertainty

**Exceptions**
- Randomized/lift study can support stronger inference

**Common failure modes**
- Creator audience ignored
- Offer/page changed
- Survivorship bias

**Expert-review trigger**
- Major budget decision from public signal
- Multiple variables changed

**Seller-facing explanation**  
Public signals tell us what to study, not why it worked.

**Creator-facing correction**  
Use the pattern as inspiration, but produce a differentiated test rather than copying a proven formula.

**Implementation**
```json
{
  "rule": "causal_language_allowed only for randomized_experiment or validated_lift_study"
}
```
**Sources:** [PERF01] Creative Benchmarks 2026 — Motion (https://motionapp.com/library/research/creative-benchmarks-2026/); [TT17] About Conversion Lift Study — TikTok for Business Help Center (https://ads.tiktok.com/help/article/about-conversion-lift-study); [PERF07] Offline-to-Online Creative Optimization with Generative Models and Adaptive Testing — Lee et al., arXiv preprint (https://arxiv.org/abs/2607.23696)

## PERF-TEST-001 — Tests should isolate the intended variable or be labeled multivariate
- **Domain:** `performance_creative`
- **Rule type:** `established_best_practice`
- **Severity:** `high`

**Applicability**
- TikTok split test
- ViralKit test matrix

**Required conditions**
- Seller wants to learn effect of hook, angle, creator, offer or format

**Expected behavior**
- Define hypothesis, metric, control/treatment, stable variables, allocation and stop rule

**Prohibited behavior**
- Changing hook, offer, creator, audience, page and budget while attributing result to one factor

**Unknown behavior**
- When isolation is impossible, label multi_change_directional

**Exceptions**
- Multivariate/sequential design is valid if analyzed as such

**Common failure modes**
- Post-hoc hypothesis
- Unequal distribution
- Version changed mid-test

**Expert-review trigger**
- Confounded design
- Metric changed after result
- Insufficient traffic

**Seller-facing explanation**  
A test is useful only when the result answers the question written before launch.

**Creator-facing correction**  
Please keep non-test variables stable while changing the selected element.

**Implementation**
```json
{
  "required_fields": [
    "hypothesis",
    "test_variable",
    "control_asset_id",
    "treatment_asset_ids",
    "primary_metric",
    "allocation",
    "stop_rule",
    "confounders"
  ]
}
```
**Sources:** [TT16] How to create a split test in TikTok Ads Manager — TikTok for Business Help Center (https://ads.tiktok.com/help/article/create-split-test); [PERF04] Creative Iteration for Better Ads — Alison.ai (https://alison.ai/resources/blog/creative-iteration-for-better-ads); [PERF06] Best Practices for Testing Ad Creative — Marpipe (https://www.marpipe.com/blog/best-practices-for-testing-ad-creative)

## PERF-PREFLIGHT-001 — Preflight is a structural filter, not a GMV prediction
- **Domain:** `performance_creative`
- **Rule type:** `established_best_practice`
- **Severity:** `critical`

**Applicability**
- UGC Preflight
- ViralKit ranking

**Required conditions**
- Viraldy scores before live spend

**Expected behavior**
- Catch blockers and prioritize a slate
- Display score type, confidence and evidence
- Validate online

**Prohibited behavior**
- Guaranteeing result
- Selecting certain winner from offline score
- Killing novel idea solely on score

**Unknown behavior**
- Without calibration label score structural, not performance_prediction

**Exceptions**
- Hard compliance blocker can reject without testing

**Common failure modes**
- High score mistaken for GMV forecast
- Model overfits past format

**Expert-review trigger**
- User asks for GMV prediction
- Novel category
- Confidence overstated

**Seller-facing explanation**  
Preflight tells what is structurally ready and what to fix; the market still decides performance.

**Creator-facing correction**  
The draft may be approved for a controlled test after blockers are fixed, but the score is not a sales guarantee.

**Implementation**
```json
{
  "rule": "output must include score_type,confidence,missing_evidence,test_required"
}
```
**Sources:** [PERF07] Offline-to-Online Creative Optimization with Generative Models and Adaptive Testing — Lee et al., arXiv preprint (https://arxiv.org/abs/2607.23696); [PERF01] Creative Benchmarks 2026 — Motion (https://motionapp.com/library/research/creative-benchmarks-2026/); [TT16] How to create a split test in TikTok Ads Manager — TikTok for Business Help Center (https://ads.tiktok.com/help/article/create-split-test)

## PERF-METRIC-001 — Engagement cannot be translated into GMV or profit guarantee
- **Domain:** `performance_creative`
- **Rule type:** `established_best_practice`
- **Severity:** `critical`

**Applicability**
- Research report
- creative experiment
- recommendation

**Required conditions**
- Evidence measures views, watch, clicks, engagement or CTR

**Expected behavior**
- Name exact outcome
- Require commerce metrics for sales/profit conclusion

**Prohibited behavior**
- Reporting engagement lift as GMV, ROAS or profit lift

**Unknown behavior**
- No downstream link returns commerce_outcome_unknown

**Exceptions**
- A validated seller funnel can support leading-indicator use

**Common failure modes**
- CTR winner called conversion winner
- View winner scaled despite negative margin

**Expert-review trigger**
- Revenue forecast from view data
- Attribution gap
- Negative margin

**Seller-facing explanation**  
A creative can win attention and still lose money. Viraldy needs orders, costs, returns and margin to recommend scale.

**Creator-facing correction**  
The creative is ready to test for attention, but no sales claim follows from engagement alone.

**Implementation**
```json
{
  "rule": "gmv_or_profit_label forbidden unless linked orders and complete economics exist"
}
```
**Sources:** [PERF01] Creative Benchmarks 2026 — Motion (https://motionapp.com/library/research/creative-benchmarks-2026/); [PERF07] Offline-to-Online Creative Optimization with Generative Models and Adaptive Testing — Lee et al., arXiv preprint (https://arxiv.org/abs/2607.23696); [COM02] 1.4M-view affiliate video with weak sales — Reddit r/TikTokshop (https://www.reddit.com/r/TikTokshop/comments/1lgdfzj/our_tiktok_affiliate_video_went_viral_14m_views/)

## PERF-SMALL-001 — Sparse data must return uncertainty, not false precision
- **Domain:** `performance_creative`
- **Rule type:** `established_best_practice`
- **Severity:** `high`

**Applicability**
- Benchmarks
- creator ranking
- fatigue
- element analysis

**Required conditions**
- Sample size or outcome count is limited

**Expected behavior**
- Show sample size, completeness, uncertainty and next test
- Use shrinkage/confidence where possible

**Prohibited behavior**
- Precise causal ranking from one/few assets

**Unknown behavior**
- Return insufficient_evidence when analytical conditions are unmet; no universal sample threshold in prompt

**Exceptions**
- Hard structural findings remain valid with asset evidence

**Common failure modes**
- One order defines winner
- Zero conversion after tiny reach kills product

**Expert-review trigger**
- User requests definitive scale/kill
- Outlier dominates
- Missing denominator

**Seller-facing explanation**  
The data is too limited for a strong performance conclusion; use it to design the next test.

**Creator-facing correction**  
The feedback is structural; performance confidence remains low until comparable tests run.

**Implementation**
```json
{
  "rule": "confidence from evidence completeness, comparable count and outcomes; thresholds versioned by metric/design"
}
```
**Sources:** [PERF01] Creative Benchmarks 2026 — Motion (https://motionapp.com/library/research/creative-benchmarks-2026/); [PERF07] Offline-to-Online Creative Optimization with Generative Models and Adaptive Testing — Lee et al., arXiv preprint (https://arxiv.org/abs/2607.23696); [TT16] How to create a split test in TikTok Ads Manager — TikTok for Business Help Center (https://ads.tiktok.com/help/article/create-split-test)

## PERF-FATIGUE-001 — Fatigue requires baseline, comparable window and sufficient volume
- **Domain:** `performance_creative`
- **Rule type:** `established_best_practice`
- **Severity:** `high`

**Applicability**
- Fatigue alerts
- asset/hook/angle monitoring

**Required conditions**
- Metrics decline over time

**Expected behavior**
- Account for spend, audience, seasonality, offer, inventory, page and measurement
- Separate asset/hook/angle/creator/product decline

**Prohibited behavior**
- Calling fatigue from age alone or one-day volatility

**Unknown behavior**
- Insufficient context returns directional_fatigue_signal

**Exceptions**
- Workspace can set operational refresh rules; not universal truth

**Common failure modes**
- Price changed
- Audience expanded
- Attribution delay
- Low volume

**Expert-review trigger**
- Large budget
- Multiple confounders
- No stable baseline

**Seller-facing explanation**  
A falling metric may be fatigue, but it may also be offer, inventory, page, distribution or measurement.

**Creator-facing correction**  
Prepare a refresh while the seller checks non-creative causes.

**Implementation**
```json
{
  "rule": "fatigue cannot exceed directional unless baseline_valid and volume_sufficient and confounders_reviewed"
}
```
**Sources:** [PERF05] Creative Intelligence Reports — Alison.ai (https://alison.ai/resources/creative-intelligence-reports); [PERF01] Creative Benchmarks 2026 — Motion (https://motionapp.com/library/research/creative-benchmarks-2026/); [PERF04] Creative Iteration for Better Ads — Alison.ai (https://alison.ai/resources/blog/creative-iteration-for-better-ads)

## PERF-CONTEXT-001 — Creative guidance must be conditioned on product, buyer, objective and channel
- **Domain:** `performance_creative`
- **Rule type:** `established_best_practice`
- **Severity:** `medium`

**Applicability**
- PatternKit retrieval
- prompt overlay
- recommendation

**Required conditions**
- Generic best practice or benchmark is applied

**Expected behavior**
- Filter by product traits, buyer context, objective, placement, commerce model and evidence
- Show contraindications

**Prohibited behavior**
- Universal format/timing rule regardless of product/context

**Unknown behavior**
- Missing context returns broad low-confidence hypothesis and smallest next question

**Exceptions**
- Official best practice remains starting point, not guarantee

**Common failure modes**
- 3-second heuristic used as policy blocker
- Trend copied despite mismatch

**Expert-review trigger**
- Unusual product
- User asks for universal winner
- Pattern conflicts with policy

**Seller-facing explanation**  
Best practices are starting hypotheses. Viraldy must explain why they fit this product and buyer.

**Creator-facing correction**  
Keep product truth and objective, but adapt pacing and delivery to the creator and product.

**Implementation**
```json
{
  "prompt_overlay_required": [
    "product_traits",
    "buyer_context",
    "objective",
    "channel",
    "commerce_model",
    "evidence_status"
  ]
}
```
**Sources:** [PERF01] Creative Benchmarks 2026 — Motion (https://motionapp.com/library/research/creative-benchmarks-2026/); [PERF02] 2025 DTC Creative Trends: Expert Lightning Round — Motion (https://motionapp.com/library/talk/motion-s-2025-facebook-ad-creative-trends-dtc-expert-lightning-round/); [TT12] Creative best practices for performance ads — TikTok for Business Help Center (https://ads.tiktok.com/help/article/creative-best-practices); [TT15] Creative Codes: Six Principles for TikTok-First Ads — TikTok for Business (https://ads.tiktok.com/business/creativecenter/quicktok/online/TikTokCreativeCodes.pdf)

## PERF-TIME-001 — Hook/product timing is contextual unless the campaign explicitly requires it
- **Domain:** `performance_creative`
- **Rule type:** `contextual_guideline`
- **Severity:** `medium`

**Applicability**
- Brief
- Preflight
- PatternKit

**Required conditions**
- Recommendation mentions first 3/6 seconds or reveal/CTA timing

**Expected behavior**
- Attribute timing to official guidance, PatternKit or campaign requirement
- Only make blocker when brief/contract requires

**Prohibited behavior**
- Presenting one number as universal platform requirement

**Unknown behavior**
- No campaign timing requirement means observation/optimization, not hard failure

**Exceptions**
- Narrative formats can intentionally delay reveal

**Common failure modes**
- Heuristic turned into compliance blocker
- Slow reveal misclassified as policy violation

**Expert-review trigger**
- Timing blocker disputed
- Narrative product
- Guidance updated

**Seller-facing explanation**  
TikTok publishes early-attention guidance, but Viraldy treats it as a hypothesis unless the Campaign Pack makes it a requirement.

**Creator-facing correction**  
The reveal is later than this selected pattern. Move it earlier for this version or keep it as a separate test.

**Implementation**
```json
{
  "rule": "timing issue blocker only when source in [campaign_pack,contract,official_hard_rule]; otherwise optimization"
}
```
**Sources:** [TT12] Creative best practices for performance ads — TikTok for Business Help Center (https://ads.tiktok.com/help/article/creative-best-practices); [TT15] Creative Codes: Six Principles for TikTok-First Ads — TikTok for Business (https://ads.tiktok.com/business/creativecenter/quicktok/online/TikTokCreativeCodes.pdf); [PERF01] Creative Benchmarks 2026 — Motion (https://motionapp.com/library/research/creative-benchmarks-2026/)

## SYS-UNKNOWN-001 — Missing material facts must return typed unknown or insufficient evidence
- **Domain:** `system_governance`
- **Rule type:** `operational_hard_constraint`
- **Severity:** `critical`

**Applicability**
- All Viraldy features

**Required conditions**
- Recommendation depends on material unverified fact

**Expected behavior**
- Return typed unknown, missing field, decision impact and smallest question
- Allow partial output only for unaffected dimensions

**Prohibited behavior**
- Inventing product facts, rights, economics, policy status, performance or deadline

**Unknown behavior**
- Use unknown, insufficient_evidence, policy_conflict, seller_confirmation_required, expert_review_required

**Exceptions**
- Low-risk creative suggestions can proceed if separated

**Common failure modes**
- LLM fills COGS
- Assumes rights
- Infers shipping from comments

**Expert-review trigger**
- Material fact disputed
- Sources conflict
- High-risk category

**Seller-facing explanation**  
Viraldy does not have enough verified information to make this decision; provide the missing input or keep it conditional.

**Creator-facing correction**  
The creative suggestion can proceed, but the seller must confirm the missing product, claim, disclosure or rights detail.

**Implementation**
```json
{
  "rule": "LLM cannot populate source_of_truth fields; missing material field produces typed state"
}
```
**Sources:** [PERF07] Offline-to-Online Creative Optimization with Generative Models and Adaptive Testing — Lee et al., arXiv preprint (https://arxiv.org/abs/2607.23696); [TT08] TikTok Shop Content Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837891779151617); [FTC04] Health Products Compliance Guidance — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance)

## SYS-REVIEW-001 — High-risk findings require seller or expert review before activation
- **Domain:** `system_governance`
- **Rule type:** `operational_hard_constraint`
- **Severity:** `blocker`

**Applicability**
- All campaign outputs
- Preflight
- Product Scan
- Rights

**Required conditions**
- Configured review trigger fires

**Expected behavior**
- Route to correct reviewer with evidence and unresolved question
- Lock activation and record disposition

**Prohibited behavior**
- LLM silently clears legal, health, safety, IP, regulated, rights or severe economics risk

**Unknown behavior**
- No reviewer response keeps blocked_pending_review

**Exceptions**
- Low-risk optional optimization does not require expert review

**Common failure modes**
- Alert without evidence
- Reviewer role unclear
- Override without audit

**Expert-review trigger**
- Health/safety
- IP uncertainty
- Restricted category
- Rights dispute
- Negative economics
- Policy conflict

**Seller-facing explanation**  
This issue needs a human decision before the campaign can be marked ready.

**Creator-facing correction**  
Please pause publication while the seller or specialist reviews the flagged issue.

**Implementation**
```json
{
  "rule": "activation_locked=true until review disposition approved"
}
```
**Sources:** [TT19] Prohibited Products Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=1399532709988097); [TT20] Restricted Products Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=3238037484275457); [FTC04] Health Products Compliance Guidance — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance); [USPTO02] Likelihood of Confusion — United States Patent and Trademark Office (https://www.uspto.gov/trademarks/search/likelihood-confusion)

## SYS-PROV-001 — Every recommendation must preserve evidence and version provenance
- **Domain:** `system_governance`
- **Rule type:** `operational_hard_constraint`
- **Severity:** `high`

**Applicability**
- Creative DNA
- PatternKit
- ViralKit
- Preflight
- Campaign Pack
- performance

**Required conditions**
- Viraldy creates/updates recommendation

**Expected behavior**
- Store immutable input versions, evidence IDs/timestamps, policy/rubric/model/prompt versions, sources, confidence and actions

**Prohibited behavior**
- Overwriting history
- Unexplained score
- Pattern evidence without source

**Unknown behavior**
- Incomplete provenance marks non_auditable and blocks high-confidence promotion

**Exceptions**
- Minor UI copy can avoid analytical version; material logic/input cannot

**Common failure modes**
- New listing with old brief
- PatternKit updated without version
- Override not logged

**Expert-review trigger**
- Disputed output
- Model/rule change
- Audit request

**Seller-facing explanation**  
Viraldy should explain which product, asset, policy and evidence produced every recommendation.

**Creator-facing correction**  
Please use the latest approved brief and asset version; prior drafts remain in history.

**Implementation**
```json
{
  "required_fields": [
    "input_version_ids",
    "evidence_ids",
    "source_ids",
    "policy_pack_version",
    "rubric_version",
    "model_version",
    "prompt_version",
    "created_at",
    "actor",
    "override_log"
  ]
}
```
**Sources:** [PERF07] Offline-to-Online Creative Optimization with Generative Models and Adaptive Testing — Lee et al., arXiv preprint (https://arxiv.org/abs/2607.23696)

## SYS-PRIVATE-001 — Private seller performance cannot be exposed as another seller’s evidence
- **Domain:** `system_governance`
- **Rule type:** `operational_hard_constraint`
- **Severity:** `blocker`

**Applicability**
- Benchmarks
- PatternKit retrieval
- agency workspaces

**Required conditions**
- System aggregates/retrieves private campaign data

**Expected behavior**
- Apply workspace isolation
- Use anonymized aggregate only with consent, cohort safeguards and no re-identification
- Label scope

**Prohibited behavior**
- Leaking product, creative, creator, GMV, margin or strategy

**Unknown behavior**
- If privacy conditions fail, keep insight workspace-private

**Exceptions**
- Agency access follows granted permissions

**Common failure modes**
- Small cohort reveals competitor
- Private pattern shown globally

**Expert-review trigger**
- Cohort too small
- Sensitive SKU/creator
- Client permission conflict

**Seller-facing explanation**  
Your private campaign history improves your workspace; cross-seller benchmarks appear only when privacy safeguards are met.

**Creator-facing correction**  
Creator-level performance should be shared only with authorized parties and agreed purposes.

**Implementation**
```json
{
  "rule": "global_benchmark_publishable=false unless consented and cohort_size>=privacy_minimum and reidentification_risk=low"
}
```
**Sources:** [PERF07] Offline-to-Online Creative Optimization with Generative Models and Adaptive Testing — Lee et al., arXiv preprint (https://arxiv.org/abs/2607.23696)

# B. Creative Pattern Catalog
**Count:** 23 patterns. No pattern is labelled winning unless linked performance evidence exists.

## PAT-DEMO-001 — Problem → product → visible result
- **Finding classification:** `established_best_practice`
- **Message angle:** A recognizable problem is made easier by the product
- **Creative mechanic:** Show real problem, exact product mechanism and observable result
- **Hook tactic:** Open on the problem state, not a generic greeting

**Psychological trigger**
- problem recognition
- relief
- convenience

**Visual format**
- hands-on vertical demo
- matched before/result

**Narrative structure**
- problem
- product
- mechanism
- result
- CTA

**Suitable product traits**
- clear pain
- visible mechanism
- short feedback loop

**Unsuitable product traits**
- no visible change
- long-term subjective benefit
- regulated outcome

**Suitable buyer contexts**
- buyer already feels problem
- needs functional proof

**Common misuse**
- Staged problem
- mechanism hidden
- result manufactured by editing

**Evidence required**
- Exact sample
- verified mechanism
- truthful result
- current offer/tag

**Demo mechanism:** Real-time use of central function  
**Proof mechanism:** Continuous or matched before/result evidence  
**Offer framing:** Offer after mechanism is understood  
**CTA strategy:** Exact product tag after result

**Copycat risk:** Medium; structure common, execution must be product-specific  
**Adaptation guidance:** Keep structure but replace script, setting, persona and proof  
**Expected learning:** Whether problem recognition plus mechanism improves product clicks/orders  
**Performance-evidence status:** Candidate until linked product-level performance exists

**Sources:** [TT12] Creative best practices for performance ads — TikTok for Business Help Center (https://ads.tiktok.com/help/article/creative-best-practices); [TT15] Creative Codes: Six Principles for TikTok-First Ads — TikTok for Business (https://ads.tiktok.com/business/creativecenter/quicktok/online/TikTokCreativeCodes.pdf); [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief); [PERF01] Creative Benchmarks 2026 — Motion (https://motionapp.com/library/research/creative-benchmarks-2026/)

## PAT-DEMO-002 — Product-first mechanism close-up
- **Finding classification:** `established_best_practice`
- **Message angle:** Novel function earns attention immediately
- **Creative mechanic:** Reveal exact product and macro mechanism before explanation
- **Hook tactic:** Unusual movement, texture or transformation in opening

**Psychological trigger**
- curiosity
- sensory interest
- competence

**Visual format**
- macro close-up
- hands-only demo

**Narrative structure**
- mechanism
- explanation
- use case
- result
- CTA

**Suitable product traits**
- novel mechanism
- tool/gadget
- tactile product

**Unsuitable product traits**
- hidden mechanism
- no safe visible use
- commodity with no differentiation

**Suitable buyer contexts**
- buyer asks how it works

**Common misuse**
- Supplier footage of other model
- close-up hides scale

**Evidence required**
- Exact supplier SKU
- real-use footage
- dimensions/compatibility evidence

**Demo mechanism:** Continuous close-up of exact model  
**Proof mechanism:** Mechanism plus verified labels/specs  
**Offer framing:** Value after mechanism  
**CTA strategy:** Tag exact SKU

**Copycat risk:** High in generic dropship categories  
**Adaptation guidance:** Change camera, context, user and wording; do not clone supplier clip  
**Expected learning:** Whether mechanism-first improves hold and qualified clicks  
**Performance-evidence status:** Untested for current SKU

**Sources:** [TT15] Creative Codes: Six Principles for TikTok-First Ads — TikTok for Business (https://ads.tiktok.com/business/creativecenter/quicktok/online/TikTokCreativeCodes.pdf); [PERF03] How to Make Ads for Meta and TikTok in 2026 — Motion / Savannah Sanchez (https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026); [DS03] Product Sourcing Guide: How To Get Started (2026) — Shopify (https://www.shopify.com/blog/product-sourcing-apps)

## PAT-PROOF-001 — Matched before/after process proof
- **Finding classification:** `contextual_guideline`
- **Message angle:** State change is attributable to documented use
- **Creative mechanic:** Use same object, framing and relevant conditions before/after
- **Hook tactic:** Open on before state or side-by-side

**Psychological trigger**
- transformation
- certainty

**Visual format**
- locked frame
- continuous process
- split screen

**Narrative structure**
- before
- process
- after
- conditions
- CTA

**Suitable product traits**
- cleaning
- organization
- visible physical change

**Unsuitable product traits**
- health outcomes
- long time horizon
- lighting-dependent result

**Suitable buyer contexts**
- skeptical buyer

**Common misuse**
- Different lighting/object
- process omitted
- exceptional result presented typical

**Evidence required**
- Raw/continuous footage
- same conditions
- claim evidence

**Demo mechanism:** Show enough process for continuity  
**Proof mechanism:** Same object/conditions, no deceptive cuts  
**Offer framing:** Secondary to truthful proof  
**CTA strategy:** Invite inspection; no guarantee

**Copycat risk:** Medium  
**Adaptation guidance:** Adapt proof protocol, not original composition  
**Expected learning:** Whether matched proof improves conversion-quality signals  
**Performance-evidence status:** No universal performance status; high compliance sensitivity

**Sources:** [TT10] Misleading and false content — TikTok Advertising Policies (https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content); [FTC04] Health Products Compliance Guidance — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance); [PERF04] Creative Iteration for Better Ads — Alison.ai (https://alison.ai/resources/blog/creative-iteration-for-better-ads)

## PAT-COMP-001 — Alternative-versus-product workflow
- **Finding classification:** `established_best_practice`
- **Message angle:** Product replaces slower, harder or more expensive method
- **Creative mechanic:** Compare old and new methods under comparable conditions
- **Hook tactic:** Start with frustrating alternative

**Psychological trigger**
- contrast
- loss aversion
- efficiency

**Visual format**
- side-by-side
- timer/cost overlay when verified

**Narrative structure**
- old way
- pain/cost
- new way
- trade-offs
- CTA

**Suitable product traits**
- measurable workflow replacement
- clear steps

**Unsuitable product traits**
- no fair comparator
- named competitor legal risk

**Suitable buyer contexts**
- buyer uses an alternative

**Common misuse**
- Cherry-picked comparator
- invented cost/time

**Evidence required**
- Comparable protocol
- price/time source
- trademark review

**Demo mechanism:** Fair comparable task  
**Proof mechanism:** Comparable conditions and verified time/cost  
**Offer framing:** Verified value, not unsupported superiority  
**CTA strategy:** CTA after evidence

**Copycat risk:** Medium-high when named competitor/exact execution copied  
**Adaptation guidance:** Prefer category alternative unless named comparison is necessary  
**Expected learning:** Whether contrast changes price tolerance and orders  
**Performance-evidence status:** Directional until controlled evidence

**Sources:** [TT10] Misleading and false content — TikTok Advertising Policies (https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content); [FTC04] Health Products Compliance Guidance — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance); [PERF04] Creative Iteration for Better Ads — Alison.ai (https://alison.ai/resources/blog/creative-iteration-for-better-ads)

## PAT-UNBOX-001 — Unboxing → setup → first use
- **Finding classification:** `established_best_practice`
- **Message angle:** Buyer experiences arrival and first use with creator
- **Creative mechanic:** Authentic opening, inventory check, setup and immediate use
- **Hook tactic:** Anticipation or real question about contents

**Psychological trigger**
- novelty
- trust
- vicarious ownership

**Visual format**
- creator POV
- overhead package layout

**Narrative structure**
- package
- included items
- setup
- first use
- assessment
- CTA

**Suitable product traits**
- giftable
- setup required
- multiple included items

**Unsuitable product traits**
- unstable supplier packaging
- long-term benefit product

**Suitable buyer contexts**
- buyer worries what arrives

**Common misuse**
- Creator express sample differs
- fake reaction
- components hidden

**Evidence required**
- Customer-equivalent package
- included-item verification

**Demo mechanism:** Show setup without skipping material step  
**Proof mechanism:** Actual package and customer-equivalent contents  
**Offer framing:** Bundle framing only when current  
**CTA strategy:** Tag after showing what arrives

**Copycat risk:** Medium  
**Adaptation guidance:** Use real package and creator questions, not competitor beat sheet  
**Expected learning:** Whether arrival/setup clarity reduces objections  
**Performance-evidence status:** Not winning by default

**Sources:** [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief); [DS01] Dropshipping Fulfillment: The Complete Guide (2026) — Shopify (https://www.shopify.com/blog/dropshipping-fulfillment); [TT08] TikTok Shop Content Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837891779151617)

## PAT-FAQ-001 — Verified comment or objection reply
- **Finding classification:** `established_best_practice`
- **Message angle:** A real question becomes the premise
- **Creative mechanic:** Display/paraphrase verified question then answer with evidence
- **Hook tactic:** Open on the question in plain language

**Psychological trigger**
- relevance
- uncertainty reduction
- social proof

**Visual format**
- reply-to-comment
- text question + demo

**Narrative structure**
- question
- answer
- demo
- condition
- CTA

**Suitable product traits**
- frequent objections
- compatibility/setup/size questions

**Unsuitable product traits**
- no verified answer
- manufactured social proof

**Suitable buyer contexts**
- consideration-stage buyer

**Common misuse**
- Fake comment
- answer overgeneralizes

**Evidence required**
- Question provenance
- verified answer

**Demo mechanism:** Use product to answer  
**Proof mechanism:** Real source or common-question label plus verified facts  
**Offer framing:** Only if question is price/value  
**CTA strategy:** Exact option/tag

**Copycat risk:** Low-medium  
**Adaptation guidance:** Use own comments/search data; do not copy competitor screenshot  
**Expected learning:** Which objection limits orders and whether answer reduces it  
**Performance-evidence status:** Requires seller-specific evidence

**Sources:** [TT15] Creative Codes: Six Principles for TikTok-First Ads — TikTok for Business (https://ads.tiktok.com/business/creativecenter/quicktok/online/TikTokCreativeCodes.pdf); [FTC03] Final Rule Banning Fake Reviews and Testimonials — Federal Trade Commission (https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials); [PERF03] How to Make Ads for Meta and TikTok in 2026 — Motion / Savannah Sanchez (https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026)

## PAT-TESTIMONIAL-001 — Truthful personal-use testimonial
- **Finding classification:** `contextual_guideline`
- **Message angle:** Creator explains real product fit in a specific situation
- **Creative mechanic:** Personal context, actual use, observed benefit and limitation
- **Hook tactic:** Specific situation rather than generic praise

**Psychological trigger**
- identification
- trust
- specificity

**Visual format**
- talking head + b-roll
- day-in-life

**Narrative structure**
- context
- problem
- use
- observation
- fit
- CTA/disclosure

**Suitable product traits**
- routine/experience products
- identity products

**Unsuitable product traits**
- creator has not used product
- health guarantee

**Suitable buyer contexts**
- buyer identifies with creator

**Common misuse**
- Scripted fake history
- one experience presented typical

**Evidence required**
- Creator use confirmation
- disclosure
- claim evidence

**Demo mechanism:** Show use supporting statement  
**Proof mechanism:** Verified creator experience and disclosure  
**Offer framing:** Personal value, no universal promise  
**CTA strategy:** Disclose and tag exact product

**Copycat risk:** Medium  
**Adaptation guidance:** Brief truth boundaries; let creator choose honest wording  
**Expected learning:** Whether creator/context improves qualified commerce outcome  
**Performance-evidence status:** Unknown until linked to creator/product

**Sources:** [FTC01] FTC Endorsement Guides: What People Are Asking — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking); [FTC03] Final Rule Banning Fake Reviews and Testimonials — Federal Trade Commission (https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials); [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief)

## PAT-ROUTINE-001 — Routine insertion / day-in-the-life
- **Finding classification:** `established_best_practice`
- **Message angle:** Product becomes a natural step in an existing routine
- **Creative mechanic:** Place product within believable before/during/after sequence
- **Hook tactic:** Relatable routine friction

**Psychological trigger**
- self-projection
- habit
- convenience

**Visual format**
- day-in-life
- POV routine
- voiceover

**Narrative structure**
- context
- friction
- product step
- result
- CTA

**Suitable product traits**
- portable
- habitual
- home/beauty/pet routine

**Unsuitable product traits**
- rare emergency use
- complex setup

**Suitable buyer contexts**
- buyer wants to imagine ownership

**Common misuse**
- Product forced into unrelated lifestyle
- fake routine

**Evidence required**
- Creator context
- exact use
- disclosure

**Demo mechanism:** Show relevant step naturally  
**Proof mechanism:** Authentic use and verified fit  
**Offer framing:** Ease/fit, not false necessity  
**CTA strategy:** Soft tag after routine

**Copycat risk:** Medium  
**Adaptation guidance:** Select creator whose existing content contains routine  
**Expected learning:** Which routine/creator context improves relevance  
**Performance-evidence status:** Expert-supported, not universally proven

**Sources:** [PERF02] 2025 DTC Creative Trends: Expert Lightning Round — Motion (https://motionapp.com/library/talk/motion-s-2025-facebook-ad-creative-trends-dtc-expert-lightning-round/); [PERF03] How to Make Ads for Meta and TikTok in 2026 — Motion / Savannah Sanchez (https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026); [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief)

## PAT-CURIOSITY-001 — Unexpected discovery
- **Finding classification:** `directional_pattern`
- **Message angle:** Novel product solves overlooked friction
- **Creative mechanic:** Establish specific curiosity then reveal/prove mechanism
- **Hook tactic:** Real overlooked problem, not empty clickbait

**Psychological trigger**
- curiosity gap
- novelty

**Visual format**
- creator discovery
- mystery close-up

**Narrative structure**
- setup
- reveal
- mechanism
- use
- CTA

**Suitable product traits**
- novel mechanism
- under-known use

**Unsuitable product traits**
- commodity
- slow explanation
- misleading mystery

**Suitable buyer contexts**
- low-awareness discovery buyer

**Common misuse**
- Clickbait unresolved
- product too late
- fake discovery

**Evidence required**
- Exact sample
- real function
- downstream metrics

**Demo mechanism:** Quick proof after reveal  
**Proof mechanism:** Exact product and function  
**Offer framing:** Value after proof  
**CTA strategy:** Tag after reveal

**Copycat risk:** High for generic gadgets  
**Adaptation guidance:** Use a real buyer situation and original execution  
**Expected learning:** Whether curiosity produces clicks/orders, not only views  
**Performance-evidence status:** Views are not performance proof

**Sources:** [TT15] Creative Codes: Six Principles for TikTok-First Ads — TikTok for Business (https://ads.tiktok.com/business/creativecenter/quicktok/online/TikTokCreativeCodes.pdf); [COM02] 1.4M-view affiliate video with weak sales — Reddit r/TikTokshop (https://www.reddit.com/r/TikTokshop/comments/1lgdfzj/our_tiktok_affiliate_video_went_viral_14m_views/); [PERF01] Creative Benchmarks 2026 — Motion (https://motionapp.com/library/research/creative-benchmarks-2026/)

## PAT-MISTAKE-001 — Mistake / myth correction
- **Finding classification:** `established_best_practice`
- **Message angle:** Correct common misuse or misconception
- **Creative mechanic:** Wrong approach, consequence, correct product use
- **Hook tactic:** Concrete mistake: “you are doing X…”

**Psychological trigger**
- competence
- loss avoidance
- education

**Visual format**
- tutorial
- wrong/right split

**Narrative structure**
- mistake
- why
- correct method
- proof
- CTA

**Suitable product traits**
- usage-sensitive product
- setup/maintenance

**Unsuitable product traits**
- safety advice without expertise
- manufactured myth

**Suitable buyer contexts**
- buyer already attempts task

**Common misuse**
- False authority
- all alternatives wrong
- unsafe demo

**Evidence required**
- Instructions
- safety evidence
- exact conditions

**Demo mechanism:** Step-by-step correction  
**Proof mechanism:** Verified instructions/specs  
**Offer framing:** Utility first  
**CTA strategy:** Link product/instructions

**Copycat risk:** Medium  
**Adaptation guidance:** Use support tickets/comments to choose misconception  
**Expected learning:** Whether education improves orders or reduces returns  
**Performance-evidence status:** Directional until outcome linked

**Sources:** [PERF03] How to Make Ads for Meta and TikTok in 2026 — Motion / Savannah Sanchez (https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026); [TT08] TikTok Shop Content Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837891779151617); [DS03] Product Sourcing Guide: How To Get Started (2026) — Shopify (https://www.shopify.com/blog/product-sourcing-apps)

## PAT-STRESS-001 — Relevant stress test
- **Finding classification:** `contextual_guideline`
- **Message angle:** Product is tested in demanding but relevant condition
- **Creative mechanic:** Define test and pass/fail before running
- **Hook tactic:** Open with challenge and exact product

**Psychological trigger**
- spectacle
- uncertainty reduction

**Visual format**
- single-take test
- measured challenge

**Narrative structure**
- setup
- conditions
- execution
- result
- limitation
- CTA

**Suitable product traits**
- durability
- capacity
- cleaning
- grip

**Unsuitable product traits**
- safety-critical
- outside rated conditions

**Suitable buyer contexts**
- skeptical buyer

**Common misuse**
- Unsafe stunt
- hidden prep
- one test becomes guarantee

**Evidence required**
- Manufacturer rating
- protocol
- raw footage
- safety review

**Demo mechanism:** Real-time/minimally edited test  
**Proof mechanism:** Documented conditions and exact model  
**Offer framing:** Verified function, no lifetime guarantee  
**CTA strategy:** Specs/CTA after result

**Copycat risk:** Medium-high  
**Adaptation guidance:** Design product-relevant original test  
**Expected learning:** Whether objective proof changes conversion and returns  
**Performance-evidence status:** No universal status

**Sources:** [TT10] Misleading and false content — TikTok Advertising Policies (https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content); [FTC04] Health Products Compliance Guidance — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance); [DS03] Product Sourcing Guide: How To Get Started (2026) — Shopify (https://www.shopify.com/blog/product-sourcing-apps)

## PAT-LIST-001 — Three reasons / use cases
- **Finding classification:** `established_best_practice`
- **Message angle:** Several buyer reasons compressed into clear asset
- **Creative mechanic:** Numbered sections with visual proof for each reason
- **Hook tactic:** Specific audience: “three reasons this works for…”

**Psychological trigger**
- completeness
- self-selection

**Visual format**
- talking head + labeled b-roll

**Narrative structure**
- premise
- reason 1
- reason 2
- reason 3
- CTA

**Suitable product traits**
- multiple use cases
- variant-rich

**Unsuitable product traits**
- one-feature product padded
- reasons not demonstrable

**Suitable buyer contexts**
- comparison shopper

**Common misuse**
- Synonym reasons
- feature dump
- claim inserted for count

**Evidence required**
- Feature verification
- visual per reason

**Demo mechanism:** Each reason gets visual use  
**Proof mechanism:** Verified features and distinct benefits  
**Offer framing:** Offer only if current/material  
**CTA strategy:** Choose/check relevant option

**Copycat risk:** Medium  
**Adaptation guidance:** Build from real objections/attributes  
**Expected learning:** Which reason becomes best standalone variant  
**Performance-evidence status:** Needs element-level outcome

**Sources:** [TT12] Creative best practices for performance ads — TikTok for Business Help Center (https://ads.tiktok.com/help/article/creative-best-practices); [PERF03] How to Make Ads for Meta and TikTok in 2026 — Motion / Savannah Sanchez (https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026); [PERF04] Creative Iteration for Better Ads — Alison.ai (https://alison.ai/resources/blog/creative-iteration-for-better-ads)

## PAT-VALUE-001 — Verified value / bundle framing
- **Finding classification:** `contextual_guideline`
- **Message angle:** Product offers credible value relative to task or bundle
- **Creative mechanic:** Show what buyer gets and equivalent comparison
- **Hook tactic:** Real cost/friction or exact current offer

**Psychological trigger**
- value
- loss aversion

**Visual format**
- cost overlay
- bundle layout

**Narrative structure**
- cost problem
- product/bundle
- comparison
- trade-off
- CTA

**Suitable product traits**
- bundle
- repeat-use item
- credible alternative

**Unsuitable product traits**
- volatile price
- no comparator

**Suitable buyer contexts**
- budget-conscious buyer

**Common misuse**
- Fake crossed-out price
- old discount
- invented lifetime

**Evidence required**
- Offer snapshot
- comparator evidence
- bundle contents

**Demo mechanism:** Show included items and utility  
**Proof mechanism:** Current price/bundle/comparator source  
**Offer framing:** No false anchor; exact current offer  
**CTA strategy:** Link exact offer and expiry

**Copycat risk:** High if copying competitor offer  
**Adaptation guidance:** Use seller-specific current economics  
**Expected learning:** Whether value framing improves profitable conversion  
**Performance-evidence status:** Requires commerce outcomes

**Sources:** [TT10] Misleading and false content — TikTok Advertising Policies (https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content); [TT11] Common Reasons Ads Fail Review — TikTok Advertising Policies (https://ads.tiktok.com/help/article/common-reasons-ads-fail-review?lang=en); [FTC02] FTC Staff Revises Online Advertising Disclosure Guidelines — Federal Trade Commission (https://www.ftc.gov/news-events/news/press-releases/2013/03/ftc-staff-revises-online-advertising-disclosure-guidelines)

## PAT-SOCIAL-001 — Verified review/comment proof
- **Finding classification:** `contextual_guideline`
- **Message angle:** Real buyer feedback answers uncertainty
- **Creative mechanic:** Show verified review and connect to product evidence
- **Hook tactic:** Specific verified quote or recurring question

**Psychological trigger**
- social proof
- trust

**Visual format**
- comment screenshot + demo
- review voiceover

**Narrative structure**
- source
- context
- demo
- limitation
- CTA

**Suitable product traits**
- review-rich product
- recurring objection

**Unsuitable product traits**
- no reliable review
- high-risk result

**Suitable buyer contexts**
- skeptical buyer

**Common misuse**
- Fabricated comment
- extreme result implied typical

**Evidence required**
- Review provenance
- permission
- claim support

**Demo mechanism:** Demonstrate claim behind review  
**Proof mechanism:** Provenance, disclosure, representative framing  
**Offer framing:** Separate offer from proof  
**CTA strategy:** Tag exact product

**Copycat risk:** Low for seller-owned proof, high when copied  
**Adaptation guidance:** Use seller’s own verified feedback  
**Expected learning:** Which proof type improves qualified orders/returns  
**Performance-evidence status:** Not winning without outcomes

**Sources:** [FTC03] Final Rule Banning Fake Reviews and Testimonials — Federal Trade Commission (https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials); [FTC01] FTC Endorsement Guides: What People Are Asking — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking); [TT08] TikTok Shop Content Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837891779151617)

## PAT-OBJECTION-001 — Single-objection resolution
- **Finding classification:** `established_best_practice`
- **Message angle:** One material reason not to buy is answered
- **Creative mechanic:** Name objection, show evidence, state limitation
- **Hook tactic:** Use objection verbatim or as question

**Psychological trigger**
- trust
- risk reduction

**Visual format**
- talking head + evidence
- FAQ demo

**Narrative structure**
- objection
- evidence
- condition
- CTA

**Suitable product traits**
- known objection
- return-prone category

**Unsuitable product traits**
- unknown answer
- high-risk legal question

**Suitable buyer contexts**
- consideration stage

**Common misuse**
- Unsupported reassurance
- hides limitation

**Evidence required**
- Support comments
- exact product evidence

**Demo mechanism:** Demonstrate relevant property  
**Proof mechanism:** Verified spec/shipping/compatibility  
**Offer framing:** Discount only if price is objection  
**CTA strategy:** Exact variant/spec link

**Copycat risk:** Low-medium  
**Adaptation guidance:** Choose highest-cost unresolved objection  
**Expected learning:** Whether resolution improves conversion quality/returns  
**Performance-evidence status:** Needs seller outcomes

**Sources:** [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief); [PERF03] How to Make Ads for Meta and TikTok in 2026 — Motion / Savannah Sanchez (https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026); [DS01] Dropshipping Fulfillment: The Complete Guide (2026) — Shopify (https://www.shopify.com/blog/dropshipping-fulfillment)

## PAT-MAKER-001 — Founder/designer/maker process
- **Finding classification:** `directional_pattern`
- **Message angle:** Origin, craft or production detail builds trust
- **Creative mechanic:** Show real role, process/material and QC
- **Hook tactic:** Surprising production detail or customer request

**Psychological trigger**
- craft
- transparency
- identity

**Visual format**
- behind-scenes
- workbench

**Narrative structure**
- why
- process
- QC
- finished item
- CTA

**Suitable product traits**
- POD/custom/small brand

**Unsuitable product traits**
- reseller pretending to manufacture

**Suitable buyer contexts**
- buyer values craft/small business

**Common misuse**
- Dropshipper poses as maker
- stock factory footage

**Evidence required**
- Process footage
- role/source evidence

**Demo mechanism:** Show actual seller-controlled process  
**Proof mechanism:** Real role and material/origin evidence  
**Offer framing:** Premium only if supportable  
**CTA strategy:** Customization/product details

**Copycat risk:** Low if genuine, high trust risk if fabricated  
**Adaptation guidance:** State seller’s real role: designer, curator or maker  
**Expected learning:** Whether process transparency increases trust/AOV  
**Performance-evidence status:** Directional

**Sources:** [PERF02] 2025 DTC Creative Trends: Expert Lightning Round — Motion (https://motionapp.com/library/talk/motion-s-2025-facebook-ad-creative-trends-dtc-expert-lightning-round/); [FTC01] FTC Endorsement Guides: What People Are Asking — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking); [TT08] TikTok Shop Content Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837891779151617)

## PAT-POD-001 — Personalization reveal
- **Finding classification:** `established_best_practice`
- **Message angle:** Generic item becomes specific to recipient
- **Creative mechanic:** Show base item, input/process and final reveal
- **Hook tactic:** Recipient/name/occasion question or partial reveal

**Psychological trigger**
- identity
- anticipation
- giftability

**Visual format**
- close-up reveal
- maker process

**Narrative structure**
- recipient
- input
- production/reveal
- detail
- CTA

**Suitable product traits**
- visible personalization
- giftable

**Unsuitable product traits**
- mockup-only
- checkout cannot support option

**Suitable buyer contexts**
- gift/identity buyer

**Common misuse**
- Any font promise
- mockup as physical reveal

**Evidence required**
- Approved preview
- physical sample
- checkout limits
- IP clearance

**Demo mechanism:** Approved flow and physical sample  
**Proof mechanism:** Exact personalization and example label  
**Offer framing:** Recipient/occasion value  
**CTA strategy:** Accurate personalization CTA

**Copycat risk:** Medium  
**Adaptation guidance:** Change recipient, occasion, product and setting  
**Expected learning:** Which recipient/reveal style drives personalization orders  
**Performance-evidence status:** Suitable, not proven

**Sources:** [POD01] How do I review orders with personalized products? — Printify Help Center (https://help.printify.com/hc/en-us/articles/28903834238097-How-do-I-review-orders-with-personalized-products); [POD04] How do I set up product personalization? — Printify Help Center (https://help.printify.com/hc/en-us/articles/29856933892241-How-do-I-set-up-product-personalization); [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief)

## PAT-POD-002 — Recipient identity story
- **Finding classification:** `directional_pattern`
- **Message angle:** Product signals a specific relationship or identity
- **Creative mechanic:** Genuine creator context shows why personalization matters
- **Hook tactic:** “For the person who…” plus specific moment

**Psychological trigger**
- belonging
- recognition

**Visual format**
- creator story
- gift recommendation

**Narrative structure**
- recipient context
- generic gift misses
- detail
- payoff
- CTA

**Suitable product traits**
- niche gifts
- pet/family/hobby identity

**Unsuitable product traits**
- stereotype-heavy
- IP fandom

**Suitable buyer contexts**
- gift buyer needs idea

**Common misuse**
- Generic stereotype
- creator mismatch
- trademark phrase

**Evidence required**
- Buyer research
- creator fit
- IP clearance

**Demo mechanism:** Show recipient-specific detail  
**Proof mechanism:** Creator fit, product and customization truth  
**Offer framing:** Meaning, not guaranteed reaction  
**CTA strategy:** Options/cutoff only if verified

**Copycat risk:** Medium-high in saturated POD  
**Adaptation guidance:** Adapt emotional job, not exact slogan/design  
**Expected learning:** Which recipient segment converts/returns  
**Performance-evidence status:** Directional

**Sources:** [PERF02] 2025 DTC Creative Trends: Expert Lightning Round — Motion (https://motionapp.com/library/talk/motion-s-2025-facebook-ad-creative-trends-dtc-expert-lightning-round/); [POD04] How do I set up product personalization? — Printify Help Center (https://help.printify.com/hc/en-us/articles/29856933892241-How-do-I-set-up-product-personalization); [POD05] Etsy Creativity Standards — Etsy (https://www.etsy.com/legal/creativity/)

## PAT-POD-003 — Customization process / maker proof
- **Finding classification:** `established_best_practice`
- **Message angle:** Buyer understands how input becomes finished item
- **Creative mechanic:** Show input, preview, production, QC and physical result
- **Hook tactic:** “From this input to this item”

**Psychological trigger**
- control
- craft
- trust

**Visual format**
- screen-to-product
- overhead production

**Narrative structure**
- input
- preview
- production
- QC
- result
- CTA

**Suitable product traits**
- complex personalization
- photo/text item

**Unsuitable product traits**
- fake handmade claim
- supplier workflow unknown

**Suitable buyer contexts**
- buyer fears errors

**Common misuse**
- Footage from other provider
- manual review omitted

**Evidence required**
- Workflow evidence
- template version
- sample

**Demo mechanism:** Actual workflow and sample  
**Proof mechanism:** Workflow accuracy and approval step  
**Offer framing:** Premium based on real work  
**CTA strategy:** Explain next personalization step

**Copycat risk:** Low-medium if owned process  
**Adaptation guidance:** Show seller’s real role even if outsourced  
**Expected learning:** Whether transparency reduces errors/cancellations  
**Performance-evidence status:** Best-practice fit

**Sources:** [POD01] How do I review orders with personalized products? — Printify Help Center (https://help.printify.com/hc/en-us/articles/28903834238097-How-do-I-review-orders-with-personalized-products); [POD04] How do I set up product personalization? — Printify Help Center (https://help.printify.com/hc/en-us/articles/29856933892241-How-do-I-set-up-product-personalization); [TT09] TikTok Shop Fulfillment Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=3995852763301633)

## PAT-DROP-001 — Exact-variant compatibility proof
- **Finding classification:** `established_best_practice`
- **Message angle:** Product works with a specific model/condition
- **Creative mechanic:** Identify model and demonstrate fit/function
- **Hook tactic:** Open with exact compatibility question

**Psychological trigger**
- certainty
- risk reduction

**Visual format**
- model label + demo
- fit test

**Narrative structure**
- model
- fit/setup
- function
- limitation
- CTA

**Suitable product traits**
- accessory
- replacement part
- size-dependent

**Unsuitable product traits**
- unknown compatibility
- supplier variants change

**Suitable buyer contexts**
- buyer fears wrong item

**Common misuse**
- One model generalized
- model number hidden

**Evidence required**
- Matrix
- supplier SKU
- model visible

**Demo mechanism:** Continuous exact-model test  
**Proof mechanism:** Compatibility matrix and exact sample  
**Offer framing:** No universal fit without evidence  
**CTA strategy:** Buyer checks model/size

**Copycat risk:** Medium  
**Adaptation guidance:** Create separate versions by verified model cluster  
**Expected learning:** Which model questions improve orders/reduce returns  
**Performance-evidence status:** Requires exact evidence

**Sources:** [DS03] Product Sourcing Guide: How To Get Started (2026) — Shopify (https://www.shopify.com/blog/product-sourcing-apps); [DS04] How Does Alibaba Work? Buying and Safety Guide (2026) — Shopify (https://www.shopify.com/blog/16665772-alibaba-101-how-to-safely-source-products-from-the-worlds-biggest-supplier-directory); [TT08] TikTok Shop Content Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837891779151617)

## PAT-DROP-002 — Transparent delivery expectation
- **Finding classification:** `contextual_guideline`
- **Message angle:** Reduce shipping uncertainty without overpromising
- **Creative mechanic:** Explain seller-verified route/range
- **Hook tactic:** Use shipping objection only with reliable evidence

**Psychological trigger**
- risk reduction
- trust

**Visual format**
- FAQ overlay
- tracking context

**Narrative structure**
- concern
- verified range/process
- expectation
- CTA

**Suitable product traits**
- stable tracked route

**Unsuitable product traits**
- unstable supplier route
- express sample only

**Suitable buyer contexts**
- consideration-stage shipping concern

**Common misuse**
- Personal sample transit generalized

**Evidence required**
- Current route/SLA
- destination
- production time

**Demo mechanism:** No special demo beyond real package  
**Proof mechanism:** Current route/warehouse/handling/carrier  
**Offer framing:** Transparency, no false urgency  
**CTA strategy:** Current listing estimate

**Copycat risk:** Low copycat; high truth risk  
**Adaptation guidance:** Geo/variant-specific only when supported  
**Expected learning:** Whether transparency improves qualified conversion/complaints  
**Performance-evidence status:** Operational pattern, performance unknown

**Sources:** [FTC05] Mail, Internet, or Telephone Order Merchandise Rule — Federal Trade Commission (https://www.ftc.gov/legal-library/browse/rules/mail-internet-or-telephone-order-merchandise-rule); [TT09] TikTok Shop Fulfillment Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=3995852763301633); [DS01] Dropshipping Fulfillment: The Complete Guide (2026) — Shopify (https://www.shopify.com/blog/dropshipping-fulfillment)

## PAT-MOD-001 — Modular hook–body–CTA system
- **Finding classification:** `established_best_practice`
- **Message angle:** One verified core demo supports controlled variants
- **Creative mechanic:** Film clean body plus swappable hooks, proof and CTA
- **Hook tactic:** Meaningfully different hook hypotheses, not synonyms

**Psychological trigger**
- testing efficiency
- message discovery

**Visual format**
- clean base edit
- alternate openings

**Narrative structure**
- hook module
- core demo
- proof
- CTA

**Suitable product traits**
- repeatable demo
- paid testing

**Unsuitable product traits**
- one-shot reaction
- no editing rights

**Suitable buyer contexts**
- seller needs iteration speed

**Common misuse**
- Multiple variables change
- music baked in
- near-duplicate hooks

**Evidence required**
- Modular contract
- edit rights
- asset IDs
- test map

**Demo mechanism:** Keep core demo constant for hook test  
**Proof mechanism:** Versioned modules and rights  
**Offer framing:** Offer variant treated as separate variable  
**CTA strategy:** CTA matches objective

**Copycat risk:** Low when original and versioned  
**Adaptation guidance:** Record constant and changed axes  
**Expected learning:** Which message dimension changes outcome efficiently  
**Performance-evidence status:** Workflow best practice; each module unproven

**Sources:** [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief); [UGC04] How to repurpose UGC — Billo (https://billo.app/blog/repurpose-ugc/); [TT16] How to create a split test in TikTok Ads Manager — TikTok for Business Help Center (https://ads.tiktok.com/help/article/create-split-test); [PERF04] Creative Iteration for Better Ads — Alison.ai (https://alison.ai/resources/blog/creative-iteration-for-better-ads)

## PAT-PERSONA-001 — Same mechanism, different buyer persona
- **Finding classification:** `established_best_practice`
- **Message angle:** Mechanism constant while context/language change
- **Creative mechanic:** Film persona-specific setting, pain and objection
- **Hook tactic:** Open with persona-specific moment, not label alone

**Psychological trigger**
- identification
- relevance

**Visual format**
- creator-native versions

**Narrative structure**
- context
- shared mechanism
- benefit
- objection
- CTA

**Suitable product traits**
- multi-use product
- several authentic contexts

**Unsuitable product traits**
- stereotype-only swap
- too little traffic

**Suitable buyer contexts**
- cross-border seller learning US buyer

**Common misuse**
- Cosmetic demographic swap
- everything changes

**Evidence required**
- Persona hypothesis
- creator fit
- test mapping

**Demo mechanism:** Comparable core mechanism  
**Proof mechanism:** Creator fit and same product/offer for controlled test  
**Offer framing:** Offer differs only if test recognizes it  
**CTA strategy:** Persona-specific CTA

**Copycat risk:** Low-medium  
**Adaptation guidance:** Define what remains constant vs persona-specific  
**Expected learning:** Which context drives higher-quality outcomes  
**Performance-evidence status:** Expert-supported test strategy

**Sources:** [PERF02] 2025 DTC Creative Trends: Expert Lightning Round — Motion (https://motionapp.com/library/talk/motion-s-2025-facebook-ad-creative-trends-dtc-expert-lightning-round/); [PERF03] How to Make Ads for Meta and TikTok in 2026 — Motion / Savannah Sanchez (https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026); [PERF04] Creative Iteration for Better Ads — Alison.ai (https://alison.ai/resources/blog/creative-iteration-for-better-ads)

# C. Real-world Mistake Taxonomy
**Count:** 20 mistake codes.

## M-PROD-001 — Observed product differs from linked SKU/variant
- **Category:** `product_mismatch`
- **Severity:** `blocker`
- **Remediation:** `reshoot`

**Expected example**  
Exact linked color, model, size, bundle and accessories are shown.

**Observed example**  
Video shows a black two-piece set while listing is a white single unit.

**Seller message**  
Block approval; confirm SKU/variant and replace asset or link.

**Creator message**  
Please reshoot with the exact seller-approved product and only the included items.

**Escalation behavior**  
Lock publish/Spark; review supplier substitution if suspected.

**Detection signals**
- visual/listing mismatch
- variant mismatch
- tag mismatch

**Related policy codes**
- TT-CONTENT-001
- QUALITY-001

**Sources:** [TT08] TikTok Shop Content Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837891779151617); [TT10] Misleading and false content — TikTok Advertising Policies (https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content); [TT18] Product Quality Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=5203348292765486)

## M-PROD-002 — Product appears late or disconnected from the hook
- **Category:** `late_or_forced_product_appearance`
- **Severity:** `medium`
- **Remediation:** `edit if footage exists; otherwise reshoot`

**Expected example**  
Campaign-specific product-reveal requirement is met and product role follows naturally.

**Observed example**  
Unrelated lifestyle intro; product first appears at 0:08 with no link to problem.

**Seller message**  
Treat as brief alignment, not universal platform violation.

**Creator message**  
Move an existing relevant product shot earlier or reshoot the opening beat.

**Escalation behavior**  
Block only when brief/contract requires timing; otherwise optimization.

**Detection signals**
- first appearance time
- hook-product semantic gap

**Related policy codes**
- PERF-TIME-001
- UGC-REV-002

**Sources:** [TT12] Creative best practices for performance ads — TikTok for Business Help Center (https://ads.tiktok.com/help/article/creative-best-practices); [TT15] Creative Codes: Six Principles for TikTok-First Ads — TikTok for Business (https://ads.tiktok.com/business/creativecenter/quicktok/online/TikTokCreativeCodes.pdf); [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief)

## M-DEMO-001 — Product mechanism or use is not understandable
- **Category:** `unclear_demo`
- **Severity:** `high`
- **Remediation:** `edit or reshoot`

**Expected example**  
Viewer sees setup, operation and result under normal conditions.

**Observed example**  
Fast cuts show before and after but not how the product works.

**Seller message**  
Request one clear mechanism shot; edit if raw footage exists.

**Creator message**  
Please add a continuous shot showing setup/use and the result on the same object.

**Escalation behavior**  
Block proof-heavy paid readiness; escalate unsafe/compatibility concerns.

**Detection signals**
- setup omitted
- no continuous use
- result discontinuity

**Related policy codes**
- TT-CONTENT-001
- UGC-REV-002

**Sources:** [TT08] TikTok Shop Content Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837891779151617); [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief); [PERF03] How to Make Ads for Meta and TikTok in 2026 — Motion / Savannah Sanchez (https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026)

## M-PROOF-001 — Proof or testimonial exceeds evidence
- **Category:** `unsupported_proof`
- **Severity:** `blocker`
- **Remediation:** `expert review / remove claim`

**Expected example**  
Objective result is linked to adequate evidence and actual creator experience.

**Observed example**  
“Removes 100% instantly” appears over one edited clip with no evidence.

**Seller message**  
Remove the claim and request exact substantiation.

**Creator message**  
Replace the absolute result with truthful personal observation or approved measurable demo.

**Escalation behavior**  
Lock activation; route health/safety/comparative proof to expert review.

**Detection signals**
- absolute claim
- before/after discontinuity
- missing evidence

**Related policy codes**
- TT-CLAIM-001
- FTC-CLAIM-001

**Sources:** [TT10] Misleading and false content — TikTok Advertising Policies (https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content); [FTC04] Health Products Compliance Guidance — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance)

## M-OFFER-001 — Price, discount, bundle or shipping differs from live offer
- **Category:** `offer_mismatch`
- **Severity:** `blocker`
- **Remediation:** `edit`

**Expected example**  
Creative matches timestamped live listing and conditions.

**Observed example**  
Video says $19.99/free shipping; listing is $27.99 and shipping varies.

**Seller message**  
Update/remove offer or restore verified listing offer.

**Creator message**  
Please use the seller-approved current price and shipping language.

**Escalation behavior**  
Block publish/Spark; require fresh offer snapshot.

**Detection signals**
- OCR price mismatch
- bundle mismatch
- shipping offer unverified

**Related policy codes**
- TT-OFFER-001

**Sources:** [TT10] Misleading and false content — TikTok Advertising Policies (https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content); [TT11] Common Reasons Ads Fail Review — TikTok Advertising Policies (https://ads.tiktok.com/help/article/common-reasons-ads-fail-review?lang=en)

## M-OFFER-002 — Urgency/scarcity is unverified
- **Category:** `false_urgency`
- **Severity:** `blocker`
- **Remediation:** `edit`

**Expected example**  
Real expiry or inventory signal is stored and creative expires with it.

**Observed example**  
Evergreen video says “today only” and “3 left” without evidence.

**Seller message**  
Remove urgency or provide live source/expiry.

**Creator message**  
Please remove the countdown or use the approved current deadline.

**Escalation behavior**  
Block activation; repeated false scarcity triggers governance review.

**Detection signals**
- urgency phrase
- no expiry/inventory source

**Related policy codes**
- TT-URGENCY-001

**Sources:** [TT10] Misleading and false content — TikTok Advertising Policies (https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content); [FTC02] FTC Staff Revises Online Advertising Disclosure Guidelines — Federal Trade Commission (https://www.ftc.gov/news-events/news/press-releases/2013/03/ftc-staff-revises-online-advertising-disclosure-guidelines)

## M-CLAIM-001 — Health, safety, financial, environmental or comparative claim risk
- **Category:** `claim_risk`
- **Severity:** `blocker`
- **Remediation:** `expert review`

**Expected example**  
Only approved wording matching vetted evidence appears.

**Observed example**  
Creator says “clinically proven to cure pain” with no evidence.

**Seller message**  
Suppress claim and route to specialist.

**Creator message**  
Remove the medical/clinical statement until seller supplies approved wording.

**Escalation behavior**  
Activation blocked; regulated-category review may also fire.

**Detection signals**
- health keywords
- clinical claim
- comparative superiority

**Related policy codes**
- FTC-HEALTH-001
- CATEGORY-001

**Sources:** [FTC04] Health Products Compliance Guidance — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance); [TT19] Prohibited Products Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=1399532709988097); [TT20] Restricted Products Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=3238037484275457)

## M-DISC-001 — Material connection disclosure missing or unclear
- **Category:** `disclosure`
- **Severity:** `blocker`
- **Remediation:** `edit + publish metadata`

**Expected example**  
Platform disclosure is enabled and relationship is plainly stated near endorsement.

**Observed example**  
Gifted/commissioned video only includes #collab after many tags.

**Seller message**  
Do not publish until disclosure is complete.

**Creator message**  
Enable TikTok disclosure and add clear seller-approved wording near the endorsement.

**Escalation behavior**  
Block publish; cross-channel relationship disputes go to review.

**Detection signals**
- material connection yes/unknown
- disclosure absent/ambiguous

**Related policy codes**
- DISC-001

**Sources:** [TT13] Commercial Content Disclosure setting for advertisers — TikTok for Business Help Center (https://ads.tiktok.com/help/article/about-the-commercial-content-disclosure-setting-for-advertisers); [FTC01] FTC Endorsement Guides: What People Are Asking — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking); [FTC02] FTC Staff Revises Online Advertising Disclosure Guidelines — Federal Trade Commission (https://www.ftc.gov/news-events/news/press-releases/2013/03/ftc-staff-revises-online-advertising-disclosure-guidelines)

## M-CTA-001 — Required product tag/link or campaign CTA is missing/wrong
- **Category:** `product_tag_and_cta`
- **Severity:** `high`
- **Remediation:** `edit or publish check`

**Expected example**  
Shoppable/sample-obligation post uses exact product link and approved CTA.

**Observed example**  
Draft says link in bio and published post tags another SKU.

**Seller message**  
Add approved CTA and verify exact tag at publication.

**Creator message**  
Please add the approved CTA and tag the exact product; send post proof.

**Escalation behavior**  
Wrong/missing link blocks sample fulfillment and paid readiness; optional CTA absence is only optimization.

**Detection signals**
- CTA absent
- product_id mismatch
- link missing

**Related policy codes**
- TT-CONTENT-001
- SAMPLE-001

**Sources:** [TT01] Guide to Samples: Free and Refundable — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=5764641632306946); [TT02] How to set up and manage samples — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=5694209038927617); [TT08] TikTok Shop Content Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837891779151617)

## M-CREATOR-001 — Creator experience/reaction is fabricated or forced
- **Category:** `creator_authenticity`
- **Severity:** `high`
- **Remediation:** `reshoot/reframe`

**Expected example**  
Creator uses real experience or clearly non-testimonial demonstration.

**Observed example**  
Creator says “used for months” on first receipt and performs fake reaction.

**Seller message**  
Change format to demonstration or first-use observation.

**Creator message**  
Use your natural voice and only describe what you actually observed.

**Escalation behavior**  
Block testimonial format; review fake-review risk.

**Detection signals**
- testimonial language
- experience unverified
- style mismatch

**Related policy codes**
- UGC-AUTH-001
- FTC-REVIEW-001

**Sources:** [FTC01] FTC Endorsement Guides: What People Are Asking — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking); [FTC03] Final Rule Banning Fake Reviews and Testimonials — Federal Trade Commission (https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials); [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief)

## M-REV-001 — Requested change is outside approved brief/rounds
- **Category:** `revision_scope`
- **Severity:** `medium`
- **Remediation:** `non-creative scope fix`

**Expected example**  
Revision maps to missed agreed requirement; new concepts are re-scoped.

**Observed example**  
Seller asks for three hooks, raw footage and new persona after one-video approval.

**Seller message**  
Classify as new scope and approve extra deliverables/fee.

**Creator message**  
These changes exceed the approved brief; please confirm new scope/timeline.

**Escalation behavior**  
Pause countdown and preserve original brief/version.

**Detection signals**
- request absent from deliverables
- brief changed after production

**Related policy codes**
- UGC-REV-001
- UGC-MOD-001
- SYS-PROV-001

**Sources:** [COM08] Brand-side UGC pricing and rights discussion — Reddit r/UGCcreators (https://www.reddit.com/r/UGCcreators/comments/1v6fwqw/im_on_the_brand_side_of_ugc_deals_heres_what/); [COM09] UGC glossary: rights, revisions, raw footage — Reddit r/UGCcreators (https://www.reddit.com/r/UGCcreators/comments/1vat08s/a_glossary_of_common_ugc_terms_for_newer_creators/)

## M-RIGHTS-001 — Paid use/Spark scope missing, invalid or expired
- **Category:** `rights_and_spark`
- **Severity:** `blocker`
- **Remediation:** `non-creative rights fix`

**Expected example**  
Rights and authorization cover exact asset, channel, duration and advertiser.

**Observed example**  
Agreement covers organic only and Spark code expired.

**Seller message**  
Keep organic-only; request rights and authorization renewal.

**Creator message**  
Please confirm paid usage and renew authorization for this exact post.

**Escalation behavior**  
Block paid-ready; rights dispute goes to legal/operations review.

**Detection signals**
- rights missing
- authorization expired
- post mismatch

**Related policy codes**
- UGC-RIGHTS-001
- SPARK-001
- SPARK-003

**Sources:** [TT05] Differences between affiliate mass authorization and video code authorization — TikTok for Business Help Center (https://ads.tiktok.com/help/article/differences-between-affiliate-creative-authorization-and-video-code); [TT06] How to create Spark Ads for Manual and Search Campaigns — TikTok for Business Help Center (https://ads.tiktok.com/help/article/spark-ads-creation-guide); [UGC02] Paid Media UGC: What it is and how to do it — Insense (https://insense.pro/blog/paid-media-ugc)

## M-POD-001 — Personalization differs from approved input/preview
- **Category:** `pod_personalization`
- **Severity:** `blocker`
- **Remediation:** `reshoot after product correction`

**Expected example**  
Input snapshot, preview, template and output match.

**Observed example**  
Approved “Milo” becomes “Mila” or font/placement differs.

**Seller message**  
Stop production/launch and correct product/design.

**Creator message**  
Do not publish; reshoot after corrected item arrives.

**Escalation behavior**  
Open production/customer-support incident; lock proof if systemic.

**Detection signals**
- OCR mismatch
- template mismatch
- unsupported character

**Related policy codes**
- POD-PERS-001
- POD-PERS-002

**Sources:** [POD01] How do I review orders with personalized products? — Printify Help Center (https://help.printify.com/hc/en-us/articles/28903834238097-How-do-I-review-orders-with-personalized-products); [POD04] How do I set up product personalization? — Printify Help Center (https://help.printify.com/hc/en-us/articles/29856933892241-How-do-I-set-up-product-personalization)

## M-POD-002 — Mockup is presented as exact physical proof
- **Category:** `mockup_vs_physical_sample`
- **Severity:** `high`
- **Remediation:** `physical sample/reshoot`

**Expected example**  
Mockup is labeled representation; physical proof uses exact sample.

**Observed example**  
AI mockup shows vivid embroidery/perfect centering; no sample exists.

**Seller message**  
Downgrade to concept-only and require sample for proof-heavy launch.

**Creator message**  
Replace mockup close-up with physical-item footage.

**Escalation behavior**  
Block paid proof; repeated mismatch triggers provider review.

**Detection signals**
- mockup-only
- texture/color claim
- no sample

**Related policy codes**
- POD-MOCK-001
- POD-SAMPLE-001
- TT-LISTING-001

**Sources:** [POD02] How can I create mockups for Early Access Catalog products? — Printify Help Center (https://help.printify.com/hc/en-us/articles/25641196380817-How-can-I-create-mockups-for-Early-Access-Catalog-products); [POD03] Why does my product look different from the mockup? — Printify Help Center (https://help.printify.com/hc/en-us/articles/4483617784721-Why-does-my-product-look-different-from-the-mockup); [COM04] Mockup tool and printed product mismatch — Reddit r/printondemand (https://www.reddit.com/r/printondemand/comments/1t7d1dl/avoid_fourthwall_their_mockup_tool_and_printed/)

## M-IP-001 — Unauthorized logo, character, artwork, footage or music
- **Category:** `ip_risk`
- **Severity:** `blocker`
- **Remediation:** `expert review/replacement`

**Expected example**  
All third-party elements have verified license/ownership.

**Observed example**  
POD art uses sports logo/character; video includes competitor clip and song.

**Seller message**  
Remove unverified elements and start clearance.

**Creator message**  
Replace all unapproved logos, art, footage and music.

**Escalation behavior**  
Lock listing/content; legal review for trademark/copyright/parody.

**Detection signals**
- logo/character detection
- license missing
- similar mark hit

**Related policy codes**
- IP-001
- POD-IP-001
- UGC-MUSIC-001

**Sources:** [TT14] TikTok Shop Intellectual Property Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837901778306818); [USPTO02] Likelihood of Confusion — United States Patent and Trademark Office (https://www.uspto.gov/trademarks/search/likelihood-confusion); [USCO01] Visual Artists: Copyright Basics — U.S. Copyright Office (https://www.copyright.gov/engage/visual-artists/)

## M-DROP-001 — Compatibility overstated or based on other model
- **Category:** `dropshipping_compatibility`
- **Severity:** `blocker`
- **Remediation:** `reshoot`

**Expected example**  
Exact supported model/condition is named and tested with exact supplier SKU.

**Observed example**  
Video says fits every phone; tests one model and shipped connector differs.

**Seller message**  
Remove universal claim, verify matrix and reshoot exact use.

**Creator message**  
Name only verified compatible models and film exact variant.

**Escalation behavior**  
Block paid/listing; safety/electrical/vehicle fit goes to specialist.

**Detection signals**
- fits-all phrase
- model missing
- supplier SKU mismatch

**Related policy codes**
- DROP-COMP-001
- DROP-SUP-002

**Sources:** [DS03] Product Sourcing Guide: How To Get Started (2026) — Shopify (https://www.shopify.com/blog/product-sourcing-apps); [DS04] How Does Alibaba Work? Buying and Safety Guide (2026) — Shopify (https://www.shopify.com/blog/16665772-alibaba-101-how-to-safely-source-products-from-the-worlds-biggest-supplier-directory); [TT08] TikTok Shop Content Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=6837891779151617)

## M-SUP-001 — Supplier stock, price, quality or route is stale/unverified
- **Category:** `supplier_and_shipping_risk`
- **Severity:** `critical`
- **Remediation:** `non-creative operational fix`

**Expected example**  
Fresh supplier snapshot and exact-sample/QC support campaign/economics.

**Observed example**  
Campaign scheduled after stockout; landed cost rose and old offer is unprofitable.

**Seller message**  
Pause samples/scale; refresh stock, cost, lead time and supplier SKU.

**Creator message**  
Avoid stock, price, delivery or quality statements until seller confirms data.

**Escalation behavior**  
Single-source/quality incident escalates; block scale.

**Detection signals**
- snapshot stale
- stockout
- cost changed
- tracking/quality fail

**Related policy codes**
- DROP-SUP-001
- DROP-STOCK-001
- DROP-SHIP-001

**Sources:** [DS05] Product sourcing and supplier monitoring documentation — AutoDS Help Center (https://help.autods.com/); [COM05] Supplier stock and price changes — Reddit r/dropshipping (https://www.reddit.com/r/dropshipping/comments/1u9gt9c/how_do_you_track_supplier_stock_and_price_changes/); [COM07] Unexpected shipping cost and low supplier stock — Reddit r/dropshipping (https://www.reddit.com/r/dropshipping/comments/1q15jg9/unexpected_aliexpress_shipping_costs_and_low/)

## M-ECON-001 — Creative marked scale-ready with incomplete/negative economics
- **Category:** `economics_and_paid_test_readiness`
- **Severity:** `critical`
- **Remediation:** `non-creative economics fix`

**Expected example**  
Recommendation includes full contribution inputs, sensitivity and budget cap.

**Observed example**  
Score 88 triggers scale though COGS, returns, commission and shipping are missing.

**Seller message**  
Withhold scale/sample recommendation; collect economics or label capped learning test.

**Creator message**  
Creative may be usable, but paid activation is waiting on seller economics.

**Escalation behavior**  
Negative-margin/loss-leader decision requires seller approval.

**Detection signals**
- economics missing
- GMV-only scale
- gross profit <=0

**Related policy codes**
- ECON-001
- PERF-METRIC-001
- SYS-UNKNOWN-001

**Sources:** [DS01] Dropshipping Fulfillment: The Complete Guide (2026) — Shopify (https://www.shopify.com/blog/dropshipping-fulfillment); [DS02] How To Start an Online Store Without Inventory (2026) — Shopify (https://www.shopify.com/blog/how-to-start-an-online-store-without-inventory); [COM01] 30 samples sent, no sale — Reddit r/TikTokshop (https://www.reddit.com/r/TikTokshop/comments/1ux5rk0/30_samples_sent_no_sale/)

## M-EVID-001 — Definitive conclusion from weak/missing evidence
- **Category:** `insufficient_evidence`
- **Severity:** `high`
- **Remediation:** `downgrade conclusion and test`

**Expected example**  
Conclusion names metric, sample, context, confidence and limits.

**Observed example**  
One video makes 20 orders and hook is labeled universally winning.

**Seller message**  
Downgrade to candidate and plan comparable test.

**Creator message**  
This structure is worth testing, but not proven for this product/creator.

**Escalation behavior**  
Block high-confidence PatternKit and causal language.

**Detection signals**
- small sample
- no denominator
- no control
- metric provenance missing

**Related policy codes**
- PERF-EVID-001
- PERF-CAUSAL-001
- PERF-SMALL-001

**Sources:** [PERF01] Creative Benchmarks 2026 — Motion (https://motionapp.com/library/research/creative-benchmarks-2026/); [PERF07] Offline-to-Online Creative Optimization with Generative Models and Adaptive Testing — Lee et al., arXiv preprint (https://arxiv.org/abs/2607.23696); [COM02] 1.4M-view affiliate video with weak sales — Reddit r/TikTokshop (https://www.reddit.com/r/TikTokshop/comments/1lgdfzj/our_tiktok_affiliate_video_went_viral_14m_views/)

## M-TEST-001 — Test changes multiple variables but attributes result to one
- **Category:** `experimentation`
- **Severity:** `high`
- **Remediation:** `redesign test`

**Expected example**  
Control/treatment differ only in intended variable or are analyzed multivariately.

**Observed example**  
Hook version also changes creator, offer, page, audience and budget.

**Seller message**  
Mark confounded and plan cleaner follow-up.

**Creator message**  
Keep core demo, offer, audience and page stable while changing selected hook.

**Escalation behavior**  
Do not update causal PatternKit; review high-spend decision.

**Detection signals**
- multiple changed dimensions
- post-hoc hypothesis
- allocation mismatch

**Related policy codes**
- PERF-TEST-001
- PERF-CAUSAL-001

**Sources:** [TT16] How to create a split test in TikTok Ads Manager — TikTok for Business Help Center (https://ads.tiktok.com/help/article/create-split-test); [PERF04] Creative Iteration for Better Ads — Alison.ai (https://alison.ai/resources/blog/creative-iteration-for-better-ads); [PERF06] Best Practices for Testing Ad Creative — Marpipe (https://www.marpipe.com/blog/best-practices-for-testing-ad-creative)

# D. Seller Workflow and UX Findings
```json
{
  "research_note": "Official platform documentation defines hard workflow. Product/provider documentation gives operational constraints. Community posts are used only as anecdotal pain evidence, not prevalence estimates.",
  "segments": [
    {
      "segment": "TikTok Shop US seller / cross-border operator",
      "current_workflow": [
        "Select or import products, listings and offers in Seller Center or an internal sheet.",
        "Use Open/Target Collaboration, direct outreach or an external creator relationship to recruit creators.",
        "Approve sample requests, confirm stock, ship, track delivery and creator posting obligation.",
        "Send product facts, references, claims and creator instructions through platform messages, chat, Docs or Sheets.",
        "Review drafts or posts manually, request revisions, collect usage rights and Spark authorization when needed.",
        "Read Seller Center, Ads Manager, comments, orders, GMV and cost data in separate tools.",
        "Decide whether to revise, reshoot, Spark, scale, stop, rehire or send another sample."
      ],
      "data_sources": [
        "TikTok Shop Seller/Affiliate Center",
        "TikTok Ads Manager",
        "creator profile and messages",
        "sample/order/tracking records",
        "Google Sheets/Drive/Notion/chat",
        "listing and offer snapshots",
        "manual margin calculator"
      ],
      "repeated_manual_steps": [
        "copy entity data between tools",
        "check effective Open versus Target terms",
        "track sample deadlines and product tags",
        "compare draft against brief",
        "ask for rights/Spark code/renewal",
        "map URL to product, creator, sample, ad and GMV",
        "write weekly report and next brief"
      ],
      "decision_points": [
        "approve/reject sample",
        "free/refundable/affiliate-only/paid UGC",
        "creator-product-angle assignment",
        "approve/revise/reshoot/reject",
        "organic-only versus paid-ready",
        "scale/fix/hold/kill/rehire"
      ],
      "seller_usually_knows": [
        "exact listing and current offer",
        "approximate product cost",
        "available inventory or supplier",
        "campaign objective and budget",
        "which creators replied/posted",
        "current operational status"
      ],
      "seller_usually_does_not_know": [
        "which creative element caused performance",
        "creator-product fit before outcome",
        "whether a popular reference sells profitably",
        "how well a structural score predicts GMV",
        "rights scope when agreed informally",
        "supplier/customer-batch consistency"
      ],
      "onboarding_friction": [
        "inconsistent IDs across exports",
        "rights/dates buried in messages",
        "missing attribution and margin definitions",
        "expectation of private API access before integrations",
        "need for English creator output and local-language internal guidance"
      ],
      "evidence_classification": [
        "official_hard_rule",
        "operational_hard_constraint",
        "seller_anecdote"
      ],
      "sources": [
        {
          "source_id": "TT01",
          "title": "Guide to Samples: Free and Refundable",
          "publisher": "TikTok Shop Academy",
          "url": "https://seller-us.tiktok.com/university/essay?knowledge_id=5764641632306946",
          "source_type": "official_platform",
          "evidence_strength": 5
        },
        {
          "source_id": "TT02",
          "title": "How to set up and manage samples",
          "publisher": "TikTok Shop Academy",
          "url": "https://seller-us.tiktok.com/university/essay?knowledge_id=5694209038927617",
          "source_type": "official_platform",
          "evidence_strength": 5
        },
        {
          "source_id": "TT04",
          "title": "Setting Up Affiliate Collaborations",
          "publisher": "TikTok Shop Academy",
          "url": "https://seller-us.tiktok.com/university/essay?knowledge_id=6837873164896001",
          "source_type": "official_platform",
          "evidence_strength": 5
        },
        {
          "source_id": "TT05",
          "title": "Differences between affiliate mass authorization and video code authorization",
          "publisher": "TikTok for Business Help Center",
          "url": "https://ads.tiktok.com/help/article/differences-between-affiliate-creative-authorization-and-video-code",
          "source_type": "official_platform",
          "evidence_strength": 5
        },
        {
          "source_id": "TT06",
          "title": "How to create Spark Ads for Manual and Search Campaigns",
          "publisher": "TikTok for Business Help Center",
          "url": "https://ads.tiktok.com/help/article/spark-ads-creation-guide",
          "source_type": "official_platform",
          "evidence_strength": 5
        },
        {
          "source_id": "COM01",
          "title": "30 samples sent, no sale",
          "publisher": "Reddit r/TikTokshop",
          "url": "https://www.reddit.com/r/TikTokshop/comments/1ux5rk0/30_samples_sent_no_sale/",
          "source_type": "seller_anecdote",
          "evidence_strength": 2
        },
        {
          "source_id": "COM02",
          "title": "1.4M-view affiliate video with weak sales",
          "publisher": "Reddit r/TikTokshop",
          "url": "https://www.reddit.com/r/TikTokshop/comments/1lgdfzj/our_tiktok_affiliate_video_went_viral_14m_views/",
          "source_type": "seller_anecdote",
          "evidence_strength": 2
        },
        {
          "source_id": "COM03",
          "title": "Affiliates receiving samples but not posting",
          "publisher": "Reddit r/TikTokshop",
          "url": "https://www.reddit.com/r/TikTokshop/comments/1b9p0cw/what_do_you_do_when_affiliates_dont_post_any/",
          "source_type": "seller_anecdote",
          "evidence_strength": 2
        }
      ]
    },
    {
      "segment": "POD and personalization seller",
      "current_workflow": [
        "Create/import design and POD variant",
        "configure personalization fields and instructions",
        "review buyer input and generate/approve production design",
        "use mockups for listing/ideation and order samples selectively",
        "send physical sample/reference to creator",
        "review personalization and creative accuracy separately",
        "track provider production, handling, shipping, cancellation and complaint"
      ],
      "data_sources": [
        "POD provider product/template data",
        "personalization input and preview",
        "mockups and sample media",
        "provider production/shipping status",
        "shop listing/orders",
        "design license records",
        "creator content and comments"
      ],
      "repeated_manual_steps": [
        "copy buyer input into template",
        "check spelling/font/placement/print area",
        "compare mockup with sample",
        "create recipient/occasion briefs",
        "explain production and character limits",
        "screen IP risk",
        "prioritize a small sample set from large catalog"
      ],
      "decision_points": [
        "which SKU deserves physical sample",
        "which recipient/occasion to test",
        "mockup sufficient for ideation versus physical proof required",
        "production can match promise",
        "IP review required",
        "occasion deadline feasible"
      ],
      "seller_usually_knows": [
        "provider/template",
        "design file and personalization fields",
        "price/base cost",
        "recipient or occasion hypothesis",
        "production method at high level"
      ],
      "seller_usually_does_not_know": [
        "exact color/texture/placement before sample",
        "best emotional angle for recipient",
        "provider/batch variation",
        "IP clearance certainty",
        "which of hundreds of designs deserves scarce creator budget"
      ],
      "onboarding_friction": [
        "large near-duplicate catalog",
        "unnormalized personalization inputs",
        "mockup mistaken for proof",
        "variable production SLA",
        "IP cannot be reduced to one confidence score"
      ],
      "evidence_classification": [
        "operational_hard_constraint",
        "official_hard_rule",
        "seller_anecdote"
      ],
      "sources": [
        {
          "source_id": "POD01",
          "title": "How do I review orders with personalized products?",
          "publisher": "Printify Help Center",
          "url": "https://help.printify.com/hc/en-us/articles/28903834238097-How-do-I-review-orders-with-personalized-products",
          "source_type": "provider_documentation",
          "evidence_strength": 4
        },
        {
          "source_id": "POD02",
          "title": "How can I create mockups for Early Access Catalog products?",
          "publisher": "Printify Help Center",
          "url": "https://help.printify.com/hc/en-us/articles/25641196380817-How-can-I-create-mockups-for-Early-Access-Catalog-products",
          "source_type": "provider_documentation",
          "evidence_strength": 4
        },
        {
          "source_id": "POD03",
          "title": "Why does my product look different from the mockup?",
          "publisher": "Printify Help Center",
          "url": "https://help.printify.com/hc/en-us/articles/4483617784721-Why-does-my-product-look-different-from-the-mockup",
          "source_type": "provider_documentation",
          "evidence_strength": 4
        },
        {
          "source_id": "POD04",
          "title": "How do I set up product personalization?",
          "publisher": "Printify Help Center",
          "url": "https://help.printify.com/hc/en-us/articles/29856933892241-How-do-I-set-up-product-personalization",
          "source_type": "provider_documentation",
          "evidence_strength": 4
        },
        {
          "source_id": "TT07",
          "title": "Product Listing Policy",
          "publisher": "TikTok Shop Academy",
          "url": "https://seller-us.tiktok.com/university/essay?knowledge_id=3196690250417921",
          "source_type": "official_platform",
          "evidence_strength": 5
        },
        {
          "source_id": "COM04",
          "title": "Mockup tool and printed product mismatch",
          "publisher": "Reddit r/printondemand",
          "url": "https://www.reddit.com/r/printondemand/comments/1t7d1dl/avoid_fourthwall_their_mockup_tool_and_printed/",
          "source_type": "seller_anecdote",
          "evidence_strength": 2
        }
      ]
    },
    {
      "segment": "Dropshipping operator",
      "current_workflow": [
        "Find supplier/product from marketplace or agent",
        "compare listing, reviews, price, route and sample",
        "import/recreate product listing",
        "order sample or commission UGC before mature sales history",
        "test organic/paid creative while monitoring supplier and page",
        "handle wrong item, stockout, tracking, returns and supplier communication",
        "replace supplier or kill product when fulfillment/economics fail"
      ],
      "data_sources": [
        "supplier marketplace/agent",
        "supplier messages/invoices",
        "sample inspection",
        "TikTok Shop/Shopify listing",
        "tracking and support data",
        "creator/ad performance",
        "landed-cost sheet"
      ],
      "repeated_manual_steps": [
        "refresh stock/price/shipping",
        "map supplier variants",
        "calculate landed cost and commission sensitivity",
        "verify compatibility/specs",
        "resolve wrong item/refund",
        "re-film after model change",
        "separate creative failure from page/fulfillment failure"
      ],
      "decision_points": [
        "supplier/variant reliable enough",
        "product has observable demo",
        "margin survives sample/commission/returns/spend",
        "shipping claim supportable",
        "backup source or stop",
        "viral-view signal actually converts profitably"
      ],
      "seller_usually_knows": [
        "current supplier listing/quote",
        "intended price",
        "reference/demo concept",
        "target market and broad delivery estimate"
      ],
      "seller_usually_does_not_know": [
        "future stock/price stability",
        "sample and customer batch identity",
        "defect/wrong-item rate",
        "sample route versus customer route",
        "profitability before complete return/ad data"
      ],
      "onboarding_friction": [
        "supplier data lacks API and goes stale",
        "same imagery can hide different model",
        "return/shipping subsidy omitted",
        "demo footage may be another model",
        "seller asks for binary answer despite material unknowns"
      ],
      "evidence_classification": [
        "established_best_practice",
        "operational_hard_constraint",
        "seller_anecdote"
      ],
      "sources": [
        {
          "source_id": "DS01",
          "title": "Dropshipping Fulfillment: The Complete Guide (2026)",
          "publisher": "Shopify",
          "url": "https://www.shopify.com/blog/dropshipping-fulfillment",
          "source_type": "established_product_documentation",
          "evidence_strength": 4
        },
        {
          "source_id": "DS02",
          "title": "How To Start an Online Store Without Inventory (2026)",
          "publisher": "Shopify",
          "url": "https://www.shopify.com/blog/how-to-start-an-online-store-without-inventory",
          "source_type": "established_product_documentation",
          "evidence_strength": 4
        },
        {
          "source_id": "DS03",
          "title": "Product Sourcing Guide: How To Get Started (2026)",
          "publisher": "Shopify",
          "url": "https://www.shopify.com/blog/product-sourcing-apps",
          "source_type": "established_product_documentation",
          "evidence_strength": 4
        },
        {
          "source_id": "DS04",
          "title": "How Does Alibaba Work? Buying and Safety Guide (2026)",
          "publisher": "Shopify",
          "url": "https://www.shopify.com/blog/16665772-alibaba-101-how-to-safely-source-products-from-the-worlds-biggest-supplier-directory",
          "source_type": "established_product_documentation",
          "evidence_strength": 4
        },
        {
          "source_id": "DS05",
          "title": "Product sourcing and supplier monitoring documentation",
          "publisher": "AutoDS Help Center",
          "url": "https://help.autods.com/",
          "source_type": "provider_documentation",
          "evidence_strength": 3
        },
        {
          "source_id": "COM05",
          "title": "Supplier stock and price changes",
          "publisher": "Reddit r/dropshipping",
          "url": "https://www.reddit.com/r/dropshipping/comments/1u9gt9c/how_do_you_track_supplier_stock_and_price_changes/",
          "source_type": "seller_anecdote",
          "evidence_strength": 2
        },
        {
          "source_id": "COM06",
          "title": "Wrong item from dropshipping supplier",
          "publisher": "Reddit r/dropshipping",
          "url": "https://www.reddit.com/r/dropshipping/comments/1sirqc6/how_do_you_verify_product_quality_before_it_ships/",
          "source_type": "seller_anecdote",
          "evidence_strength": 2
        },
        {
          "source_id": "COM07",
          "title": "Unexpected shipping cost and low supplier stock",
          "publisher": "Reddit r/dropshipping",
          "url": "https://www.reddit.com/r/dropshipping/comments/1q15jg9/unexpected_aliexpress_shipping_costs_and_low/",
          "source_type": "seller_anecdote",
          "evidence_strength": 2
        }
      ]
    },
    {
      "segment": "Small agency / VA / creative-ops team",
      "current_workflow": [
        "Receive product/brief data in different client formats",
        "maintain separate swipe files, creator lists, asset folders and reports",
        "coordinate outreach, revisions, rights and approvals",
        "rebuild reports from exports and subjective notes",
        "reuse learning informally through chat/docs rather than versioned PatternKit"
      ],
      "data_sources": [
        "multi-client workspaces",
        "spreadsheets/BI exports",
        "creative libraries/task tools",
        "client product/brand guidelines",
        "creator agreements/invoices",
        "shops/ad accounts"
      ],
      "repeated_manual_steps": [
        "normalize names/IDs",
        "recreate similar briefs",
        "write revision messages",
        "prepare client reports",
        "track rights expiry and approvals",
        "avoid cross-client data leakage"
      ],
      "decision_points": [
        "which private pattern may be reused",
        "which asset deserves client budget",
        "who approves claim/rights exception",
        "structural versus performance-backed finding",
        "which workflow saving justifies software spend"
      ],
      "seller_usually_knows": [
        "client goal/deliverables",
        "campaign operational state",
        "approval owners",
        "historical client context"
      ],
      "seller_usually_does_not_know": [
        "consistent cross-client taxonomy",
        "causal element learning",
        "benchmark transfer validity",
        "actual WTP until hours/spend are avoided"
      ],
      "onboarding_friction": [
        "permissions and isolation",
        "inconsistent schemas",
        "white-label/auditability",
        "demand for bulk import before clean entity mapping"
      ],
      "evidence_classification": [
        "expert_opinion",
        "directional_pattern"
      ],
      "sources": [
        {
          "source_id": "PERF03",
          "title": "How to Make Ads for Meta and TikTok in 2026",
          "publisher": "Motion / Savannah Sanchez",
          "url": "https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026",
          "source_type": "industry_expert_interview",
          "evidence_strength": 3
        },
        {
          "source_id": "PERF09",
          "title": "Creative Strategy Platform Synergies",
          "publisher": "Foreplay",
          "url": "https://www.foreplay.co/post/creative-strategy-platform-synergies",
          "source_type": "industry_product_blog",
          "evidence_strength": 3
        },
        {
          "source_id": "WTP01",
          "title": "Motion Pricing and Plans",
          "publisher": "Motion",
          "url": "https://motionapp.com/llm-info",
          "source_type": "official_product_pricing",
          "evidence_strength": 3
        },
        {
          "source_id": "WTP02",
          "title": "Foreplay Pricing",
          "publisher": "Foreplay",
          "url": "https://www.foreplay.co/pricing",
          "source_type": "official_product_pricing",
          "evidence_strength": 3
        }
      ]
    }
  ],
  "cross_segment_stages": [
    {
      "stage": "1_product_and_policy_intake",
      "decision": "Can this exact product be listed, fulfilled and tested?",
      "minimum_output": [
        "Verified Product Context",
        "typed unknowns",
        "policy gates",
        "economics completeness"
      ],
      "hard_stops": [
        "prohibited/restricted unqualified",
        "exact SKU unknown",
        "shipping basis missing",
        "material IP risk"
      ]
    },
    {
      "stage": "2_reference_and_pattern_research",
      "decision": "Which structures are worth studying without treating popularity as proof?",
      "minimum_output": [
        "Creative DNA evidence",
        "PatternKit candidate",
        "copycat risk",
        "performance-evidence status"
      ],
      "hard_stops": [
        "reference assets copied into final",
        "winning label without linked evidence"
      ]
    },
    {
      "stage": "3_viral_kit_and_campaign_pack",
      "decision": "Which differentiated hypothesis should be produced?",
      "minimum_output": [
        "three differentiated ViralKits",
        "selected hypothesis",
        "brief requirements",
        "claims/rights/disclosure scope"
      ],
      "hard_stops": [
        "material product facts missing",
        "unapproved claim",
        "personalization flow unknown"
      ]
    },
    {
      "stage": "4_creator_sample_and_production",
      "decision": "Which creator/collaboration deserves money or sample?",
      "minimum_output": [
        "Creator Fit evidence",
        "Sample ROI status",
        "dates",
        "deliverables/revision scope"
      ],
      "hard_stops": [
        "economics insufficient",
        "stock/variant unverified",
        "deadline unknown"
      ]
    },
    {
      "stage": "5_preflight_and_revision",
      "decision": "Approve, revise, reshoot or reject?",
      "minimum_output": [
        "expected-versus-observed",
        "blockers",
        "editability",
        "creator message",
        "confidence"
      ],
      "hard_stops": [
        "product mismatch",
        "unsupported high-risk claim",
        "missing disclosure",
        "unclear proof demo"
      ]
    },
    {
      "stage": "6_rights_spark_and_activation",
      "decision": "Is the exact approved asset usable in the intended channel?",
      "minimum_output": [
        "rights card",
        "authorization/expiry",
        "audio",
        "tag publish check",
        "activation status"
      ],
      "hard_stops": [
        "rights incomplete",
        "authorization invalid",
        "audio scope insufficient",
        "offer expired"
      ]
    },
    {
      "stage": "7_outcome_and_learning",
      "decision": "Scale, fix, hold, kill, rehire or run next test?",
      "minimum_output": [
        "normalized metrics/economics",
        "confidence",
        "diagnosis",
        "next experiment",
        "PatternKit evidence update"
      ],
      "hard_stops": [
        "unmapped metrics",
        "GMV without cost",
        "confounded test",
        "insufficient evidence"
      ]
    }
  ],
  "just_in_time_questions": [
    {
      "trigger": "health_or_safety_claim",
      "question": "What exact seller-approved claim and evidence object support this wording?",
      "fallback": "Remove claim and route to expert review."
    },
    {
      "trigger": "mockup_only_pod",
      "question": "Do you have the exact physical sample and provider/template version?",
      "fallback": "Concept-only; block quality/texture/placement proof."
    },
    {
      "trigger": "refundable_sample",
      "question": "What deadline and sales goal appear in the live TikTok Shop collaboration?",
      "fallback": "Return policy_conflict; do not hard-code 90 or 120 days."
    },
    {
      "trigger": "free_sample_recommendation",
      "question": "What are all-in sample cost, contribution/order, creator reliability, stock and delivery SLA?",
      "fallback": "Affiliate-only or seller confirmation required."
    },
    {
      "trigger": "shipping_claim",
      "question": "Which customer route, handling time, destination and carrier evidence support the promise?",
      "fallback": "Remove shipping claim."
    },
    {
      "trigger": "spark_ready",
      "question": "Which authorization method, post, advertiser, expiry and contractual paid rights apply?",
      "fallback": "Organic-only."
    },
    {
      "trigger": "winning_label",
      "question": "Which linked assets, metric, window, spend/distribution, sample size and outcome support “winning”?",
      "fallback": "Rename PatternKit candidate."
    },
    {
      "trigger": "creator_testimonial",
      "question": "Has the creator actually used the product, and what material connection must be disclosed?",
      "fallback": "Use demonstration/spokesperson format."
    },
    {
      "trigger": "scale_recommendation",
      "question": "Are price, COGS, fees, shipping, commission, returns, sample, creator cost, ad cost, stock and rights current?",
      "fallback": "economics_insufficient."
    }
  ],
  "minimum_input_per_feature": [
    {
      "feature": "Product Readiness",
      "minimum": [
        "exact SKU/product",
        "commerce model",
        "market/channel",
        "listing/media",
        "price",
        "COGS or explicit unknown",
        "fulfillment type",
        "shipping evidence status",
        "category policy",
        "sample status"
      ],
      "high_value_optional": [
        "returns/complaints",
        "supplier QC",
        "inventory",
        "commission",
        "offer"
      ],
      "partial": true,
      "blocked_when_missing": [
        "paid-test readiness",
        "free-sample recommendation",
        "shipping approval",
        "proof-heavy readiness"
      ]
    },
    {
      "feature": "Creative DNA",
      "minimum": [
        "immutable asset/reference",
        "source/provenance",
        "platform",
        "asset type"
      ],
      "high_value_optional": [
        "product context",
        "performance metrics"
      ],
      "partial": true,
      "blocked_when_missing": [
        "winning label",
        "product-match conclusion",
        "claim approval"
      ]
    },
    {
      "feature": "PatternKit Candidate",
      "minimum": [
        "Creative DNA",
        "evidence IDs",
        "applicability hypothesis",
        "source asset IDs"
      ],
      "high_value_optional": [
        "comparable assets",
        "performance metrics",
        "contraindications"
      ],
      "partial": true,
      "blocked_when_missing": [
        "validated/high-confidence status"
      ]
    },
    {
      "feature": "ViralKit / Campaign Pack",
      "minimum": [
        "verified product context",
        "objective",
        "buyer context",
        "selected PatternKit",
        "allowed/prohibited claims",
        "deliverables",
        "disclosure",
        "rights request"
      ],
      "high_value_optional": [
        "creator profile",
        "economics",
        "past performance"
      ],
      "partial": true,
      "blocked_when_missing": [
        "creator-ready/send-ready"
      ]
    },
    {
      "feature": "Creator Fit",
      "minimum": [
        "creator identity",
        "sample content",
        "product",
        "objective",
        "market",
        "known audience/reliability"
      ],
      "high_value_optional": [
        "past sample/post/GMV",
        "audience geo"
      ],
      "partial": true,
      "blocked_when_missing": [
        "high-confidence free-sample/rehire decision"
      ]
    },
    {
      "feature": "Sample ROI",
      "minimum": [
        "sample type",
        "product/production/shipping cost",
        "creator fee",
        "commission",
        "price",
        "profit inputs",
        "stock/fulfillment",
        "creator reliability"
      ],
      "high_value_optional": [
        "expected order distribution",
        "returns",
        "past GMV/sample"
      ],
      "partial": false,
      "blocked_when_missing": [
        "collaboration recommendation",
        "break-even orders/GMV"
      ]
    },
    {
      "feature": "UGC Preflight",
      "minimum": [
        "immutable draft",
        "exact product",
        "approved brief/version",
        "objective"
      ],
      "high_value_optional": [
        "contract/rights",
        "listing/offer",
        "raw footage"
      ],
      "partial": true,
      "blocked_when_missing": [
        "brief alignment without brief",
        "paid-ready without rights",
        "claim-safe without evidence"
      ]
    },
    {
      "feature": "Rights & Spark",
      "minimum": [
        "exact asset/post",
        "creator/account",
        "channels",
        "paid use",
        "duration",
        "editing/raw",
        "geography",
        "proof",
        "Spark method/status/expiry",
        "audio status"
      ],
      "high_value_optional": [
        "renewal price",
        "sublicensing",
        "derivative approval"
      ],
      "partial": false,
      "blocked_when_missing": [
        "paid-ready",
        "cross-channel-ready",
        "Spark-ready"
      ]
    },
    {
      "feature": "Performance Loop",
      "minimum": [
        "asset/product/creator/campaign mapping",
        "metric definitions",
        "date/attribution window",
        "denominator",
        "orders/GMV for commerce conclusion",
        "cost/economics for profit/scale"
      ],
      "high_value_optional": [
        "audience/placement",
        "inventory",
        "offer/page changes",
        "returns",
        "rights"
      ],
      "partial": true,
      "blocked_when_missing": [
        "causal claim",
        "profit/scale recommendation",
        "high-confidence fatigue"
      ]
    }
  ],
  "bulk_import_behavior": {
    "first_formats": [
      "Product CSV with exact SKU/provider IDs",
      "Creator list with handles and fit/reliability",
      "Asset manifest with product/creator/campaign/brief version",
      "TikTok Shop/Ads metrics CSV with mapping preview",
      "Rights template with channel/duration/paid/editing/Spark"
    ],
    "rules": [
      "Import to staging; never silently merge ambiguous entities",
      "Show duplicate/stale/missing/conflicting rows before commit",
      "Require exact product/variant mapping",
      "Preserve original file, checksum, mapping, timezone, currency and actor",
      "Allow partial acceptance and exception export",
      "Never create high-confidence PatternKit evidence from unmapped rows"
    ],
    "cost_safety": [
      "Apply deterministic blockers before LLM",
      "Queue expensive video analysis with estimate/cancel",
      "Require seller confirmation before sending messages or changing platform state"
    ]
  },
  "exception_handling": [
    {
      "exception": "official_policy_conflict",
      "behavior": "Show both official sources/dates, prefer live campaign object, lock deterministic deadline."
    },
    {
      "exception": "product_or_variant_unmatched",
      "behavior": "Do not merge or score product-specific dimensions; request explicit seller selection."
    },
    {
      "exception": "supplier_data_stale",
      "behavior": "Allow ideation; block offer, shipping, sample and scale decisions."
    },
    {
      "exception": "no_physical_sample",
      "behavior": "Allow concept generation; mark quality/proof/compatibility unknown and block proof-heavy paid readiness."
    },
    {
      "exception": "rights_missing",
      "behavior": "Allow organic creative review; mark organic-only and generate rights request."
    },
    {
      "exception": "low_performance_volume",
      "behavior": "Return directional learning and next-test plan, not winner/loser or causal claim."
    },
    {
      "exception": "raw_footage_can_fix",
      "behavior": "Prefer edit with exact clips/timestamps; avoid unnecessary reshoot."
    },
    {
      "exception": "seller_override",
      "behavior": "Require actor, reason, scope, expiry and audit log; never erase the blocker."
    }
  ],
  "output_preferences": {
    "seller": [
      "Decision first",
      "money/risk impact",
      "expected-versus-observed with evidence",
      "required fixes before optional optimizations",
      "copyable creator message",
      "confidence/missing inputs/source labels",
      "stable IDs and export"
    ],
    "creator": [
      "respectful natural language",
      "required versus optional",
      "exact scene/line",
      "edit versus reshoot",
      "deadline/scope",
      "no irrelevant internal score or margin"
    ],
    "agency": [
      "client summary plus evidence appendix",
      "version/approval history",
      "bulk exception queue",
      "white-label export",
      "cost/usage controls",
      "privacy isolation"
    ]
  },
  "actionability_contract": {
    "required": [
      "action_label",
      "reason_codes",
      "evidence_ids",
      "expected",
      "observed",
      "severity",
      "editability",
      "next_action",
      "owner",
      "due_or_expiry_if_known",
      "confidence",
      "missing_inputs",
      "policy/model/input versions"
    ],
    "forbidden": [
      "score-only output",
      "generic “make it viral” feedback",
      "performance guarantee",
      "silent rights/economics/policy assumption",
      "winning label from popularity"
    ]
  },
  "repeat_use_triggers": [
    "new product/variant",
    "new reference",
    "sample request",
    "sample shipped/delivered/due",
    "new draft/revision",
    "rights/Spark expiry",
    "offer/listing/supplier change",
    "metrics import",
    "fatigue/fulfillment exception",
    "next Variant/ViralKit request"
  ],
  "willingness_to_pay": {
    "signals": [
      {
        "finding": "Existing creative-workflow, intelligence and UGC platforms charge recurring fees. This is a market proxy, not direct Viraldy WTP.",
        "classification": "directional_pattern",
        "sources": [
          {
            "source_id": "WTP01",
            "title": "Motion Pricing and Plans",
            "publisher": "Motion",
            "url": "https://motionapp.com/llm-info",
            "source_type": "official_product_pricing",
            "evidence_strength": 3
          },
          {
            "source_id": "WTP02",
            "title": "Foreplay Pricing",
            "publisher": "Foreplay",
            "url": "https://www.foreplay.co/pricing",
            "source_type": "official_product_pricing",
            "evidence_strength": 3
          },
          {
            "source_id": "UGC06",
            "title": "Influencer and UGC Campaign Pricing",
            "publisher": "Insense",
            "url": "https://insense.pro/pricing",
            "source_type": "official_product_pricing",
            "evidence_strength": 3
          }
        ]
      },
      {
        "finding": "Seller anecdotes describe sample waste, no-post creators, high views with weak sales, stockouts, wrong items and shipping-cost shocks.",
        "classification": "seller_anecdote",
        "sources": [
          {
            "source_id": "COM01",
            "title": "30 samples sent, no sale",
            "publisher": "Reddit r/TikTokshop",
            "url": "https://www.reddit.com/r/TikTokshop/comments/1ux5rk0/30_samples_sent_no_sale/",
            "source_type": "seller_anecdote",
            "evidence_strength": 2
          },
          {
            "source_id": "COM02",
            "title": "1.4M-view affiliate video with weak sales",
            "publisher": "Reddit r/TikTokshop",
            "url": "https://www.reddit.com/r/TikTokshop/comments/1lgdfzj/our_tiktok_affiliate_video_went_viral_14m_views/",
            "source_type": "seller_anecdote",
            "evidence_strength": 2
          },
          {
            "source_id": "COM03",
            "title": "Affiliates receiving samples but not posting",
            "publisher": "Reddit r/TikTokshop",
            "url": "https://www.reddit.com/r/TikTokshop/comments/1b9p0cw/what_do_you_do_when_affiliates_dont_post_any/",
            "source_type": "seller_anecdote",
            "evidence_strength": 2
          },
          {
            "source_id": "COM05",
            "title": "Supplier stock and price changes",
            "publisher": "Reddit r/dropshipping",
            "url": "https://www.reddit.com/r/dropshipping/comments/1u9gt9c/how_do_you_track_supplier_stock_and_price_changes/",
            "source_type": "seller_anecdote",
            "evidence_strength": 2
          },
          {
            "source_id": "COM06",
            "title": "Wrong item from dropshipping supplier",
            "publisher": "Reddit r/dropshipping",
            "url": "https://www.reddit.com/r/dropshipping/comments/1sirqc6/how_do_you_verify_product_quality_before_it_ships/",
            "source_type": "seller_anecdote",
            "evidence_strength": 2
          },
          {
            "source_id": "COM07",
            "title": "Unexpected shipping cost and low supplier stock",
            "publisher": "Reddit r/dropshipping",
            "url": "https://www.reddit.com/r/dropshipping/comments/1q15jg9/unexpected_aliexpress_shipping_costs_and_low/",
            "source_type": "seller_anecdote",
            "evidence_strength": 2
          }
        ]
      },
      {
        "finding": "Expert/operator sources describe scattered briefs, feedback, QC and reporting work.",
        "classification": "expert_opinion",
        "sources": [
          {
            "source_id": "PERF03",
            "title": "How to Make Ads for Meta and TikTok in 2026",
            "publisher": "Motion / Savannah Sanchez",
            "url": "https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026",
            "source_type": "industry_expert_interview",
            "evidence_strength": 3
          },
          {
            "source_id": "PERF09",
            "title": "Creative Strategy Platform Synergies",
            "publisher": "Foreplay",
            "url": "https://www.foreplay.co/post/creative-strategy-platform-synergies",
            "source_type": "industry_product_blog",
            "evidence_strength": 3
          }
        ]
      }
    ],
    "hypothesized_paid_jobs": [
      "avoid one bad sample/supplier-dependent campaign",
      "reduce one revision or reshoot cycle",
      "prevent unauthorized/weak paid activation",
      "prioritize a smaller slate",
      "replace recurring spreadsheet/report work",
      "build private reusable learning"
    ],
    "not_yet_proven": [
      "price by seller size/geo",
      "strongest paid wedge",
      "retention after first report",
      "measured savings or GMV/profit lift",
      "seat versus credits preference"
    ],
    "validation_plan": [
      "Recruit active sellers with live spend/workflow",
      "run concierge analysis on current decisions",
      "ask for a paid pilot after first value event",
      "measure changed action and avoided cost/time",
      "segment by weekly volume/team/money at risk"
    ]
  }
}
```

# E. Golden Cases
The cases are synthetic regression fixtures. “Verified” means verified against the fixture manifest/evidence, not a claim about a real product or market result.

## GC-TTS-DEMO-001 — TikTok Shop US product demo — CounterSpace Expandable Counter Rack

### Fixture Integrity
```json
{
  "statement": "All product, cost and creative facts are verified only inside this synthetic fixture manifest and physical-sample evidence. They are not real-market claims or performance predictions.",
  "manifest_version": "gc-tts-demo-001:v1",
  "evidence_assets": [
    {
      "id": "E-PROD-001",
      "type": "fixture_manifest",
      "description": "SKU, dimensions, included items and fixture economics."
    },
    {
      "id": "E-PROD-002",
      "type": "physical_sample_stills",
      "description": "Exact white single rack and continuous expansion/setup."
    },
    {
      "id": "E-PROD-003",
      "type": "seller_confirmation",
      "description": "No universal-fit, weight, antimicrobial or fast-delivery claim approved."
    }
  ]
}
```

### Verified Product Context
```json
{
  "product_id": "PROD-CSR-001",
  "sku": "CSR-WHT-01",
  "product_name": "CounterSpace Expandable Counter Rack",
  "commerce_model": "seller-stocked TikTok Shop US fixture",
  "market": "US",
  "variant": "white, single rack",
  "fixture_price_usd": 24.99,
  "fixture_cogs_usd": 8.4,
  "fixture_outbound_shipping_usd": 4.1,
  "fixture_platform_fees_usd": 2.0,
  "fixture_commission_percent": 15,
  "verified_dimensions": "adjusts from 16 to 22 inches in the fixture; buyer must measure intended surface",
  "included_items": [
    "one rack",
    "two removable rails",
    "instruction card"
  ],
  "mechanism": "two halves slide to widen the elevated organizing surface",
  "approved_benefits": [
    "adds an elevated organizing surface",
    "adjusts within verified fixture range",
    "visible organization result"
  ],
  "claims_not_approved": [
    "fits every sink/counter",
    "specific load capacity",
    "antimicrobial benefit",
    "arrives in two days",
    "guaranteed organization result"
  ],
  "physical_sample_status": "verified_in_fixture",
  "listing_snapshot_status": "verified_in_fixture",
  "unknowns": [
    "real stock",
    "real return rate",
    "live listing/offer",
    "actual fulfillment metrics",
    "real fees/commission"
  ]
}
```

### Source Creative Observations
```json
{
  "reference_asset_id": "REF-KITCHEN-PSR-001",
  "source_status": "synthetic reference; no performance evidence",
  "observations": [
    {
      "time": "0:00–0:01.8",
      "observation": "Messy counter problem before narration."
    },
    {
      "time": "0:01.8–0:04.0",
      "observation": "Product enters and expands in one continuous shot."
    },
    {
      "time": "0:04.0–0:10.5",
      "observation": "Same items move to the rack in same camera position."
    },
    {
      "time": "0:10.5–0:14.0",
      "observation": "Before/result; no offer, disclosure, product-tag or performance evidence."
    }
  ],
  "performance_evidence_status": "none; do not call winning",
  "copycat_note": "Study structure only; script, objects, creator, framing and scene execution must be original."
}
```

### Creative Dna
```json
{
  "dna_id": "DNA-REF-KITCHEN-001:v1",
  "hook_type": "visual_problem",
  "message_angle": "small-space organization",
  "creator_persona": "hands-only home organizer",
  "format": "locked-camera before/process/result",
  "narrative": [
    "problem",
    "product reveal",
    "continuous setup",
    "result"
  ],
  "demo_type": "physical transformation",
  "proof_type": "matched before/result",
  "offer": "absent",
  "cta": "absent",
  "first_product_appearance_second": 1.8,
  "risks": [
    "exact product match not externally verified",
    "no disclosure context",
    "no performance evidence"
  ],
  "confidence": "high for observed structure; none for commercial performance"
}
```

### Patternkit Candidate
```json
{
  "pattern_kit_id": "PK-HOME-PROBLEM-TRANSFORM-001:v1",
  "status": "candidate",
  "name": "Problem visual → exact product reveal → continuous transformation",
  "classification": "established_best_practice",
  "keep": [
    "real problem state",
    "early product role",
    "continuous mechanism",
    "matched result"
  ],
  "contraindications": [
    "no visible product change",
    "deceptive editing required",
    "fit cannot be verified",
    "health/safety outcome"
  ],
  "applicability": [
    "home organization",
    "visual utility product"
  ],
  "performance_evidence_status": "no linked performance; test required",
  "source_assets": [
    "REF-KITCHEN-PSR-001"
  ]
}
```

### Viral Kit Concepts
```json
[
  {
    "viral_kit_id": "VK-CSR-A:v1",
    "name": "The counter-space reset",
    "angle": "small-apartment crowded counter",
    "hook": "“I needed another level, not another cabinet.” over the real problem scene",
    "mechanic": "continuous expand-and-organize",
    "proof": "same-area before/result",
    "creator_fit": "small-space/home organizer",
    "hypothesis": "problem recognition plus mechanism may improve qualified product clicks",
    "evidence_status": "untested"
  },
  {
    "viral_kit_id": "VK-CSR-B:v1",
    "name": "Measure first, then expand",
    "angle": "fit-objection resolution",
    "hook": "Tape measure and “Will it fit your space?”",
    "mechanic": "measure, expand within verified range, show limitation",
    "proof": "visible measurement",
    "creator_fit": "practical home/DIY reviewer",
    "hypothesis": "fit education may improve qualified clicks and reduce mismatch",
    "evidence_status": "untested; compatibility-sensitive"
  },
  {
    "viral_kit_id": "VK-CSR-C:v1",
    "name": "One-minute kitchen reset",
    "angle": "routine convenience",
    "hook": "real cooking cleanup moment",
    "mechanic": "insert product into existing routine",
    "proof": "same surface and items; no universal time-saving claim",
    "creator_fit": "home-cooking creator",
    "hypothesis": "routine relevance may outperform standalone demo for cooking audience",
    "evidence_status": "untested"
  }
]
```

### Creative Campaign Pack
```json
{
  "campaign_id": "CAMP-CSR-001",
  "selected_viral_kit": "VK-CSR-A:v1",
  "objective": "TikTok Shop affiliate organic test; paid only after rights/economics review",
  "target_buyer": "US small-space renter/household with crowded counter",
  "core_angle": "add an elevated organizing surface without universal-fit claim",
  "creator_brief": "Film an original natural counter reset with the exact white single-rack sample.",
  "deliverables": [
    "one 20–28 second vertical post",
    "one clean base edit",
    "two alternate hooks only if contracted"
  ],
  "must_show": [
    "exact white variant",
    "real crowded surface",
    "continuous expansion",
    "same items before/result",
    "measurement/fit limitation",
    "seller-approved CTA",
    "correct product tag at publish"
  ],
  "must_not_show_or_say": [
    "fits every sink/counter",
    "weight capacity",
    "health benefit",
    "two-day delivery",
    "guaranteed result",
    "reference script/footage"
  ],
  "disclosure": "commercial-content setting plus clear material-connection disclosure when gifted/paid/commissioned",
  "creator_flexible_zones": [
    "natural wording",
    "home setting",
    "safe objects",
    "editing rhythm after clear mechanism"
  ],
  "rights_request": {
    "organic_post": true,
    "Spark_paid_use": "requested_not_granted",
    "raw_footage": "only if contracted",
    "editing": "contract-specific",
    "duration": "seller_confirmation_required"
  },
  "revision_scope": "Fixture assumes one in-scope edit and one reshoot only for missed must-show/material mismatch; not a universal contract rule."
}
```

### Compiled Requirements
```json
[
  {
    "id": "R1",
    "requirement": "Exact SKU/variant",
    "source": "TT-CONTENT-001",
    "severity": "blocker",
    "verification": "visual match to E-PROD-002"
  },
  {
    "id": "R2",
    "requirement": "Product in opening beat by 2.5s for this selected concept",
    "source": "Campaign Pack, not universal TikTok rule",
    "severity": "high",
    "verification": "first_product_appearance_second <= 2.5"
  },
  {
    "id": "R3",
    "requirement": "Continuous expansion/setup",
    "source": "selected demo mechanism",
    "severity": "high",
    "verification": "unbroken expand action"
  },
  {
    "id": "R4",
    "requirement": "No universal-fit/unapproved capacity claim",
    "source": "TT-CLAIM-001 + fixture",
    "severity": "blocker",
    "verification": "ASR/OCR scan"
  },
  {
    "id": "R5",
    "requirement": "Matched before/result",
    "source": "PatternKit proof",
    "severity": "medium",
    "verification": "same area/object continuity"
  },
  {
    "id": "R6",
    "requirement": "Disclosure complete",
    "source": "DISC-001",
    "severity": "blocker",
    "verification": "creative + platform metadata"
  },
  {
    "id": "R7",
    "requirement": "Correct product tag at publish",
    "source": "SAMPLE-001 / content match",
    "severity": "blocker_at_publish",
    "verification": "post metadata"
  },
  {
    "id": "R8",
    "requirement": "Paid rights, Spark authorization and cleared audio",
    "source": "UGC-RIGHTS-001 / SPARK-001 / UGC-MUSIC-001",
    "severity": "blocker_for_paid",
    "verification": "rights card"
  }
]
```

### First Draft Ugc Observations
```json
{
  "asset_id": "UGC-CSR-D1",
  "duration_seconds": 24.0,
  "observations": [
    {
      "time": "0:00–0:05.9",
      "observed": "Talking-head “kitchen hack”; no relevant problem or product."
    },
    {
      "time": "0:06.2",
      "observed": "Exact white rack first appears."
    },
    {
      "time": "0:06.2–0:10.0",
      "observed": "Jump cuts omit expansion mechanism."
    },
    {
      "time": "0:10.4",
      "observed": "“It fits every sink.”"
    },
    {
      "time": "0:13.0–0:18.0",
      "observed": "Result from different angle; continuity weak."
    },
    {
      "time": "0:19.5–0:23.0",
      "observed": "Generic CTA; no visible disclosure."
    }
  ],
  "publish_metadata_unknown": [
    "platform disclosure",
    "correct product tag",
    "audio license"
  ],
  "rights_unknown": [
    "paid duration",
    "Spark authorization",
    "editing/raw footage"
  ]
}
```

### Preflight Expected Vs Observed
```json
[
  {
    "requirement_id": "R1",
    "expected": "Exact white single rack",
    "observed": "Exact sample at 0:06.2",
    "status": "pass",
    "severity": "blocker",
    "editability": "n/a"
  },
  {
    "requirement_id": "R2",
    "expected": "Product by 0:02.5 for this concept",
    "observed": "0:06.2",
    "status": "fail",
    "severity": "high",
    "editability": "edit if earlier clip exists; otherwise reshoot"
  },
  {
    "requirement_id": "R3",
    "expected": "Continuous expansion/setup",
    "observed": "Jump cuts hide action",
    "status": "fail",
    "severity": "high",
    "editability": "reshoot"
  },
  {
    "requirement_id": "R4",
    "expected": "No universal-fit claim",
    "observed": "“fits every sink”",
    "status": "fail",
    "severity": "blocker",
    "editability": "remove/replace audio-overlay or reshoot line"
  },
  {
    "requirement_id": "R5",
    "expected": "Matched before/result",
    "observed": "Different angle",
    "status": "fail",
    "severity": "medium",
    "editability": "reshoot preferred"
  },
  {
    "requirement_id": "R6",
    "expected": "Clear disclosure",
    "observed": "Absent in file; setting unknown",
    "status": "fail",
    "severity": "blocker",
    "editability": "edit plus publish metadata"
  },
  {
    "requirement_id": "R7",
    "expected": "Correct product tag",
    "observed": "Cannot verify from draft",
    "status": "unknown",
    "severity": "blocker_at_publish",
    "editability": "publish check"
  },
  {
    "requirement_id": "R8",
    "expected": "Rights/Spark/audio complete",
    "observed": "Not provided",
    "status": "unknown",
    "severity": "blocker_for_paid",
    "editability": "non-creative fix"
  }
]
```

### Preflight Decision
```json
{
  "structural_score_fixture_only": 61,
  "score_type": "deterministic structural fixture; not a performance prediction",
  "confidence": "high for observed blockers",
  "action_label": "reshoot_required_before_post",
  "hard_blockers": [
    "universal-fit claim",
    "missing disclosure",
    "unclear mechanism"
  ],
  "optional": [
    "stronger matched result",
    "CTA wording"
  ]
}
```

### Seller Action Plan
```json
[
  {
    "priority": 1,
    "owner": "seller",
    "action": "Confirm fit wording, disclosure, exact product tag and revised due date."
  },
  {
    "priority": 2,
    "owner": "creator",
    "action": "Reshoot opening and continuous expansion; remove universal-fit claim."
  },
  {
    "priority": 3,
    "owner": "seller/creator",
    "action": "Add disclosure and enable platform setting at publish."
  },
  {
    "priority": 4,
    "owner": "seller",
    "action": "Verify exact product tag on published post."
  },
  {
    "priority": 5,
    "owner": "rights owner",
    "action": "Collect paid rights, clean audio and Spark authorization before paid use."
  },
  {
    "priority": 6,
    "owner": "operator",
    "action": "Keep paid test blocked until real economics, stock and fulfillment health are complete."
  }
]
```

### Creator Revision Message
The exact product looks correct and the counter-reset idea is usable. Please reshoot the opening/setup so the crowded surface and white rack appear within the first 2.5 seconds for this concept, and show the rack expanding in one continuous shot. Remove “fits every sink” and use the seller-approved line: “Measure your space; this sample adjusts from 16 to 22 inches.” Keep the camera angle consistent for before/result, add the approved commercial disclosure, and send a clean-audio cut. The seller will verify the product tag and Spark rights separately.

### Revised Draft
```json
{
  "asset_id": "UGC-CSR-D2",
  "duration_seconds": 23.4,
  "changes": [
    {
      "time": "0:00–0:01.2",
      "change": "Crowded surface and disclosure."
    },
    {
      "time": "0:01.3",
      "change": "Exact rack enters."
    },
    {
      "time": "0:01.3–0:07.8",
      "change": "Continuous expansion/setup."
    },
    {
      "time": "0:08.0–0:13.5",
      "change": "Same-angle before/result."
    },
    {
      "time": "0:13.6",
      "change": "Verified measurement line."
    },
    {
      "time": "0:19.0–0:22.5",
      "change": "Approved CTA; clean audio."
    }
  ],
  "remaining_unknown": [
    "platform disclosure metadata",
    "published product tag",
    "paid rights",
    "Spark authorization",
    "live economics/fulfillment"
  ]
}
```

### Final Decision
```json
{
  "organic": "approve_after_publish_checks",
  "paid_or_spark": "blocked_pending_rights_economics_authorization",
  "reason": "Creative blockers fixed; platform metadata and paid-use inputs remain unknown.",
  "confidence": "high structural; none for sales performance"
}
```

### Missing Economic Or Rights Inputs
```json
[
  "live offer/inventory",
  "actual fees/commission/returns",
  "account fulfillment metrics",
  "paid use channels/duration",
  "Spark method/code/expiry",
  "publish disclosure/tag proof"
]
```

### Expected Learning
```json
[
  "Compare problem-first against product-first while keeping offer/page/audience stable where practical.",
  "Use product clicks/orders and complete economics for commerce learning; views are diagnostic only.",
  "Track fit questions/returns.",
  "Do not promote PatternKit beyond candidate until linked evidence is sufficient."
]
```

### Expert Labels
```json
[
  "official_hard_rule: product, claim, disclosure, tag and rights gates",
  "established_best_practice: continuous mechanism and matched proof",
  "contextual_guideline: 2.5-second reveal is campaign-specific",
  "directional_pattern: small-space persona",
  "insufficient_evidence: no performance/profit conclusion"
]
```

### Seller Usefulness Criteria
```json
[
  "revision message is sendable",
  "edit versus reshoot is clear",
  "organic and Spark readiness are separate",
  "no universal timing/fit/GMV promise",
  "each blocker links to evidence and requirement"
]
```

## GC-POD-PERS-001 — POD personalized product — Pet-name embroidered cap

### Fixture Integrity
```json
{
  "statement": "All product, personalization, production, cost and sample facts are synthetic fixture facts verified against the fixture manifest, approved preview and physical-sample evidence.",
  "manifest_version": "gc-pod-pers-001:v1",
  "evidence_assets": [
    {
      "id": "POD-E-001",
      "type": "fixture_manifest",
      "description": "Navy cap, cream thread, template and fixture economics."
    },
    {
      "id": "POD-E-002",
      "type": "approved_preview",
      "description": "Name “Milo”, font F-02, center-front placement, template v3."
    },
    {
      "id": "POD-E-003",
      "type": "physical_sample",
      "description": "Exact navy cap embroidered “Milo” in cream thread."
    },
    {
      "id": "POD-E-004",
      "type": "seller_confirmation",
      "description": "No any-font/symbol, handmade, fixed-cutoff or guaranteed-reaction claim approved."
    }
  ]
}
```

### Verified Product Context
```json
{
  "product_id": "PROD-POD-CAP-001",
  "sku": "POD-CAP-NAVY-EMB-01",
  "product_name": "Personalized Pet-Name Embroidered Cap",
  "commerce_model": "POD made-to-order fixture",
  "market": "US",
  "variant": "navy adult cap, cream thread, font F-02",
  "fixture_price_usd": 29.95,
  "fixture_provider_base_cost_usd": 13.6,
  "fixture_provider_shipping_usd": 5.2,
  "fixture_personalization_labor_usd": 1.4,
  "fixture_platform_fees_usd": 2.4,
  "personalization_fields": {
    "name_text": "1–12 Latin letters and spaces in this fixture",
    "font": "F-02 only",
    "thread_color": "cream only",
    "preview_required": true
  },
  "sample_personalization": "Milo",
  "physical_sample_status": "verified_in_fixture",
  "approved_benefits": [
    "visible personalized name",
    "gift/identity relevance",
    "seller review before production"
  ],
  "claims_not_approved": [
    "any name/font/symbol",
    "exact screen-to-thread color match",
    "handmade by seller/creator",
    "guaranteed emotional reaction",
    "guaranteed occasion delivery"
  ],
  "ip_status": "generic name and seller-owned layout in fixture; real designs still require clearance",
  "unknowns": [
    "real provider SLA",
    "reprint/defect rate",
    "live order cutoff",
    "real returns/cancellations",
    "creator rights"
  ]
}
```

### Source Creative Observations
```json
{
  "reference_asset_id": "REF-POD-REVEAL-001",
  "source_status": "synthetic reference; no performance evidence",
  "observations": [
    {
      "time": "0:00–0:02.0",
      "observation": "Pet-owner context establishes recipient identity."
    },
    {
      "time": "0:02.0–0:05.0",
      "observation": "Generic/base product before personalization."
    },
    {
      "time": "0:05.0–0:10.0",
      "observation": "Name reveal and embroidery close-up."
    },
    {
      "time": "0:10.0–0:15.0",
      "observation": "Gift handoff/reaction; product detail becomes less visible."
    }
  ],
  "performance_evidence_status": "none",
  "copycat_note": "Use personalization-reveal mechanism only; do not copy slogan, design, recipient, reaction or scene order."
}
```

### Creative Dna
```json
{
  "dna_id": "DNA-REF-POD-001:v1",
  "hook_type": "recipient_identity",
  "message_angle": "personalized pet-owner gift",
  "creator_persona": "pet owner / gift giver",
  "format": "identity setup → reveal → detail → reaction",
  "narrative": [
    "recipient context",
    "customization reveal",
    "physical detail",
    "reaction"
  ],
  "demo_type": "personalization reveal",
  "proof_type": "physical close-up",
  "psychology": [
    "identity",
    "recognition",
    "gift anticipation"
  ],
  "risks": [
    "reaction may overwhelm product detail",
    "example personalization may be unclear",
    "no performance evidence"
  ],
  "confidence": "high for observed structure; none for performance"
}
```

### Patternkit Candidate
```json
{
  "pattern_kit_id": "PK-POD-PERSONALIZATION-REVEAL-001:v1",
  "status": "candidate",
  "name": "Recipient context → personalization process/reveal → physical detail",
  "classification": "established_best_practice",
  "keep": [
    "recipient specificity",
    "input-to-output transformation",
    "physical close-up",
    "example labeling"
  ],
  "contraindications": [
    "mockup-only proof",
    "checkout cannot support shown option",
    "IP-dependent design",
    "unverified occasion cutoff"
  ],
  "applicability": [
    "name/photo/date customization",
    "giftable visible personalization"
  ],
  "performance_evidence_status": "no linked product outcome; test required"
}
```

### Viral Kit Concepts
```json
[
  {
    "viral_kit_id": "VK-POD-CAP-A:v1",
    "name": "From one name to their cap",
    "angle": "maker/process transparency",
    "hook": "Show the approved name input and ask “How does this become the final cap?”",
    "mechanic": "screen preview → embroidery process → exact physical reveal",
    "proof": "preview and sample match",
    "creator_fit": "maker/process or small-business creator",
    "hypothesis": "process transparency may increase confidence and reduce personalization questions",
    "evidence_status": "untested"
  },
  {
    "viral_kit_id": "VK-POD-CAP-B:v1",
    "name": "The pet-owner identity reveal",
    "angle": "identity/recognition",
    "hook": "“For the person whose pet is part of every outfit.”",
    "mechanic": "day-in-life context then close-up name reveal",
    "proof": "physical cap and real creator context",
    "creator_fit": "genuine pet-owner lifestyle creator",
    "hypothesis": "identity fit may improve qualified personalization starts",
    "evidence_status": "untested"
  },
  {
    "viral_kit_id": "VK-POD-CAP-C:v1",
    "name": "Gift handoff plus product detail",
    "angle": "recipient reaction",
    "hook": "anticipation before the personalized name is visible",
    "mechanic": "handoff, recognition, then deliberate detail insert",
    "proof": "real recipient consent/reaction plus exact sample",
    "creator_fit": "real relationship/occasion creator",
    "hypothesis": "reaction may improve attention while detail insert protects product comprehension",
    "evidence_status": "untested; emotion may not translate to orders"
  }
]
```

### Creative Campaign Pack
```json
{
  "campaign_id": "CAMP-POD-CAP-001",
  "selected_viral_kit": "VK-POD-CAP-A:v1",
  "objective": "Organic affiliate/UGC concept test; paid only after physical proof, rights and MTO economics",
  "target_buyer": "US pet owner or gift buyer seeking visible personalization",
  "core_angle": "show how an approved name becomes the exact embroidered cap",
  "creator_brief": "Film the real navy “Milo” sample and seller-approved input/preview process. The displayed name is an example.",
  "deliverables": [
    "one 22–32 second vertical post",
    "one clean physical-product close-up",
    "one screen-to-product transition",
    "clean-audio cut if paid use requested"
  ],
  "must_show": [
    "exact navy cap and cream thread",
    "example name “Milo” labeled as example",
    "approved F-02 font only",
    "input/preview step",
    "physical sample close-up",
    "seller review before production",
    "commercial disclosure/product tag at publish"
  ],
  "must_not_show_or_say": [
    "any font or symbol",
    "perfect color on every screen/product",
    "handmade by seller if outsourced",
    "guaranteed reaction",
    "unverified occasion arrival",
    "AI mockup as physical proof"
  ],
  "creator_flexible_zones": [
    "natural pet-owner context",
    "personal story if truthful",
    "camera style after product details remain clear"
  ],
  "rights_request": {
    "organic_post": true,
    "paid_use": "requested_not_granted",
    "raw_footage": "close-up/process clips if contracted",
    "editing": "contract-specific",
    "audio": "clean version requested"
  },
  "revision_scope": "Misspelled/mismatched personalization or mockup-only proof requires corrected product/reshoot; optional emotional angle changes are new scope."
}
```

### Compiled Requirements
```json
[
  {
    "id": "P1",
    "requirement": "Exact preview, template, name, font, thread and physical output match",
    "source": "POD-PERS-001",
    "severity": "blocker",
    "verification": "OCR/visual against POD-E-002/003"
  },
  {
    "id": "P2",
    "requirement": "Physical sample used for color/texture/quality proof",
    "source": "POD-MOCK-001 / POD-SAMPLE-001",
    "severity": "blocker_for_proof",
    "verification": "physical sample evidence"
  },
  {
    "id": "P3",
    "requirement": "Example personalization clearly labeled and ordering limits accurate",
    "source": "POD-PERS-002",
    "severity": "high",
    "verification": "ASR/OCR plus checkout fixture"
  },
  {
    "id": "P4",
    "requirement": "No any-font/symbol or handmade claim",
    "source": "TT-CLAIM-001 / fixture",
    "severity": "blocker",
    "verification": "ASR/OCR"
  },
  {
    "id": "P5",
    "requirement": "MTO handling/shipping language only if verified",
    "source": "TT-FULFILL-002 / FTC-SHIP-001",
    "severity": "blocker_if_claimed",
    "verification": "seller SLA evidence"
  },
  {
    "id": "P6",
    "requirement": "IP clearance for design/asset",
    "source": "POD-IP-001",
    "severity": "blocker",
    "verification": "clearance record"
  },
  {
    "id": "P7",
    "requirement": "Disclosure and exact product tag",
    "source": "DISC-001 / TT content match",
    "severity": "blocker_at_publish",
    "verification": "post metadata"
  },
  {
    "id": "P8",
    "requirement": "Paid rights/audio/Spark complete",
    "source": "UGC-RIGHTS-001 / UGC-MUSIC-001 / SPARK-001",
    "severity": "blocker_for_paid",
    "verification": "rights card"
  }
]
```

### First Draft Ugc Observations
```json
{
  "asset_id": "UGC-POD-CAP-D1",
  "duration_seconds": 27.8,
  "observations": [
    {
      "time": "0:00–0:05.5",
      "observed": "AI mockup-only cap in black with gold thread; exact campaign sample is navy/cream."
    },
    {
      "time": "0:05.8",
      "observed": "Creator says “choose any name, any font, any symbol.”"
    },
    {
      "time": "0:07.0–0:12.0",
      "observed": "Checkout/personalization flow is not shown."
    },
    {
      "time": "0:12.5–0:18.0",
      "observed": "Very brief physical cap shot; thread and name unreadable."
    },
    {
      "time": "0:18.5",
      "observed": "Overlay: “Handmade just for you.” Seller uses outsourced POD provider."
    },
    {
      "time": "0:22.0–0:27.0",
      "observed": "Generic gift reaction and “order now for next week”; no evidence/disclosure."
    }
  ],
  "metadata_unknown": [
    "product tag",
    "disclosure setting"
  ],
  "rights_unknown": [
    "paid duration",
    "editing/raw footage",
    "audio"
  ]
}
```

### Preflight Expected Vs Observed
```json
[
  {
    "requirement_id": "P1",
    "expected": "Navy/cream F-02 “Milo” sample",
    "observed": "Opening black/gold mockup; physical detail unreadable",
    "status": "fail",
    "severity": "blocker",
    "editability": "reshoot with exact sample"
  },
  {
    "requirement_id": "P2",
    "expected": "Physical sample carries proof",
    "observed": "Mockup carries primary quality/color proof",
    "status": "fail",
    "severity": "blocker_for_proof",
    "editability": "reshoot"
  },
  {
    "requirement_id": "P3",
    "expected": "Example label and accurate limits",
    "observed": "“Any name/font/symbol”; no flow",
    "status": "fail",
    "severity": "high",
    "editability": "remove line plus reshoot process"
  },
  {
    "requirement_id": "P4",
    "expected": "No unsupported handmade claim",
    "observed": "“Handmade just for you”",
    "status": "fail",
    "severity": "blocker",
    "editability": "remove/replace line"
  },
  {
    "requirement_id": "P5",
    "expected": "No unverified delivery promise",
    "observed": "“Order now for next week”",
    "status": "fail",
    "severity": "blocker",
    "editability": "remove line"
  },
  {
    "requirement_id": "P6",
    "expected": "IP fixture clear",
    "observed": "Generic name/layout only",
    "status": "pass",
    "severity": "blocker",
    "editability": "n/a"
  },
  {
    "requirement_id": "P7",
    "expected": "Disclosure/tag",
    "observed": "Absent/unknown",
    "status": "fail_or_unknown",
    "severity": "blocker_at_publish",
    "editability": "edit and publish check"
  },
  {
    "requirement_id": "P8",
    "expected": "Paid rights/audio/Spark complete",
    "observed": "Not provided",
    "status": "unknown",
    "severity": "blocker_for_paid",
    "editability": "non-creative fix"
  }
]
```

### Preflight Decision
```json
{
  "structural_score_fixture_only": 48,
  "score_type": "deterministic structural fixture; not performance prediction",
  "confidence": "high for product/personalization mismatch",
  "action_label": "reshoot_required",
  "hard_blockers": [
    "mockup/sample mismatch",
    "unsupported personalization options",
    "false handmade claim",
    "unverified delivery",
    "missing disclosure"
  ]
}
```

### Seller Action Plan
```json
[
  {
    "priority": 1,
    "owner": "seller/POD operator",
    "action": "Confirm exact template, allowed characters, provider role and MTO handling statement."
  },
  {
    "priority": 2,
    "owner": "creator",
    "action": "Reshoot with navy/cream physical sample and readable “Milo” close-up."
  },
  {
    "priority": 3,
    "owner": "creator",
    "action": "Show approved input/preview and label “Milo” as example; remove any-font/symbol claim."
  },
  {
    "priority": 4,
    "owner": "seller",
    "action": "Replace handmade and delivery language; provide disclosure/CTA."
  },
  {
    "priority": 5,
    "owner": "rights owner",
    "action": "Complete paid rights and clean audio before amplification."
  },
  {
    "priority": 6,
    "owner": "operator",
    "action": "Keep paid/occasion campaign blocked until real provider SLA, defect/reprint rate and contribution economics are known."
  }
]
```

### Creator Revision Message
The pet-owner idea is relevant, but this draft needs a reshoot because the opening mockup does not match the exact product. Please use only the navy cap with cream “Milo” embroidery, show the seller-approved name input and preview, and add a readable physical close-up. Label “Milo” as an example. Remove “any font, any symbol,” “handmade,” and “order now for next week.” Add the approved commercial disclosure and send a clean-audio cut. The seller will verify the product tag and paid-use rights separately.

### Revised Draft
```json
{
  "asset_id": "UGC-POD-CAP-D2",
  "duration_seconds": 29.1,
  "changes": [
    {
      "time": "0:00–0:02.2",
      "change": "Real navy sample and pet-owner context; disclosure visible."
    },
    {
      "time": "0:02.3–0:07.5",
      "change": "Seller-approved input/preview; “Example: Milo” label."
    },
    {
      "time": "0:07.6–0:14.0",
      "change": "Process transition without claiming seller handmade production."
    },
    {
      "time": "0:14.1–0:20.5",
      "change": "Readable cream embroidery close-up; exact sample."
    },
    {
      "time": "0:20.6–0:27.5",
      "change": "Gift/identity context and accurate customization CTA; no shipping promise."
    }
  ],
  "remaining_unknown": [
    "platform tag/disclosure metadata",
    "real provider SLA and defect rate",
    "paid rights/Spark",
    "actual economics"
  ]
}
```

### Final Decision
```json
{
  "organic": "approve_after_publish_checks",
  "paid_or_spark": "blocked_pending_rights_audio_economics",
  "reason": "Physical/personalization truth fixed; paid and operational inputs remain unknown.",
  "confidence": "high structural; no performance guarantee"
}
```

### Missing Economic Or Rights Inputs
```json
[
  "real provider production/handling range",
  "reprint/defect/cancellation cost",
  "actual platform/commission/return inputs",
  "rights channels/duration/editing",
  "Spark authorization",
  "publish metadata"
]
```

### Expected Learning
```json
[
  "Compare process transparency with recipient-reaction and identity variants.",
  "Track personalization-start/order completion and support questions, not views alone.",
  "Monitor spelling/customization error and cancellation outcomes.",
  "Do not infer a universal gifting winner from one occasion/creator."
]
```

### Expert Labels
```json
[
  "official_hard_rule: product accuracy, claims, disclosure, IP and fulfillment",
  "operational_hard_constraint: personalization approval and rights",
  "established_best_practice: physical sample/process proof",
  "contextual_guideline: recipient emotion and reveal pacing",
  "insufficient_evidence: no performance or WTP claim"
]
```

### Seller Usefulness Criteria
```json
[
  "prevents mockup-only paid proof",
  "protects exact personalization",
  "separates creative reshoot from provider/economics tasks",
  "produces sendable creator message",
  "leaves unknown fulfillment/rights explicit"
]
```

## GC-DROP-DEMO-001 — Dropshipping visual-demo product — FurLift Reusable Pet Hair Roller

### Fixture Integrity
```json
{
  "statement": "All product, supplier, cost, shipping and demo facts are synthetic fixture facts. They are verified only against the fixture supplier record, exact sample and controlled demonstration.",
  "manifest_version": "gc-drop-demo-001:v1",
  "evidence_assets": [
    {
      "id": "DROP-E-001",
      "type": "supplier_fixture",
      "description": "Supplier SKU FLR-GR-02, green roller, package contents and fixture landed cost."
    },
    {
      "id": "DROP-E-002",
      "type": "exact_sample",
      "description": "Green roller and customer-equivalent package."
    },
    {
      "id": "DROP-E-003",
      "type": "controlled_demo",
      "description": "Visible loose pet hair pickup on one tested polyester couch section."
    },
    {
      "id": "DROP-E-004",
      "type": "seller_confirmation",
      "description": "No every-fabric, 100%, one-swipe, allergy, or two-day-delivery claim approved."
    }
  ]
}
```

### Verified Product Context
```json
{
  "product_id": "PROD-FLR-001",
  "sku": "FLR-GR-02",
  "supplier_sku": "SUP-FLR-GR-02",
  "product_name": "FurLift Reusable Pet Hair Roller",
  "commerce_model": "dropshipping fixture",
  "market": "US",
  "variant": "green manual roller with collection chamber",
  "fixture_price_usd": 19.99,
  "fixture_supplier_unit_cost_usd": 4.8,
  "fixture_supplier_shipping_usd": 5.7,
  "fixture_platform_fees_usd": 1.6,
  "fixture_commission_percent": 15,
  "mechanism": "manual back-and-forth roller lifts visible loose hair into a collection chamber",
  "tested_context": "fixture polyester couch with visible loose pet hair",
  "approved_benefits": [
    "picked up visible loose pet hair in the fixture test",
    "reusable manual mechanism",
    "collection chamber can be shown"
  ],
  "claims_not_approved": [
    "removes 100%",
    "works on every fabric",
    "one swipe",
    "helps allergies",
    "no lint/hair remains",
    "two-day delivery",
    "lifetime durability"
  ],
  "exact_sample_status": "verified_in_fixture",
  "customer_route_status": "unverified",
  "supplier_snapshot_status": "fixture_only",
  "unknowns": [
    "real stock/price freshness",
    "real delivery route",
    "defect/wrong-item rate",
    "return rate",
    "actual paid economics",
    "creator rights"
  ]
}
```

### Source Creative Observations
```json
{
  "reference_asset_id": "REF-PET-ROLLER-001",
  "source_status": "synthetic supplier-style reference; no performance evidence",
  "observations": [
    {
      "time": "0:00–0:01.0",
      "observation": "Macro product mechanism opens the video."
    },
    {
      "time": "0:01.0–0:06.0",
      "observation": "One-pass couch demonstration with several cuts."
    },
    {
      "time": "0:06.0–0:09.0",
      "observation": "Collection chamber reveal."
    },
    {
      "time": "0:09.0–0:12.0",
      "observation": "“Works everywhere” overlay and generic CTA."
    }
  ],
  "performance_evidence_status": "none",
  "copycat_note": "Supplier footage and wording cannot be reused as proof. Film the seller’s exact sample and original test."
}
```

### Creative Dna
```json
{
  "dna_id": "DNA-REF-DROP-001:v1",
  "hook_type": "product_first_mechanism",
  "message_angle": "fast pet-hair cleanup",
  "creator_persona": "hands-only product demo",
  "format": "macro mechanism → surface demo → chamber proof",
  "narrative": [
    "mechanism",
    "demo",
    "proof",
    "CTA"
  ],
  "demo_type": "visual utility",
  "proof_type": "surface result plus chamber close-up",
  "risks": [
    "supplier model unknown",
    "cuts may hide test",
    "universal claim",
    "no shipping/economics/rights evidence"
  ],
  "confidence": "high observation; zero commercial proof"
}
```

### Patternkit Candidate
```json
{
  "pattern_kit_id": "PK-DROP-MECHANISM-PROOF-001:v1",
  "status": "candidate",
  "name": "Exact product mechanism → controlled surface demo → chamber/result proof",
  "classification": "established_best_practice",
  "keep": [
    "immediate mechanism",
    "same-surface controlled use",
    "collection chamber proof",
    "limitation language"
  ],
  "contraindications": [
    "exact supplier SKU unavailable",
    "surface compatibility unknown",
    "safety/health claim",
    "customer route unverified"
  ],
  "applicability": [
    "visual cleaning utility",
    "mechanical gadget",
    "short feedback loop"
  ],
  "performance_evidence_status": "no linked performance; online test required"
}
```

### Viral Kit Concepts
```json
[
  {
    "viral_kit_id": "VK-FLR-A:v1",
    "name": "One couch section, one continuous test",
    "angle": "mechanism proof",
    "hook": "Macro roller enters a clearly marked couch section",
    "mechanic": "continuous back-and-forth use on same section",
    "proof": "before/process/result plus chamber close-up",
    "creator_fit": "pet-owner product demonstrator",
    "hypothesis": "controlled continuity may improve trust and product clicks",
    "evidence_status": "untested"
  },
  {
    "viral_kit_id": "VK-FLR-B:v1",
    "name": "Reusable versus disposable routine",
    "angle": "workflow comparison",
    "hook": "Show recurring disposable lint-roll sheet use, then exact reusable roller",
    "mechanic": "comparable couch sections and documented steps",
    "proof": "same task; no unsupported lifetime cost claim",
    "creator_fit": "practical home/pet reviewer",
    "hypothesis": "workflow contrast may improve value understanding",
    "evidence_status": "untested; comparator conditions required"
  },
  {
    "viral_kit_id": "VK-FLR-C:v1",
    "name": "Pet-owner reset before guests",
    "angle": "routine/occasion",
    "hook": "Real visible hair before a guest-arrival cleanup",
    "mechanic": "insert exact roller into routine and empty chamber",
    "proof": "same surface and realistic result",
    "creator_fit": "pet-owner lifestyle creator",
    "hypothesis": "specific routine may improve relevance without universal claim",
    "evidence_status": "untested"
  }
]
```

### Creative Campaign Pack
```json
{
  "campaign_id": "CAMP-FLR-001",
  "selected_viral_kit": "VK-FLR-A:v1",
  "objective": "Organic TikTok Shop product demo; paid small test only after supplier/economics/rights completion",
  "target_buyer": "US pet owner with loose visible hair on tested upholstery",
  "core_angle": "show exact reusable mechanism honestly on one verified surface",
  "creator_brief": "Use the exact green FLR-GR-02 sample. Film an original continuous test on a clearly identified safe upholstery surface.",
  "deliverables": [
    "one 18–25 second vertical post",
    "one clean continuous demo clip",
    "one clean-audio cut",
    "optional second tested-context clip only if contracted"
  ],
  "must_show": [
    "exact green model/package",
    "surface before use",
    "continuous demo on same area",
    "collection chamber",
    "truthful limitation: result shown on this couch",
    "commercial disclosure and correct tag at publish"
  ],
  "must_not_show_or_say": [
    "100%",
    "every fabric",
    "one swipe",
    "allergy benefit",
    "two-day delivery",
    "supplier/reference footage",
    "different blue model",
    "unverified price/discount"
  ],
  "creator_flexible_zones": [
    "natural pet-owner context",
    "opening wording",
    "safe filming style while continuity remains visible"
  ],
  "rights_request": {
    "organic_post": true,
    "paid_use": "requested_not_granted",
    "Spark": "requested_not_authorized",
    "raw_footage": "continuous demo requested if contracted",
    "audio": "clean cut required"
  },
  "revision_scope": "Material model/surface/proof mismatch requires reshoot; removing a text/offer line is editable."
}
```

### Compiled Requirements
```json
[
  {
    "id": "D1",
    "requirement": "Exact supplier SKU/model and customer-equivalent package",
    "source": "DROP-SUP-002 / TT-CONTENT-001",
    "severity": "blocker",
    "verification": "visual/model match to DROP-E-001/002"
  },
  {
    "id": "D2",
    "requirement": "Continuous mechanism on identified tested surface",
    "source": "selected PatternKit",
    "severity": "high",
    "verification": "unbroken same-area use"
  },
  {
    "id": "D3",
    "requirement": "No universal/absolute or health claim",
    "source": "TT-CLAIM-001 / FTC-CLAIM-001",
    "severity": "blocker",
    "verification": "ASR/OCR"
  },
  {
    "id": "D4",
    "requirement": "Shipping statement uses actual customer route or is omitted",
    "source": "DROP-SHIP-001 / FTC-SHIP-001",
    "severity": "blocker_if_claimed",
    "verification": "route evidence"
  },
  {
    "id": "D5",
    "requirement": "Offer/price matches current listing",
    "source": "TT-OFFER-001",
    "severity": "blocker_if_claimed",
    "verification": "offer snapshot"
  },
  {
    "id": "D6",
    "requirement": "Disclosure and exact product tag",
    "source": "DISC-001 / content match",
    "severity": "blocker_at_publish",
    "verification": "post metadata"
  },
  {
    "id": "D7",
    "requirement": "Current supplier stock/cost/economics before paid scale",
    "source": "DROP-STOCK-001 / ECON-001",
    "severity": "blocker_for_paid_scale",
    "verification": "fresh snapshot and economics"
  },
  {
    "id": "D8",
    "requirement": "Rights/Spark/audio complete",
    "source": "UGC-RIGHTS-001 / SPARK-001 / UGC-MUSIC-001",
    "severity": "blocker_for_paid",
    "verification": "rights card"
  }
]
```

### First Draft Ugc Observations
```json
{
  "asset_id": "UGC-FLR-D1",
  "duration_seconds": 21.6,
  "observations": [
    {
      "time": "0:00–0:04.0",
      "observed": "Supplier clip shows a blue model; campaign SKU is green FLR-GR-02."
    },
    {
      "time": "0:04.2",
      "observed": "Overlay: “100% of hair in one swipe.”"
    },
    {
      "time": "0:05.0–0:10.0",
      "observed": "Rapid cuts prevent continuity; fabric not identified."
    },
    {
      "time": "0:10.5",
      "observed": "Creator says “works on every fabric.”"
    },
    {
      "time": "0:13.0",
      "observed": "Creator says “mine arrived in two days”; sample was sent express, customer route unknown."
    },
    {
      "time": "0:16.0",
      "observed": "Price overlay $14.99; fixture listing is $19.99."
    },
    {
      "time": "0:18.0–0:21.0",
      "observed": "No disclosure; tag/audio/rights unknown."
    }
  ],
  "metadata_unknown": [
    "disclosure",
    "product tag",
    "audio"
  ],
  "rights_unknown": [
    "paid use",
    "Spark",
    "editing/raw"
  ],
  "supplier_unknown": [
    "current stock/cost",
    "customer route"
  ]
}
```

### Preflight Expected Vs Observed
```json
[
  {
    "requirement_id": "D1",
    "expected": "Exact green FLR-GR-02",
    "observed": "Blue supplier model in opening",
    "status": "fail",
    "severity": "blocker",
    "editability": "remove supplier clip and reshoot exact model"
  },
  {
    "requirement_id": "D2",
    "expected": "Continuous same-area demo",
    "observed": "Rapid cuts; surface unidentified",
    "status": "fail",
    "severity": "high",
    "editability": "reshoot"
  },
  {
    "requirement_id": "D3",
    "expected": "No 100%/every-fabric/one-swipe claim",
    "observed": "All three appear",
    "status": "fail",
    "severity": "blocker",
    "editability": "remove lines plus reshoot truthful demo"
  },
  {
    "requirement_id": "D4",
    "expected": "No shipping claim without customer route",
    "observed": "Two-day claim based on express creator sample",
    "status": "fail",
    "severity": "blocker",
    "editability": "remove line"
  },
  {
    "requirement_id": "D5",
    "expected": "Current verified price",
    "observed": "$14.99 versus $19.99 fixture",
    "status": "fail",
    "severity": "blocker",
    "editability": "replace/remove overlay"
  },
  {
    "requirement_id": "D6",
    "expected": "Disclosure/tag",
    "observed": "Absent/unknown",
    "status": "fail_or_unknown",
    "severity": "blocker_at_publish",
    "editability": "edit and publish check"
  },
  {
    "requirement_id": "D7",
    "expected": "Fresh supplier/economics for paid scale",
    "observed": "Not provided",
    "status": "unknown",
    "severity": "blocker_for_paid_scale",
    "editability": "operational fix"
  },
  {
    "requirement_id": "D8",
    "expected": "Rights/Spark/audio complete",
    "observed": "Not provided",
    "status": "unknown",
    "severity": "blocker_for_paid",
    "editability": "non-creative fix"
  }
]
```

### Preflight Decision
```json
{
  "structural_score_fixture_only": 36,
  "score_type": "deterministic structural fixture; not performance prediction",
  "confidence": "high for mismatch/claims",
  "action_label": "reject_current_draft_and_reshoot",
  "hard_blockers": [
    "wrong model",
    "unsupported absolute/compatibility claims",
    "unverified shipping",
    "offer mismatch",
    "missing disclosure"
  ]
}
```

### Seller Action Plan
```json
[
  {
    "priority": 1,
    "owner": "seller/sourcing",
    "action": "Confirm exact supplier SKU, customer-equivalent package, current stock/cost and customer shipping route."
  },
  {
    "priority": 2,
    "owner": "creator",
    "action": "Discard supplier clip and reshoot exact green sample in one continuous same-area test."
  },
  {
    "priority": 3,
    "owner": "creator",
    "action": "Use truthful observed wording: “It picked up visible loose hair on this couch.” Remove 100%, every-fabric and one-swipe claims."
  },
  {
    "priority": 4,
    "owner": "seller",
    "action": "Remove two-day statement and replace/remove price from current offer snapshot."
  },
  {
    "priority": 5,
    "owner": "seller/creator",
    "action": "Complete disclosure and exact product tag at publish."
  },
  {
    "priority": 6,
    "owner": "rights/economics owner",
    "action": "Complete rights, Spark, audio and contribution economics before paid test."
  }
]
```

### Creator Revision Message
Please do not use the blue supplier clip; it is not the seller’s exact product. Reshoot the green FLR-GR-02 sample on one clearly identified couch section and keep the mechanism continuous. Remove “100%,” “one swipe,” “every fabric,” and the two-day delivery statement. Use the seller-approved observation: “It picked up visible loose hair on this couch.” Remove or update the price from the seller’s current offer, add the approved commercial disclosure, and send a clean-audio cut. Product tag and Spark rights will be verified separately.

### Revised Draft
```json
{
  "asset_id": "UGC-FLR-D2",
  "duration_seconds": 22.2,
  "changes": [
    {
      "time": "0:00–0:00.8",
      "change": "Exact green sample and disclosure visible."
    },
    {
      "time": "0:00.8–0:03.0",
      "change": "Marked polyester couch section before state."
    },
    {
      "time": "0:03.0–0:10.2",
      "change": "Continuous back-and-forth mechanism."
    },
    {
      "time": "0:10.3–0:14.5",
      "change": "Same-area result and collection chamber."
    },
    {
      "time": "0:14.6",
      "change": "Truthful context line; no universal claim."
    },
    {
      "time": "0:18.0–0:21.5",
      "change": "Approved CTA; no price or shipping promise; clean audio."
    }
  ],
  "remaining_unknown": [
    "live product tag/disclosure metadata",
    "fresh supplier stock/cost/route",
    "paid rights/Spark",
    "complete economics"
  ]
}
```

### Final Decision
```json
{
  "organic": "approve_small_organic_test_after_publish_checks",
  "paid_or_spark": "blocked_pending_supplier_economics_rights",
  "reason": "Exact-product and claim blockers corrected; operational and paid-use inputs remain unknown.",
  "confidence": "high structural; no GMV/profit prediction"
}
```

### Missing Economic Or Rights Inputs
```json
[
  "fresh supplier stock/price/shipping destination",
  "wrong-item/defect/return history",
  "actual fees/commission/returns",
  "paid channels/duration/editing",
  "Spark authorization",
  "publish metadata"
]
```

### Expected Learning
```json
[
  "Compare exact mechanism-first against fair reusable-versus-disposable workflow while controlling other variables.",
  "Use product clicks/orders, contribution and return/compatibility complaints; do not judge from views alone.",
  "Track whether context limitation reduces incompatible-surface complaints.",
  "Do not call supplier-style mechanism a winner without linked product evidence."
]
```

### Expert Labels
```json
[
  "official_hard_rule: product/offer/claim/disclosure consistency",
  "operational_hard_constraint: supplier route/stock/economics/rights",
  "established_best_practice: exact sample and continuous demo",
  "contextual_guideline: pet-owner routine",
  "seller_anecdote: stock/wrong-item/shipping pain",
  "insufficient_evidence: performance unknown"
]
```

### Seller Usefulness Criteria
```json
[
  "stops wrong-model supplier footage",
  "removes unsupported absolute and shipping claims",
  "separates reshoot from sourcing/economics tasks",
  "keeps organic and paid decisions distinct",
  "defines a testable learning question"
]
```

# F. Disagreements and Uncertainties

## UNC-SAMPLE-001 — TikTok Shop refundable-sample qualification window
- **Classification:** `unresolved_disagreement`
- **What is known:** Free-sample posting obligation is separately described as 14 days after receipt; live collaboration contains campaign-specific goal/deadline.
- **Viraldy behavior:** Never hard-code 90 or 120 as global truth. Prefer the live collaboration/order object, store observed policy version, otherwise return policy_conflict.
- **Seller confirmation required:** Deadline and sales goal shown in the seller/creator account.

**Positions / disagreement**
- One official June 2026 sample guide used 120-day wording.
- Another official sample-management page used 90-day wording.

**Sources:** [TT01] Guide to Samples: Free and Refundable — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=5764641632306946); [TT02] How to set up and manage samples — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=5694209038927617)

## UNC-POLICY-001 — TikTok policy pages and operational thresholds change
- **Classification:** `contextual_guideline`
- **What is known:** Policy and workflow values can be revised, scoped by category, program or account.
- **Viraldy behavior:** Version all policy values and show last verified date; prefer live account object where available; require review after material policy change.
- **Seller confirmation required:** Current account/category status for high-risk decisions.

**Positions / disagreement**
- Official page is authoritative at a point in time.
- Live Seller Center/campaign state may be more specific than a general article.

**Sources:** [TT01] Guide to Samples: Free and Refundable — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=5764641632306946); [TT02] How to set up and manage samples — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=5694209038927617); [TT09] TikTok Shop Fulfillment Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=3995852763301633); [TT20] Restricted Products Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=3238037484275457)

## UNC-TIMING-001 — Universal first-3-second or product-reveal timing rule
- **Classification:** `contextual_guideline`
- **What is known:** Early clarity is a useful test hypothesis, not a universal compliance requirement.
- **Viraldy behavior:** Use timing as a blocker only when campaign/contract explicitly requires it; otherwise label optimization and propose a test.
- **Seller confirmation required:** Chosen PatternKit and campaign-specific timing requirement.

**Positions / disagreement**
- TikTok publishes early-attention and hook/body/CTA guidance.
- Products, narratives, creators and objectives require different pacing.

**Sources:** [TT12] Creative best practices for performance ads — TikTok for Business Help Center (https://ads.tiktok.com/help/article/creative-best-practices); [TT15] Creative Codes: Six Principles for TikTok-First Ads — TikTok for Business (https://ads.tiktok.com/business/creativecenter/quicktok/online/TikTokCreativeCodes.pdf); [PERF01] Creative Benchmarks 2026 — Motion (https://motionapp.com/library/research/creative-benchmarks-2026/)

## UNC-BRIEF-001 — Creator freedom versus prescriptive scripting
- **Classification:** `unresolved_disagreement`
- **What is known:** Product truth, claims, disclosure, deliverables and rights must be explicit; exact wording/style is contextual.
- **Viraldy behavior:** Separate hard requirements from creator-flexible zones; tighten only for legal/technical facts or repeated misses.
- **Seller confirmation required:** Which lines are exact and which may be rewritten naturally.

**Positions / disagreement**
- More specificity reduces missed requirements.
- Over-scripting can damage creator-native delivery and authenticity.

**Sources:** [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief); [UGC05] UGC Brief Template and Production Guidance — Billo (https://billo.app/blog/ugc-brief-template/); [PERF03] How to Make Ads for Meta and TikTok in 2026 — Motion / Savannah Sanchez (https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026)

## UNC-MOCKUP-001 — When a POD mockup is sufficient
- **Classification:** `contextual_guideline`
- **What is known:** Physical proof is stronger and often required for proof-heavy paid creative; channel rules differ.
- **Viraldy behavior:** Allow concept-only output from mockup; block exact physical proof claims and TikTok-listing-ready status when current policy/asset evidence is insufficient.
- **Seller confirmation required:** Channel, exact asset purpose and physical-sample availability.

**Positions / disagreement**
- Mockups support design/ideation and some marketplace workflows.
- They do not prove exact physical color, texture, placement or quality; TikTok listing policy may require physical representation.

**Sources:** [TT07] Product Listing Policy — TikTok Shop Academy (https://seller-us.tiktok.com/university/essay?knowledge_id=3196690250417921); [POD02] How can I create mockups for Early Access Catalog products? — Printify Help Center (https://help.printify.com/hc/en-us/articles/25641196380817-How-can-I-create-mockups-for-Early-Access-Catalog-products); [POD03] Why does my product look different from the mockup? — Printify Help Center (https://help.printify.com/hc/en-us/articles/4483617784721-Why-does-my-product-look-different-from-the-mockup); [COM04] Mockup tool and printed product mismatch — Reddit r/printondemand (https://www.reddit.com/r/printondemand/comments/1t7d1dl/avoid_fourthwall_their_mockup_tool_and_printed/)

## UNC-BEFOREAFTER-001 — Before/after demonstrations
- **Classification:** `contextual_guideline`
- **What is known:** Truth, continuity, typicality and claim substantiation determine risk; there is no blanket performance guarantee.
- **Viraldy behavior:** Require same-object/condition evidence, raw continuity where material, and expert review for high-risk outcome claims.
- **Seller confirmation required:** Claim evidence and whether result is typical/representative.

**Positions / disagreement**
- Matched before/after can make a physical mechanism understandable.
- Edited, atypical or health-related before/after can mislead or imply unsupported results.

**Sources:** [TT10] Misleading and false content — TikTok Advertising Policies (https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content); [FTC04] Health Products Compliance Guidance — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance)

## UNC-AUTH-001 — “Authentic UGC” as a performance rule
- **Classification:** `expert_opinion`
- **What is known:** Authenticity is a contextual quality dimension and never waives disclosure/claim rules.
- **Viraldy behavior:** Score observable fit/truth separately from style; never guarantee performance from “authentic” appearance.
- **Seller confirmation required:** Creator’s actual experience and intended format.

**Positions / disagreement**
- Industry experts often prefer native/creator-led delivery.
- Casual appearance alone does not prove truth, fit or performance.

**Sources:** [FTC01] FTC Endorsement Guides: What People Are Asking — Federal Trade Commission (https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking); [UGC01] How to Write a UGC Brief That Gets Results — Insense (https://insense.pro/blog/ugc-brief); [PERF02] 2025 DTC Creative Trends: Expert Lightning Round — Motion (https://motionapp.com/library/talk/motion-s-2025-facebook-ad-creative-trends-dtc-expert-lightning-round/); [PERF03] How to Make Ads for Meta and TikTok in 2026 — Motion / Savannah Sanchez (https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026)

## UNC-CREATOR-001 — Follower count, engagement and creator-product fit
- **Classification:** `directional_pattern`
- **What is known:** Fit and outcome require product/context/history; missing audience/performance lowers confidence.
- **Viraldy behavior:** Use follower/engagement only as features; display confidence and keep free-sample/rehire decisions conditional without history.
- **Seller confirmation required:** Audience geography, product relevance and previous collaboration outcomes where available.

**Positions / disagreement**
- Follower/engagement are easy screening signals.
- They may not predict demo skill, US audience fit, reliability or GMV/sample.

**Sources:** [COM01] 30 samples sent, no sale — Reddit r/TikTokshop (https://www.reddit.com/r/TikTokshop/comments/1ux5rk0/30_samples_sent_no_sale/); [COM03] Affiliates receiving samples but not posting — Reddit r/TikTokshop (https://www.reddit.com/r/TikTokshop/comments/1b9p0cw/what_do_you_do_when_affiliates_dont_post_any/); [PERF03] How to Make Ads for Meta and TikTok in 2026 — Motion / Savannah Sanchez (https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026)

## UNC-PUBLICSIGNAL-001 — Public ad longevity, views, engagement or estimated spend as winning proof
- **Classification:** `directional_pattern`
- **What is known:** A highly viewed or long-running asset can still have weak sales/profit.
- **Viraldy behavior:** Label observed/directional/candidate; “winning” requires linked outcome evidence with context.
- **Seller confirmation required:** Internal outcome data or credible linked evidence.

**Positions / disagreement**
- Public signals can prioritize references.
- They do not reveal margin, attribution, distribution, product page, inventory or causality.

**Sources:** [COM02] 1.4M-view affiliate video with weak sales — Reddit r/TikTokshop (https://www.reddit.com/r/TikTokshop/comments/1lgdfzj/our_tiktok_affiliate_video_went_viral_14m_views/); [PERF01] Creative Benchmarks 2026 — Motion (https://motionapp.com/library/research/creative-benchmarks-2026/); [TT17] About Conversion Lift Study — TikTok for Business Help Center (https://ads.tiktok.com/help/article/about-conversion-lift-study)

## UNC-SPARK-001 — Spark authorization method, duration and workflow behavior
- **Classification:** `contextual_guideline`
- **What is known:** Exact post, advertiser, method, expiry and contract scope must all be tracked.
- **Viraldy behavior:** No default Spark duration. Read live authorization, store method/version and use the shorter valid platform/contract scope.
- **Seller confirmation required:** Chosen authorization method and signed rights scope.

**Positions / disagreement**
- Different official methods support different code, mass-authorization, caption, visibility and duration behavior.
- Contractual paid rights remain separate from platform authorization.

**Sources:** [TT05] Differences between affiliate mass authorization and video code authorization — TikTok for Business Help Center (https://ads.tiktok.com/help/article/differences-between-affiliate-creative-authorization-and-video-code); [TT06] How to create Spark Ads for Manual and Search Campaigns — TikTok for Business Help Center (https://ads.tiktok.com/help/article/spark-ads-creation-guide); [UGC03] TikTok Spark Ads Setup Guide (2026) — Insense (https://insense.pro/blog/tiktok-spark-ads)

## UNC-SUPPLIER-001 — Supplier stock, price, quality and shipping estimates
- **Classification:** `operational_hard_constraint`
- **What is known:** External supplier facts are perishable and sample/customer routes may differ.
- **Viraldy behavior:** Timestamp snapshots, use workspace freshness thresholds, block scale/shipping claims when stale, and require exact sample for proof-heavy claims.
- **Seller confirmation required:** Current stock, landed cost, exact supplier SKU, route and backup plan.

**Positions / disagreement**
- Supplier listings provide useful current inputs.
- They can become stale, vary by destination, or differ from customer batch.

**Sources:** [DS01] Dropshipping Fulfillment: The Complete Guide (2026) — Shopify (https://www.shopify.com/blog/dropshipping-fulfillment); [DS03] Product Sourcing Guide: How To Get Started (2026) — Shopify (https://www.shopify.com/blog/product-sourcing-apps); [DS05] Product sourcing and supplier monitoring documentation — AutoDS Help Center (https://help.autods.com/); [COM05] Supplier stock and price changes — Reddit r/dropshipping (https://www.reddit.com/r/dropshipping/comments/1u9gt9c/how_do_you_track_supplier_stock_and_price_changes/); [COM06] Wrong item from dropshipping supplier — Reddit r/dropshipping (https://www.reddit.com/r/dropshipping/comments/1sirqc6/how_do_you_verify_product_quality_before_it_ships/); [COM07] Unexpected shipping cost and low supplier stock — Reddit r/dropshipping (https://www.reddit.com/r/dropshipping/comments/1q15jg9/unexpected_aliexpress_shipping_costs_and_low/)

## UNC-DATA-001 — Minimum sample size for creative performance conclusions
- **Classification:** `unresolved_disagreement`
- **What is known:** Sparse data increases uncertainty and should not produce precise causal rankings.
- **Viraldy behavior:** Use design-specific analytical thresholds/versioned rules, show denominators/confidence and return insufficient_evidence when unmet.
- **Seller confirmation required:** Primary metric, acceptable error, budget/traffic and decision cost.

**Positions / disagreement**
- Teams need operational thresholds.
- A universal number is invalid because metric, base rate, allocation and test design differ.

**Sources:** [TT16] How to create a split test in TikTok Ads Manager — TikTok for Business Help Center (https://ads.tiktok.com/help/article/create-split-test); [PERF01] Creative Benchmarks 2026 — Motion (https://motionapp.com/library/research/creative-benchmarks-2026/); [PERF07] Offline-to-Online Creative Optimization with Generative Models and Adaptive Testing — Lee et al., arXiv preprint (https://arxiv.org/abs/2607.23696)

## UNC-METRIC-001 — Engagement or watch metrics as commerce outcome
- **Classification:** `operational_hard_constraint`
- **What is known:** Downstream commerce and economics must be linked for scale/profit conclusions.
- **Viraldy behavior:** Name exact metric; prohibit GMV/profit labels from engagement-only evidence.
- **Seller confirmation required:** Asset mapping, attribution window and cost/order data.

**Positions / disagreement**
- Attention metrics diagnose hooks/creative delivery.
- They do not directly establish orders, GMV, profit or incrementality.

**Sources:** [PERF07] Offline-to-Online Creative Optimization with Generative Models and Adaptive Testing — Lee et al., arXiv preprint (https://arxiv.org/abs/2607.23696); [COM02] 1.4M-view affiliate video with weak sales — Reddit r/TikTokshop (https://www.reddit.com/r/TikTokshop/comments/1lgdfzj/our_tiktok_affiliate_video_went_viral_14m_views/); [TT17] About Conversion Lift Study — TikTok for Business Help Center (https://ads.tiktok.com/help/article/about-conversion-lift-study)

## UNC-WTP-001 — Seller willingness to pay for Viraldy
- **Classification:** `directional_pattern`
- **What is known:** The strongest hypothesis is decision value near sample, revision, rights and paid-spend risk.
- **Viraldy behavior:** Do not present price or ROI as validated; run paid concierge/design-partner tests and measure changed decisions/avoided cost.
- **Seller confirmation required:** Actual paid pilot and repeat-use behavior.

**Positions / disagreement**
- Adjacent tools and workflow pain show a plausible paid category.
- Public pricing and community pain do not prove Viraldy conversion, price or retention.

**Sources:** [WTP01] Motion Pricing and Plans — Motion (https://motionapp.com/llm-info); [WTP02] Foreplay Pricing — Foreplay (https://www.foreplay.co/pricing); [UGC06] Influencer and UGC Campaign Pricing — Insense (https://insense.pro/pricing); [COM01] 30 samples sent, no sale — Reddit r/TikTokshop (https://www.reddit.com/r/TikTokshop/comments/1ux5rk0/30_samples_sent_no_sale/); [PERF03] How to Make Ads for Meta and TikTok in 2026 — Motion / Savannah Sanchez (https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026)

## UNC-PRIVATE-001 — Cross-seller benchmarks and private learning
- **Classification:** `operational_hard_constraint`
- **What is known:** Consent, isolation, cohort safeguards and low re-identification risk are required.
- **Viraldy behavior:** Default to workspace-private PatternKit; publish aggregate only after privacy policy conditions pass.
- **Seller confirmation required:** Consent and benchmark scope.

**Positions / disagreement**
- Aggregates can improve niche priors.
- Small cohorts can reveal private seller/creator strategy.

**Sources:** [PERF07] Offline-to-Online Creative Optimization with Generative Models and Adaptive Testing — Lee et al., arXiv preprint (https://arxiv.org/abs/2607.23696)

# Implementation Mapping
```json
{
  "DomainExpertPolicyPackV1": {
    "version": "1.0.0-research-2026-07-31",
    "precedence": [
      "official_hard_rule",
      "operational_hard_constraint",
      "expert_review disposition",
      "established_best_practice",
      "contextual_guideline",
      "directional_pattern",
      "expert_opinion",
      "seller_anecdote"
    ],
    "evaluation_order": [
      "normalize input and versions",
      "run deterministic category/product/offer/claim/disclosure/rights/economics gates",
      "run domain constraints",
      "run multimodal extraction",
      "compare expected-versus-observed",
      "generate seller/creator action",
      "record override/outcome"
    ],
    "typed_unknowns": [
      "unknown",
      "insufficient_evidence",
      "seller_confirmation_required",
      "expert_review_required",
      "policy_conflict",
      "rights_incomplete",
      "economics_insufficient",
      "supplier_data_stale",
      "publish_check_required"
    ],
    "hard_output_rules": [
      "Never invent material product/economics/rights/policy facts",
      "Never label winning without linked evidence",
      "Never convert views/engagement into GMV/profit guarantee",
      "Never turn contextual timing into universal platform requirement",
      "Never expose another seller’s private data"
    ],
    "policy_versioning": [
      "source_id",
      "source_url",
      "observed_or_effective_date",
      "policy_pack_version",
      "rule_version",
      "last_verified_at",
      "supersedes",
      "review_owner"
    ]
  },
  "prompt_domain_overlays": [
    {
      "overlay": "tiktok_shop_us",
      "required_context": [
        "listing/product/variant",
        "campaign type",
        "sample type",
        "disclosure",
        "tag",
        "fulfillment",
        "offer",
        "account health"
      ],
      "special_rules": [
        "live platform object outranks general article",
        "draft file cannot prove publish metadata"
      ]
    },
    {
      "overlay": "pod_personalization",
      "required_context": [
        "provider/template",
        "personalization fields",
        "preview/version",
        "physical sample",
        "MTO handling",
        "IP clearance"
      ],
      "special_rules": [
        "mockup-only is not exact physical proof",
        "buyer input is production data"
      ]
    },
    {
      "overlay": "dropshipping",
      "required_context": [
        "supplier SKU",
        "sample identity",
        "stock/cost snapshot",
        "route/destination",
        "compatibility",
        "returns/QC"
      ],
      "special_rules": [
        "supplier facts are perishable",
        "creator sample route is not customer route"
      ]
    },
    {
      "overlay": "ugc_creator",
      "required_context": [
        "brief/version",
        "creator experience",
        "deliverables",
        "revisions",
        "disclosure",
        "rights",
        "audio",
        "Spark"
      ],
      "special_rules": [
        "hard requirements separate from creator-flexible zones",
        "paid rights are not implied by organic posting"
      ]
    },
    {
      "overlay": "performance_creative",
      "required_context": [
        "hypothesis",
        "metric",
        "asset mapping",
        "date/window",
        "allocation",
        "economics",
        "confounders"
      ],
      "special_rules": [
        "offline score filters risk but does not guarantee performance",
        "public popularity is hypothesis evidence only"
      ]
    }
  ],
  "deterministic_rules": [
    "Product/content/tag material mismatch => block.",
    "Objective/high-risk claim without adequate evidence => block or expert review.",
    "Material connection yes/unknown and disclosure incomplete => block publish-ready.",
    "Rights/Spark/audio incomplete => organic-only, not paid-ready.",
    "Required economics missing => no free-sample/paid-scale recommendation.",
    "Exact supplier/POD sample mismatch => proof-heavy creative blocked.",
    "Official policy conflict => live object required; otherwise unknown.",
    "Performance evidence not linked/sufficient => no winning or causal label.",
    "Campaign timing miss => blocker only when source is brief/contract/hard rule; otherwise optimization."
  ],
  "expert_review_triggers": [
    "health, disease, safety, clinical or child/pregnancy claim",
    "regulated/prohibited/restricted product ambiguity",
    "trademark/copyright/parody/fair-use uncertainty",
    "counterfeit/knockoff or patent concern",
    "material before/after or comparative superiority claim",
    "electrical/vehicle/safety-critical compatibility",
    "perpetual/broad rights, sublicensing or creator dispute",
    "synthetic person/testimonial/voice or material AI alteration",
    "policy-source conflict affecting money/deadline",
    "negative-margin or high-spend override",
    "privacy/cohort re-identification risk"
  ],
  "seller_onboarding_contract": {
    "first_value_goal": "One verified product plus one reference/draft produces one evidence-backed decision within the seller’s current review cycle.",
    "progressive_steps": [
      "workspace and commerce model",
      "current money decision",
      "exact product truth",
      "claims/fulfillment/economics",
      "creator/deliverable/rights",
      "evidence/metrics"
    ],
    "do_not_require_initially": [
      "full store integration",
      "complete historical data",
      "all catalog SKUs",
      "automated crawl",
      "performance model calibration"
    ],
    "show_for_every_missing_field": [
      "what is missing",
      "why it matters",
      "which output is blocked",
      "who should supply it",
      "whether partial analysis can continue"
    ]
  },
  "golden_output_contract": {
    "required_sections": [
      "Verified Product Context",
      "Source Creative Observations",
      "Creative DNA",
      "PatternKit Candidate",
      "Three ViralKit Concepts",
      "Creative Campaign Pack",
      "Compiled Requirements",
      "First-Draft Observations",
      "Expected-versus-Observed Preflight",
      "SellerActionPlan",
      "Creator Revision Message",
      "Revised Draft",
      "Final Decision",
      "Missing Inputs",
      "Expected Learning",
      "Expert Labels",
      "Seller Usefulness Criteria"
    ],
    "decision_labels": [
      "reject",
      "reshoot",
      "revise",
      "approve_organic",
      "organic_only",
      "paid_ready",
      "blocked_pending_review",
      "test_small",
      "scale",
      "fix",
      "hold",
      "kill",
      "rehire"
    ],
    "quality_checks": [
      "every blocker has evidence",
      "edit versus reshoot explicit",
      "unknowns not fabricated",
      "performance status explicit",
      "seller and creator messages differ by audience",
      "policy/brief source attached",
      "asset/input versions immutable"
    ]
  }
}
```

# Semantic Regression Tests
The bundle includes **35** JSONL test cases covering policy conflicts, product mismatch, timing, claims, disclosure, POD, dropshipping, rights, economics, performance evidence, privacy and overrides.

# Source Registry
| ID | Strength | Type | Publisher | Title | URL |
|---|---:|---|---|---|---|
| TT01 | 5 | official_platform | TikTok Shop Academy | Guide to Samples: Free and Refundable | https://seller-us.tiktok.com/university/essay?knowledge_id=5764641632306946 |
| TT02 | 5 | official_platform | TikTok Shop Academy | How to set up and manage samples | https://seller-us.tiktok.com/university/essay?knowledge_id=5694209038927617 |
| TT03 | 5 | official_platform | TikTok Shop Academy | Sample Integrity Policy | https://seller-us.tiktok.com/university/essay?knowledge_id=6118437723506474 |
| TT04 | 5 | official_platform | TikTok Shop Academy | Setting Up Affiliate Collaborations | https://seller-us.tiktok.com/university/essay?knowledge_id=6837873164896001 |
| TT05 | 5 | official_platform | TikTok for Business Help Center | Differences between affiliate mass authorization and video code authorization | https://ads.tiktok.com/help/article/differences-between-affiliate-creative-authorization-and-video-code |
| TT06 | 5 | official_platform | TikTok for Business Help Center | How to create Spark Ads for Manual and Search Campaigns | https://ads.tiktok.com/help/article/spark-ads-creation-guide |
| TT07 | 5 | official_platform | TikTok Shop Academy | Product Listing Policy | https://seller-us.tiktok.com/university/essay?knowledge_id=3196690250417921 |
| TT08 | 5 | official_platform | TikTok Shop Academy | TikTok Shop Content Policy | https://seller-us.tiktok.com/university/essay?knowledge_id=6837891779151617 |
| TT09 | 5 | official_platform | TikTok Shop Academy | TikTok Shop Fulfillment Policy | https://seller-us.tiktok.com/university/essay?knowledge_id=3995852763301633 |
| TT10 | 5 | official_platform | TikTok Advertising Policies | Misleading and false content | https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content |
| TT11 | 5 | official_platform | TikTok Advertising Policies | Common Reasons Ads Fail Review | https://ads.tiktok.com/help/article/common-reasons-ads-fail-review?lang=en |
| TT12 | 4 | official_platform_guidance | TikTok for Business Help Center | Creative best practices for performance ads | https://ads.tiktok.com/help/article/creative-best-practices |
| TT13 | 5 | official_platform | TikTok for Business Help Center | Commercial Content Disclosure setting for advertisers | https://ads.tiktok.com/help/article/about-the-commercial-content-disclosure-setting-for-advertisers |
| TT14 | 5 | official_platform | TikTok Shop Academy | TikTok Shop Intellectual Property Policy | https://seller-us.tiktok.com/university/essay?knowledge_id=6837901778306818 |
| TT15 | 4 | official_platform_guidance | TikTok for Business | Creative Codes: Six Principles for TikTok-First Ads | https://ads.tiktok.com/business/creativecenter/quicktok/online/TikTokCreativeCodes.pdf |
| TT16 | 4 | official_platform_guidance | TikTok for Business Help Center | How to create a split test in TikTok Ads Manager | https://ads.tiktok.com/help/article/create-split-test |
| TT17 | 5 | official_platform_measurement | TikTok for Business Help Center | About Conversion Lift Study | https://ads.tiktok.com/help/article/about-conversion-lift-study |
| TT18 | 5 | official_platform | TikTok Shop Academy | Product Quality Policy | https://seller-us.tiktok.com/university/essay?knowledge_id=5203348292765486 |
| TT19 | 5 | official_platform | TikTok Shop Academy | Prohibited Products Policy | https://seller-us.tiktok.com/university/essay?knowledge_id=1399532709988097 |
| TT20 | 5 | official_platform | TikTok Shop Academy | Restricted Products Policy | https://seller-us.tiktok.com/university/essay?knowledge_id=3238037484275457 |
| FTC01 | 5 | official_regulator | Federal Trade Commission | FTC Endorsement Guides: What People Are Asking | https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking |
| FTC02 | 5 | official_regulator | Federal Trade Commission | FTC Staff Revises Online Advertising Disclosure Guidelines | https://www.ftc.gov/news-events/news/press-releases/2013/03/ftc-staff-revises-online-advertising-disclosure-guidelines |
| FTC03 | 5 | official_regulator | Federal Trade Commission | Final Rule Banning Fake Reviews and Testimonials | https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials |
| FTC04 | 5 | official_regulator | Federal Trade Commission | Health Products Compliance Guidance | https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance |
| FTC05 | 5 | official_regulator | Federal Trade Commission | Mail, Internet, or Telephone Order Merchandise Rule | https://www.ftc.gov/legal-library/browse/rules/mail-internet-or-telephone-order-merchandise-rule |
| USPTO01 | 5 | official_government | United States Patent and Trademark Office | Trademark Search System Updates | https://www.uspto.gov/trademarks/search/trademark-search-system-updates |
| USPTO02 | 5 | official_government | United States Patent and Trademark Office | Likelihood of Confusion | https://www.uspto.gov/trademarks/search/likelihood-confusion |
| USCO01 | 5 | official_government | U.S. Copyright Office | Visual Artists: Copyright Basics | https://www.copyright.gov/engage/visual-artists/ |
| POD01 | 4 | provider_documentation | Printify Help Center | How do I review orders with personalized products? | https://help.printify.com/hc/en-us/articles/28903834238097-How-do-I-review-orders-with-personalized-products |
| POD02 | 4 | provider_documentation | Printify Help Center | How can I create mockups for Early Access Catalog products? | https://help.printify.com/hc/en-us/articles/25641196380817-How-can-I-create-mockups-for-Early-Access-Catalog-products |
| POD03 | 4 | provider_documentation | Printify Help Center | Why does my product look different from the mockup? | https://help.printify.com/hc/en-us/articles/4483617784721-Why-does-my-product-look-different-from-the-mockup |
| POD04 | 4 | provider_documentation | Printify Help Center | How do I set up product personalization? | https://help.printify.com/hc/en-us/articles/29856933892241-How-do-I-set-up-product-personalization |
| POD05 | 5 | official_marketplace_policy | Etsy | Etsy Creativity Standards | https://www.etsy.com/legal/creativity/ |
| DS01 | 4 | established_product_documentation | Shopify | Dropshipping Fulfillment: The Complete Guide (2026) | https://www.shopify.com/blog/dropshipping-fulfillment |
| DS02 | 4 | established_product_documentation | Shopify | How To Start an Online Store Without Inventory (2026) | https://www.shopify.com/blog/how-to-start-an-online-store-without-inventory |
| DS03 | 4 | established_product_documentation | Shopify | Product Sourcing Guide: How To Get Started (2026) | https://www.shopify.com/blog/product-sourcing-apps |
| DS04 | 4 | established_product_documentation | Shopify | How Does Alibaba Work? Buying and Safety Guide (2026) | https://www.shopify.com/blog/16665772-alibaba-101-how-to-safely-source-products-from-the-worlds-biggest-supplier-directory |
| DS05 | 3 | provider_documentation | AutoDS Help Center | Product sourcing and supplier monitoring documentation | https://help.autods.com/ |
| UGC01 | 3 | industry_product_blog | Insense | How to Write a UGC Brief That Gets Results | https://insense.pro/blog/ugc-brief |
| UGC02 | 3 | industry_product_blog | Insense | Paid Media UGC: What it is and how to do it | https://insense.pro/blog/paid-media-ugc |
| UGC03 | 3 | industry_product_blog | Insense | TikTok Spark Ads Setup Guide (2026) | https://insense.pro/blog/tiktok-spark-ads |
| UGC04 | 3 | industry_product_blog | Billo | How to repurpose UGC | https://billo.app/blog/repurpose-ugc/ |
| UGC05 | 3 | industry_product_blog | Billo | UGC Brief Template and Production Guidance | https://billo.app/blog/ugc-brief-template/ |
| UGC06 | 3 | official_product_pricing | Insense | Influencer and UGC Campaign Pricing | https://insense.pro/pricing |
| UGC07 | 3 | industry_product_blog | Modash | Influencer Whitelisting Guidance | https://www.modash.io/blog/influencer-whitelisting |
| PERF01 | 4 | vendor_first_party_dataset | Motion | Creative Benchmarks 2026 | https://motionapp.com/library/research/creative-benchmarks-2026/ |
| PERF02 | 3 | industry_expert_event | Motion | 2025 DTC Creative Trends: Expert Lightning Round | https://motionapp.com/library/talk/motion-s-2025-facebook-ad-creative-trends-dtc-expert-lightning-round/ |
| PERF03 | 3 | industry_expert_interview | Motion / Savannah Sanchez | How to Make Ads for Meta and TikTok in 2026 | https://motionapp.com/blog/how-to-build-a-high-volume-ad-production-system-for-meta-and-tiktok-in-2026 |
| PERF04 | 3 | industry_product_blog | Alison.ai | Creative Iteration for Better Ads | https://alison.ai/resources/blog/creative-iteration-for-better-ads |
| PERF05 | 3 | vendor_first_party_reports | Alison.ai | Creative Intelligence Reports | https://alison.ai/resources/creative-intelligence-reports |
| PERF06 | 3 | industry_product_blog | Marpipe | Best Practices for Testing Ad Creative | https://www.marpipe.com/blog/best-practices-for-testing-ad-creative |
| PERF07 | 4 | primary_research_preprint | Lee et al., arXiv preprint | Offline-to-Online Creative Optimization with Generative Models and Adaptive Testing | https://arxiv.org/abs/2607.23696 |
| PERF08 | 3 | industry_product_blog | Foreplay | Guide to Creating an Effective Creative Brief | https://www.foreplay.co/post/guide-to-creating-an-effective-creative-brief |
| PERF09 | 3 | industry_product_blog | Foreplay | Creative Strategy Platform Synergies | https://www.foreplay.co/post/creative-strategy-platform-synergies |
| WTP01 | 3 | official_product_pricing | Motion | Motion Pricing and Plans | https://motionapp.com/llm-info |
| WTP02 | 3 | official_product_pricing | Foreplay | Foreplay Pricing | https://www.foreplay.co/pricing |
| COM01 | 2 | seller_anecdote | Reddit r/TikTokshop | 30 samples sent, no sale | https://www.reddit.com/r/TikTokshop/comments/1ux5rk0/30_samples_sent_no_sale/ |
| COM02 | 2 | seller_anecdote | Reddit r/TikTokshop | 1.4M-view affiliate video with weak sales | https://www.reddit.com/r/TikTokshop/comments/1lgdfzj/our_tiktok_affiliate_video_went_viral_14m_views/ |
| COM03 | 2 | seller_anecdote | Reddit r/TikTokshop | Affiliates receiving samples but not posting | https://www.reddit.com/r/TikTokshop/comments/1b9p0cw/what_do_you_do_when_affiliates_dont_post_any/ |
| COM04 | 2 | seller_anecdote | Reddit r/printondemand | Mockup tool and printed product mismatch | https://www.reddit.com/r/printondemand/comments/1t7d1dl/avoid_fourthwall_their_mockup_tool_and_printed/ |
| COM05 | 2 | seller_anecdote | Reddit r/dropshipping | Supplier stock and price changes | https://www.reddit.com/r/dropshipping/comments/1u9gt9c/how_do_you_track_supplier_stock_and_price_changes/ |
| COM06 | 2 | seller_anecdote | Reddit r/dropshipping | Wrong item from dropshipping supplier | https://www.reddit.com/r/dropshipping/comments/1sirqc6/how_do_you_verify_product_quality_before_it_ships/ |
| COM07 | 2 | seller_anecdote | Reddit r/dropshipping | Unexpected shipping cost and low supplier stock | https://www.reddit.com/r/dropshipping/comments/1q15jg9/unexpected_aliexpress_shipping_costs_and_low/ |
| COM08 | 2 | creator_community_anecdote | Reddit r/UGCcreators | Brand-side UGC pricing and rights discussion | https://www.reddit.com/r/UGCcreators/comments/1v6fwqw/im_on_the_brand_side_of_ugc_deals_heres_what/ |
| COM09 | 2 | creator_community_anecdote | Reddit r/UGCcreators | UGC glossary: rights, revisions, raw footage | https://www.reddit.com/r/UGCcreators/comments/1vat08s/a_glossary_of_common_ugc_terms_for_newer_creators/ |
| COM10 | 2 | creator_community_anecdote | Reddit r/UGCcreators | Perpetual paid usage requested without compensation | https://www.reddit.com/r/UGCcreators/comments/1uma3mc/the_amount_of_disrespect/ |
