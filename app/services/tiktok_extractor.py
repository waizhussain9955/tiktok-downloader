"""
TikTok video data extractor.
Fetches public HTML and extracts embedded JSON data from SIGI_STATE.
"""

import httpx
import json
import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class TikTokExtractor:
    """
    Extracts TikTok video data from public HTML pages.
    
    Strategy:
    1. Fetch the video page HTML
    2. Locate <script id="SIGI_STATE"> tag
    3. Parse embedded JSON
    4. Extract video URL and metadata
    """
    
    def __init__(self):
        # Using a stable, widely accepted Mobile User-Agent
        self.user_agent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
        import ssl
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')
    
    async def extract_video_data(self, url: str) -> Dict[str, Any]:
        """
        Extract video data from a TikTok URL.
        """
        try:
            # Normalize URL
            normalized_url = await self._normalize_url(url)
            logger.info(f"Normalized URL: {normalized_url}")
            
            # Fetch HTML page and cookies
            html_content, cookies = await self._fetch_html(normalized_url)
            
            # Extract video ID
            video_id = self._extract_video_id(normalized_url)
            logger.info(f"Extracted Video ID: {video_id}")
            
            # Parse embedded JSON data
            try:
                video_data = self._parse_sigi_state(html_content, video_id)
                video_data['cookies'] = cookies # Add cookies to data
                return video_data
            except Exception as e:
                logger.error(f"Extraction failed: {str(e)}")
                raise e
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError("Video not found or has been removed")
            elif e.response.status_code == 403:
                raise ValueError("Access denied. The video may be private or region-locked")
            else:
                raise ValueError(f"Failed to fetch video: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"Extraction failed for {url}: {str(e)}")
            raise ValueError(f"Failed to extract video data: {str(e)}")
    
    async def _normalize_url(self, url: str) -> str:
        """
        Normalize TikTok short URLs (vm.tiktok.com) to full URLs.
        
        Args:
            url: Original TikTok URL
            
        Returns:
            Normalized full TikTok URL
        """
        # If it's already a full URL, return as is
        if 'tiktok.com/@' in url and '/video/' in url:
            return url
        
        # Handle short URLs by following redirects
        if any(domain in url for domain in ['vm.tiktok.com', 'vt.tiktok.com', 'tiktok.com/t/']):
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True) as client:
                response = await client.get(url, timeout=10.0)
                return str(response.url)
        
        return url
    
    async def _fetch_html(self, url: str) -> tuple[str, str]:
        """
        Fetch HTML content and cookies from TikTok video page.
        """
        fetch_headers = self.headers.copy()
        # Add a realistic referer to avoid SlardarWAF challenges
        fetch_headers['Referer'] = 'https://www.google.com/'
        
        async with httpx.AsyncClient(headers=fetch_headers, follow_redirects=True, timeout=30.0, verify=self.ssl_context, http2=False) as client:
            response = await client.get(url)
            
            # If 403, try once more with a different referer
            if response.status_code == 403:
                logger.warning("Access forbidden (403). Retrying with different referer...")
                fetch_headers['Referer'] = 'https://www.tiktok.com/'
                response = await client.get(url)

            if response.status_code == 403:
                # If still 403, it might be a hard block or CAPTCHA
                logger.error("Access forbidden (403) after retry.")
                raise ValueError("Access denied by TikTok. Try again later or use a different URL.")
            
            response.raise_for_status()
            
            cookies_str = "; ".join([f"{k}={v}" for k, v in response.cookies.items()])
            content = response.text
            
            # WAF Check
            if "SlardarWAF" in content or "Please wait..." in content and len(content) < 5000:
                logger.error("SlardarWAF challenge detected in HTML")
                raise ValueError("Anti-bot protection detected. Try again in a few minutes.")

            if content.startswith('\x1f\x8b') or content.startswith('\x00'):
                content = response.content.decode('utf-8', errors='ignore')
            
            return content, cookies_str
    
    def _extract_video_id(self, url: str) -> str:
        """
        Extract video ID from TikTok URL.
        
        Args:
            url: TikTok video URL
            
        Returns:
            Video ID string
        """
        # Pattern: https://www.tiktok.com/@username/video/7123456789012345678
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1)
        raise ValueError("Could not extract video ID from URL")
    
    def _parse_sigi_state(self, html: str, video_id: str) -> Dict[str, Any]:
        """
        Parse embedded JSON from HTML with multiple fallback patterns.
        """
        patterns = [
            r'<script id="api-data" type="application/json">(.*?)</script>',
            r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
            r'<script id="SIGI_STATE"[^>]*>(.*?)</script>',
            r'<script id="sigi-persisted-data"[^>]*>(.*?)</script>',
            r'window[\'SIGI_STATE\']\s*=\s*({.*?});',
            r'window.__INITIAL_STATE__\s*=\s*({.*?});'
        ]
        
        json_data = None
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    content = match.group(1).strip()
                    json_data = json.loads(content)
                    logger.info(f"Successfully matched pattern: {pattern[:30]}...")
                    break
                except json.JSONDecodeError:
                    continue
        
        if not json_data:
            # Last resort: look for any large JSON-like object content
            large_json_match = re.search(r'\{"ItemModule":.*?"\}\}', html, re.DOTALL)
            if large_json_match:
                try:
                    json_data = json.loads(large_json_match.group(0))
                except:
                    pass

        if not json_data:
            logger.error("Could not find any usable JSON data in the page HTML")
            raise ValueError("Could not find video data. The page structure might have changed.")
        
        return self._extract_from_sigi(json_data, video_id)
    
    def _extract_from_sigi(self, sigi_data: Dict, video_id: str) -> Dict[str, Any]:
        """
        Navigate complex nested JSON to find video data.
        """
        item = None
        
        # Strategy 1: New webapp.video-detail structure (Universal Data Rehydration)
        try:
            default_scope = sigi_data.get('__DEFAULT_SCOPE__', {})
            video_detail = default_scope.get('webapp.video-detail', {})
            if not video_detail:
                # Try simple videoDetail key if webapp nesting is missing
                video_detail = sigi_data.get('videoDetail', {})
            
            if video_detail:
                item = video_detail.get('itemInfo', {}).get('itemStruct')
        except Exception as e:
            logger.debug(f"Failed Strategy 1: {e}")

        # Strategy 1.5: Direct itemStruct search (api-data pattern)
        if not item:
            if 'itemStruct' in sigi_data:
                item = sigi_data['itemStruct']

        # Strategy 2: Standard ItemModule path (SIGI_STATE)
        if not item:
            item = sigi_data.get('ItemModule', {}).get(video_id)
        
        # Strategy 3: Recursive search for item with video structure
        if not item:
            def find_video_item(data, target_id):
                if isinstance(data, dict):
                    # Check if this node is our target video
                    if str(data.get('id')) == str(target_id) and 'video' in data:
                        return data
                    # Recurse
                    for v in data.values():
                        res = find_video_item(v, target_id)
                        if res: return res
                elif isinstance(data, list):
                    for v in data:
                        res = find_video_item(v, target_id)
                        if res: return res
                return None
            
            item = find_video_item(sigi_data, video_id)

        if not item:
            # Final fallback: look for ANY video object if we can't find by ID
            if 'ItemModule' in sigi_data and sigi_data['ItemModule']:
                item = next(iter(sigi_data['ItemModule'].values()))
            else:
                # Last ditch effort: if we have videoDetail but no itemStruct, maybe it's elsewhere
                item = sigi_data.get('itemInfo', {}).get('itemStruct')

        if not item:
            raise ValueError("Video data not found in extracted JSON.")

        # Extract Core Data
        video_obj = item.get('video', {})
        author_info = item.get('author', {})
        if not author_info and 'authorName' in item:
            author_info = {'uniqueId': item.get('authorName')}
            
        stats = item.get('stats', {}) or item.get('statsV2', {})
        music = item.get('music', {})
        
        # Get available video URLs
        # We look for all possible sources to make proxy more resilient
        urls = []
        
        # Source 1: downloadAddr
        if video_obj.get('downloadAddr'):
            urls.append(video_obj['downloadAddr'])
            
        # Source 2: bitrateInfo
        if 'bitrateInfo' in video_obj:
            bitrates = video_obj['bitrateInfo']
            try:
                sorted_bitrates = sorted(bitrates, key=lambda x: x.get('Bitrate', 0), reverse=True)
                for br in sorted_bitrates:
                    url_list = br.get('PlayAddr', {}).get('UrlList', [])
                    for u in url_list:
                        if u not in urls: urls.append(u)
            except:
                pass

        # Source 3: playAddr / videoUrl
        p_addr = video_obj.get('playAddr') or item.get('videoUrl')
        if p_addr and p_addr not in urls:
            urls.append(p_addr)

        if not urls:
            raise ValueError("Could not find any video download URLs in the page.")

        # Clean URLs (ensure absolute and HTTPS)
        clean_urls = []
        for u in urls:
            if u.startswith('//'): u = 'https:' + u
            elif u.startswith('http://'): u = u.replace('http://', 'https://', 1)
            clean_urls.append(u)

        return {
            'video_id': video_id,
            'mp4_url': clean_urls[0], # Primary URL
            'alternative_urls': clean_urls[1:], # Save others for proxy retries
            'author': author_info.get('uniqueId') or author_info.get('nickname') or 'unknown',
            'caption': item.get('desc') or item.get('contents', [{}])[0].get('desc', ''),
            'music': music.get('title') or music.get('authorName') or 'Original Sound',
            'duration': video_obj.get('duration', 0),
            'play_count': stats.get('playCount', 0),
            'like_count': stats.get('diggCount', stats.get('likeCount', 0)),
            'comment_count': stats.get('commentCount', 0),
            'share_count': stats.get('shareCount', 0),
            'created_at': item.get('createTime', 0),
        }
