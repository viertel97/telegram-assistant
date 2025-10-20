import json
from datetime import datetime
from quarter_lib.logging import setup_logging

logger = setup_logging(__file__)


def export_to_obsidian(messages, metadata, output_path='conversation.md'):
	"""
	Exports the conversation messages and metadata to a Markdown file formatted for Obsidian.
	"""
	# YAML frontmatter
	md_lines = ["---"]
	for key, value in metadata.items():
		# format datetime fields
		if key in ("create_time", "update_time") and isinstance(value, (int, float)):
			value = datetime.fromtimestamp(value).isoformat()
		md_lines.append(f"{key}: {json.dumps(value)}")
	md_lines.append("---")

	# Headline from metadata title
	title = metadata.get("title", "Conversation")
	md_lines.append(f"# {title}\n")

	# conversation
	for msg in messages:
		role = msg["author"]["role"]
		author = "User" if role == "user" else "Assistant"
		# convert message timestamp to human-readable
		ts = msg.get("create_time")
		try:
			timestamp = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
		except Exception:
			timestamp = str(ts)
		# message content
		content_parts = msg.get("content", {}).get("parts", [])
		corrected_content_parts = []
		for i, part in enumerate(content_parts):
			if isinstance(part, dict) and "text" in part:
				corrected_content_parts.append(part["text"])
			elif isinstance(part, dict):
				logger.info(f"Skipping dict part without text: {part}")
			elif isinstance(part, str):
				corrected_content_parts.append(part)
			else:
				logger.info(f"Skipping unknown part type: {part}")

		content = "\n".join(corrected_content_parts).strip()
		# format entry with blockquote for metadata
		md_lines.append(f"> **{author}**, {timestamp}\n")
		md_lines.append(f"{content}\n")

	return "\n".join(md_lines)