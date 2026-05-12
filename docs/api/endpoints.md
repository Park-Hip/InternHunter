# Endpoints

## Current Endpoints

- `GET /` -> returns a welcome message
- `POST /api/chat` -> runs the chat agent
- `GET /api/chat/sessions/{session_id}` -> returns chat history
- `GET /api/chat/users/{user_id}/sessions` -> returns user sessions
- `DELETE /api/chat/sessions/{session_id}` -> deletes a chat session

## Planned Endpoints

- planned: job search endpoint
- planned: resume upload endpoint outside the chat tool path
- planned: job match endpoint outside the chat tool path

## Notes

- The repo currently exposes search and resume matching mainly through chat tools, not dedicated HTTP routes.
