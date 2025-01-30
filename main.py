from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os
from typing import Optional
from datetime import datetime
import googleapiclient.discovery
import googleapiclient.errors
from youtube_transcript_api import YouTubeTranscriptApi
import openai
from dotenv import load_dotenv
import logging
from supabase.client import create_client, Client

# Load environment variables
load_dotenv()

# FastAPI setup
app = FastAPI()
security = HTTPBearer()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model definitions
class AgentRequest(BaseModel):
    query: str
    user_id: str
    request_id: str
    session_id: str

class AgentResponse(BaseModel):
    response: str
    success: bool
    error: Optional[str] = None

# Authentication
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != os.getenv("API_BEARER_TOKEN"):
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials

# Supabase Setup
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Update store_message function
def store_message(session_id: str, message_type: str, content: str, data: Optional[dict] = None):
    message = {
        "type": message_type,
        "content": content
    }
    if data:
        message["data"] = data
        
    supabase.table("messages").insert({
        "session_id": session_id,
        "message": message
    }).execute()

# YouTube API Setup
youtube = googleapiclient.discovery.build(
    "youtube", 
    "v3", 
    developerKey=os.getenv("YOUTUBE_API_KEY")
)

# OpenAI API Setup
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_latest_video(playlist_id):
    """Fetches the most recent video from a public YouTube playlist."""
    # Get video basic info from playlist
    try:
        logger.info(f"Fetching playlist items for playlist ID: {playlist_id}")
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=1
        )
        response = request.execute()
        logger.info(f"Playlist API response snippet: {response['items'][0]['snippet']}")
        
        if "items" not in response or not response["items"]:
            logger.error("No items found in playlist response")
            return None
        
        video = response["items"][0]["snippet"]
        video_id = video["resourceId"]["videoId"]
        logger.info(f"Found video ID: {video_id}")
        
        # Get additional video statistics and details
        logger.info("Fetching video statistics")
        video_request = youtube.videos().list(
            part="statistics,snippet,contentDetails,topicDetails,status",
            id=video_id
        )
        video_response = video_request.execute()
        logger.info(f"Video details snippet: {video_response['items'][0]['snippet']}")
        
        if not video_response["items"]:
            logger.error("No video details found")
            return None
            
        video_item = video_response["items"][0]  # Get the whole video item
        video_details = video_item["snippet"]    # Get snippet for title, description etc
        video_stats = video_item["statistics"]   # Get statistics separately
        video_content = video_item["contentDetails"]
        
        # Use the channel info from the video details
        channel_name = video_details["channelTitle"]
        
        # Get top comments
        try:
            logger.info("Fetching video comments")
            comments_request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                order="relevance",
                maxResults=5
            )
            comments_response = comments_request.execute()
            top_comments = [
                {
                    "author": item["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"],
                    "text": item["snippet"]["topLevelComment"]["snippet"]["textDisplay"],
                    "likes": item["snippet"]["topLevelComment"]["snippet"]["likeCount"]
                }
                for item in comments_response.get("items", [])
            ]
            logger.info(f"Found {len(top_comments)} comments")
        except Exception as e:
            logger.error(f"Error fetching comments: {str(e)}")
            top_comments = []
        
        return {
            "video_id": video_id,
            "title": video_details["title"],
            "description": video_details["description"],
            "published_at": video_details["publishedAt"],
            "channel_name": channel_name,
            "view_count": video_stats.get("viewCount", "N/A"),
            "like_count": video_stats.get("likeCount", "N/A"),
            "comment_count": video_stats.get("commentCount", "N/A"),
            "top_comments": top_comments,
            "duration": video_content["duration"],  # Video length in ISO 8601 format
            "tags": video_details.get("tags", []),  # Keywords/tags
            "category_id": video_details.get("categoryId", "N/A"),  # YouTube category
            "language": video_details.get("defaultLanguage", "N/A"),
            "made_for_kids": video_item["status"]["madeForKids"],
            "privacy_status": video_item["status"]["privacyStatus"],
            "definition": video_content["definition"],  # HD or SD
            "caption": video_content["caption"],  # Has captions?
            "licensed_content": video_content.get("licensedContent", False),
            "projection": video_content["projection"],  # 360° video?
            "topics": video_item.get("topicDetails", {}).get("topicCategories", [])
        }
    except Exception as e:
        logger.error(f"Error in get_latest_video: {str(e)}")
        raise

def get_video_transcript(video_id):
    """Fetches transcript of the video, if available."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t["text"] for t in transcript])
    except:
        return None  # No transcript available

def summarize_text(text, video_data):
    """Summarizes the transcript using OpenAI GPT, with video metadata for context."""
    system_prompt = """You are an AI that summarizes YouTube videos. 
    Provide a clear, informative summary that captures the key points and maintains accuracy, 
    especially regarding technical terms, proper nouns, and people mentioned. 
    The channel name often indicates the primary content creator or presenter - use this context 
    to accurately attribute statements and actions in the video."""

    context = f"""Video Title: {video_data['title']}
Channel: {video_data['channel_name']} (This is likely the presenter/creator's channel)
Description: {video_data['description']}
Duration: {video_data['duration']}
View Count: {video_data['view_count']}
Tags: {', '.join(video_data['tags'][:5]) if video_data['tags'] else 'None'}
Topics: {', '.join(video_data['topics']) if video_data['topics'] else 'None'}
Language: {video_data['language']}
Has Captions: {'Yes' if video_data['caption'] == 'true' else 'No'}

Using this context, please provide an accurate summary of the following transcript, 
being especially careful to correctly attribute who is speaking or presenting:
"""

    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context + text}
        ]
    )
    return response["choices"][0]["message"]["content"]

def process_playlist(playlist_id):
    """Main function to process the latest video from a playlist."""
    video_data = get_latest_video(playlist_id)
    if not video_data:
        # Return a properly structured error response
        return {
            "title": "Error",
            "description": "No videos found in the playlist.",
            "published_at": datetime.now().isoformat(),
            "channel_name": "N/A",
            "view_count": "N/A",
            "like_count": "N/A",
            "comment_count": "N/A",
            "top_comments": [],
            "summary": "No videos found in the playlist."
        }

    transcript = get_video_transcript(video_data["video_id"])
    summary = summarize_text(transcript, video_data) if transcript else "Transcript unavailable."

    # Return all metadata fields
    return {
        **video_data,  # Include all video metadata
        "summary": summary
    }

def format_response(result):
    """Formats the video information and summary into a readable response."""
    # Format the date
    published_date = datetime.fromisoformat(result["published_at"].replace('Z', '+00:00'))
    formatted_date = published_date.strftime("%B %d, %Y")
    
    # Format view count with commas
    try:
        view_count = "{:,}".format(int(result["view_count"]))
    except:
        view_count = result["view_count"]
    
    # Format duration from ISO 8601 to readable format
    duration = result.get("duration", "N/A")
    if duration.startswith("PT"):
        # Remove the "PT" prefix
        duration = duration[2:]
        # Convert XhYmZs format to readable string
        hours = "0"
        minutes = "0"
        seconds = "0"
        
        if "H" in duration:
            hours, duration = duration.split("H")
        if "M" in duration:
            minutes, duration = duration.split("M")
        if "S" in duration:
            seconds = duration.replace("S", "")
            
        if hours != "0":
            duration = f"{hours}:{minutes.zfill(2)}:{seconds.zfill(2)}"
        else:
            duration = f"{minutes}:{seconds.zfill(2)}"
    
    # Format tags and topics
    tags = ", ".join(result.get("tags", [])[:5]) if result.get("tags") else "None"
    # Clean up topic URLs to just show the topic name
    topics = []
    for topic in result.get("topics", []):
        if "wikipedia.org/wiki/" in topic:
            topic_name = topic.split("/wiki/")[-1].replace("_", " ")
            topics.append(topic_name)
    topics = ", ".join(topics) if topics else "None"
    
    response = f"""Here's a summary of the latest video:

📺 Title: {result['title']}
👤 Channel: {result['channel_name']}
📅 Upload Date: {formatted_date}
⏱️ Duration: {duration}
👀 Views: {view_count}
🏷️ Tags: {tags}
📚 Topics: {topics}
🗣️ Captions: {'Available' if result.get('caption') == 'true' else 'Not Available'}

📝 Summary:
{result['summary']}

💬 Top Comments:"""

    if result["top_comments"]:
        for i, comment in enumerate(result["top_comments"], 1):
            response += f"\n{i}. {comment['text']} - {comment['author']}"
    else:
        response += "\nNo comments available"
    
    return response

@app.post("/api/youtube-summary-agent", response_model=AgentResponse)
async def process_request(
    request: AgentRequest,
    credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    try:
        logger.info(f"Processing request for session {request.session_id}")
        
        # Store user's message
        try:
            store_message(request.session_id, "human", request.query)
            logger.info("Successfully stored user message")
        except Exception as e:
            logger.error(f"Failed to store user message: {str(e)}")
            raise

        # Extract YouTube playlist ID from query
        playlist_id = request.query.strip()
        logger.info(f"Processing playlist ID: {playlist_id}")
        
        # Process the playlist
        try:
            result = process_playlist(playlist_id)
            logger.info("Successfully processed playlist")
        except Exception as e:
            logger.error(f"Failed to process playlist: {str(e)}")
            raise
        
        # Store agent's response with additional data
        response_data = {
            "video_title": result["title"],
            "published_at": result["published_at"],
            "video_description": result["description"]
        }
        
        response_text = format_response(result)
        
        try:
            store_message(
                request.session_id, 
                "ai", 
                response_text,
                response_data
            )
            logger.info("Successfully stored AI response")
        except Exception as e:
            logger.error(f"Failed to store AI response: {str(e)}")
            raise
        
        return AgentResponse(
            response=response_text,
            success=True
        )
        
    except Exception as e:
        error_message = f"Error processing request: {str(e)}"
        logger.error(error_message)
        return AgentResponse(
            response="I encountered an error while processing your request.",
            success=False,
            error=error_message
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
