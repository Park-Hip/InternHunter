def test_canonical_boundary_imports():
    import src.internhunter.llm
    import src.internhunter.embeddings
    import src.internhunter.extraction
    import src.internhunter.resume
    import src.internhunter.chat

    assert src.internhunter.llm is not None
    assert src.internhunter.embeddings is not None
    assert src.internhunter.extraction is not None
    assert src.internhunter.resume is not None
    assert src.internhunter.chat is not None


def test_resume_matching_exports():
    from src.internhunter.resume.matching import (
        MatchResumeArgs,
        UploadResumeArgs,
        execute_match_resume,
        execute_upload_resume,
    )

    assert MatchResumeArgs is not None
    assert UploadResumeArgs is not None
    assert callable(execute_match_resume)
    assert callable(execute_upload_resume)
