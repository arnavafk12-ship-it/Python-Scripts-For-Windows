
from __future__ import annotations

import os
import re
import sys
import json
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable, Any

try:
    from rapidfuzz import fuzz, process
except ImportError:
    print("Missing dependency: rapidfuzz")
    print("Install with: pip install rapidfuzz")
    sys.exit(1)


                                                                             
               
                                                                             

SKIP_DIRS = {
    "$RECYCLE.BIN",
    "System Volume Information",
    "Recovery",
    "Config.Msi",
    "MSOCache",
}

COMMAND_ALIASES = {
    "open": ["open", "launch", "start", "go", "goto", "enter", "access"],
    "find": ["find", "locate", "where", "look", "search"],
    "list": ["list", "show", "display", "ls", "dir"],
    "count": ["count", "total", "how many"],
    "size": ["size", "space", "storage"],
    "largest": ["largest", "biggest", "heaviest"],
    "tree": ["tree", "structure", "hierarchy"],
    "search": ["search", "find"],
    "drives": ["drives", "disks", "volumes"],
    "pc": ["pc", "computer", "system"],
    "help": ["help", "?"],
    "exit": ["exit", "quit", "bye"],
    "delete": ["delete", "remove", "erase", "trash"],
    "copy": ["copy", "duplicate"],
    "move": ["move", "transfer"],
    "rename": ["rename"],
}

PATH_WORDS = {
    "my downloads": Path.home() / "Downloads",
    "downloads": Path.home() / "Downloads",
    "my documents": Path.home() / "Documents",
    "documents": Path.home() / "Documents",
    "my desktop": Path.home() / "Desktop",
    "desktop": Path.home() / "Desktop",
    "home": Path.home(),
    "user": Path.home(),
    "pictures": Path.home() / "Pictures",
    "my pictures": Path.home() / "Pictures",
    "videos": Path.home() / "Videos",
    "my videos": Path.home() / "Videos",
    "music": Path.home() / "Music",
    "temp": Path(os.environ.get("TEMP", str(Path.home()))),
}

SIZE_UNITS = {
    "b": 1,
    "kb": 1024,
    "k": 1024,
    "mb": 1024**2,
    "m": 1024**2,
    "gb": 1024**3,
    "g": 1024**3,
    "tb": 1024**4,
    "t": 1024**4,
}


                                                                             
           
                                                                             

def clean_text(text: str) -> str:
    text = text.strip()
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("‘", "'").replace("’", "'")
    text = re.sub(r"\s+", " ", text)
    return text


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if value < 1024 or unit == "PB":
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"


def quote_path(path: Path) -> str:
    return f'"{path}"'


def is_windows() -> bool:
    return os.name == "nt"


def is_reparse_point(path: Path) -> bool:
    try:
        return bool(path.stat().st_file_attributes & 0x400)
    except Exception:
        return False


def safe_stat(path: Path):
    try:
        return path.stat()
    except (OSError, PermissionError):
        return None


def drives() -> list[Path]:
    result = []
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        path = Path(f"{letter}:\\")
        if path.exists():
            result.append(path)
    return result


def ask_yes_no(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer in {"y", "yes", "yeah", "yep", "do it", "confirm"}


                                                                             
                   
                                                                             

class WindowsFS:
    """Filesystem operations. No GUI dependencies."""

    def __init__(self):
        self.home = Path.home()

    def exact(self, raw: str) -> Optional[Path]:
        raw = raw.strip().strip('"').strip("'")
        raw = os.path.expandvars(os.path.expanduser(raw))

                                                     
        raw = raw.replace("/", os.sep)

        try:
            path = Path(raw)
            if path.exists():
                return path.resolve()
        except (OSError, ValueError):
            pass

        return None

    def _candidate_places(self) -> list[Path]:
        places = [
            self.home,
            self.home / "Desktop",
            self.home / "Downloads",
            self.home / "Documents",
            self.home / "Projects",
        ]

        places.extend(drives())

                            
        seen = set()
        output = []
        for p in places:
            try:
                key = str(p.resolve()).lower()
                if key not in seen and p.exists():
                    seen.add(key)
                    output.append(p)
            except OSError:
                pass

        return output

    def resolve_special(self, text: str) -> Optional[Path]:
        query = clean_text(text).lower()

                                  
        if query in PATH_WORDS:
            path = PATH_WORDS[query]
            return path.resolve() if path.exists() else path

                                
        expanded = os.path.expandvars(os.path.expanduser(text))
        if expanded != text:
            exact = self.exact(expanded)
            if exact:
                return exact

        return None

    def fuzzy_find(self, query: str, limit: int = 10) -> list[tuple[float, Path]]:
        """
        Find files/directories by fuzzy name.

        Designed for:
            dowloads -> Downloads
            documnts -> Documents
            vs codum -> VS Codium
            brighauth -> BrightAuth
        """
        query = clean_text(query).lower()

        if not query:
            return []

        exact = self.resolve_special(query)
        if exact:
            return [(1000, exact)]

        results: list[tuple[float, Path]] = []
        seen: set[str] = set()

                                                                              
                                                                              
                                     
        for root in self._candidate_places():
            try:
                for current, dirs, files in os.walk(
                    root,
                    topdown=True,
                    followlinks=False,
                ):
                    dirs[:] = [
                        d for d in dirs
                        if d not in SKIP_DIRS
                        and not d.startswith("$")
                    ]

                    names = dirs + files

                    for name in names:
                        path = Path(current) / name
                        key = str(path).lower()

                        if key in seen:
                            continue
                        seen.add(key)

                        score = self._score(query, name, path)

                        if score >= 58:
                            results.append((score, path))

                                                                             
                                                                            
                    if len(results) > limit * 80:
                        break

            except (OSError, PermissionError):
                continue

        results.sort(
            key=lambda item: (
                -item[0],
                len(item[1].parts),
                len(item[1].name),
            )
        )

        return results[:limit]

    @staticmethod
    def _score(query: str, name: str, path: Path) -> float:
        n = name.lower()
        full = str(path).lower()

        if n == query:
            return 1000

        if n.startswith(query):
            return 930

        if query in n:
            return 900 - min(len(n) - len(query), 100)

                                                          
        compact_q = re.sub(r"[^a-z0-9]", "", query)
        compact_n = re.sub(r"[^a-z0-9]", "", n)

        if compact_q and compact_n:
            ratio = fuzz.ratio(compact_q, compact_n)
            partial = fuzz.partial_ratio(compact_q, compact_n)

                                                              
            score = max(ratio, partial * 0.94)

                                                             
            if score >= 62:
                return score

                                 
        if query in full:
            return 65

        return 0

    def best(self, query: str) -> Optional[Path]:
        matches = self.fuzzy_find(query, 8)
        return matches[0][1] if matches else None

    def open(self, path: Path):
        if not is_windows():
            raise RuntimeError("This controller is Windows-only.")
        os.startfile(str(path))

    def reveal(self, path: Path):
        if path.is_dir():
            subprocess.Popen(["explorer.exe", str(path)])
        else:
            subprocess.Popen(["explorer.exe", "/select,", str(path)])

    def scan(self, root: Path) -> dict[str, Any]:
        files = dirs = total = errors = 0

        for current, dirnames, filenames in os.walk(
            root,
            topdown=True,
            followlinks=False,
        ):
            dirnames[:] = [
                d for d in dirnames
                if d not in SKIP_DIRS and not d.startswith("$")
            ]

            dirs += len(dirnames)

            for name in filenames:
                files += 1
                try:
                    total += (Path(current) / name).stat().st_size
                except OSError:
                    errors += 1

        return {
            "root": str(root),
            "files": files,
            "directories": dirs,
            "items": files + dirs,
            "bytes": total,
            "size": human_size(total),
            "errors": errors,
        }

    def list_items(self, root: Path) -> list[Path]:
        try:
            return sorted(
                root.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except (OSError, PermissionError):
            return []

    def largest(self, root: Path, limit: int = 20):
        result = []

        for current, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            for name in files:
                path = Path(current) / name
                try:
                    result.append((path.stat().st_size, path))
                except OSError:
                    pass

        result.sort(reverse=True, key=lambda x: x[0])
        return result[:limit]

    def search_files(
        self,
        root: Path,
        pattern: str,
        dirs_only: bool = False,
    ) -> list[Path]:
        result = []

        for current, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            names = dirs if dirs_only else files

            for name in names:
                if fnmatch.fnmatch(name.lower(), pattern.lower()):
                    result.append(Path(current) / name)

        return result

    def tree(self, root: Path, depth: int = 3) -> str:
        lines = [str(root)]

        def walk(path: Path, prefix: str, level: int):
            if level > depth:
                return

            try:
                children = self.list_items(path)
            except Exception:
                return

            for i, child in enumerate(children):
                last = i == len(children) - 1
                branch = "└── " if last else "├── "
                lines.append(prefix + branch + child.name)

                if child.is_dir() and child.name not in SKIP_DIRS:
                    walk(
                        child,
                        prefix + ("    " if last else "│   "),
                        level + 1,
                    )

        walk(root, "", 1)
        return "\n".join(lines)


                                                                             
            
                                                                             

@dataclass
class Intent:
    command: str
    target: str = ""
    extra: str = ""
    confidence: float = 0.0


class NLPParser:
    """
    Lightweight local NLP.

    It is deliberately deterministic: no API, no cloud model, no GUI.
    rapidfuzz handles typo tolerance and command similarity.
    """

    def __init__(self):
        self.commands = sorted(
            {
                alias
                for aliases in COMMAND_ALIASES.values()
                for alias in aliases
            },
            key=len,
            reverse=True,
        )

    def command_similarity(self, word: str, canonical: str) -> float:
        return max(
            fuzz.ratio(word, canonical),
            fuzz.partial_ratio(word, canonical),
        )

    def detect_command(self, text: str) -> tuple[str, float]:
        low = text.lower().strip()

                                          
        phrases = [
            ("how many", "count"),
            ("how much space", "size"),
            ("show me", "list"),
            ("list all", "list"),
            ("where is", "find"),
            ("find", "find"),
            ("open", "open"),
            ("go to", "open"),
            ("goto", "open"),
            ("launch", "open"),
            ("start", "open"),
            ("delete", "delete"),
            ("remove", "delete"),
            ("move", "move"),
            ("copy", "copy"),
            ("rename", "rename"),
            ("biggest", "largest"),
            ("largest", "largest"),
            ("tree", "tree"),
            ("drives", "drives"),
            ("disks", "drives"),
            ("help", "help"),
        ]

        for phrase, canonical in phrases:
            if low.startswith(phrase + " ") or low == phrase:
                return canonical, 100.0

        first = low.split(maxsplit=1)[0] if low else ""

                        
        for canonical, aliases in COMMAND_ALIASES.items():
            if first in aliases:
                return canonical, 100.0

                                    
        best = ("", 0.0)

        for canonical, aliases in COMMAND_ALIASES.items():
            for alias in aliases:
                score = self.command_similarity(first, alias)

                if score > best[1]:
                    best = (canonical, score)

        if best[1] >= 70:
            return best

                                                      
                             
                      
                    
                            
        return "find", 60.0

    def parse(self, text: str) -> Intent:
        text = clean_text(text)

        if not text:
            return Intent("help")

        command, confidence = self.detect_command(text)

                                            
        target = text

        prefixes = [
            "how many files are in",
            "how many items are in",
            "how many things are in",
            "how many are in",
            "show me the largest files in",
            "show largest files in",
            "largest files in",
            "biggest files in",
            "list all files in",
            "list everything in",
            "show everything in",
            "show me everything in",
            "search for",
            "search",
            "find",
            "where is",
            "where",
            "open",
            "launch",
            "start",
            "go to",
            "goto",
            "enter",
            "count",
            "total",
            "size of",
            "space used by",
            "tree of",
            "tree",
            "delete",
            "remove",
            "erase",
            "trash",
            "copy",
            "move",
            "rename",
        ]

        low = text.lower()

        for prefix in sorted(prefixes, key=len, reverse=True):
            if low == prefix:
                target = ""
                break
            if low.startswith(prefix + " "):
                target = text[len(prefix):].strip()
                break

                                                                       
        target = re.sub(
            r"^(the|this|that|my|folder|directory|file)\s+",
            "",
            target,
            flags=re.I,
        ).strip()

                                     
        if "largest" in low or "biggest" in low or "heaviest" in low:
            command = "largest"

        if any(x in low for x in ("how many", "number of", "count all", "total files")):
            command = "count"

        if "disk space" in low or "storage" in low:
            command = "size"

        if "folder structure" in low or "directory tree" in low:
            command = "tree"

        return Intent(command, target, confidence=confidence)


                                                                             
                      
                                                                             

class APEXFiles:
    BANNER = r"""
╔══════════════════════════════════════════════════════╗
║             APEX FILE SYSTEM CONTROLLER             ║
║              Windows • NLP • Terminal               ║
╚══════════════════════════════════════════════════════╝
"""

    def __init__(self):
        self.fs = WindowsFS()
        self.nlp = NLPParser()
        self.running = True

    def print_matches(self, matches):
        if not matches:
            print("  No matching files or directories.")
            return

        print()
        for i, (score, path) in enumerate(matches, 1):
            kind = "DIR " if path.is_dir() else "FILE"
            print(f"  {i:>2}. [{kind}] {path}")
        print()

    def resolve_target(self, target: str) -> Optional[Path]:
        target = target.strip()

        if not target:
            return Path.cwd()

        exact = self.fs.exact(target)
        if exact:
            return exact

        special = self.fs.resolve_special(target)
        if special:
            return special

        matches = self.fs.fuzzy_find(target, 10)

        if not matches:
            return None

                                                                            
        top_score = matches[0][0]
        second = matches[1][0] if len(matches) > 1 else 0

        if top_score >= 88 and top_score - second >= 5:
            return matches[0][1]

        if top_score >= 92 and len(matches) == 1:
            return matches[0][1]

        self.print_matches(matches)

        choice = input("  Choose a result (Enter = #1, 0 = cancel): ").strip()

        if not choice:
            return matches[0][1]

        try:
            n = int(choice)
            if n == 0:
                return None
            if 1 <= n <= len(matches):
                return matches[n - 1][1]
        except ValueError:
            pass

        return None

                                                

    def cmd_find(self, target: str):
        if not target:
            print("Usage: find <name>")
            return

        matches = self.fs.fuzzy_find(target, 15)
        self.print_matches(matches)

    def cmd_open(self, target: str):
        path = self.resolve_target(target)

        if not path:
            print("  Could not resolve that path.")
            return

        print(f"  Opening: {path}")
        self.fs.open(path)

    def cmd_list(self, target: str):
        path = self.resolve_target(target)

        if not path:
            print("  Directory not found.")
            return

        if not path.is_dir():
            print(f"  {path}")
            return

        items = self.fs.list_items(path)

        print(f"\n  {path}")
        print(f"  {len(items):,} immediate items\n")

        for item in items:
            marker = "[D]" if item.is_dir() else "[F]"
            print(f"  {marker} {item.name}")

    def cmd_count(self, target: str):
        path = self.resolve_target(target)

        if not path:
            print("  Directory not found.")
            return

        if path.is_file():
            print("  Files: 1")
            print("  Size:", human_size(path.stat().st_size))
            return

        print(f"  Scanning {path} ...")
        result = self.fs.scan(path)

        print()
        print(f"  Files:       {result['files']:,}")
        print(f"  Directories: {result['directories']:,}")
        print(f"  Total items: {result['items']:,}")
        print(f"  Total size:  {result['size']}")
        if result["errors"]:
            print(f"  Errors:      {result['errors']:,}")

    def cmd_size(self, target: str):
        path = self.resolve_target(target)

        if not path:
            print("  Could not resolve that path.")
            return

        if path.is_file():
            print(f"  {path}: {human_size(path.stat().st_size)}")
            return

        result = self.fs.scan(path)
        print(f"  {path}")
        print(f"  Size: {result['size']}")

    def cmd_largest(self, target: str):
        path = self.resolve_target(target)

        if not path:
            print("  Could not resolve that directory.")
            return

        print(f"  Scanning {path} ...")
        results = self.fs.largest(path, 20)

        print()
        for i, (size, item) in enumerate(results, 1):
            print(f"  {i:>2}. {human_size(size):>12}  {item}")

    def cmd_tree(self, target: str):
        path = self.resolve_target(target)

        if not path:
            print("  Directory not found.")
            return

        print(self.fs.tree(path, 3))

    def cmd_search(self, target: str):
        if not target:
            print("Usage: search <pattern>")
            return

                                                                               
                                      
        possible = self.fs.exact(target)

        if possible and possible.is_dir():
            pattern = "*"
            root = possible
        else:
            root = Path.cwd()
            pattern = target

                                            
            ext = re.search(
                r"\b(py|js|ts|tsx|jsx|json|html|css|cpp|c|h|java|md|txt|pdf)\b",
                target.lower(),
            )

            if ext:
                pattern = f"*.{ext.group(1)}"

        print(f"  Searching {root} for {pattern} ...")
        results = self.fs.search_files(root, pattern)

        for path in results[:500]:
            print(" ", path)

        if len(results) > 500:
            print(f"\n  Showing 500 of {len(results):,} results.")
        else:
            print(f"\n  {len(results):,} result(s).")

    def cmd_drives(self):
        print()
        for drive in drives():
            try:
                usage = shutil.disk_usage(drive)
                print(
                    f"  {drive} "
                    f"total={human_size(usage.total)} "
                    f"free={human_size(usage.free)} "
                    f"used={human_size(usage.used)}"
                )
            except OSError:
                print(f"  {drive}")

    def cmd_pc(self):
        print("\n  Windows drives:\n")
        self.cmd_drives()

    def cmd_delete(self, target: str):
        path = self.resolve_target(target)

        if not path:
            print("  Could not resolve target.")
            return

        print(f"\n  WARNING: this will delete:\n  {path}\n")

        if not ask_yes_no("  Move this item to the Recycle Bin?"):
            print("  Cancelled.")
            return

        try:
            from send2trash import send2trash as trash
        except ImportError:
            print("  Install send2trash first: pip install send2trash")
            return

        trash(str(path))
        print("  Moved to Recycle Bin.")

    def cmd_copy(self, target: str):
        parts = self._split_two_paths(target)

        if not parts:
            print("Usage: copy <source> <destination>")
            return

        source, destination = parts

        src = self.resolve_target(source)
        if not src:
            print("  Source not found.")
            return

        dst = Path(destination.strip('"'))

        if not ask_yes_no(f"Copy {src} -> {dst}?"):
            print("  Cancelled.")
            return

        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)

        print(f"  Copied to {dst}")

    def cmd_move(self, target: str):
        parts = self._split_two_paths(target)

        if not parts:
            print("Usage: move <source> <destination>")
            return

        source, destination = parts
        src = self.resolve_target(source)

        if not src:
            print("  Source not found.")
            return

        dst = Path(destination.strip('"'))

        if not ask_yes_no(f"Move {src} -> {dst}?"):
            print("  Cancelled.")
            return

        shutil.move(str(src), str(dst))
        print(f"  Moved to {dst}")

    def cmd_rename(self, target: str):
        parts = self._split_two_paths(target)

        if not parts:
            print("Usage: rename <old> <new>")
            return

        source, new_name = parts
        src = self.resolve_target(source)

        if not src:
            print("  Source not found.")
            return

        dst = src.parent / new_name.strip('"')

        if not ask_yes_no(f"Rename {src.name} -> {dst.name}?"):
            print("  Cancelled.")
            return

        src.rename(dst)
        print(f"  Renamed to {dst}")

    @staticmethod
    def _split_two_paths(text: str) -> Optional[tuple[str, str]]:
                                             
        quoted = re.match(r'^\s*"([^"]+)"\s+(.+)$', text)

        if quoted:
            return quoted.group(1), quoted.group(2)

        parts = text.split(maxsplit=1)

        if len(parts) == 2:
            return parts[0], parts[1]

        return None

    def help(self):
        print(
r"""
  APEX understands natural language. You do NOT need exact syntax.

  OPEN
    open downloads
    open dowloads
    go to my documents
    launch vscode

  FIND
    find docker
    where is brighauth
    vs codum
    locate my portfolio

  LIST
    list downloads
    show everything in documents
    list all files in H:\Projects

  COUNT
    count downloads
    how many files are in H:\BRIGHT
    count everything in C:\Users\Intel

  SIZE
    size downloads
    how much space does docker take
    storage used by H:\

  LARGEST
    largest files in C:\
    show me the biggest files in downloads

  SEARCH
    search *.py
    search python files
    search *.json

  TREE
    tree downloads
    show directory structure of H:\BRIGHT

  SYSTEM
    drives
    show my disks
    pc

  FILE OPERATIONS
    copy <source> <destination>
    move <source> <destination>
    rename <old> <new>
    delete <path>

  EXIT
    exit
    quit

  TYPO TOLERANCE
    "dowloads"     -> Downloads
    "documnts"     -> Documents
    "vs codum"     -> VS Codium
    "brighauth"    -> BrightAuth

  Any command that changes/deletes files asks for confirmation.
"""
        )

    def execute(self, text: str):
        intent = self.nlp.parse(text)

        handlers: dict[str, Callable[[str], None]] = {
            "find": self.cmd_find,
            "open": self.cmd_open,
            "list": self.cmd_list,
            "count": self.cmd_count,
            "size": self.cmd_size,
            "largest": self.cmd_largest,
            "tree": self.cmd_tree,
            "search": self.cmd_search,
            "drives": lambda _: self.cmd_drives(),
            "pc": lambda _: self.cmd_pc(),
            "delete": self.cmd_delete,
            "copy": self.cmd_copy,
            "move": self.cmd_move,
            "rename": self.cmd_rename,
        }

        if intent.command == "exit":
            self.running = False
            return

        if intent.command == "help":
            self.help()
            return

        handler = handlers.get(intent.command)

        if not handler:
            print(
                f"  I couldn't understand that command "
                f"(confidence {intent.confidence:.0f}%)."
            )
            print("  Try: find, open, list, count, size, largest, tree, search")
            return

        try:
            handler(intent.target)
        except KeyboardInterrupt:
            print("\n  Cancelled.")
        except PermissionError:
            print("  Permission denied. Try an elevated terminal if appropriate.")
        except OSError as exc:
            print(f"  Windows filesystem error: {exc}")
        except Exception as exc:
            print(f"  Error: {exc}")

    def run(self):
        if not is_windows():
            print("APEX FILES requires Windows.")
            sys.exit(1)

        print(self.BANNER)
        print("  Type 'help' for examples. Type 'exit' to quit.")
        print("  Small spelling mistakes are intentionally tolerated.\n")

        while self.running:
            try:
                text = input("APEX-FS > ").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                break

            if text:
                self.execute(text)


def main():
    app = APEXFiles()

                                 
                                     
    if len(sys.argv) > 1:
        app.execute(" ".join(sys.argv[1:]))
        return

    app.run()


if __name__ == "__main__":
    main()
