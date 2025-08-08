from typing import Optional


def _itinerary_editing_prompt(itinerary_edit_limit: int) -> Optional[str]:
    """Edit the workflow itinerary."""
    return (
        "You may use the `_edit_itinerary` output_type function to insert additional steps "
        "into the workflow after executing your logic. "
        f"You are allowed up to {itinerary_edit_limit} insertions. "
        "Inspect ctx.activity_registry for available agents and their prompts. "
        "Don't add agents that are not in the activity registry. "
        "Only add agents if you are prompted to do so."
    )
