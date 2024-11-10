import os
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi

MAX_TRANSCRIPT_LENGTH = 100000

class YouTubeChannelMonitor:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('YOUTUBE_API_KEY')
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        
        self.shapiro_channel_id = 'UCnQC_G5Xsjhp9fEJKuIcrSw'  # Ben Shapiro's channel: The Daily Wire
        
        # Cache file for storing video information
        self.cache_file = 'youtube_cache.json'
        self.cache_duration = timedelta(hours=1)  # How long to keep cache
        
    def get_channel_latest_videos(self, channel_id: str, max_results: int = 5) -> List[Dict]:
        """
        Get the latest videos from a specific channel.
        
        Args:
            channel_id: The YouTube channel ID
            max_results: Maximum number of videos to return
            
        Returns:
            List of video information dictionaries
        """
        try:
            # Check cache first
            cached_data = self._get_from_cache(channel_id)
            if cached_data:
                return cached_data
            
            # Get channel's uploads playlist ID
            channels_response = self.youtube.channels().list(
                id=channel_id,
                part='contentDetails'
            ).execute()
            
            print(f"Channels response: {channels_response}")
            
            playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Get videos from uploads playlist
            videos_response = self.youtube.playlistItems().list(
                playlistId=playlist_id,
                part='snippet',
                maxResults=max_results
            ).execute()
            
            videos = []
            for item in videos_response['items']:
                video_data = {
                    'video_id': item['snippet']['resourceId']['videoId'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'published_at': item['snippet']['publishedAt'],
                    'thumbnail': item['snippet']['thumbnails']['default']['url']
                }
                videos.append(video_data)
            
            # Cache the results
            self._cache_results(channel_id, videos)
            
            # for video in videos:
            #     print(f"\nTitle: {video['title']}")
            #     print(f"Published: {video['published_at']}")
            #     print(f"Video ID: {video['video_id']}")
            #     print(f"URL: https://www.youtube.com/watch?v={video['video_id']}")
            
            return videos
            
        except Exception as e:
            print(f"Error fetching videos: {e}")
            return []

    def get_latest_video_transcript(self, channel_id: str = None) -> Optional[Dict]:
        """
        Get transcript of the latest video from a channel.
        If no channel_id is provided, uses Ben Shapiro's channel.
        """
        try:
            channel_id = channel_id or self.shapiro_channel_id
            latest_videos = self.get_channel_latest_videos(channel_id, max_results=1)
            
            if not latest_videos:
                return None
            
            video = latest_videos[0]
            transcript_text = self._get_transcript(video['video_id'])
            
            if transcript_text:
                return {
                    'video_id': video['video_id'],
                    'title': video['title'],
                    'published_at': video['published_at'],
                    'transcript': transcript_text,
                    'url': f"https://www.youtube.com/watch?v={video['video_id']}"
                }
                
            return None
            
        except Exception as e:
            print(f"Error getting latest transcript: {e}")
            return None

    def _get_transcript(self, video_id: str) -> Optional[str]:
        """Get transcript for a specific video."""
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            
            # Combine transcript pieces with timestamps
            formatted_transcript = []
            for entry in transcript_list:
                time_in_mins = int(entry['start']) // 60
                time_in_secs = int(entry['start']) % 60
                formatted_transcript.append(
                    f"[{time_in_mins}:{time_in_secs:02d}] {entry['text']}"
                )
            
            return '\n'.join(formatted_transcript)
            
        except Exception as e:
            print(f"Error getting transcript: {e}")
            return None

    def _get_from_cache(self, channel_id: str) -> Optional[List[Dict]]:
        """Get data from cache if it exists and is fresh."""
        try:
            if not os.path.exists(self.cache_file):
                return None
                
            with open(self.cache_file, 'r') as f:
                cache = json.load(f)
                
            channel_cache = cache.get(channel_id)
            if not channel_cache:
                return None
                
            # Check if cache is fresh
            cache_time = datetime.fromisoformat(channel_cache['timestamp'])
            if datetime.now() - cache_time > self.cache_duration:
                return None
                
            return channel_cache['videos']
            
        except Exception:
            return None

    def _cache_results(self, channel_id: str, videos: List[Dict]):
        """Cache results for a channel."""
        try:
            # Load existing cache
            cache = {}
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
            
            # Update cache
            cache[channel_id] = {
                'timestamp': datetime.now().isoformat(),
                'videos': videos
            }
            
            # Save cache
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f)
                
        except Exception as e:
            print(f"Error caching results: {e}")

    def summarize_latest_video(self, openai_client) -> Optional[Dict]:
        """
        Get and summarize the latest video using OpenAI.
        
        Args:
            openai_client: Initialized OpenAI client
            
        Returns:
            Dictionary containing video info and summary
        """
        video_data = self.get_latest_video_transcript()
        if not video_data:
            return None
            
        print(f"Transcript data length: {len(video_data['transcript'])} characters")
        try:
            # Create a prompt for ChatGPT
            prompt = f"""
            Please summarize the following YouTube video transcript. 
            Video title: {video_data['title']}
            
            Focus on:
            1. Main topics discussed
            2. Key arguments or points made
            3. Any significant conclusions
            
            Transcript:
            {video_data['transcript'][:MAX_TRANSCRIPT_LENGTH]}  # Limit transcript length for API
            """
            
            # Get summary from ChatGPT
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes video transcripts accurately and objectively."},
                    {"role": "user", "content": prompt}
                ]
            )

            print("\n===  SUMMARY  ===\n")
            print(response.choices[0].message.content)
            print("\n== END SUMMARY ===\n")
            
            summary = response.choices[0].message.content
            
            return {
                'title': video_data['title'],
                'url': video_data['url'],
                'published_at': video_data['published_at'],
                'summary': summary
            }
            
        except Exception as e:
            print(f"Error summarizing video: {e}")
            return None

""" potential enhancements:

Channel Features:
Track multiple political commentators
Compare viewpoints on same topics
Monitor video upload frequency
Track engagement metrics


Content Analysis:
Topic classification
Sentiment analysis
Key quote extraction
Fact verification links


Practical Improvements:
Background polling for new videos
Better error handling for transcripts
Improved summary quality
"""

# Example usage
# if __name__ == "__main__":
#     monitor = YouTubeChannelMonitor()
    
#     # Get latest videos
#     print("Getting latest videos...")
#     videos = monitor.get_channel_latest_videos(monitor.shapiro_channel_id)
#     for video in videos:
#         print(f"\nTitle: {video['title']}")
#         print(f"Published: {video['published_at']}")
#         print(f"Video ID: {video['video_id']}")
#         print(f"URL: https://www.youtube.com/watch?v={video['video_id']}")
    
#     # Get latest video transcript
#     print("\nGetting latest video transcript...")
#     latest = monitor.get_latest_video_transcript()
#     if latest:
#         print(f"\nLatest Video: {latest['title']}")
#         print(f"Published: {latest['published_at']}")
#         print("\nTranscript excerpt:")
#         print(latest['transcript'][:500] + "...")
        
#     # Example of summarizing with OpenAI
#     # from openai import OpenAI
#     client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
#     summary = monitor.summarize_latest_video(client)
#     if summary:
#         print(f"\nSummary of: {summary['title']}")
#         print(summary['summary'])