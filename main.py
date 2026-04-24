import requests
from dotenv import load_dotenv
import os
from datetime import datetime
load_dotenv()


JELLYFIN = os.getenv("JELLYFIN_URL")
HEADERS = {
    "Authorization": f"MediaBrowser Token={os.getenv('JELLYFIN_TOKEN')}",
    "accept": "application/json"
}
LOG_FILE = "./prefetch.log"
PREFETCH_MIN = 256 * 1024 * 1024
PREFETCH_FRACTION = 0.50
CHUNK_SIZE = 4 * 1024 * 1024

def get_current_episodes():
    try:
        sessions = requests.get(f"{JELLYFIN}/Sessions?activeWithinSeconds=10", headers=HEADERS, timeout=10).json()
    except requests.RequestException as e:
        print(f"Jellyfin unreachable: {e}")
        exit()

    if not sessions:
        exit()

    now_playing = sessions[0].get("NowPlayingItem")
    if not now_playing or now_playing.get("Type") != "Episode":
        exit()

    position = sessions[0].get("PlayState", {}).get("PositionTicks", 0)
    duration = now_playing.get("RunTimeTicks", 0)
    if duration == 0 or (duration - position) / 10_000_000 > 600:
        exit()
    ep_data = {
        "now_playing": now_playing,
        "series_id": now_playing["SeriesId"],
        "season_id": now_playing["SeasonId"],
        "ep_index":   now_playing["IndexNumber"]
    }
    return ep_data

def get_ep_info(ep_data):
    try:
        series_id = ep_data["series_id"]
        season_id = ep_data["season_id"]
        ep_index = ep_data["ep_index"]
        episodes = requests.get(
            f"{JELLYFIN}/Shows/{series_id}/Episodes",
            headers=HEADERS,
            params={"SeasonId": season_id, "Fields": "Path,MediaSources"},
            timeout=10
        ).json()
    except requests.RequestException as e:
        print(f"Failed to fetch episodes: {e}")
        exit()

    next_item = next(
        (item for item in episodes["Items"] if item.get("IndexNumber") == ep_index + 1),
        None
    )
    if not next_item:
        exit()
    try:
        file_path = next_item.get("Path") or next_item["MediaSources"][0]["Path"]
        file_size     = os.path.getsize(file_path)
        file_info ={
            "file_path": file_path,
            "file_size": file_size,
            "next_item": next_item
        }
    except OSError as e:
        print(f"Episode Path not Found: {e}")
        exit()
    return file_info

def is_already_prefetched(file_path):
    try:
        with open(LOG_FILE, 'r') as f:
            return any(file_path in line for line in f)
    except FileNotFoundError:
        return False

    
def prefetch_ep(file_info):
    prefetch_size = min(file_info["file_size"], max(PREFETCH_MIN, int(file_info["file_size"] * PREFETCH_FRACTION)))

    print(f"Prefetching {prefetch_size // 1024 // 1024} MB of: {file_info['file_path']}")

    try:
        bytes_read = 0
        with open(file_info["file_path"], "rb") as f:
            while bytes_read < prefetch_size:
                chunk = f.read(min(CHUNK_SIZE, prefetch_size - bytes_read))
                if not chunk:
                    break
                bytes_read += len(chunk)
        return bytes_read
    except OSError as e:
        print(f"Failed to read file: {e}")
        return False

def write_log(ep_data,file_info,bytes_read):
    next_item = file_info["next_item"]
    now_playing = ep_data["now_playing"]
    show        = now_playing.get("SeriesName", "Unknown")
    current_ep  = now_playing.get("Name", "Unknown")
    next_season = next_item.get("ParentIndexNumber", 0)
    next_index  = next_item.get("IndexNumber", 0)
    next_name   = next_item.get("Name", "Unknown")

    with open(LOG_FILE, "a") as log:
        log.write(
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"{show} | current={current_ep} | "
            f"next=S{next_season:02d}E{next_index:02d} {next_name} | "
            f"prefetched={bytes_read // 1024 // 1024}MB | {file_info['file_path']}\n"
        )

    print("Done")

def main():
    ep_data = get_current_episodes()
    file_info = get_ep_info(ep_data)
    isprefetched = is_already_prefetched(file_info["file_path"])
    if isprefetched:
        exit()
    bytes_read = prefetch_ep(file_info)
    write_log(ep_data,file_info,bytes_read)

        
if __name__ == "__main__":
    main()
