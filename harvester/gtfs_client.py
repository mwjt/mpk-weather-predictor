import httpx

FILE_LIST_URL = "https://api.open-data.cui.wroclaw.pl/od2/6/?format=json"
DOWNLOAD_URL_TEMPLATE = "https://api.open-data.cui.wroclaw.pl/od2-files/{file_id}/download/"

async def get_latest_file_id() -> int:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(FILE_LIST_URL)
        resp.raise_for_status()
        payload = resp.json()
    file_ids = payload["pliki"]
    # Heuristic: highest numeric id = most recently published.
    # Worth spot-checking this assumption once against feed_info.txt's
    # feed_start_date inside the zip, in case ids aren't strictly sequential.
    return max(file_ids)

async def download_gtfs_zip(file_id: int, dest_path: str):
    url = DOWNLOAD_URL_TEMPLATE.format(file_id=file_id)
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(resp.content)