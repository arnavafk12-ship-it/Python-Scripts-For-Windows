import os, glob, win32com.client, difflib, subprocess

# 1. Scan the Start Menu for apps
apps = {}
shell = win32com.client.Dispatch("WScript.Shell")
start_menu = os.path.join(os.environ["ProgramData"], r"Microsoft\Windows\Start Menu\Programs")

for path in glob.glob(os.path.join(start_menu, "**/*.lnk"), recursive=True):
    name = os.path.basename(path).lower().replace(".lnk", "")
    try: apps[name] = shell.CreateShortCut(path).TargetPath
    except: pass

# Find Chrome's path dynamically
CHROME_PATH = apps.get("google chrome") or r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def search_directly_in_chrome(search_text, is_search=False):
    """Launches Chrome. If it's a search query, uses the '?' native prefix to force a web search."""
    if is_search:
        # 💡 THE NATIVE TRICK: Prefixing with '? ' forces Chrome to treat it as a direct web search!
        argument = f"? {search_text}"
    else:
        argument = search_text

    if os.path.exists(CHROME_PATH):
        subprocess.Popen([CHROME_PATH, argument])
    else:
        os.system(f'start chrome "{argument}"')

# 2. Main Input Loop
while True:
    query = input("\nType app name, website, or search (or 'exit'): ").strip()
    if query.lower() == 'exit': break
    if not query: continue
    
    # DIRECT CHROME SEARCH: Checks for '-g'
    if query.lower().endswith('-g'):
        search_term = query[:-2].strip()
        print(f"🌐 Feeding raw text straight into Chrome search: '{search_term}'...")
        # Notice we pass True here to trigger the '?' search force!
        search_directly_in_chrome(search_term, is_search=True)
        continue

    query_lower = query.lower()

    # SITE LAUNCHER CHECK: If it contains web domains
    if any(domain in query_lower for domain in ['.com', '.org', '.net', '.edu', 'http://', 'https://']):
        print(f"🌐 Opening website: {query_lower}")
        search_directly_in_chrome(query_lower, is_search=False)
        continue
        match = next((path for name, path in apps.items() if query_lower in name and path), None)
        print(f"🚀 Opening: {match}")
        os.startfile(match)
    else:
        # Typo correction check
        close_matches = difflib.get_close_matches(query_lower, apps.keys(), n=1, cutoff=0.4)
        
        if close_matches:
            suggestion = close_matches[0]
            confirm = input(f"🤔 Did you mean '{suggestion}'? (y/n): ").strip().lower()
            if confirm == 'y':
                print(f"🚀 Opening: {apps[suggestion]}")
                os.startfile(apps[suggestion])
                continue

        print("Trying Windows direct launch...")
        os.system(f"start {query_lower}");
