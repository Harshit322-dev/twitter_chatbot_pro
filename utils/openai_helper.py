import logging
from typing import Dict
from openai import OpenAI

from twitter_bot.config import config

logger = logging.getLogger(__name__)

_client = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client

SYSTEM_PROMPT = (
    "You are a helpful, concise social media assistant for a freelancer/web dev/AI tools brand. "
    "Be friendly, add value, avoid spam. Keep replies under 280 characters. Use Indian English tone when appropriate."
)

COMMON_QA = {
    "pricing": "We offer flexible pricing based on scope. Share your requirements and we’ll quote quickly. Starter websites begin around $500.",
    "cost": "Cost depends on features and timeline. Happy to provide a quick estimate—what are you building?",
    "hire": "We’re available for new projects this month. Tell us about your idea and preferred timeline!",
    "available": "Yes—taking on select projects right now. What are you looking to build?",
}


def generate_reply(context: Dict) -> str:
    client = _get_client()
    user_input = context.get("text", "")
    username = context.get("username", "there")
    profile = context.get("profile", "")
    intent_hint = context.get("intent_hint", "")

    hint = "\n".join([f"- {k}: {v}" for k, v in COMMON_QA.items()])
    content = (
        f"User @{username} said: '{user_input}'.\n"
        f"Profile: {profile}\n"
        f"Intent hint: {intent_hint}\n"
        f"Use the following short answers if relevant:\n{hint}"
    )

    try:
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            temperature=0.7,
            max_tokens=180,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        logger.exception("OpenAI reply generation failed; using fallback")
        # Simple fallback
        for k, v in COMMON_QA.items():
            if k in user_input.lower():
                return v
        return f"Thanks @{username}! Appreciate your message—DM us more details and we’ll help."
