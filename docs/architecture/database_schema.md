# Database Schema

This is a draft schema summary based on `src/infrastructure/db/models.py`.

## `raw_jobs`

- `id`
- `url`
- `title`
- `company`
- `location`
- `full_json_dump`
- `status`
- `extraction_method`
- `raw_markdown`
- `retry_count`
- `created_at`

## `clean_jobs`

- `id`
- `raw_job_id`
- `standardized_title`
- `job_level`
- `is_internship`
- `description`
- `requirement`
- `benefit`
- `cities`
- `experience`
- `min_gpa`
- `english_requirement`
- `salary_min`
- `salary_max`
- `currency`
- `is_salary_negotiable`
- `tech_stack`
- `technical_competencies`
- `domain_knowledge`
- `embedding`
- `created_at`

## `audit_jobs`

- `id`
- `url`
- `error_type`
- `error_message`
- `screenshot_path`
- `html_content`
- `created_at`

## `user_profiles`

- `id`
- `user_id`
- `resume_text`
- `resume_embedding`
- `created_at`
- `updated_at`

## `chat_sessions`

- `id`
- `user_id`
- `created_at`

## `chat_messages`

- `id`
- `session_id`
- `role`
- `content`
- `tool_calls`
- `tool_call_id`
- `tokens_used`
- `created_at`

## `pipeline_runs`

- `id`
- `run_id`
- `timestamp`
- `jobs_acquired`
- `jobs_processed`
- `jobs_failed`
- `status`

## TODO

- TODO: verify indexes, constraints, and nullability directly from migrations or live DDL.
