from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ai-voice-agent")


@mcp.tool()
def get_business_information() -> dict:
    """Return basic demo business information."""
    return {
        "name": "AI Voice Assistant ",
        "services": [
            "General enquiries",
            "Appointment enquiries",
        ],
        "notice": "Demo data; configure real business details before deployment.",
    }


@mcp.tool()
def create_greeting(name: str = "there") -> str:
    """Create a greeting for a caller."""
    clean_name = name.strip()[:80] or "there"
    return f"Hello, {clean_name}! How can I help you today?"


if __name__ == "__main__":
    mcp.run()
