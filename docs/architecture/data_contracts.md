# Data Contracts

Draft contracts based on the current core models and repositories.

## RawJobPage

- `url: string`
- `scraped_at: string`
- `source: string`
- `title: string | TODO`
- `company: string | TODO`
- `location: string | TODO`
- `full_json_dump: object | TODO`
- `raw_markdown: string | TODO`

## ExtractedJob / ProcessedJob

- `standardized_title: string`
- `job_level: string | null`
- `is_internship: boolean`
- `description: string | null`
- `requirement: string | null`
- `benefit: string | null`
- `cities: string[]`
- `experience: number | null`
- `min_gpa: number | null`
- `english_requirement: string | null`
- `salary_min: number | null`
- `salary_max: number | null`
- `currency: string | null`
- `is_salary_negotiable: boolean`
- `tech_stack: string[]`
- `technical_competencies: string[]`
- `domain_knowledge: string[]`
- TODO: verify whether `full_json_dump` is ever stored on the structured model.

## JobEmbedding

- `job_id: number | TODO`
- `embedding: number[768]`
- `model_name: string | TODO`
- `created_at: string | TODO`

## UserProfile / ResumeProfile

- `user_id: string`
- `resume_text: string`
- `resume_embedding: number[768] | null`
- TODO: verify whether a separate parsed resume model exists or is planned.

## SearchQuery

- `title: string[] | null`
- `job_level: string[] | null`
- `cities: string[] | null`
- `experience: number | null`
- `limit: number`
- TODO: verify whether natural-language query fields are stored separately.

## MatchResult

- `title: string`
- `level: string`
- `company: string`
- `cities: string[]`
- `experience_required_years: number | null`
- `salary_range: string`
- `url: string`
- `match_score: number | null`
- TODO: verify whether a ranking score is computed now or only planned.
