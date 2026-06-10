from ..models import Promo, Show, Episode
from .lm_studio import lm_studio_client


class PromoGenerator:
    """Orchestrates promo generation using LM Studio and FFmpeg."""

    async def generate(
        self,
        show: Show,
        episode: Episode | None,
        ad_type: str,
        duration: float,
        aspect_ratio: str,
        mode: str,
        options: dict | None = None,
    ) -> dict:
        """
        Generate a promo for the given show/episode.

        Steps:
        1. Analyze source content
        2. Generate script using LM Studio
        3. Select key moments from episode
        4. Assemble timeline
        5. Render output with FFmpeg
        """
        # Step 1: Build prompt for LM Studio
        prompt = self._build_prompt(show, episode, ad_type, duration)

        # Step 2: Get AI-generated script
        try:
            script = await lm_studio_client.generate_completion(prompt)
        except Exception as e:
            return {"status": "failed", "error": str(e)}

        # Step 3-5: Would involve video processing with FFmpeg
        # This is a placeholder for the full pipeline
        return {
            "status": "processing",
            "script": script,
            "ad_type": ad_type,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
        }

    def _build_prompt(
        self,
        show: Show,
        episode: Episode | None,
        ad_type: str,
        duration: float,
    ) -> str:
        """Build the LM Studio prompt for promo script generation."""
        episode_info = f" for episode '{episode.title}'" if episode else ""
        return (
            f"Generate a {duration}-second {ad_type} promotional script "
            f"for the show '{show.name}'{episode_info}. "
            f"Include timing cues, suggested visuals, and text overlays. "
            f"Format as a structured timeline."
        )


promo_generator = PromoGenerator()
