# YouTube Summary Agent

A Live Agent Studio agent that fetches and summarizes YouTube videos. The agent provides rich metadata including view counts, upload dates, top comments, and generates AI-powered summaries using GPT-4.

## Features

- Supports multiple YouTube URL formats:
  - Full video URLs
  - Short video URLs (youtu.be)
  - Direct video IDs
  - Playlist URLs (grabs the most recent video from the playlist)
  - Direct playlist IDs (grabs the most recent video from the playlist)
- Generates AI-powered summary of video content
  - Grounds the summary on the video's metadata and transcript
- Provides comprehensive video metadata:
  - Title and channel information
  - View counts and engagement metrics
  - Upload date and duration
  - Tags and topics
  - Availability of captions
- Shows top comments with engagement metrics
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

Send a POST request to `/api/youtube-summary-agent` with any of these formats:
- YouTube video URL: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
- YouTube playlist URL: `https://www.youtube.com/playlist?list=PLlaN88a7y2_plecYoJxvRFTLHVbIVAOoc`
- Short video URL: `https://youtu.be/dQw4w9WgXcQ`
- Direct video ID: `dQw4w9WgXcQ`
- Direct playlist ID: `PLlaN88a7y2_plecYoJxvRFTLHVbIVAOoc`

Request format:
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

## Testing

Use the included PowerShell test script to verify functionality:
```powershell
.\test.ps1
```

The test script will:
1. Load configuration from your .env file
2. Test all supported URL formats
3. Display formatted results with color coding
4. Show any errors or issues

## Development

See `TODO.md` for planned features and improvements.