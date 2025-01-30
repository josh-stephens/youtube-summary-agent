# YouTube Summary Agent

A Live Agent Studio agent that fetches and summarizes the latest video from a YouTube playlist. The agent provides rich metadata including view counts, upload dates, and top comments.

## Features

- Fetches latest video from a YouTube playlist
- Generates AI-powered summary of video content
- Provides video metadata (title, channel, views, etc.)
- Shows top comments
- Stores conversation history in Supabase

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in your credentials:
   - `API_BEARER_TOKEN`: Your chosen authentication token
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase anon/public key
   - `YOUTUBE_API_KEY`: Your YouTube Data API key
   - `OPENAI_API_KEY`: Your OpenAI API key

4. Create a `messages` table in your Supabase database:
   ```sql
   CREATE TABLE messages (
       id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
       session_id TEXT NOT NULL,
       message JSONB NOT NULL
   );
   ```

## Usage

Send a POST request to `/api/youtube-summary-agent` with:

The query can be any of these formats:
- YouTube video URL: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
- YouTube playlist URL: `https://www.youtube.com/playlist?list=PLlaN88a7y2_plecYoJxvRFTLHVbIVAOoc`
- Short video URL: `https://youtu.be/dQw4w9WgXcQ`
- Direct video ID: `dQw4w9WgXcQ`
- Direct playlist ID: `PLlaN88a7y2_plecYoJxvRFTLHVbIVAOoc`

```json
{
    "query": "YOUR_VIDEO_OR_PLAYLIST_URL",
    "user_id": "test-user",
    "request_id": "test-request",
    "session_id": "test-session"
}
```

Headers:
```http
Authorization: Bearer your_token_here
Content-Type: application/json
```

## Development

See `TODO.md` for planned features and improvements.