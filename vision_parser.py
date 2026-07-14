import base64
import streamlit as st
from anthropic import Anthropic

def parse_floorplan_with_claude(uploaded_file):
    """
    Parse a floorplan image using Claude Vision.
    Returns extracted room data or an error message.
    """

    # Initialize Anthropic client with your API key from secrets.toml
    client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

    # Convert uploaded file to base64
    file_bytes = uploaded_file.read()
    encoded_image = base64.b64encode(file_bytes).decode("utf-8")

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extract room names and their areas (in m²) "
                                "from this floorplan image. Return the result "
                                "as a JSON list like: "
                                "[{\"room\": \"Living Room\", \"area_m2\": 20}, ...]"
                            )
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": encoded_image
                            }
                        }
                    ]
                }
            ]
        )

        # Return Claude's text output
        return response.content[0].text

    except Exception as e:
        # Fallback if Claude Vision fails
        return {"error": f"Claude Vision unavailable: {str(e)}"}

