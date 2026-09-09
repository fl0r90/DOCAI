import re
from typing import List, Dict, Any, Optional

class SemanticChunker:
    """
    Forensic Document Chunker (v0.7.1):
    - Structure & Markdown Aware (Headings, Paragraphs, Lists, Tables).
    - Table Preservation: Tables <= max_chunk_size remain 100% intact.
      Consecutive table blocks (split across page/newlines) are cleanly merged.
      Large tables repeat column header on every slice.
    - Never slices across words, dates, or numbers.
    - Contextual header breadcrumbs: [Doc: <filename> | <Header Path>].
    - Hierarchical Parent-Child chunk generation for forensic RAG.
    """
    def __init__(
        self,
        target_chunk_size: int = 1500,
        max_chunk_size: int = 2500,
        chunk_overlap: int = 200,
        parent_chunk_size: int = 4500
    ):
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        self.parent_chunk_size = parent_chunk_size

    def is_table_block(self, text: str) -> bool:
        """Returns True if text appears to be a markdown table or table fragment."""
        lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
        if not lines:
            return False
        # If all or nearly all lines contain '|'
        pipe_lines = sum(1 for l in lines if '|' in l)
        return pipe_lines >= 1 and (pipe_lines / len(lines)) >= 0.7

    def merge_table_blocks(self, raw_blocks: List[str]) -> List[str]:
        """Merges consecutive table blocks that were separated by newlines."""
        merged = []
        for block in raw_blocks:
            b_str = block.strip()
            if not b_str:
                continue
            if merged and self.is_table_block(merged[-1]) and self.is_table_block(b_str):
                # If combined size is within parent/max size, combine them
                if len(merged[-1]) + len(b_str) + 1 <= self.max_chunk_size:
                    merged[-1] = merged[-1] + "\n" + b_str
                else:
                    merged.append(b_str)
            else:
                merged.append(b_str)
        return merged

    def chunk_table(self, table_text: str, context_header: str = "") -> List[str]:
        """Keeps small/medium tables whole. Slices large tables while repeating table header."""
        lines = [line for line in table_text.strip().split('\n') if line.strip()]
        if not lines:
            return []

        # If table fits within max_chunk_size, return it whole with context header
        full_table = (context_header + "\n\n" if context_header else "") + table_text.strip()
        if len(full_table) <= self.max_chunk_size:
            return [full_table]

        # Table is large: extract table header (first 2 lines if standard markdown table)
        header_lines = lines[:2]
        header_text = "\n".join(header_lines) + "\n"
        data_lines = lines[2:]

        chunks = []
        current_rows = []
        prefix = (context_header + "\n\n" if context_header else "") + header_text
        current_len = len(prefix)

        for row in data_lines:
            row_len = len(row) + 1
            if current_len + row_len > self.target_chunk_size and current_rows:
                chunk_content = prefix + "\n".join(current_rows)
                chunks.append(chunk_content)
                current_rows = [row]
                current_len = len(prefix) + row_len
            else:
                current_rows.append(row)
                current_len += row_len

        if current_rows:
            chunk_content = prefix + "\n".join(current_rows)
            chunks.append(chunk_content)

        return chunks

    def split_narrative(self, text: str, context_header: str = "") -> List[str]:
        """Splits narrative text on paragraphs, sentences, or lines with overlap."""
        text = text.strip()
        if not text:
            return []

        full_text = (context_header + "\n\n" if context_header else "") + text
        if len(full_text) <= self.max_chunk_size:
            return [full_text]

        # Split into paragraphs
        paragraphs = re.split(r'\n{2,}', text)
        chunks = []
        current_paras = []
        prefix = (context_header + "\n\n" if context_header else "")
        current_len = len(prefix)

        for p in paragraphs:
            p = p.strip()
            if not p:
                continue

            p_len = len(p) + 2
            # If paragraph itself is too large, split by sentences
            if p_len > self.target_chunk_size:
                if current_paras:
                    chunks.append(prefix + "\n\n".join(current_paras))
                    current_paras = []
                    current_len = len(prefix)

                sentences = re.split(r'(?<=[.!?])\s+', p)
                curr_sents = []
                curr_sent_len = len(prefix)
                for s in sentences:
                    s_len = len(s) + 1
                    if curr_sent_len + s_len > self.target_chunk_size and curr_sents:
                        chunks.append(prefix + " ".join(curr_sents))
                        overlap_sents = curr_sents[-1:] if len(curr_sents[-1]) < self.chunk_overlap else []
                        curr_sents = overlap_sents + [s]
                        curr_sent_len = len(prefix) + sum(len(x) + 1 for x in curr_sents)
                    else:
                        curr_sents.append(s)
                        curr_sent_len += s_len
                if curr_sents:
                    chunks.append(prefix + " ".join(curr_sents))
            elif current_len + p_len > self.target_chunk_size and current_paras:
                chunks.append(prefix + "\n\n".join(current_paras))
                overlap_p = current_paras[-1:] if len(current_paras[-1]) < self.chunk_overlap else []
                current_paras = overlap_p + [p]
                current_len = len(prefix) + sum(len(x) + 2 for x in current_paras)
            else:
                current_paras.append(p)
                current_len += p_len

        if current_paras:
            chunks.append(prefix + "\n\n".join(current_paras))

        return chunks

    def chunk_markdown(
        self,
        markdown_text: str,
        filename: str = "",
        page_no: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Parses Markdown document hierarchically by headings (#, ##, ###),
        identifies tables vs narrative text, merges table blocks, and yields semantic chunks
        with parent-child hierarchy.
        
        Returns a list of chunk dicts:
        {
            "chunk_index": int,
            "content": str,         # Child content (for embedding and vector search)
            "parent_content": str,  # Parent content (for broad context during LLM synthesis)
            "is_table": bool,
            "header_path": str,
            "page_number": int
        }
        """
        if not markdown_text or not markdown_text.strip():
            return []

        lines = markdown_text.split('\n')
        sections = []
        current_header_hierarchy = []
        current_section_lines = []

        def get_header_path():
            return " > ".join(current_header_hierarchy) if current_header_hierarchy else ""

        for line in lines:
            header_match = re.match(r'^(#{1,4})\s+(.+)$', line.strip())
            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2).strip()

                if current_section_lines:
                    sections.append({
                        "header_path": get_header_path(),
                        "text": "\n".join(current_section_lines).strip()
                    })
                    current_section_lines = []

                if level <= len(current_header_hierarchy):
                    current_header_hierarchy = current_header_hierarchy[:level-1]
                current_header_hierarchy.append(title)
            else:
                current_section_lines.append(line)

        if current_section_lines:
            sections.append({
                "header_path": get_header_path(),
                "text": "\n".join(current_section_lines).strip()
            })

        final_chunks = []
        chunk_idx = 0

        for sec in sections:
            sec_text = sec["text"].strip()
            if not sec_text:
                continue

            header_path = sec["header_path"]
            context_header = f"[Doc: {filename} | {header_path}]" if (filename and header_path) else (
                f"[Doc: {filename}]" if filename else (f"[{header_path}]" if header_path else "")
            )

            # Split by double newlines into blocks and merge consecutive table blocks
            raw_blocks = re.split(r'\n{2,}', sec_text)
            blocks = self.merge_table_blocks(raw_blocks)

            accumulated_narrative = []
            accumulated_len = len(context_header)

            def flush_accumulated_narrative():
                nonlocal accumulated_narrative, accumulated_len, chunk_idx
                if not accumulated_narrative:
                    return
                combined_text = "\n\n".join(accumulated_narrative)
                parent_content = (context_header + "\n\n" if context_header else "") + combined_text
                text_chunks = self.split_narrative(combined_text, context_header=context_header)
                for ntc in text_chunks:
                    final_chunks.append({
                        "chunk_index": chunk_idx,
                        "content": ntc,
                        "parent_content": parent_content,
                        "is_table": False,
                        "header_path": header_path,
                        "page_number": page_no
                    })
                    chunk_idx += 1
                accumulated_narrative = []
                accumulated_len = len(context_header)

            for block in blocks:
                block = block.strip()
                if not block:
                    continue

                if self.is_table_block(block):
                    flush_accumulated_narrative()
                    parent_table_content = (context_header + "\n\n" if context_header else "") + block
                    table_chunks = self.chunk_table(block, context_header=context_header)
                    for tc in table_chunks:
                        final_chunks.append({
                            "chunk_index": chunk_idx,
                            "content": tc,
                            "parent_content": parent_table_content,
                            "is_table": True,
                            "header_path": header_path,
                            "page_number": page_no
                        })
                        chunk_idx += 1
                else:
                    block_len = len(block) + 2
                    if accumulated_len + block_len > self.target_chunk_size and accumulated_narrative:
                        flush_accumulated_narrative()
                    accumulated_narrative.append(block)
                    accumulated_len += block_len

            flush_accumulated_narrative()

        return final_chunks

semantic_chunker = SemanticChunker()
