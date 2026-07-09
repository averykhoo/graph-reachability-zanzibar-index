#!/usr/bin/env python3
"""
==============================================================================
Repository Intelligence Flattener (v2)
https://gist.github.com/averykhoo/f59c85794876249e963698ae45de49cc
==============================================================================
A robust, zero-dependency (except pathspec) repository scanner designed to
build high-quality, high-signal system prompts for Large Language Models.

Features:
- Hierarchical Ignore Rules (.gitignore, .aiignore)
- Python Internal Dependency Mapping (Forward & Reverse Indexing)
- Pure-Python Binary Metadata Extraction (.npy shapes, .wav formats)
- Notebook (.ipynb) Conversion (Preserves Markdown as documentation)
- Excel File Representation (.xlsx Sheets to CSV Blocks)
- Word / PowerPoint File Representation
- Pure-Python PDF Text Extraction (Falls back to binary signature if empty/corrupt)
- Text Sanitization (Null-byte stripping, binary-fallback detection)
- Smart File Truncation (Preserves line boundaries, reports CSV/text dimensions)
- Directory-Aware Content Grouping

Usage:
    python build_system_prompt.py
==============================================================================
"""

import binascii
import csv
import fnmatch
import io
import json
import os
import re
import struct
import xml.etree.ElementTree as ET
import zipfile
import zlib
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

import pathspec

# ==============================================================================
# 1. GLOBAL CONFIGURATION
# ==============================================================================

REPO_PATH = Path("./")
OUTPUT_FILENAME = "system-prompt.txt"
IGNORE_FILENAMES = [".gitignore", ".aiignore", ".llmignore"]

# Limit for raw text files (prevent massive logs from blowing out context)
MAX_FILE_ESTIMATED_TOKENS = 80000
TRUNCATE_TARGET_TOKENS = 10000  # How many tokens to keep when truncating

# Namespaces used to identify "internal" imports for the dependency graph.
# Top-level packages (dirs with .py files) and top-level modules are auto-detected
# from the scan; list extra names here only for namespaces that can't be detected
# (e.g. a package injected onto sys.path from outside the repo).
INTERNAL_NAMESPACES: List[str] = []

# Glob patterns to always exclude (case-insensitive matching on filenames or relative paths)
EXCLUDED_PATTERNS = {
    "~$*.*",  # Microsoft Office temporary lock files
    "thumbs.db",  # Windows thumbnail cache database
    ".DS_Store",
    # "*.lnk",  # Windows shortcut files
    # "*.tmp",  # Temporary files
}

# Extension Categorization
TEXT_EXTENSIONS = {
    "asm",
    "asp",
    "bash",
    "bat",
    "c",
    "cjs",
    "cl",
    "clj",
    "cmake",
    "cmd",
    "coffee",
    "cpp",
    "cs",
    "css",
    "csv",
    "cxx",
    "dart",
    "dockerfile",
    "env",
    "erl",
    "ex",
    "exs",
    "f",
    "f90",
    "f95",
    "for",
    "go",
    "gql",
    "graphql",
    "groovy",
    "h",
    "hpp",
    "hrl",
    "hs",
    "htm",
    "html",
    "hxx",
    "ini",
    "java",
    "jl",
    "js",
    "json",
    "jsonl",
    "jsp",
    "jsx",
    "kt",
    "kts",
    "lean",
    "less",
    "lisp",
    "log",
    "lua",
    "m",
    "makefile",
    "markdown",
    "md",
    "mjs",
    "mk",
    "ml",
    "mli",
    "mm",
    "pas",
    "php",
    "pl",
    "pm",
    "pro",
    "proto",
    "ps1",
    "py",
    "pyw",
    "r",
    "rb",
    "rs",
    "s",
    "sass",
    "scala",
    "scm",
    "scss",
    "sh",
    "sql",
    "ss",
    "sv",
    "swift",
    "tcl",
    "tex",
    "text",
    "tf",
    "toml",
    "ts",
    "tsv",
    "tsx",
    "txt",
    "v",
    "vb",
    "vbs",
    "vhdl",
    "xml",
    "yaml",
    "yml",
    "zsh",
}
NOTEBOOK_EXTENSIONS = {"ipynb"}
AUDIO_EXTENSIONS = {"wav"}
NUMPY_EXTENSIONS = {"npy", "npz"}
EXCEL_EXTENSIONS = {"xlsx"}
PDF_EXTENSIONS = {"pdf"}
DOCX_EXTENSIONS = {"docx"}
PPTX_EXTENSIONS = {"pptx"}

# Language hint mapping for markdown code blocks
EXT_TO_LANG = {
    "asm":        "assembly",
    "bat":        "batch",
    "c":          "c",
    "cc":         "cpp",
    "cl":         "commonlisp",
    "clj":        "clojure",
    "cmake":      "cmake",
    "cmd":        "batch",
    "cpp":        "cpp",
    "cs":         "csharp",
    "css":        "css",
    "cxx":        "cpp",
    "dart":       "dart",
    "dockerfile": "dockerfile",
    "ex":         "elixir",
    "exs":        "elixir",
    "f":          "fortran",
    "f90":        "fortran",
    "f95":        "fortran",
    "for":        "fortran",
    "go":         "go",
    "gql":        "graphql",
    "graphql":    "graphql",
    "groovy":     "groovy",
    "h":          "c",
    "hpp":        "cpp",
    "hs":         "haskell",
    "html":       "html",
    "hxx":        "cpp",
    "ini":        "ini",
    "java":       "java",
    "js":         "javascript",
    "json":       "json",
    "jsp":        "jsp",
    "jsx":        "jsx",
    "kt":         "kotlin",
    "lean":       "lean",
    "less":       "less",
    "lisp":       "lisp",
    "log":        "",  # Empty hint for generic text
    "lua":        "lua",
    "m":          "objectivec",
    "makefile":   "makefile",
    "md":         "markdown",
    "mk":         "makefile",
    "mm":         "objectivec",  # obj-c
    "pas":        "pascal",
    "php":        "php",
    "pl":         "perl",
    "proto":      "protobuf",
    "ps1":        "powershell",
    "py":         "python",
    "r":          "r",
    "rb":         "ruby",
    "rs":         "rust",
    "s":          "assembly",
    "scala":      "scala",
    "scss":       "scss",
    "sh":         "bash",
    "sql":        "sql",
    "sv":         "systemverilog",
    "swift":      "swift",
    "tcl":        "tcl",
    "tex":        "latex",
    "text":       "",
    "tf":         "terraform",
    "toml":       "toml",
    "ts":         "typescript",
    "tsx":        "tsx",
    "txt":        "",
    "v":          "verilog",
    "vb":         "vbnet",
    "vbs":        "vbscript",
    "vhdl":       "vhdl",
    "xml":        "xml",
    "yaml":       "yaml",
    "yml":        "yaml",
    "xlsx":       "markdown",  # Outputs sheets as markdown subheaders + csv blocks
    "pdf":        "markdown",  # Outputs pages with page headers
    "docx":       "markdown",  # Outputs document content with headers
    "pptx":       "markdown",  # Outputs slides with slide headers
}


# ==============================================================================
# 2. DATA MODELS
# ==============================================================================

@dataclass
class AnalyzedFile:
    """Represents a scanned file with extracted intelligence."""
    path_abs: Path
    path_rel: Path
    extension: str

    is_text: bool = False
    is_binary: bool = False
    is_notebook: bool = False

    content: str = ""
    metadata: str = ""
    tokens: int = 0

    # Dependency Tracking
    imports: Set[Path] = field(default_factory=set)
    imported_by: Set[Path] = field(default_factory=set)


# ==============================================================================
# 3. UTILITIES & SANITIZATION
# ==============================================================================

class Sanitizer:
    """Stateless utilities for token estimation, text cleaning, and truncation."""

    # groups approximated tokens:
    # * contiguous digits
    # * contiguous words, without digits or underscores
    # * leading underscores, then contiguous words or digits (but not both)
    # * contiguous whitespace
    # * contiguous punctuation
    TOKEN_REGEX = re.compile(r'(?:\d+|[^\W\d\s_]+|_+(?:\d+|[^\W\d\s_]+)?|\s+|[^\s\w\d]+)')

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Heuristic tokenizer counting word-chunks and symbols."""
        if not text: return 0
        return len(Sanitizer.TOKEN_REGEX.findall(text))

    @staticmethod
    def sanitize_and_check(text: str) -> Tuple[str, bool]:
        """
        Cleans text and determines if it's actually disguised binary.
        Returns (clean_text, is_binary_flag)

        >> text, is_bin = Sanitizer.sanitize_and_check("Hello\\x00World")
        >> text == "Hello[NULL]World"
        True
        """
        if not text:
            return "", False

        # Strip dangerous null bytes
        clean_text = text.replace('\x00', ' ')  # originally this replaced it with `[NULL]`, but i like whitespace

        # Calculate concentration of non-printable control characters
        # (excluding standard whitespace \n, \r, \t)
        control_chars = sum(1 for c in clean_text if ord(c) < 32 and c not in '\n\r\t')

        # If more than 1% of the file is control characters, it's likely binary data
        is_binary = (control_chars / len(clean_text)) > 0.01 if clean_text else False
        return clean_text, is_binary

    @staticmethod
    def get_comment_style(ext: str) -> Tuple[str, str]:
        """Provides syntactically correct comment indicators based on file types."""
        if ext in {"py", "sh", "bash", "yaml", "yml", "ini", "toml", "csv", "tsv", "makefile", "mk", "ipynb"}:
            return "# ", ""
        elif ext in {"js", "ts", "jsx", "tsx", "cpp", "c", "h", "hpp", "cs", "java", "go", "rs", "swift"}:
            return "// ", ""
        elif ext in {"html", "xml", "md", "markdown", "xlsx", "pdf", "docx", "pptx"}:
            return "<!-- ", " -->"
        elif ext in {"css", "scss", "sass"}:
            return "/* ", " */"
        elif ext in {"lean", "hs", "elm"}:
            return "-- ", ""
        else:
            return "[", "]"

    @staticmethod
    def truncate_with_dimensions(content: str, ext: str, target_tokens: int) -> Tuple[str, str]:
        """
        Truncates text safely at line boundaries, calculates original dimensions
        (including CSV structural metrics), and appends a clear notice for the LLM.
        """
        lines = content.splitlines()
        total_lines = len(lines)
        total_chars = len(content)

        # 1. Inspect CSV/TSV structural dimensions
        num_cols = None
        if ext in {"csv", "tsv"} and lines:
            first_line = lines[0]
            delim = "\t" if ext == "tsv" else ","
            if ext == "csv" and ";" in first_line and "," not in first_line:
                delim = ";"
            num_cols = len(first_line.split(delim))

        # 2. Extract lines up to target token limit
        truncated_lines = []
        current_tokens = 0
        truncated = False

        for line in lines:
            line_tokens = Sanitizer.estimate_tokens(line) + 1  # Add 1 as estimated newline token
            if current_tokens + line_tokens > target_tokens:
                truncated = True
                break
            truncated_lines.append(line)
            current_tokens += line_tokens

        if not truncated:
            return content, ""

        # 3. Compile structural truncation message for target LLM
        p_start, p_end = Sanitizer.get_comment_style(ext)
        banner = []
        banner.append(f"\n{p_start}... [TRUNCATED] ...{p_end}")
        banner.append(f"{p_start}[PREVIEW ONLY - FILE TRUNCATED TO PREVENT CONTEXT BLOWOUT]{p_end}")

        if num_cols is not None:
            banner.append(f"{p_start}Original File Dimensions: {total_lines:,} rows x {num_cols} columns{p_end}")
            banner.append(f"{p_start}Shown: First {len(truncated_lines):,} rows (~{current_tokens:,} tokens){p_end}")
        else:
            banner.append(f"{p_start}Original File Dimensions: {total_lines:,} lines, {total_chars:,} chars{p_end}")
            banner.append(f"{p_start}Shown: First {len(truncated_lines):,} lines (~{current_tokens:,} tokens){p_end}")

        truncated_content = "\n".join(truncated_lines) + "\n" + "\n".join(banner)

        # Metadata representation for the index
        if num_cols is not None:
            metadata = f"Truncated Preview (~{current_tokens:,} tokens). Total: {total_lines:,} rows x {num_cols} cols."
        else:
            metadata = f"Truncated Preview (~{current_tokens:,} tokens). Total: {total_lines:,} lines."

        return truncated_content, metadata


class IgnoreEngine:
    """Handles .gitignore hierarchy and path exclusions with git precedence:
    a deeper ignore file overrides a shallower one, the LAST matching pattern
    within a file wins (so `!negations` re-include), and nothing can be
    re-included under a directory that is itself ignored."""

    @staticmethod
    def build_matcher(repo_root: Path, filenames: List[str]) -> Callable[[Path], bool]:
        """Creates a function that checks if a path is ignored based on hierarchical rules."""
        repo_root = repo_root.resolve()
        cache: Dict[Path, Optional[pathspec.PathSpec]] = {}

        def get_spec(directory: Path) -> Optional[pathspec.PathSpec]:
            if directory in cache:
                return cache[directory]
            lines = []
            found = False
            for fn in filenames:
                file_path = directory / fn
                if file_path.is_file():
                    found = True
                    try:
                        with file_path.open('r', encoding='utf-8', errors='ignore') as f:
                            if lines and not lines[-1].endswith('\n'): lines.append('\n')
                            lines.extend(f.readlines())
                    except Exception:
                        pass
            spec = pathspec.PathSpec.from_lines('gitwildmatch', lines) if found else None
            cache[directory] = spec
            return spec

        def spec_decision(spec: pathspec.PathSpec, rel_str: str) -> Optional[bool]:
            """Polarity of the LAST matching pattern in one ignore file
            (True = ignored, False = re-included by `!`), or None if no match."""
            for pattern in reversed(spec.patterns):
                if pattern.include is None:  # blank / comment lines
                    continue
                if pattern.match_file(rel_str):
                    return pattern.include
            return None

        def is_ignored(filepath: Path) -> bool:
            try:
                rel = filepath.resolve().relative_to(repo_root)
            except (ValueError, OSError):
                return True  # outside the repo (or unresolvable)

            # 1. Hardcoded exclusions
            if rel.parts and rel.parts[0] == '.git': return True
            if rel.parts and rel.parts[-1] == OUTPUT_FILENAME: return True
            if rel.parts and rel.parts[-1] == Path(__file__).name: return True

            try:
                path_is_dir = filepath.is_dir()
            except OSError:
                path_is_dir = False

            # 2. Evaluate every prefix of the path: an ignored directory prefix is
            #    final (git cannot re-include files under an ignored directory).
            parts = rel.parts
            for i in range(len(parts)):
                prefix_is_dir = (i < len(parts) - 1) or path_is_dir
                # Deeper ignore files take precedence: walk spec dirs from the
                # prefix's own parent up to the repo root; first decision wins.
                decision = None
                for j in range(i, -1, -1):
                    spec = get_spec(repo_root.joinpath(*parts[:j]))
                    if spec is None:
                        continue
                    rel_to_spec = '/'.join(parts[j:i + 1]) + ('/' if prefix_is_dir else '')
                    decision = spec_decision(spec, rel_to_spec)
                    if decision is not None:
                        break
                if decision:
                    return True
            return False

        return is_ignored


# ==============================================================================
# 4. INTERNAL PDF PARSER HELPER
# ==============================================================================

class LitePDFParser:
    """Pure-Python standard library PDF parser."""

    def __init__(self, pdf_bytes: bytes):
        self.pdf_bytes = pdf_bytes
        self.objects = {}
        self._scan_objects()

    def get_page_count(self) -> int:
        """Counts the number of page objects found inside the document structure."""
        page_ids = [
            obj_id for obj_id, obj in self.objects.items()
            if re.search(rb'/Type\s*/Page\b', obj["dict"])
        ]
        return len(page_ids)

    def _get_dict_val(self, dict_bytes: bytes, key_bytes: bytes) -> bytes:
        val_pattern = rb'(?:\d+\s+\d+\s+R|\[[^\]]*\]|<<.*?>>|/[^\s/<>[\]()]+|[^\s/<>[\]()]+)'
        match = re.search(re.escape(key_bytes) + rb'\s*(' + val_pattern + rb')', dict_bytes, re.DOTALL)
        return match.group(1).strip() if match else b""

    def _scan_objects(self):
        """Finds object boundaries safely, bypassing endobj stream collisions."""
        start_pattern = re.compile(rb'(?:^|[\r\n]+)(\d+)\s+(\d+)\s+obj\b')
        matches = list(start_pattern.finditer(self.pdf_bytes))

        for idx, m in enumerate(matches):
            try:
                id_num = int(m.group(1))
                obj_start = m.end()
                obj_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(self.pdf_bytes)

                raw_chunk = self.pdf_bytes[obj_start:obj_end].strip()
                if raw_chunk.endswith(b'endobj'):
                    raw_chunk = raw_chunk[:-6].strip()

                parts = raw_chunk.split(b'stream', 1)
                dict_part = parts[0].strip()
                stream_part = b""
                if len(parts) > 1:
                    stream_part = parts[1].strip()
                    if stream_part.endswith(b'endstream'):
                        stream_part = stream_part[:-9].strip()

                # Decompress FlateDecode; quarantine unhandled binary streams (LZW/DCT/CCITT)
                has_filter = b'/Filter' in dict_part
                if b'/FlateDecode' in dict_part or b'/Fl' in dict_part:
                    try:
                        stream_part = zlib.decompress(stream_part, 15 + 32)
                        has_filter = False
                    except Exception:
                        try:
                            stream_part = zlib.decompress(stream_part, -15)
                            has_filter = False
                        except Exception:
                            pass
                if has_filter:
                    stream_part = b""  # Clear compressed binary garbage

                self.objects[id_num] = {"dict": dict_part, "stream": stream_part}
            except Exception:
                pass

    def _parse_cmap(self, cmap_bytes: bytes) -> dict:
        cmap = {}
        if not cmap_bytes:
            return cmap
        for src, dst in re.findall(rb'<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>', cmap_bytes):
            try:
                cmap[int(src, 16)] = "".join(chr(int(dst[i:i + 4], 16)) for i in range(0, len(dst), 4))
            except Exception:
                pass
        for start, end, dst_start in re.findall(rb'<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>', cmap_bytes):
            try:
                s_val, e_val, d_val = int(start, 16), int(end, 16), int(dst_start, 16)
                for offset in range(e_val - s_val + 1):
                    cmap[s_val + offset] = chr(d_val + offset)
            except Exception:
                pass
        for start, end, arr_content in re.findall(rb'<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>\s*\[([^\]]+)\]', cmap_bytes):
            try:
                s_val, e_val = int(start, 16), int(end, 16)
                dst_list = re.findall(rb'<([0-9a-fA-F]+)>', arr_content)
                for offset, dst_hex in enumerate(dst_list):
                    if offset > (e_val - s_val): break
                    cmap[s_val + offset] = "".join(chr(int(dst_hex[i:i + 4], 16)) for i in range(0, len(dst_hex), 4))
            except Exception:
                pass
        return cmap

    def _resolve_font_cmaps(self, page_dict_bytes: bytes) -> dict:
        font_cmaps = {}
        res_val = self._get_dict_val(page_dict_bytes, b'/Resources')
        if not res_val:
            return font_cmaps
        ref_match = re.match(rb'^(\d+)\s+(\d+)\s+R$', res_val)
        dict_source = self.objects.get(int(ref_match.group(1)))["dict"] if ref_match else res_val

        font_val = self._get_dict_val(dict_source, b'/Font')
        if not font_val:
            return font_cmaps
        ref_match = re.match(rb'^(\d+)\s+(\d+)\s+R$', font_val)
        font_source = self.objects.get(int(ref_match.group(1)))["dict"] if ref_match else font_val

        for font_name, f_id, _ in re.findall(rb'(/[A-Za-z0-9_]+)\s+(\d+)\s+(\d+)\s+R', font_source):
            font_obj = self.objects.get(int(f_id))
            if font_obj:
                to_unicode_val = self._get_dict_val(font_obj["dict"], b'/ToUnicode')
                tu_match = re.match(rb'^(\d+)\s+(\d+)\s+R$', to_unicode_val)
                if tu_match:
                    tu_obj = self.objects.get(int(tu_match.group(1)))
                    if tu_obj and tu_obj["stream"]:
                        font_cmaps[font_name.decode('ascii', errors='ignore')] = self._parse_cmap(tu_obj["stream"])
        return font_cmaps

    def _resolve_contents(self, page_dict_bytes: bytes) -> bytes:
        contents_val = self._get_dict_val(page_dict_bytes, b'/Contents')
        if not contents_val:
            return b""
        ref_match = re.match(rb'^(\d+)\s+(\d+)\s+R$', contents_val)
        if ref_match:
            obj = self.objects.get(int(ref_match.group(1)))
            return obj["stream"] if obj else b""
        if contents_val.startswith(b'['):
            refs = re.findall(rb'(\d+)\s+(\d+)\s+R', contents_val)
            streams = []
            for r_id, _ in refs:
                obj = self.objects.get(int(r_id))
                if obj and obj["stream"]:
                    streams.append(obj["stream"])
            return b"\n".join(streams)
        return b""

    def _clean_literal(self, literal_bytes: bytes) -> bytes:
        esc_map = {b'n':  b'\n', b'r': b'\r', b't': b'\t', b'b': b'\b', b'f': b'\f', b'(': b'(', b')': b')',
                   b'\\': b'\\'}

        def repl(m):
            val = m.group(1)
            if val in esc_map: return esc_map[val]
            if val.startswith((b'\r', b'\n')): return b''
            if val[0:1].isdigit():
                try:
                    return bytes([int(val, 8)])
                except Exception:
                    pass
            return val

        return re.sub(rb'\\([0-7]{1,3}|[\r\n]+|.)', repl, literal_bytes)

    def _clean_hex(self, hex_bytes: bytes) -> bytes:
        try:
            hex_str = hex_bytes.decode('ascii', errors='ignore')
            if len(hex_str) % 2 == 1: hex_str += '0'
            return binascii.unhexlify(hex_str)
        except Exception:
            return b""

    def _translate(self, raw_bytes: bytes, cmap: dict) -> str:
        if not cmap:
            # Fall back safely, filtering unprintable ranges instead of forcing broad UTF-16
            if raw_bytes.startswith((b'\xfe\xff', b'\xff\xfe')) or (len(raw_bytes) >= 2 and raw_bytes[0] == 0):
                try:
                    return raw_bytes.decode('utf-16', errors='ignore')
                except Exception:
                    pass
            return raw_bytes.decode('latin-1', errors='ignore')
        is_two_byte = any(k > 255 for k in cmap)
        result = []
        step = 2 if is_two_byte else 1
        for idx in range(0, len(raw_bytes), step):
            if is_two_byte:
                if idx + 1 < len(raw_bytes):
                    val = (raw_bytes[idx] << 8) + raw_bytes[idx + 1]
                else:
                    break
            else:
                val = raw_bytes[idx]

            decoded_char = cmap.get(val)
            if decoded_char is not None:
                result.append(decoded_char)
            else:
                # Keep printable characters, map raw binary garbage to whitespace
                if 32 <= val <= 126 or val in (9, 10, 13):
                    result.append(chr(val))
                elif 160 <= val <= 255:
                    result.append(chr(val))
                else:
                    result.append(" ")
        return "".join(result)

    def _extract_text_from_stream(self, stream_bytes: bytes, font_cmaps: dict) -> str:
        pattern = re.compile(rb'(?P<font>/[A-Za-z0-9_]+)\s+[\d\.]+\s+Tf|'
                             rb'\[(?P<array>.*?)\]\s*TJ|'
                             rb'<(?P<hex>[0-9a-fA-F]*?)>\s*(?:Tj|\'|")|'
                             rb'\((?P<literal>.*?)\)\s*(?:Tj|\'|")|'
                             rb'(?P<newline>T\*)', re.DOTALL)
        output = []
        active_cmap = {}
        current_font = ""
        for m in pattern.finditer(stream_bytes):
            if m.group('font'):
                current_font = m.group('font').decode('ascii', errors='ignore')
                active_cmap = font_cmaps.get(current_font, {})
            elif m.group('array'):
                array_content = m.group('array')
                item_pattern = re.compile(rb'\((.*?)\)|<([0-9a-fA-F]*?)>|(-?\d+)', re.DOTALL)
                for item in item_pattern.finditer(array_content):
                    if item.group(1) is not None:
                        output.append(self._translate(self._clean_literal(item.group(1)), active_cmap))
                    elif item.group(2) is not None:
                        output.append(self._translate(self._clean_hex(item.group(2)), active_cmap))
                    elif item.group(3) is not None:
                        if int(item.group(3)) < -150: output.append(" ")
            elif m.group('hex'):
                output.append(self._translate(self._clean_hex(m.group('hex')), active_cmap))
            elif m.group('literal'):
                output.append(self._translate(self._clean_literal(m.group('literal')), active_cmap))
            elif m.group('newline'):
                output.append("\n")
        return "".join(output)

    def _is_page_garbled(self, text: str) -> bool:
        if not text.strip():
            return False
        total = len(text)
        clean_chars = 0
        letters = 0
        vowels = 0
        control_chars = 0
        for c in text:
            o = ord(c)
            if (32 <= o <= 126) or c in "\n\r\t":
                clean_chars += 1
                if c.isalpha():
                    letters += 1
                    if c.lower() in 'aeiou':
                        vowels += 1
            # Unified CJK ideographs/Katakana/Hiragana/Hangul are also highly "readable" and valid
            elif (0x4E00 <= o <= 0x9FFF) or (0x3040 <= o <= 0x30FF) or (0x1100 <= o <= 0x11FF) or (
                    0xAC00 <= o <= 0xD7A3):
                clean_chars += 1
                letters += 1
            # Support European accented glyphs
            elif (0xC0 <= o <= 0xFF) and o != 0xD7 and o != 0xF7:
                clean_chars += 1
                if c.isalpha():
                    letters += 1
                    if c.lower() in 'àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ':
                        vowels += 1
            elif o < 32 and c not in "\n\r\t":
                control_chars += 1

        # Reject if there is a suspiciously high concentration of nulls/control chars
        if (control_chars / total) > 0.05:
            return True
        # Reject if the standard readable density falls below 70%
        if (clean_chars / total) < 0.70:
            return True
        # Reject if a larger English block of text contains an impossibly low vowel ratio (scrambled fonts)
        if letters > 25 and (vowels / letters) < 0.10:
            return True

        return False

    def extract_text(self) -> Optional[str]:
        """Extracts text from all pages. Returns None if it fails, finds no text, or text is garbled."""
        try:
            extracted_pages = []
            page_ids = [
                obj_id for obj_id, obj in self.objects.items()
                if re.search(rb'/Type\s*/Page\b', obj["dict"])
            ]
            page_ids.sort()
            for idx, p_id in enumerate(page_ids):
                page_obj = self.objects[p_id]
                font_cmaps = self._resolve_font_cmaps(page_obj["dict"])
                content_stream = self._resolve_contents(page_obj["dict"])
                page_text = self._extract_text_from_stream(content_stream, font_cmaps)
                if page_text.strip() and not self._is_page_garbled(page_text):
                    extracted_pages.append(f"--- Page {idx + 1} ---\n{page_text.strip()}")
            result = "\n\n".join(extracted_pages)
            return result if result.strip() else None
        except Exception:
            return None


# ==============================================================================
# 5. PARSERS (THE METADATA EXTRACTORS)
# ==============================================================================

class FileParsers:
    """Collection of pure-python metadata extractors and file parsers."""

    @staticmethod
    def parse_python(filepath: Path, content: str, namespaces: Set[str]) -> Set[Path]:
        """Extracts internal dependencies from Python files."""
        imports = set()
        if not namespaces:
            return imports
        # Matches: `from src.utils import x` or `import src.utils`. The (?!\w)
        # lookahead keeps `import srcfoo` / `from src2.x import y` from matching
        # namespace `src`.
        ns_pattern = (r'^(?:from|import)\s+('
                      + '|'.join(re.escape(ns) for ns in sorted(namespaces))
                      + r')(?!\w)((?:\.\w+)*)')
        matches = re.findall(ns_pattern, content, re.MULTILINE)

        for base, rest in matches:
            # Convert python module path to file path logic
            # e.g., src.utils.constants -> src/utils/constants.py
            module_str = base + rest
            rel_parts = module_str.split('.')
            target_base = Path(*rel_parts)
            imports.add(target_base)
        return imports

    @staticmethod
    def parse_notebook(filepath: Path) -> Optional[str]:
        """Converts Jupyter Notebooks, formatting Markdown for LLMs."""
        try:
            with filepath.open('r', encoding='utf-8') as f:
                data = json.load(f)

            lines = [
                f"# [NOTE] Converted Jupyter Notebook: {filepath.name}",
                "# Code is raw, Markdown is wrapped in docstrings."
            ]

            for i, cell in enumerate(data.get("cells", [])):
                ctype = cell.get("cell_type", "")
                source = cell.get("source", [])
                if isinstance(source, str): source = source.splitlines(keepends=True)
                if not source: continue

                content = "".join(source).strip()

                if ctype == "code":
                    lines.append(f"\n# %% [code] cell_id: {i}")
                    lines.append(content)
                elif ctype == "markdown":
                    lines.append(f"\n'''[MARKDOWN CELL ID: {i}]\n{content}\n'''")

            return "\n".join(lines)
        except Exception:
            return None

    @staticmethod
    def parse_xlsx(filepath: Path) -> str:
        """
        Pure python XLSX extractor. Converts Excel worksheets into markdown headers
        and CSV code blocks with structural truncation of rows and columns.
        """
        MAX_ROWS = 50
        MAX_COLS = 20

        def strip_ns(tag):
            return tag.split('}')[-1] if '}' in tag else tag

        def cell_ref_to_indices(ref):
            letters = ''.join(c for c in ref if c.isalpha())
            digits = ''.join(c for c in ref if c.isdigit())
            col = 0
            for char in letters:
                col = col * 26 + (ord(char.upper()) - ord('A') + 1)
            col_idx = col - 1
            row_idx = int(digits) - 1
            return row_idx, col_idx

        output = [f"# [EXCEL FILE] {filepath.name}"]

        try:
            with zipfile.ZipFile(filepath, 'r') as z:
                # 1. Shared Strings Parsing
                shared_strings = []
                if 'xl/sharedStrings.xml' in z.namelist():
                    with z.open('xl/sharedStrings.xml') as f:
                        for _, elem in ET.iterparse(f, events=('end',)):
                            if strip_ns(elem.tag) == 'si':
                                text_parts = []
                                for child in elem.iter():
                                    if strip_ns(child.tag) == 't':
                                        text_parts.append(child.text or '')
                                shared_strings.append(''.join(text_parts))
                                elem.clear()

                # 2. Relationship Parsing (linking relationship rIds to sheet XML paths)
                rels = {}
                if 'xl/_rels/workbook.xml.rels' in z.namelist():
                    with z.open('xl/_rels/workbook.xml.rels') as f:
                        for _, elem in ET.iterparse(f):
                            if strip_ns(elem.tag) == 'Relationship':
                                r_id = elem.get('Id')
                                target = elem.get('Target')
                                if target:
                                    if target.startswith('/'):
                                        target = target[1:]
                                    if not target.startswith('xl/'):
                                        target = 'xl/' + target
                                    rels[r_id] = target

                # 3. Workbook Sheet Mapping
                sheets = []
                if 'xl/workbook.xml' in z.namelist():
                    with z.open('xl/workbook.xml') as f:
                        for _, elem in ET.iterparse(f):
                            if strip_ns(elem.tag) == 'sheet':
                                name = elem.get('name')
                                r_id_key = next((k for k in elem.attrib if k.endswith('id')), None)
                                r_id = elem.attrib.get(r_id_key) if r_id_key else None
                                if r_id and r_id in rels:
                                    sheets.append({'name': name, 'path': rels[r_id]})

                output.append(f"Total Sheets: {len(sheets)}\n")

                for sheet in sheets:
                    sheet_name = sheet['name']
                    sheet_path = sheet['path']

                    grid = []
                    if sheet_path in z.namelist():
                        with z.open(sheet_path) as f:
                            for _, elem in ET.iterparse(f, events=('end',)):
                                tag = strip_ns(elem.tag)
                                if tag == 'c':
                                    coord = elem.get('r')
                                    if not coord:
                                        continue
                                    row_idx, col_idx = cell_ref_to_indices(coord)
                                    cell_type = elem.get('t')
                                    val_elem = next((c for c in elem if strip_ns(c.tag) == 'v'), None)
                                    val = val_elem.text if val_elem is not None else None

                                    if cell_type == 's' and val is not None:
                                        try:
                                            val = shared_strings[int(val)]
                                        except (ValueError, IndexError):
                                            pass
                                    elif cell_type == 'inlineStr':
                                        is_elem = next((c for c in elem if strip_ns(c.tag) == 'is'), None)
                                        if is_elem is not None:
                                            t_elem = next((c for c in is_elem if strip_ns(c.tag) == 't'), None)
                                            val = t_elem.text if t_elem is not None else None
                                    elif cell_type == 'b' and val is not None:
                                        val = "TRUE" if val == '1' else "FALSE"
                                    elif val is not None:
                                        try:
                                            if '.' in val:
                                                val = float(val)
                                                if val.is_integer():
                                                    val = int(val)
                                            else:
                                                val = int(val)
                                        except ValueError:
                                            pass

                                    # Normalize raw row string values (standardize carriage returns)
                                    if isinstance(val, str):
                                        val = val.replace('\r\n', '\n').replace('\r', '\n')

                                    while len(grid) <= row_idx:
                                        grid.append([])
                                    row = grid[row_idx]
                                    while len(row) <= col_idx:
                                        row.append("")
                                    row[col_idx] = val if val is not None else ""

                    orig_rows = len(grid)
                    orig_cols = max((len(row) for row in grid), default=0)

                    output.append(f"#### Sheet: {sheet_name}\n")

                    if orig_rows == 0:
                        output.append("*(Empty sheet)*\n")
                        continue

                    # Apply structural truncation limits
                    trunc_rows = min(orig_rows, MAX_ROWS)
                    trunc_cols = min(orig_cols, MAX_COLS)

                    truncated_grid = []
                    for r in range(trunc_rows):
                        row = grid[r]
                        trimmed_row = []
                        for c in range(trunc_cols):
                            if c < len(row):
                                trimmed_row.append(row[c])
                            else:
                                trimmed_row.append("")
                        truncated_grid.append(trimmed_row)

                    # Write structured grid values to string format CSV
                    csv_io = io.StringIO()
                    # lineterminator is set to standard Unix format to avoid duplicate carriage returns/blank lines
                    csv_writer = csv.writer(csv_io, lineterminator='\n')
                    csv_writer.writerows(truncated_grid)
                    csv_content = csv_io.getvalue()

                    output.append("````csv")
                    output.append(csv_content.strip("\r\n"))
                    output.append("````")

                    # Size metadata indicators printed directly below the code block
                    size_info = f"Original Dimensions: {orig_rows} rows x {orig_cols} columns"
                    if orig_rows > MAX_ROWS or orig_cols > MAX_COLS:
                        size_info += f" (Truncated Preview: showing first {trunc_rows} rows and {trunc_cols} columns)"
                    output.append(f"{size_info}\n")

        except Exception as e:
            return f"Error parsing Excel file {filepath.name}: {e}"

        return "\n".join(output)

    @staticmethod
    def parse_docx(filepath: Path) -> str:
        """
        Pure python DOCX extractor. Extracts document paragraphs, preserving
        line-breaks, tab characters, and table contents.
        """
        try:
            def strip_ns(tag):
                return tag.split('}')[-1] if '}' in tag else tag

            with zipfile.ZipFile(filepath, 'r') as z:
                if 'word/document.xml' not in z.namelist():
                    return f"Invalid DOCX {filepath.name} (missing word/document.xml)"

                with z.open('word/document.xml') as f:
                    tree = ET.parse(f)
                    root = tree.getroot()

                    paragraphs = []
                    # Word paragraphs are <w:p>
                    for elem in root.iter():
                        tag = strip_ns(elem.tag)
                        if tag == 'p':
                            p_text = []
                            for child in elem.iter():
                                c_tag = strip_ns(child.tag)
                                if c_tag == 't':
                                    p_text.append(child.text or '')
                                elif c_tag == 'br':
                                    p_text.append('\n')
                                elif c_tag == 'tab':
                                    p_text.append('\t')

                            p_str = ''.join(p_text).strip()
                            if p_str:
                                paragraphs.append(p_str)

                    output = [f"# [DOCUMENT] {filepath.name}\n"]
                    if paragraphs:
                        output.append("\n\n".join(paragraphs))
                    else:
                        output.append("*(No text)*")
                    return "\n".join(output)
        except Exception as e:
            return f"Error parsing DOCX file {filepath.name}: {e}"

    @staticmethod
    def parse_pptx(filepath: Path) -> str:
        """
        Pure python PPTX extractor. Extracts slide text grouped by slides,
        preserving line-breaks and tab characters.
        """
        try:
            def strip_ns(tag):
                return tag.split('}')[-1] if '}' in tag else tag

            with zipfile.ZipFile(filepath, 'r') as z:
                # Find and sort all slide files
                slide_files = []
                slide_re = re.compile(r'^ppt/slides/slide(\d+)\.xml$')
                for name in z.namelist():
                    m = slide_re.match(name)
                    if m:
                        slide_files.append((int(m.group(1)), name))

                if not slide_files:
                    return f"Invalid PPTX {filepath.name} or no slides found"

                slide_files.sort()
                output = [f"# [POWERPOINT FILE] {filepath.name}\n"]

                for slide_num, name in slide_files:
                    output.append(f"#### Slide {slide_num}\n")
                    with z.open(name) as f:
                        tree = ET.parse(f)
                        root = tree.getroot()

                        slide_text = []
                        # PowerPoint paragraphs are <a:p>
                        for elem in root.iter():
                            tag = strip_ns(elem.tag)
                            if tag == 'p':
                                p_text = []
                                for child in elem.iter():
                                    c_tag = strip_ns(child.tag)
                                    if c_tag == 't':
                                        p_text.append(child.text or '')
                                    elif c_tag == 'br':
                                        p_text.append('\n')
                                    elif c_tag == 'tab':
                                        p_text.append('\t')
                                p_str = ''.join(p_text).strip()
                                if p_str:
                                    slide_text.append(p_str)

                        if slide_text:
                            output.append("\n\n".join(slide_text))
                        else:
                            output.append("*(No text)*")
                        output.append("")  # Blank line between slides

                return "\n".join(output)
        except Exception as e:
            return f"Error parsing PPTX file {filepath.name}: {e}"

    @staticmethod
    def parse_pdf(filepath: Path) -> Optional[str]:
        """Pure python PDF parser (fallback to binary if empty/unreadable)."""
        try:
            pdf_bytes = filepath.read_bytes()
            parser = LitePDFParser(pdf_bytes)
            return parser.extract_text()
        except Exception:
            return None

    @staticmethod
    def parse_wav(filepath: Path) -> str:
        """Pure python WAV metadata extraction (supports 32-bit floats natively)."""
        try:
            with open(filepath, 'rb') as f:
                riff = f.read(4)
                if riff != b'RIFF': return "WAV Audio (Invalid RIFF signature)"
                f.read(4)  # file size
                wave_tag = f.read(4)
                if wave_tag != b'WAVE': return "WAV Audio (Invalid WAVE tag)"

                channels, rate, byte_rate, bits = 0, 0, 0, 0
                data_size = 0

                # Scan chunks for 'fmt ' and 'data'. RIFF pads odd-sized chunks
                # with one uncounted byte — skip it or every later read misaligns.
                for _ in range(10):  # limit to prevent infinite loops
                    chunk_id = f.read(4)
                    if len(chunk_id) < 4: break
                    chunk_size = struct.unpack('<I', f.read(4))[0]
                    padded_size = chunk_size + (chunk_size & 1)

                    if chunk_id == b'fmt ':
                        fmt_data = f.read(chunk_size)
                        channels = struct.unpack('<H', fmt_data[2:4])[0]
                        rate = struct.unpack('<I', fmt_data[4:8])[0]
                        byte_rate = struct.unpack('<I', fmt_data[8:12])[0]
                        bits = struct.unpack('<H', fmt_data[14:16])[0]
                        f.seek(padded_size - chunk_size, 1)
                    elif chunk_id == b'data':
                        data_size = chunk_size
                        f.seek(padded_size, 1)  # skip actual audio data
                    else:
                        f.seek(padded_size, 1)

                    if rate > 0 and data_size > 0:
                        break

                if rate > 0:
                    duration = data_size / byte_rate if byte_rate > 0 else 0
                    return f"WAV Audio: {channels}ch, {rate}Hz, {bits}-bit, {duration:.2f}s"
                return "WAV Audio (Missing fmt chunk)"
        except Exception:
            return "WAV Audio (Header unreadable)"

    @staticmethod
    def parse_npy(filepath: Path) -> str:
        """Pure python Numpy metadata extraction (supports .npy and .npz)."""
        try:
            # Handle standard zip-compressed .npz files
            if filepath.suffix.lower() == '.npz':
                import zipfile
                with zipfile.ZipFile(filepath) as z:
                    arrays = []
                    for name in z.namelist():
                        if name.endswith('.npy'):
                            with z.open(name) as f:
                                magic = f.read(6)
                                if magic == b'\x93NUMPY':
                                    f.read(2)  # Version
                                    hlen = struct.unpack('<H', f.read(2))[0]
                                    header = f.read(hlen).decode('ascii', errors='ignore')
                                    shape_match = re.search(r"'shape':\s*\((.*?)\)", header)
                                    dtype_match = re.search(r"'descr':\s*'([^']+)'", header)
                                    shape = shape_match.group(1) if shape_match else "unknown"
                                    dtype = dtype_match.group(1) if dtype_match else "unknown"
                                    arrays.append(f"{name[:-4]}: shape=({shape}), dtype={dtype}")
                    if arrays:
                        return "Numpy NPZ Archive containing: " + ", ".join(arrays)
                    return "Numpy NPZ Archive (Empty or unreadable)"

            # Handle standard single-array .npy files
            with open(filepath, 'rb') as f:
                magic = f.read(6)
                if magic != b'\x93NUMPY': return "Numpy Data (Invalid signature)"
                f.read(2)  # Version
                hlen = struct.unpack('<H', f.read(2))[0]
                header = f.read(hlen).decode('ascii', errors='ignore')

                shape_match = re.search(r"'shape':\s*\((.*?)\)", header)
                dtype_match = re.search(r"'descr':\s*'([^']+)'", header)
                shape = shape_match.group(1) if shape_match else "unknown"
                dtype = dtype_match.group(1) if dtype_match else "unknown"

                return f"Numpy Array: shape=({shape}), dtype={dtype}"
        except Exception:
            return "Numpy Data (Header unreadable)"

    @staticmethod
    def parse_generic_binary(filepath: Path) -> str:
        """Reads a hex signature for unidentified binary files."""
        try:
            with open(filepath, 'rb') as f:
                return f"Binary Signature: {repr(f.read(32))}..."
        except Exception:
            return "Binary File (Unreadable)"


# ==============================================================================
# 6. CORE ANALYZER (THE BRAIN)
# ==============================================================================

class RepoAnalyzer:
    """Scans the repository and builds the Intelligence Graph."""

    def __init__(self, root_path: Path):
        self.root = root_path.resolve()
        self.ignore_checker = IgnoreEngine.build_matcher(self.root, IGNORE_FILENAMES)

        self.all_rel_paths: List[Path] = []
        self.analyzed_files: Dict[Path, AnalyzedFile] = {}

    @staticmethod
    def is_pattern_excluded(rel_path: Path, patterns: Set[str]) -> bool:
        """Determines if a relative path matches any glob patterns (case-insensitive)."""
        path_str = rel_path.as_posix().lower()
        name_str = rel_path.name.lower()

        for pattern in patterns:
            pat_lower = pattern.lower()
            if '/' in pattern or '\\' in pattern:
                pat_clean = pat_lower.replace('\\', '/')
                # Evaluates exact match, standard path glob, or nested deep-directory matches
                if (
                        fnmatch.fnmatch(path_str, pat_clean)
                        or fnmatch.fnmatch(path_str, f"*/{pat_clean}")
                        or fnmatch.fnmatch(path_str, f"**/{pat_clean}")
                ):
                    return True
            else:
                if fnmatch.fnmatch(name_str, pat_lower):
                    return True
        return False

    def scan(self):
        """First Pass: Discover files and extract local metadata."""
        print("Walking directory tree...")

        for dirpath, dirnames, filenames in os.walk(self.root):
            curr_dir = Path(dirpath)
            # Prune ignored (or outside-pointing) directories in place so the walk
            # never descends into them — rglob would enumerate every entry of .git
            # and gitignored trees only to discard them one by one. os.walk does
            # not follow directory symlinks/junctions, so nothing outside the
            # root is enumerated.
            dirnames[:] = [d for d in dirnames if not self.ignore_checker(curr_dir / d)]

            for fname in sorted(filenames):
                abs_path = curr_dir / fname
                try:
                    if not abs_path.is_file(): continue
                except OSError:
                    continue

                rel_path = abs_path.relative_to(self.root)

                # Evaluate system exclusions based on standard and custom glob patterns
                if self.is_pattern_excluded(rel_path, EXCLUDED_PATTERNS):
                    continue

                if self.ignore_checker(abs_path): continue

                self.all_rel_paths.append(rel_path)

                ext = rel_path.suffix.lower()[1:]

                af = AnalyzedFile(path_abs=abs_path, path_rel=rel_path, extension=ext)

                # --- Type Routing ---
                if ext in AUDIO_EXTENSIONS:
                    af.is_binary = True
                    af.metadata = FileParsers.parse_wav(abs_path)
                elif ext in NUMPY_EXTENSIONS:
                    af.is_binary = True
                    af.metadata = FileParsers.parse_npy(abs_path)
                elif ext in NOTEBOOK_EXTENSIONS:
                    af.is_notebook = True
                    af.content = FileParsers.parse_notebook(abs_path) or ""
                elif ext in EXCEL_EXTENSIONS:
                    af.is_text = True
                    af.content = FileParsers.parse_xlsx(abs_path)
                elif ext in DOCX_EXTENSIONS:
                    af.is_text = True
                    af.content = FileParsers.parse_docx(abs_path)
                elif ext in PPTX_EXTENSIONS:
                    af.is_text = True
                    af.content = FileParsers.parse_pptx(abs_path)
                elif ext in PDF_EXTENSIONS:
                    try:
                        pdf_bytes = abs_path.read_bytes()
                        parser = LitePDFParser(pdf_bytes)
                        page_count = parser.get_page_count()
                        pdf_text = parser.extract_text()

                        if pdf_text:
                            af.is_text = True
                            warning = "<!-- WARNING: This is a low-accuracy machine-extraction of a PDF file. Text layout and character mappings are imperfect. -->\n\n"
                            af.content = warning + pdf_text
                            af.metadata = f"PDF Document (Attempted Text Extraction, {page_count} pages, size: {len(pdf_bytes)} bytes)"
                        else:
                            af.is_binary = True
                            sig = FileParsers.parse_generic_binary(abs_path)
                            af.metadata = f"PDF Document (Unreadable/Scanned, fallback to binary, {page_count} pages, size: {len(pdf_bytes)} bytes) - {sig}"
                    except Exception:
                        # read_bytes() itself may be what failed, so pdf_bytes can be
                        # unbound here -- don't reference it in this message
                        af.is_binary = True
                        sig = FileParsers.parse_generic_binary(abs_path)
                        af.metadata = f"PDF Document (Corrupt/Unreadable, fallback to binary) - {sig}"
                elif ext in TEXT_EXTENSIONS or not ext:
                    # Read Text. One locked or permission-denied file must not
                    # abort the whole run, and an EMPTY file is still a real
                    # text file (dropping empty __init__.py would erase package
                    # import edges from the dependency map).
                    try:
                        raw_content = abs_path.read_text(encoding='utf-8')
                    except UnicodeDecodeError:
                        try:
                            raw_content = abs_path.read_text(encoding='latin-1')
                        except Exception:
                            raw_content = None
                    except OSError:
                        raw_content = None

                    if raw_content is not None:
                        clean_text, is_bin = Sanitizer.sanitize_and_check(raw_content)
                        if is_bin:
                            af.is_binary = True
                            af.metadata = FileParsers.parse_generic_binary(abs_path)
                        else:
                            af.is_text = True
                            af.content = clean_text
                    else:
                        af.metadata = "Text file (unreadable: permission or I/O error)"
                else:
                    # Generic Binary fallback
                    af.is_binary = True
                    af.metadata = FileParsers.parse_generic_binary(abs_path)

                # Size Filtering / Truncation
                af.tokens = Sanitizer.estimate_tokens(af.content)
                if af.tokens > MAX_FILE_ESTIMATED_TOKENS:
                    truncated_text, metadata_notice = Sanitizer.truncate_with_dimensions(
                        af.content, af.extension, TRUNCATE_TARGET_TOKENS
                    )
                    af.content = truncated_text
                    af.metadata = metadata_notice
                    # Recalculate estimated tokens for final compilation logging
                    af.tokens = Sanitizer.estimate_tokens(af.content)

                # Only store files that gave us SOMETHING useful
                if af.is_text or af.is_binary or af.is_notebook or af.metadata:
                    self.analyzed_files[rel_path] = af

        self.all_rel_paths.sort()
        print(f"Discovered {len(self.all_rel_paths)} total files.")
        print(f"Analyzed {len(self.analyzed_files)} files for prompt inclusion.")

        self._resolve_dependencies()

    def _resolve_dependencies(self):
        """Second Pass: Link files based on imports and calculate roles."""
        print("Resolving python dependency graph...")

        # Valid python paths in repo
        py_paths = {p for p in self.analyzed_files if p.suffix == '.py'}

        # Internal namespaces: auto-detected from the scan (top-level directories
        # holding .py files anywhere below them, and top-level modules), plus any
        # manual extras from INTERNAL_NAMESPACES.
        namespaces = set(INTERNAL_NAMESPACES)
        for p in py_paths:
            namespaces.add(p.stem if len(p.parts) == 1 else p.parts[0])

        for rel_path, af in self.analyzed_files.items():
            if rel_path.suffix == '.py' and af.is_text:
                af.imports = FileParsers.parse_python(af.path_abs, af.content, namespaces)

        for rel_path, af in self.analyzed_files.items():
            if not af.imports: continue

            resolved_imports = set()
            for imp in af.imports:
                # Try direct file match (src/utils.py)
                as_file = imp.with_suffix('.py')
                if as_file in py_paths:
                    resolved_imports.add(as_file)
                    self.analyzed_files[as_file].imported_by.add(rel_path)

                # Try init match (src/utils/__init__.py)
                as_init = imp / '__init__.py'
                if as_init in py_paths:
                    resolved_imports.add(as_init)
                    self.analyzed_files[as_init].imported_by.add(rel_path)

            af.imports = resolved_imports


# ==============================================================================
# 7. PROMPT COMPOSER (THE ARCHITECT)
# ==============================================================================

class PromptComposer:
    """Assembles the final markdown prompt document."""

    def __init__(self, analyzer: RepoAnalyzer):
        self.analyzer = analyzer

    def _build_tree(self) -> str:
        """Builds ASCII tree representation of all non-ignored files."""
        if not self.analyzer.all_rel_paths:
            return "(No files found)"

        tree_dict = {}
        for rel_path in self.analyzer.all_rel_paths:
            parts = list(rel_path.parts)
            curr = tree_dict
            for i, part in enumerate(parts):
                is_last = (i == len(parts) - 1)
                if part not in curr:
                    curr[part] = 'file' if is_last else {}
                if not is_last:
                    if curr[part] == 'file': curr[part] = {}
                    curr = curr[part]

        lines = ["."]

        def format_level(d, prefix=""):
            items = sorted(d.items())
            for i, (name, item) in enumerate(items):
                connector = "└── " if i == len(items) - 1 else "├── "
                lines.append(f"{prefix}{connector}{name}")
                if isinstance(item, dict):
                    format_level(item, prefix + ("    " if i == len(items) - 1 else "│   "))

        format_level(tree_dict)
        return "\n".join(lines)

    def _build_intelligence(self) -> str:
        """Builds the Dependency and Metadata mapping."""
        lines = ["[REPOSITORY INTELLIGENCE]"]

        # Calculate Roles
        entry_points = []
        core_utils = []
        for path, af in self.analyzer.analyzed_files.items():
            if path.suffix != '.py': continue
            if not af.imported_by and af.imports:
                entry_points.append(path)
            if len(af.imported_by) >= 3:
                core_utils.append((path, len(af.imported_by)))

        # Sort utils by popularity
        core_utils.sort(key=lambda x: x[1], reverse=True)

        lines.append("\n## System Entry Points (Top-Level Logic)")
        for ep in sorted(entry_points):
            lines.append(f"- {ep.as_posix()}")
        if not entry_points: lines.append("- (None detected)")

        lines.append("\n## Core Utilities (Highly Imported)")
        for path, count in core_utils:
            lines.append(f"- {path.as_posix()} (Imported by {count} files)")
        if not core_utils: lines.append("- (None detected)")

        lines.append("\n## Internal Dependency Map (Forward Index)")
        has_deps = False
        for path, af in sorted(self.analyzer.analyzed_files.items()):
            if af.imports:
                has_deps = True
                deps = [p.as_posix() for p in sorted(af.imports)]

                # Check for circular deps
                circular = []
                for d in af.imports:
                    if path in self.analyzer.analyzed_files[d].imports:
                        circular.append(d.as_posix())

                circ_flag = f" [CIRCULAR: {', '.join(circular)}]" if circular else ""
                lines.append(f"- {path.as_posix()} -> {deps}{circ_flag}")
        if not has_deps: lines.append("- (No internal imports detected)")

        lines.append("\n## Data File Metadata (Binary Overviews)")
        has_meta = False
        for path, af in sorted(self.analyzer.analyzed_files.items()):
            if af.metadata:
                has_meta = True
                lines.append(f"- {path.as_posix()}: {af.metadata}")
        if not has_meta: lines.append("- (No binary files analyzed)")

        return "\n".join(lines)

    def _build_contents(self) -> str:
        """Builds directory-grouped file contents."""
        lines = ["[FILE CONTENTS]\n"]

        # Group text and notebook files by parent directory
        grouped_files: Dict[Path, List[AnalyzedFile]] = {}
        for path, af in self.analyzer.analyzed_files.items():
            if af.is_text or af.is_notebook:
                dir_path = path.parent
                grouped_files.setdefault(dir_path, []).append(af)

        for dir_path in sorted(grouped_files.keys()):
            dir_str = dir_path.as_posix() if str(dir_path) != "." else "Root"
            lines.append(f"### Directory: {dir_str}\n")

            for af in sorted(grouped_files[dir_path], key=lambda x: x.path_rel):
                lang = EXT_TO_LANG.get(af.extension, af.extension)

                # Dynamic backticks to prevent escaping
                longest_ticks = 0
                for match in re.finditer(r"`{3,}", af.content):
                    longest_ticks = max(longest_ticks, len(match.group(0)))
                wrapper_ticks = "`" * max(4, longest_ticks + 1)

                lines.append(f"--- File: {af.path_rel.as_posix()} ---")
                lines.append(f"{wrapper_ticks}{lang}")
                lines.append(af.content)
                lines.append(f"{wrapper_ticks}")
                lines.append(f"--- End of File: {af.path_rel.as_posix()} ---\n")

        return "\n".join(lines)

    def build(self) -> str:
        """Assembles the final document."""
        print("Assembling final prompt...")
        prompt = [
            "System Prompt:",
            "You will be provided with a snapshot of a repository. "
            "Your task is to thoroughly understand its architecture, dependencies, and logic.",
            "Use the [REPOSITORY INTELLIGENCE] section as a map to understand how components link together.",
            "Pay close attention to binary metadata and truncation indicators when interpreting data processing pipelines.\n",
            "[REPOSITORY TREE]",
            "````",
            self._build_tree(),
            "````\n",
            self._build_intelligence(),
            "\n",
            self._build_contents(),
            "\n" + "=" * 60,
            "END OF REPOSITORY SNAPSHOT",
            "=" * 60,
            "\nThe repository context has been fully loaded. Please acknowledge receipt of this snapshot and await my specific questions or instructions regarding this codebase. Note that the codebase is included in the prompt and is (most likely) not in your code sandbox, if one has been made available to you."
        ]
        return "\n".join(prompt)


# ==============================================================================
# 8. EXECUTION SCRIPT
# ==============================================================================

if __name__ == "__main__":
    try:
        print("=" * 50)
        print("Starting Repository Intelligence Flattener (v2.0)")
        print("=" * 50)

        if not REPO_PATH.is_dir():
            raise ValueError(f"Target repository not found: {REPO_PATH.resolve()}")

        # 1. Scan and Analyze
        analyzer = RepoAnalyzer(REPO_PATH)
        analyzer.scan()

        # 2. Compose Prompt
        composer = PromptComposer(analyzer)
        final_prompt = composer.build()

        # 3. Save
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write(final_prompt)

        # 4. Per-file token breakdown
        print("\nIncluded File Contents (path, estimated 'tokens'):")
        # Filter for files that had actual text/notebook content appended
        content_files = [af for af in analyzer.analyzed_files.values() if (af.is_text or af.is_notebook) and af.content]

        if content_files:
            # Calculate column widths, clamping the path to a max of 60 characters
            MAX_PATH_WIDTH = 60
            max_actual_length = max((len(af.path_rel.as_posix()) for af in content_files), default=15)
            path_width = min(max_actual_length, MAX_PATH_WIDTH)
            token_width = 12

            # Print Table Header
            table_width = path_width + token_width + 3
            print("-" * table_width)
            print(f"{'Included File Path':<{path_width}} | {'Tokens':>{token_width}}")
            print("-" * table_width)

            # Sort by token count descending
            for af in sorted(content_files, key=lambda x: x.tokens, reverse=True):
                path_str = af.path_rel.as_posix()

                # Smart truncate from the left if the path is too long (keeps the filename visible)
                if len(path_str) > MAX_PATH_WIDTH:
                    path_str = "..." + path_str[-(MAX_PATH_WIDTH - 3):]

                print(f"{path_str:<{path_width}} | {af.tokens:>{token_width},}")

            print("-" * table_width)
        else:
            print("  (No files were included based on the filtering criteria)")

        # 5. Final Stats
        total_tokens = Sanitizer.estimate_tokens(final_prompt)
        # ASCII only: emoji here dies with UnicodeEncodeError when stdout is
        # redirected on Windows (cp1252), and would take the run down with it
        print("System prompt generated successfully!")
        print(f"Output File: {OUTPUT_FILENAME}")
        print(f"Total Estimated Prompt Tokens: ~{total_tokens:,}")
        print("=" * 50)

    except Exception as e:
        print(f"\nError during execution: {e}")
        import traceback

        traceback.print_exc()
