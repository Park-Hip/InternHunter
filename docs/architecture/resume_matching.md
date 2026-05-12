# Resume Matching

Resume matching currently exists as a chat-tool workflow backed by `user_profiles`.

## Current Flow

1. A user uploads resume text through the chat tool.
2. The resume text is embedded.
3. The embedding is stored with the user profile.
4. Matching uses pgvector similarity against `clean_jobs.embedding`.

## Current Storage

- resume text is stored in `user_profiles.resume_text`
- resume vector is stored in `user_profiles.resume_embedding`

## TODO

- TODO: verify whether resume parsing from PDF or DOCX exists anywhere else in the repo.
- TODO: verify whether matching scores are normalized or only returned as raw similarity order.
