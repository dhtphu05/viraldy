from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from .errors import SmartRemakeValidationError


SubjectPresence = Literal["none", "hands_only", "person"]
ShotPreservationMode = Literal["exact", "adaptive"]
CreativeArchetype = Literal[
    "product_demo",
    "problem_solution",
    "before_after",
    "transformation",
    "unboxing",
    "testimonial",
    "comparison",
    "lifestyle_showcase",
    "offer_led",
    "product_reveal",
    "tutorial",
    "visual_meme",
    "continuous_one_take",
    "fast_montage",
    "other",
]
VisualStructure = Literal[
    "continuous",
    "sequential_shots",
    "before_after",
    "split_screen",
    "slideshow",
    "screen_recording",
    "mixed_media",
]
PrimaryHookType = Literal[
    "visual_action",
    "visual_surprise",
    "problem",
    "transformation",
    "reaction",
    "text",
    "spoken_line",
    "offer",
    "product_result",
]
ProductCardinality = Literal["single", "multiple"]
MotionBeatRole = Literal[
    "hook",
    "setup",
    "problem",
    "action",
    "demonstration",
    "transition",
    "reveal",
    "proof",
    "reaction",
    "payoff",
    "hero",
    "cta",
]
MotionBeatPriority = Literal["mandatory", "supporting", "optional"]
CreativeRouteStrategy = Literal[
    "continuous_action",
    "sequential_demo",
    "problem_to_solution",
    "before_to_after",
    "transformation_sequence",
    "unboxing_sequence",
    "testimonial_structure",
    "comparison_sequence",
    "offer_structure",
    "reveal_sequence",
    "simplified_sequential",
]
SmartRemakePacingProfile = Literal["fast_social", "balanced", "slow_cinematic"]
RenderProvider = Literal["flowkit", "unifically"]


class UploadedMedia(BaseModel):
    bytes: bytes
    mime_type: str
    file_name: str | None = None


class VisualIdentity(BaseModel):
    colors: list[str] = Field(default_factory=list)
    pattern: str | None = None
    texture: str | None = None
    shape: str | None = None
    material: str | None = None
    visibleBranding: str | None = None


class ProductUsage(BaseModel):
    realisticUseCases: list[str] = Field(default_factory=list)
    suitableSurfaces: list[str] = Field(default_factory=list)
    contactPoints: list[str] = Field(default_factory=list)
    handlingInstructions: list[str] = Field(default_factory=list)
    usageConstraints: list[str] = Field(default_factory=list)
    forbiddenUsageErrors: list[str] = Field(default_factory=list)


class ProductReference(BaseModel):
    imageUrl: str | None = None
    storageKey: str | None = None
    characterName: str
    entityType: Literal["visual_asset"] = "visual_asset"


class ProductLock(BaseModel):
    mode: Literal["off", "auto", "strict"] = "auto"
    productName: str
    productType: str
    visualIdentity: VisualIdentity = Field(default_factory=VisualIdentity)
    productUsage: ProductUsage = Field(default_factory=ProductUsage)
    mustPreserve: list[str] = Field(default_factory=list)
    canChange: list[str] = Field(default_factory=list)
    forbiddenErrors: list[str] = Field(default_factory=list)
    productReference: ProductReference

    @field_validator("productName", "productType")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        value = normalize_text(value)
        if not value:
            raise ValueError("field must be non-empty")
        return value


class CameraStyle(BaseModel):
    angle: str
    framing: str
    movement: str


class Setting(BaseModel):
    locationType: str
    backgroundElements: list[str] = Field(default_factory=list)


class ActorBehavior(BaseModel):
    expression: str | None = None
    gestures: list[str] = Field(default_factory=list)


class CreativeConcept(BaseModel):
    hook: str
    adType: str
    productMoment: str


class PhysicalAction(BaseModel):
    operator: str | None = None
    targetSurface: str | None = None
    contactPoint: str | None = None
    movement: str | None = None
    visibleEffect: str | None = None


class MotionBeat(BaseModel):
    startSecond: float
    endSecond: float
    action: str
    role: MotionBeatRole | None = None
    priority: MotionBeatPriority | None = None
    physicalAction: PhysicalAction | None = None
    stateBefore: str | None = None
    stateAfter: str | None = None

    @model_validator(mode="after")
    def _valid_timing(self) -> "MotionBeat":
        if self.startSecond < 0 or self.endSecond < self.startSecond:
            raise ValueError("motion beat has invalid timing")
        return self


class ReferenceMusic(BaseModel):
    mode: Literal["none", "extract"] = "none"
    reason: str | None = None
    assetId: str | None = None


class AudioPlan(BaseModel):
    mode: Literal["native", "silent"] = "silent"
    language: str | None = None
    dialogue: str | None = None
    ambience: str | None = None
    soundEffects: list[str] = Field(default_factory=list)
    music: str | None = None
    warnings: list[str] = Field(default_factory=list)
    referenceMusic: ReferenceMusic = Field(default_factory=ReferenceMusic)


class PacingActionBeat(BaseModel):
    action: str
    durationSeconds: float
    shotType: str


class PacingPlan(BaseModel):
    pace: Literal["slow", "medium", "fast", "balanced"] = "medium"
    shotCount: int = 1
    averageShotDuration: float = 4
    cutStyle: Literal["continuous", "soft_cut", "hard_cut", "jump_cut", "mixed", "natural_cut"] = "soft_cut"
    motionIntensity: Literal["low", "medium", "high"] = "medium"
    cameraEnergy: Literal["static", "smooth", "dynamic", "medium"] = "smooth"
    audioEnergy: Literal["low", "medium", "high"] = "medium"
    actionBeats: list[PacingActionBeat] = Field(default_factory=list)


class OpeningShot(BaseModel):
    durationSeconds: float = 1
    framing: str = "product close-up"
    cameraAngle: str = "front"
    cameraMovement: str = "static"
    subjectPresence: SubjectPresence = "none"
    subjectPosition: str = "none"
    productPosition: str = "center frame"
    productState: str = "visible"
    initialPose: str = "static"
    firstAction: str = "show product"
    gazeDirection: str | None = None
    backgroundLayout: list[str] = Field(default_factory=list)
    cutAtSecond: float | None = None


class CreativeRouteWarning(BaseModel):
    code: str
    message: str
    originalStructure: str | None = None
    selectedStrategy: str | None = None


class ReferenceAnalysisRenderability(BaseModel):
    supported: bool = True
    selectedStrategy: CreativeRouteStrategy = "sequential_demo"
    warnings: list[CreativeRouteWarning] = Field(default_factory=list)


class MotionBeatSemantic(BaseModel):
    beatIndex: int
    role: MotionBeatRole
    priority: MotionBeatPriority
    action: str
    productStateBefore: str | None = None
    productStateAfter: str | None = None
    subjectStateBefore: str | None = None
    subjectStateAfter: str | None = None
    visualEvidence: str
    renderabilityWarnings: list[str] = Field(default_factory=list)


class StateTransitionSemantic(BaseModel):
    fromState: str
    toState: str
    triggerAction: str
    visualEvidence: str
    priority: MotionBeatPriority = "supporting"


class CreativeStructure(BaseModel):
    archetype: CreativeArchetype
    visualStructure: VisualStructure
    primaryHookType: PrimaryHookType
    productCardinality: ProductCardinality
    motionBeatSemantics: list[MotionBeatSemantic] = Field(default_factory=list)
    stateTransitions: list[StateTransitionSemantic] = Field(default_factory=list)
    renderabilityWarnings: list[str] = Field(default_factory=list)


class SourceShot(BaseModel):
    shotIndex: int
    startSecond: float
    endSecond: float
    durationSeconds: float
    role: MotionBeatRole
    priority: MotionBeatPriority
    framing: str
    cameraAngle: str
    cameraMovement: str
    subjectPresence: SubjectPresence
    action: str
    productState: str | None = None
    stateBefore: str | None = None
    stateAfter: str | None = None
    transitionOut: str | None = None


class ReferenceAnalysis(BaseModel):
    analysisOnly: Literal[True] = True
    subjectPresence: SubjectPresence
    shotPreservationMode: ShotPreservationMode = "adaptive"
    sourceShotCount: int | None = None
    sourceDurationSeconds: float | None = None
    sourceShots: list[SourceShot] | None = None
    format: str
    sceneCount: int
    cameraStyle: CameraStyle
    setting: Setting
    actorBehavior: ActorBehavior | None = None
    creativeConcept: CreativeConcept
    motionBeats: list[MotionBeat]
    forbiddenReuse: list[str] = Field(default_factory=list)
    audioPlan: AudioPlan
    pacingPlan: PacingPlan
    openingShot: OpeningShot
    openingForbiddenSubstitutions: list[str] = Field(default_factory=list)
    creativeArchetype: CreativeArchetype | None = None
    visualStructure: VisualStructure | None = None
    primaryHookType: PrimaryHookType | None = None
    productCardinality: ProductCardinality | None = None
    renderability: ReferenceAnalysisRenderability | None = None
    creativeStructure: CreativeStructure | None = None


class NormalizedShot(BaseModel):
    shotIndex: int
    startSecond: float
    endSecond: float
    durationSeconds: float
    role: MotionBeatRole
    priority: MotionBeatPriority
    action: str
    physicalAction: PhysicalAction | None = None
    framing: str | None = None
    cameraAngle: str | None = None
    cameraMovement: str | None = None
    cameraBehavior: str | None = None
    productState: str | None = None
    transitionOut: str | None = None
    subjectPresence: SubjectPresence
    stateBefore: str | None = None
    stateAfter: str | None = None
    sourceShotIndex: int | None = None
    sourceBeatIndexes: list[int] = Field(default_factory=list)


class NormalizedSceneTimeline(BaseModel):
    targetDuration: Literal[8] = 8
    pacingProfile: SmartRemakePacingProfile
    visualStructure: VisualStructure
    shots: list[NormalizedShot]
    cutTimes: list[float] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)


class SmartRemakeScene(BaseModel):
    displayOrder: int
    chainType: Literal["ROOT"] = "ROOT"
    parentSceneId: None = None
    prompt: str
    imagePrompt: str
    videoPrompt: str
    characterNames: list[str]
    source: Literal["smart_remake"] = "smart_remake"
    textOverlay: str | None = None
    sourceFrame: dict[str, Any] | None = None
    sourceFrames: list[dict[str, Any]] = Field(default_factory=list)
    sourceSegment: dict[str, Any] | None = None
    shotPlan: dict[str, Any] | None = None


class SceneMap(BaseModel):
    version: str = "smart-remake-scene-map-v1"
    mode: Literal["smart_remake", "montage"] = "smart_remake"
    targetDuration: Literal[8, 16, 24, 32]
    aspectRatio: Literal["9:16"]
    orientation: Literal["VERTICAL"] = "VERTICAL"
    sceneCount: Literal[1, 2, 3, 4]
    scenes: list[SmartRemakeScene]

    @model_validator(mode="after")
    def _valid_count(self) -> "SceneMap":
        expected = self.targetDuration // 8
        if self.sceneCount != expected or len(self.scenes) != expected:
            raise ValueError("scene count does not match target duration")
        return self


class SmartRemakeCompileResult(BaseModel):
    success: Literal[True]
    mode: Literal["smart_remake", "montage"]
    renderSubmitted: Literal[False]
    inputSummary: dict[str, Any]
    analyzeOutput: dict[str, Any]
    referenceAnalysis: dict[str, Any]
    productLock: dict[str, Any]
    sceneMap: dict[str, Any]
    compiledPrompts: list[dict[str, Any]]
    compilerVersion: str
    compilerDiagnostics: dict[str, Any]
    diagnostics: dict[str, Any]
    versions: dict[str, Any]
    warnings: list[str]


class ProductMetadata(BaseModel):
    title: str | None = None
    description: str | None = None
    specsText: str | None = None
    price: str | None = None
    originalPrice: str | None = None
    discountPercent: str | int | float | None = None
    platform: str | None = None
    sourceUrl: str | None = None


class CompileSmartRemakeRequest(BaseModel):
    mode: Literal["smart_remake", "montage"] = "smart_remake"
    targetDuration: Literal[8, 16, 24, 32]
    aspectRatio: Literal["9:16"]
    language: str | None = None
    prompt: str | None = None
    description: str | None = None
    productUrl: str | None = None
    referenceImages: list[str] = Field(default_factory=list)
    referenceVideoUrl: str | None = None
    productLock: dict[str, Any] | None = None
    visualIdentity: dict[str, Any] | None = None
    productReference: dict[str, Any] | None = None
    referenceVideo: UploadedMedia | None = None
    productImage: UploadedMedia | None = None
    productMetadata: ProductMetadata | None = None
    productSource: Literal["url", "upload", "url_and_upload", "prompt", "reference"]
    warnings: list[str] = Field(default_factory=list)


class RenderSmartRemakeInput(BaseModel):
    productLock: dict[str, Any]
    sceneMap: dict[str, Any]
    referenceAnalysis: dict[str, Any] | None = None
    versions: Any | None = None
    warnings: list[str] = Field(default_factory=list)
    audioRequired: bool = False
    productImage: UploadedMedia
    projectName: str
    provider: RenderProvider = "unifically"


def normalize_text(value: Any, fallback: str = "") -> str:
    if isinstance(value, str):
        normalized = " ".join(value.split())
        return normalized or fallback
    return fallback


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [normalize_text(item) for item in value if normalize_text(item)]


def model_to_dict(value: BaseModel) -> dict[str, Any]:
    return value.model_dump(exclude_none=True)


def validation_error(message: str, code: str, details: Any | None = None) -> SmartRemakeValidationError:
    return SmartRemakeValidationError(message, code, details)


def validate_model(model: type[BaseModel], value: Any, message: str, code: str) -> BaseModel:
    try:
        return model.model_validate(value)
    except ValidationError as exc:
        raise validation_error(message, code, exc.errors()) from exc
