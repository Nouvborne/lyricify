import requests, subprocess, time, sys, re, os
from subprocess import check_output, CalledProcessError

RESET = "\033[0m"
HIGHLIGHT = "\033[48;5;27m"

def get_current_track():
    try:
        artist = check_output(["playerctl", "metadata", "xesam:artist", "-p", "spotify"]).decode().strip()
        title = check_output(["playerctl", "metadata", "xesam:title", "-p", "spotify"]).decode().strip()
        return artist, title
    except CalledProcessError:
        print("❌ Failed to get current song from playerctl.")
        return None, None

def get_synced_lyrics(artist, title):
    query = f"{artist} {title}"
    url = f"https://lrclib.net/api/search?q={requests.utils.quote(query)}"
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
    except Exception as e:
        print(f"❌ Error while querying LRCLIB: {e}")
        return None

    if not data:
        return None

    track = data[0]

    synced = track.get("syncedLyrics", None)
    if synced:
        if isinstance(synced, str) and synced.startswith("http"):
            try:
                return requests.get(synced, timeout=5).text
            except Exception as e:
                print(f"❌ Couldn't download .lrc file: {e}")
        else:
            return synced

    plain = track.get("plainLyrics", None)
    if plain:
        return plain

    return None

def get_current_position():
    try:
        pos = subprocess.check_output(["playerctl", "position", "-p", "spotify"]).decode().strip()
        return float(pos)
    except Exception:
        return 0.0

def parse_lrc(lrc_text):
    pattern = re.compile(r"(\[(\d+):(\d+\.\d+)\])+(.+)")
    lines = []
    for line in lrc_text.splitlines():
        matches = list(re.finditer(r"\[(\d+):(\d+\.\d+)\]", line))
        if matches:
            lyric = line[matches[-1].end():].strip()
            for m in matches:
                minutes = int(m.group(1))
                seconds = float(m.group(2))
                timestamp = minutes * 60 + seconds
                lines.append((timestamp, lyric))
    return sorted(lines, key=lambda x: x[0])

def clear_terminal():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def find_current_line(lines, current_time):
    for i in range(len(lines)-1):
        if lines[i][0] <= current_time < lines[i+1][0]:
            return i
    return len(lines) - 1

def display_lyrics(lines, current_time, window=10, last_index=None):
    current_index = find_current_line(lines, current_time)
    if last_index == current_index:
        return last_index

    start = max(0, current_index - window // 2)
    end = min(len(lines), start + window)

    clear_terminal()

    for i in range(start, end):
        ts, lyric = lines[i]
        if i == current_index:
            print(f"{HIGHLIGHT}{lyric}{RESET}")
        else:
            print(lyric)
    return current_index

#Gonna be useful in the future
def is_kitty_by_term():
    return os.environ.get("TERM", "").lower() == "xterm-kitty"

def main():
    last_track = None
    last_index = None
    lines = []
    no_lyrics_msg = "❌ No lyrics found."

    try:
        while True:
            artist, title = get_current_track()
            if not artist or not title:
                time.sleep(1)
                continue

            current_track = f"{artist} - {title}"

            if current_track != last_track:
                print(f"🎧 Fetching lyrics for: {current_track}")
                lrc_text = get_synced_lyrics(artist, title)

                if lrc_text:
                    lines = parse_lrc(lrc_text)
                    last_index = None
                else:
                    lines = [(0, no_lyrics_msg)]
                    last_index = None

                last_track = current_track

            pos = get_current_position()
            last_index = display_lyrics(lines, pos, last_index=last_index)
            time.sleep(0.2)
    except KeyboardInterrupt:
        clear_terminal()
        print("Exited synced lyrics display.")

if __name__ == "__main__":
    main()
