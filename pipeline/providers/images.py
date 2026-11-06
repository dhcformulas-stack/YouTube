"""Image providers: one still per ``[VISUAL: ...]`` cue.

Online uses the OpenAI Images API (``OPENAI_API_KEY``). The API returns either
base64 (``b64_json``, gpt-image-1) or a URL (dall-e-3); both are handled.
Offline renders labelled Pillow placeholder frames so assembly has real pixels
to encode.
"""

from __future__ import annotations

import base64
import os
import textwrap

from ..config import Settings
from .base import ImageProvider, ProviderError, get_bytes, post_json

DEFAULT_STYLE = (
    "cinematic documentary still, historically accurate detail, dramatic natural "
    "lighting, shallow depth of field, 16:9 composition, muted archival colour "
    "grade, no text, no watermarks"
)


class OpenAIImageProvider(ImageProvider):
    name = "openai-images"
    requires_key = "OPENAI_API_KEY"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = settings.image_model
        self.style = os.environ.get("IMAGE_STYLE", DEFAULT_STYLE)

    def generate(
        self,
        prompt: str,
        output_path: str,
        chapter_title: str = "",
        scene_index: int = 0,
    ) -> str:
        full_prompt = f"{prompt}. Style: {self.style}"
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "size": self.settings.image_size,
            "n": 1,
        }
        # gpt-image-1 accepts quality; dall-e-3 uses "standard"/"hd".
        payload["quality"] = self.settings.image_quality
        data = post_json(
            f"{self.settings.openai_base_url}/images/generations",
            payload,
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.settings.http_timeout,
            retries=self.settings.max_retries,
        )
        items = data.get("data") or []
        if not items:
            raise ProviderError("Image API returned no data")
        item = items[0]
        if item.get("b64_json"):
            raw = base64.b64decode(item["b64_json"])
        elif item.get("url"):
            raw = get_bytes(item["url"], timeout=self.settings.http_timeout)
        else:
            raise ProviderError("Image API returned neither b64_json nor url")
        with open(output_path, "wb") as fh:
            fh.write(raw)
        return output_path


class OfflineImageProvider(ImageProvider):
    """Labelled Pillow placeholder frame at the configured video resolution."""

    name = "offline-placeholder"
    model = "pillow"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.width = settings.video_width
        self.height = settings.video_height

    def _font(self, size: int):
        from PIL import ImageFont

        for candidate in (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ):
            if os.path.exists(candidate):
                try:
                    return ImageFont.truetype(candidate, size)
                except OSError:  # pragma: no cover - unreadable font file
                    continue
        return ImageFont.load_default()

    def generate(
        self,
        prompt: str,
        output_path: str,
        chapter_title: str = "",
        scene_index: int = 0,
    ) -> str:
        from PIL import Image, ImageDraw

        width, height = self.width, self.height
        image = Image.new("RGB", (width, height), (14, 18, 28))
        draw = ImageDraw.Draw(image)

        # Simple vertical gradient so the frame is not a flat colour.
        for y in range(height):
            shade = int(14 + (y / height) * 34)
            draw.line([(0, y), (width, y)], fill=(shade, shade + 4, shade + 14))

        margin = int(width * 0.08)
        title_font = self._font(max(20, width // 34))
        body_font = self._font(max(18, width // 46))
        small_font = self._font(max(14, width // 70))

        draw.text(
            (margin, margin),
            "OFFLINE PLACEHOLDER — NOT FOR PUBLICATION",
            font=small_font,
            fill=(220, 120, 90),
        )

        y = margin + int(height * 0.14)
        if chapter_title:
            for line in textwrap.wrap(chapter_title, width=42):
                draw.text((margin, y), line, font=title_font, fill=(235, 238, 245))
                y += int(title_font.size * 1.35) if hasattr(title_font, "size") else 40
            y += int(height * 0.04)

        wrapped = textwrap.wrap(prompt, width=56) or ["(no cue text)"]
        for line in wrapped[:8]:
            draw.text((margin, y), line, font=body_font, fill=(180, 190, 210))
            y += int(body_font.size * 1.4) if hasattr(body_font, "size") else 32

        draw.text(
            (margin, height - margin - 24),
            f"scene {scene_index:03d}",
            font=small_font,
            fill=(120, 132, 155),
        )
        draw.rectangle(
            [(0, height - 8), (width, height)],
            fill=(200, 100, 70),
        )

        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
        image.save(output_path, format="PNG")
        return output_path


__all__ = ["OpenAIImageProvider", "OfflineImageProvider", "DEFAULT_STYLE"]
