from typing import List, Optional

class PromptChunker:
    """Splits large review packets into manageable chunks for LLMs."""

    def __init__(self, max_tokens: int = 15000):
        # Rough estimation: 1 token ~= 4 characters for code
        self.max_chars = max_tokens * 4

    def chunk_packet(self, packet_md: str) -> List[str]:
        """Split a packet into multiple parts if it exceeds the token budget."""
        if len(packet_md) <= self.max_chars:
            return [packet_md]

        chunks = []
        current_chunk = []
        current_len = 0

        # Split by lines to keep markdown structure mostly intact
        for line in packet_md.splitlines():
            if current_len + len(line) + 1 > self.max_chars:
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                    current_len = 0
            
            current_chunk.append(line)
            current_len += len(line) + 1

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        # Add index information to chunks
        final_chunks = []
        total = len(chunks)
        for i, content in enumerate(chunks):
            header = f"## Packet Chunk {i+1} of {total}\n\n"
            final_chunks.append(header + content)

        return final_chunks
