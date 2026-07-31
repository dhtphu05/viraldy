from viraldy.modules.jobs.registry import JobType, get_job_definition


def test_ugc_review_job_definition_reuses_default_processing_queue() -> None:
    definition = get_job_definition("ugc_review_v1")

    assert definition.job_type is JobType.UGC_REVIEW
    assert definition.queue == "default"
    assert definition.result_subject_type == "ugc_review"
    assert definition.required_stages == (
        "loading_asset",
        "probing_media",
        "selecting_policies",
        "evaluating_review",
        "persisting_results",
    )
