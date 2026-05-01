import os
import logging
from pathlib import Path
from sys import path as sys_path

sys_path.insert(0, str(Path(__file__).parent.parent))

from models.schemas import RetrievedChunk

logger = logging.getLogger(__name__)

CHUNK_SIZE = 400
CHUNK_OVERLAP = 80


def _clean_markdown(text: str) -> str:
    """
    Line-by-line markdown cleaner — no regex on full text,
    zero backtracking risk, proven fast on all 773 files.
    """
    lines = []
    in_code_block = False
    in_frontmatter = False
    frontmatter_done = False
    line_num = 0

    for line in text.splitlines():
        line_num += 1

        # Handle frontmatter (--- block at top)
        if line_num == 1 and line.strip() == '---':
            in_frontmatter = True
            continue
        if in_frontmatter:
            if line.strip() == '---':
                in_frontmatter = False
                frontmatter_done = True
            continue

        # Handle fenced code blocks
        if line.startswith('```'):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Strip markdown headers
        if line.startswith('#'):
            line = line.lstrip('#').strip()

        # Strip HTML tags (simple, bounded)
        clean = []
        i = 0
        in_tag = False
        while i < len(line):
            if line[i] == '<' and i + 1 < len(line):
                in_tag = True
            elif line[i] == '>' and in_tag:
                in_tag = False
                i += 1
                continue
            if not in_tag:
                clean.append(line[i])
            i += 1
        line = ''.join(clean)

        # Strip markdown links [text](url) → text
        result = []
        i = 0
        while i < len(line):
            if line[i] == '[':
                end_bracket = line.find(']', i)
                if end_bracket != -1 and end_bracket + 1 < len(line) and line[end_bracket + 1] == '(':
                    end_paren = line.find(')', end_bracket + 1)
                    if end_paren != -1:
                        result.append(line[i+1:end_bracket])
                        i = end_paren + 1
                        continue
            result.append(line[i])
            i += 1
        line = ''.join(result)

        # Strip bold/italic markers
        line = line.replace('**', '').replace('__', '').replace('`', '')
        # Single * only if surrounded (avoid stripping bullet points)
        if line.startswith('* '):
            line = '- ' + line[2:]

        line = line.strip()
        if line:
            lines.append(line)

    return '\n'.join(lines).strip()


def _chunk_text(text: str, source: str, company: str) -> list[RetrievedChunk]:
    """Split text into overlapping chunks at sentence boundaries."""
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + CHUNK_SIZE, text_len)

        # Try to break at sentence boundary
        if end < text_len:
            for punct in ['. ', '.\n', '? ', '! ', '\n\n', '\n']:
                boundary = text.rfind(punct, start, end)
                if boundary != -1 and boundary > start:
                    end = boundary + len(punct)
                    break

        chunk_text = text[start:end].strip()
        if len(chunk_text) > 50:
            chunks.append(RetrievedChunk(
                content=chunk_text,
                source=source,
                score=0.0,
                company=company,
            ))

        new_start = end - CHUNK_OVERLAP
        if new_start <= start:
            new_start = end
        start = new_start
        if start >= text_len:
            break

    return chunks


def _infer_company(file_path: Path, data_dir: Path) -> str:
    parts = file_path.relative_to(data_dir).parts
    return {
        'claude': 'Claude',
        'hackerrank': 'HackerRank',
        'visa': 'Visa',
    }.get(parts[0].lower(), 'Unknown')


def load_corpus(data_dir: str) -> list[RetrievedChunk]:
    """Load all .md files, clean and chunk them."""
    data_path = Path(data_dir)
    all_chunks: list[RetrievedChunk] = []
    file_count = 0
    skipped = 0

    for md_file in sorted(data_path.rglob('*.md')):
        try:
            text = md_file.read_text(encoding='utf-8', errors='ignore')
            cleaned = _clean_markdown(text)

            if len(cleaned) < 50:
                skipped += 1
                continue

            company = _infer_company(md_file, data_path)
            source = str(md_file.relative_to(data_path))
            chunks = _chunk_text(cleaned, source, company)
            all_chunks.extend(chunks)
            file_count += 1

        except Exception as e:
            logger.warning(f"Failed to load {md_file}: {e}")
            skipped += 1

    logger.info(
        f"Corpus loaded: {file_count} files → "
        f"{len(all_chunks)} chunks ({skipped} skipped)"
    )
    return all_chunks