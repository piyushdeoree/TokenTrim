"""Provider-specific official pricing page adapters."""
from .openai import parse_openai_pricing
from .anthropic import parse_anthropic_pricing
from .google import parse_google_pricing

PARSERS={"openai":parse_openai_pricing,"anthropic":parse_anthropic_pricing,"google":parse_google_pricing}
