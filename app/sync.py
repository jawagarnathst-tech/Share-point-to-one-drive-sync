import logging
import asyncio
from typing import Dict, Any, List
from app.graph import graph_client
from app.config import settings
from app.state import get_delta_token, set_delta_token, record_sync, get_sync_record

logger = logging.getLogger(__name__)

async def process_delta():
    token = get_delta_token()
    if not token:
        url = f"https://graph.microsoft.com/v1.0/drives/{settings.source_drive_id}/root/delta"
    else:
        url = token

    total_processed = 0
    while url:
        response = await graph_client.get(url)
        if response.status_code != 200:
            logger.error(f"Delta query failed: {response.text}")
            print(f"ERROR: Delta query failed: {response.text}")
            break
            
        data = response.json()
        items = data.get("value", [])
        print(f"Found {len(items)} item(s) in this page of changes.")
        
        for item in items:
            await process_item(item)
            total_processed += 1
            
        if "@odata.nextLink" in data:
            url = data["@odata.nextLink"]
        elif "@odata.deltaLink" in data:
            set_delta_token(data["@odata.deltaLink"])
            break
    print(f"Delta processing done. Total items scanned: {total_processed}")

async def process_item(item: Dict[str, Any]):
    # Skip deleted items or folders
    if "deleted" in item or "folder" in item:
        return

    parent_ref = item.get("parentReference", {})
    parent_path = parent_ref.get("path", "")
    name = item.get("name", "")
    print(f"  -> Checking item: {name} | path: {parent_path}")
    
    # ensure it's under SOURCE_ROOT_PATH
    source_root_marker = f"root:/{settings.source_root_path}"
    if source_root_marker not in parent_path and not parent_path.endswith(f":/{settings.source_root_path}"):
        print(f"     Skipping (not under source root: {settings.source_root_path})")
        return
        
    relative_path = ""
    if source_root_marker in parent_path:
        relative_path = parent_path.split(source_root_marker)[-1].strip("/")
        
    item_id = item["id"]
    etag = item["eTag"]
    
    record = get_sync_record(item_id)
    if record:
        if record["source_etag"] == etag and record["last_status"] == "Success":
            print(f"     Skipping (already synced): {name}")
            return
        if record["source_etag"] != etag and not settings.copy_updates:
            print(f"     Skipping (updates disabled): {name}")
            return

    print(f"     Copying: {name} -> Synctest/{relative_path}/{name}")
    await ensure_dest_folder(relative_path)
    
    dest_path = f"{settings.dest_root_path}/{relative_path}/{name}".replace("//", "/")
    src_path = f"{settings.source_root_path}/{relative_path}/{name}".replace("//", "/")
    
    success = await copy_item(item_id, relative_path, name)
    record_sync(item_id, etag, src_path, dest_path, "Success" if success else "Failed")
    print(f"     Result: {'SUCCESS' if success else 'FAILED'} for {name}")

async def ensure_dest_root_folder():
    """Make sure the root destination folder exists, create it if not."""
    url = f"https://graph.microsoft.com/v1.0/drives/{settings.dest_drive_id}/root:/{settings.dest_root_path}"
    resp = await graph_client.get(url)
    if resp.status_code == 200:
        return  # already exists
    # Create it
    payload = {
        "name": settings.dest_root_path,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "replace"
    }
    create_url = f"https://graph.microsoft.com/v1.0/drives/{settings.dest_drive_id}/root/children"
    await graph_client.post(create_url, json=payload)

async def ensure_dest_folder(relative_path: str):
    """Ensure all subfolders in the relative path exist inside dest_root_path."""
    if not relative_path:
        return
    parts = [p for p in relative_path.split("/") if p]
    current_parent_path = settings.dest_root_path
    for part in parts:
        folder_path = f"{current_parent_path}/{part}"
        check_url = f"https://graph.microsoft.com/v1.0/drives/{settings.dest_drive_id}/root:/{folder_path}"
        resp = await graph_client.get(check_url)
        if resp.status_code != 200:
            # Get parent folder id
            parent_url = f"https://graph.microsoft.com/v1.0/drives/{settings.dest_drive_id}/root:/{current_parent_path}"
            parent_resp = await graph_client.get(parent_url)
            if parent_resp.status_code == 200:
                parent_id = parent_resp.json()["id"]
                payload = {
                    "name": part,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "replace"
                }
                create_url = f"https://graph.microsoft.com/v1.0/drives/{settings.dest_drive_id}/items/{parent_id}/children"
                await graph_client.post(create_url, json=payload)
        current_parent_path = folder_path

async def copy_item(item_id: str, relative_path: str, name: str) -> bool:
    # Build the correct destination parent path (no extra /drive segment)
    if relative_path:
        dest_parent_path = f"{settings.dest_root_path}/{relative_path}"
    else:
        dest_parent_path = settings.dest_root_path

    # Ensure root destination folder exists
    await ensure_dest_root_folder()

    # Get destination parent drive item ref
    url_parent = f"https://graph.microsoft.com/v1.0/drives/{settings.dest_drive_id}/root:/{dest_parent_path}"
    resp = await graph_client.get(url_parent)
    if resp.status_code != 200:
        logger.error(f"Failed to get dest parent: {resp.text}")
        return False

    parent_id = resp.json()["id"]

    payload = {
        "parentReference": {
            "driveId": settings.dest_drive_id,
            "id": parent_id
        },
        "name": name,
        "@microsoft.graph.conflictBehavior": settings.copy_conflict_behavior
    }

    copy_url = f"https://graph.microsoft.com/v1.0/drives/{settings.source_drive_id}/items/{item_id}/copy"
    resp = await graph_client.post(copy_url, json=payload)

    if resp.status_code == 202:
        logger.info(f"Copy started successfully for: {name}")
        return True
    else:
        logger.error(f"Copy failed: {resp.text}")
        return False
