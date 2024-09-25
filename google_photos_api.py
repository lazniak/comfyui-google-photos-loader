import json
import aiohttp
import asyncio
import time
from .logging_config import log_message

class APICache:
    def __init__(self, ttl=300):  # TTL in seconds, default 5 minutes
        self.cache = {}
        self.ttl = ttl

    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
        return None

    def set(self, key, value):
        self.cache[key] = (value, time.time())

    def clear_old_entries(self):
        current_time = time.time()
        self.cache = {k: v for k, v in self.cache.items() if current_time - v[1] < self.ttl}

api_cache = APICache()

async def batch_load_from_album(session, creds, album_id, max_images, order_by, mediaTypeFilter, 
                                dateFilter, startDate, endDate, includeArchivedMedia, 
                                excludeNonAppCreatedData, progress_bars, 
                                check_cancelled=None, custom_filters=None, start_from=0, logger=None):
    total_images_to_fetch = start_from + max_images
    log_message(logger, f"Starting to load up to {max_images} images (skipping first {start_from} images). Total images to process: {total_images_to_fetch}", 'info')

    url = "https://photoslibrary.googleapis.com/v1/mediaItems:search"
    headers = {"Authorization": f"Bearer {creds.token}"}
    
    all_media_items = []
    next_page_token = None
    page_size = 100

    async def fetch_page(page_token):
        body = {
            "pageSize": page_size,
            "albumId": album_id if album_id else None,
            "pageToken": page_token,
            "filters": custom_filters or {}
        }
        if order_by:
            body["orderBy"] = order_by
        if mediaTypeFilter and mediaTypeFilter != "ALL_MEDIA":
            body["filters"]["mediaTypeFilter"] = {"mediaTypes": [mediaTypeFilter]}

        log_message(logger, "========== FULL API REQUEST STRUCTURE ==========", 'debug')
        log_message(logger, f"URL: {url}", 'debug')
        log_message(logger, f"Headers: {json.dumps(headers, indent=2)}", 'debug')
        log_message(logger, f"Body: {json.dumps(body, indent=2)}", 'debug')
        log_message(logger, "================================================", 'debug')

        try:
            if check_cancelled:
                check_cancelled()
            async with session.post(url, headers=headers, json=body) as response:
                if check_cancelled:
                    check_cancelled()
                response.raise_for_status()
                data = await response.json()
            log_message(logger, f"Response status: {response.status}", 'debug')
            log_message(logger, f"Response headers: {json.dumps(dict(response.headers), indent=2)}", 'debug')
            log_api_quota(response.headers, logger)
            return data.get('mediaItems', []), data.get('nextPageToken')
        except aiohttp.ClientResponseError as e:
            log_message(logger, f"API Error: Status {e.status}, Message: {e.message}", 'error')
            return [], None
        except Exception as e:
            log_message(logger, f"Error: {str(e)}", 'error')
            return [], None

    async def process_page_results(page_results):
        return [item for item in page_results if 'mediaMetadata' in item and item['mediaMetadata'].get('photo')]

    while len(all_media_items) < total_images_to_fetch:
        page_results, next_page_token = await fetch_page(next_page_token)
        
        if not page_results:
            break

        process_task = asyncio.create_task(process_page_results(page_results))

        if next_page_token and len(all_media_items) + len(page_results) < total_images_to_fetch:
            next_page_task = asyncio.create_task(fetch_page(next_page_token))
        else:
            next_page_task = None

        processed_results = await process_task
        all_media_items.extend(processed_results)
        await progress_bars.update("load_images", len(processed_results))
        log_message(logger, f"Retrieved {len(processed_results)} media items in this batch", 'info')
        log_message(logger, f"Total items processed so far: {len(all_media_items)}", 'info')

        if next_page_task:
            await next_page_task

        if check_cancelled:
            check_cancelled()

        await asyncio.sleep(1)  # Rate limiting

    final_results = all_media_items[start_from:start_from + max_images]
    log_message(logger, f"Retrieved a total of {len(final_results)} media items", 'info')
    return final_results

async def batch_load_from_album_v2(session, creds, album_id, max_images, order_by, mediaTypeFilter, 
                                   dateFilter, startDate, endDate, includeArchivedMedia, 
                                   excludeNonAppCreatedData, progress_bars, 
                                   check_cancelled=None, custom_filters=None, start_from=0, logger=None):
    total_images_to_fetch = start_from + max_images
    log_message(logger, f"Starting to load up to {max_images} images from album (skipping first {start_from} images). Total images to process: {total_images_to_fetch}", 'info')

    url = "https://photoslibrary.googleapis.com/v1/mediaItems:search"
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-type": "application/json"
    }
    
    all_media_items = []
    next_page_token = None
    page_size = min(100, max_images)  # Limit to maximum 100 items per page

    async def fetch_page(page_token):
        body = {
            "pageSize": page_size,
            "albumId": album_id
        }
        
        if page_token:
            body["pageToken"] = page_token

        if order_by:
            body["orderBy"] = order_by

        # Handle custom filters
        if custom_filters:
            filters = {}
            if 'contentFilter' in custom_filters:
                filters['contentFilter'] = custom_filters['contentFilter']
            if 'mediaTypeFilter' in custom_filters:
                filters['mediaTypeFilter'] = custom_filters['mediaTypeFilter']
            if 'dateFilter' in custom_filters:
                filters['dateFilter'] = custom_filters['dateFilter']
            if 'includeArchivedMedia' in custom_filters:
                filters['includeArchivedMedia'] = custom_filters['includeArchivedMedia']
            if filters:
                body["filters"] = filters

        log_message(logger, "========== FULL API REQUEST STRUCTURE ==========", 'debug')
        log_message(logger, f"URL: {url}", 'debug')
        log_message(logger, f"Headers: {json.dumps(headers, indent=2)}", 'debug')
        log_message(logger, f"Body: {json.dumps(body, indent=2)}", 'debug')
        log_message(logger, "================================================", 'debug')

        try:
            if check_cancelled:
                check_cancelled()
            async with session.post(url, headers=headers, json=body) as response:
                if check_cancelled:
                    check_cancelled()
                response_text = await response.text()
                log_message(logger, f"Full API Response: {response_text}", 'debug')
                response.raise_for_status()
                data = json.loads(response_text)
            log_message(logger, f"Response status: {response.status}", 'debug')
            log_message(logger, f"Response headers: {json.dumps(dict(response.headers), indent=2)}", 'debug')
            log_api_quota(response.headers, logger)
            return data.get('mediaItems', []), data.get('nextPageToken')
        except aiohttp.ClientResponseError as e:
            log_message(logger, f"API Error: Status {e.status}, Message: {e.message}", 'error')
            log_message(logger, f"Full error response: {response_text}", 'error')
            return [], None
        except Exception as e:
            log_message(logger, f"Error: {str(e)}", 'error')
            return [], None

    while len(all_media_items) < total_images_to_fetch:
        page_results, next_page_token = await fetch_page(next_page_token)
        
        if not page_results:
            break

        all_media_items.extend(page_results)
        await progress_bars.update("load_images", len(page_results))
        log_message(logger, f"Retrieved {len(page_results)} media items in this batch", 'info')
        log_message(logger, f"Total items processed so far: {len(all_media_items)}", 'info')

        if check_cancelled:
            check_cancelled()

        if not next_page_token:
            break

        await asyncio.sleep(1)  # Rate limiting

    final_results = all_media_items[start_from:total_images_to_fetch]
    log_message(logger, f"Retrieved a total of {len(final_results)} media items", 'info')
    return final_results

def choose_load_method(is_album_loader=False):
    return batch_load_from_album_v2 if is_album_loader else batch_load_from_album

async def batch_list_albums(session, creds, logger, progress_bars, check_cancelled):
    log_message(logger, "Starting to list albums", 'info')
    url = "https://photoslibrary.googleapis.com/v1/albums"
    headers = {"Authorization": f"Bearer {creds.token}"}
    params = {"pageSize": 50}
    
    all_albums = []
    
    while True:
        if check_cancelled:
            check_cancelled()
        
        log_message(logger, f"Sending request to {url}", 'debug')
        log_message(logger, f"Request params: {json.dumps(params, indent=2)}", 'debug')
        
        try:
            async with session.get(url, headers=headers, params=params) as response:
                response.raise_for_status()
                data = await response.json()
            log_message(logger, f"Response status: {response.status}", 'debug')
            log_message(logger, f"Response headers: {json.dumps(dict(response.headers), indent=2)}", 'debug')
            log_message(logger, f"Response data: {json.dumps(data, indent=2)}", 'debug')
            log_api_quota(response.headers, logger)
        except aiohttp.ClientResponseError as e:
            log_message(logger, f"API Error: Status {e.status}, Message: {e.message}", 'error')
            break
        except Exception as e:
            log_message(logger, f"Error: {str(e)}", 'error')
            break
        
        albums = data.get("albums", [])
        log_message(logger, f"Retrieved {len(albums)} albums in this batch", 'info')
        all_albums.extend(albums)
        
        if progress_bars:
            await progress_bars.update("list_albums", len(albums))
        
        if "nextPageToken" not in data:
            log_message(logger, "No more pages available", 'info')
            break
        
        params["pageToken"] = data["nextPageToken"]
        log_message(logger, f"Using next page token: {params['pageToken']}", 'debug')
        await asyncio.sleep(1)  # Rate limiting
    
    log_message(logger, f"Retrieved a total of {len(all_albums)} albums", 'info')
    return all_albums

async def batch_search_photos(session, creds, query, max_images, order_by, mediaTypeFilter, contentFilter, dateFilter, startDate, endDate, includeArchivedMedia, excludeNonAppCreatedData, progress_bars, check_cancelled, logger=None):
    log_message(logger, f"Searching up to {max_images} photos with query: {query}", 'info')
    url = "https://photoslibrary.googleapis.com/v1/mediaItems:search"
    headers = {"Authorization": f"Bearer {creds.token}", "Content-type": "application/json"}
    
    body = {
        "pageSize": str(min(100, max_images))
    }

    if order_by:
        body["orderBy"] = order_by

    filters = {}

    if mediaTypeFilter != "ALL_MEDIA":
        filters["mediaTypeFilter"] = {"mediaTypes": [mediaTypeFilter]}
    
    if contentFilter != "NONE":
        filters["contentFilter"] = {"includedContentCategories": [contentFilter]}
    
    if dateFilter != "NONE" and startDate:
        date_filter = {}
        start_date = {"year": int(startDate.split('-')[0]), "month": int(startDate.split('-')[1]), "day": int(startDate.split('-')[2])}
        if dateFilter == "DATE":
            date_filter["dates"] = [start_date]
        elif dateFilter == "RANGE" and endDate:
            end_date = {"year": int(endDate.split('-')[0]), "month": int(endDate.split('-')[1]), "day": int(endDate.split('-')[2])}
            date_filter["ranges"] = [{"startDate": start_date, "endDate": end_date}]
        
        if date_filter:
            filters["dateFilter"] = date_filter

    if includeArchivedMedia:
        filters["includeArchivedMedia"] = True

    if filters:
        body["filters"] = filters

    if excludeNonAppCreatedData:
        body["excludeNonAppCreatedData"] = True

    if query:
        body["filters"] = body.get("filters", {})
        body["filters"]["contentFilter"] = body["filters"].get("contentFilter", {})
        body["filters"]["contentFilter"]["includedContentCategories"] = [query]

    log_message(logger, "========== FULL API REQUEST STRUCTURE ==========", 'debug')
    log_message(logger, f"URL: {url}", 'debug')
    log_message(logger, f"Headers: {json.dumps(headers, indent=2)}", 'debug')
    log_message(logger, f"Body: {json.dumps(body, indent=2)}", 'debug')
    log_message(logger, "================================================", 'debug')

    all_media_items = []
    page_token = None

    while len(all_media_items) < max_images:
        if check_cancelled:
            check_cancelled()
        
        if page_token:
            body["pageToken"] = page_token

        log_message(logger, f"Sending request to {url}", 'debug')
        try:
            async with session.post(url, headers=headers, json=body) as response:
                if check_cancelled:
                    check_cancelled()
                response.raise_for_status()
                data = await response.json()
            log_message(logger, f"Response status: {response.status}", 'debug')
            log_message(logger, f"Response headers: {json.dumps(dict(response.headers), indent=2)}", 'debug')
            log_api_quota(response.headers, logger)
        except aiohttp.ClientResponseError as e:
            log_message(logger, f"API Error: Status {e.status}, Message: {e.message}", 'error')
            log_message(logger, f"Request URL: {e.request_info.url}", 'error')
            log_message(logger, f"Request Headers: {e.request_info.headers}", 'error')
            log_message(logger, f"Request Body: {body}", 'error')
            break
        except Exception as e:
            log_message(logger, f"Error: {str(e)}", 'error')
            break
        
        media_items = data.get("mediaItems", [])
        if not media_items:
            log_message(logger, "No more items found", 'info')
            break
        
        log_message(logger, f"Retrieved {len(media_items)} media items in this batch", 'info')
        all_media_items.extend(media_items)
        await progress_bars.update("search_photos", len(media_items))
        
        page_token = data.get("nextPageToken")
        if not page_token:
            log_message(logger, "No more pages available", 'info')
            break
        
        await asyncio.sleep(1)  # Rate limiting
    
    log_message(logger, f"Retrieved a total of {len(all_media_items)} media items", 'info')
    return all_media_items[:max_images]

def log_api_quota(response_headers, logger):
    quota_limit = response_headers.get('X-Goog-Quota-User-Info', 'Not available')
    log_message(logger, f"API Quota Information: {quota_limit}", 'info')

def parse_error_response(response_data, logger):
    error = response_data.get('error', {})
    code = error.get('code')
    message = error.get('message')
    status = error.get('status')
    
    log_message(logger, "API Error Details:", 'error')
    log_message(logger, f"  Code: {code}", 'error')
    log_message(logger, f"  Message: {message}", 'error')
    log_message(logger, f"  Status: {status}", 'error')

    if 'errors' in error:
        for detail in error['errors']:
            log_message(logger, f"  Detail: {detail}", 'error')

async def make_authenticated_request(session, url, method, headers, body, logger):
    log_message(logger, f"Making {method} request to {url}", 'debug')
    log_message(logger, f"Headers: {json.dumps(headers, indent=2)}", 'debug')
    if body:
        log_message(logger, f"Body: {json.dumps(body, indent=2)}", 'debug')

    try:
        if method.lower() == 'get':
            async with session.get(url, headers=headers) as response:
                return await handle_response(response, logger)
        elif method.lower() == 'post':
            async with session.post(url, headers=headers, json=body) as response:
                return await handle_response(response, logger)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    except aiohttp.ClientResponseError as e:
        log_message(logger, f"API Error: Status {e.status}, Message: {e.message}", 'error')
        log_message(logger, f"Request URL: {e.request_info.url}", 'error')
        log_message(logger, f"Request Headers: {e.request_info.headers}", 'error')
        if body:
            log_message(logger, f"Request Body: {body}", 'error')
        raise
    except Exception as e:
        log_message(logger, f"Unexpected error: {str(e)}", 'error')
        raise

async def handle_response(response, logger):
    log_message(logger, f"Response status: {response.status}", 'debug')
    log_message(logger, f"Response headers: {json.dumps(dict(response.headers), indent=2)}", 'debug')

    log_api_quota(response.headers, logger)

    response.raise_for_status()
    data = await response.json()

    if 'error' in data:
        parse_error_response(data, logger)
        raise aiohttp.ClientResponseError(
            request_info=response.request_info,
            history=response.history,
            status=response.status,
            message=data['error'].get('message', 'Unknown API error'),
            headers=response.headers
        )

    return data

def get_largest_image_url(base_url, original_size):
    if original_size and original_size > 0:
        return f"{base_url}=w{original_size}-h{original_size}"
    else:
        return f"{base_url}=w2048-h2048"  # Use a large default size

async def refresh_access_token(session, refresh_token, client_id, client_secret, logger):
    log_message(logger, "Refreshing access token", 'info')
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    async with session.post(token_url, data=data) as response:
        response.raise_for_status()
        token_data = await response.json()
    
    new_access_token = token_data.get("access_token")
    if not new_access_token:
        log_message(logger, "Failed to obtain new access token", 'error')
        raise ValueError("No access token in response")
    
    log_message(logger, "Successfully refreshed access token", 'info')
    return new_access_token

async def get_media_item(session, creds, media_item_id, logger):
    log_message(logger, f"Fetching media item with ID: {media_item_id}", 'info')
    url = f"https://photoslibrary.googleapis.com/v1/mediaItems/{media_item_id}"
    headers = {"Authorization": f"Bearer {creds.token}"}
    
    try:
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()
        log_message(logger, "Successfully fetched media item", 'info')
        return data
    except aiohttp.ClientResponseError as e:
        log_message(logger, f"Error fetching media item: {e.status} {e.message}", 'error')
        raise
    except Exception as e:
        log_message(logger, f"Unexpected error fetching media item: {str(e)}", 'error')
        raise

async def paginate_request(session, url, headers, body, max_items, logger, progress_bar=None):
    all_items = []
    page_token = None

    while len(all_items) < max_items:
        if page_token:
            body["pageToken"] = page_token

        try:
            async with session.post(url, headers=headers, json=body) as response:
                response.raise_for_status()
                data = await response.json()
            
            items = data.get("mediaItems", [])  # Adjust this based on the actual response structure
            all_items.extend(items[:max_items - len(all_items)])
            
            if progress_bar:
                await progress_bar.update(len(items))
            
            log_message(logger, f"Retrieved {len(items)} items in this batch", 'info')
            
            page_token = data.get("nextPageToken")
            if not page_token or len(all_items) >= max_items:
                break
            
        except aiohttp.ClientResponseError as e:
            log_message(logger, f"API Error: Status {e.status}, Message: {e.message}", 'error')
            break
        except Exception as e:
            log_message(logger, f"Unexpected error: {str(e)}", 'error')
            break

        await asyncio.sleep(1)  # Rate limiting

    log_message(logger, f"Retrieved a total of {len(all_items)} items", 'info')
    return all_items