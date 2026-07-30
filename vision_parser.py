import base64
import json
import streamlit as st
from anthropic import Anthropic

def parse_floorplan_with_claude(uploaded_file):
    """
    Parse a floorplan image using Claude Vision.
    Returns extracted room data as a Python list/dict or an error message.
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

        # Get Claude's text output
        result_text = response.content[0].text

        # Try to parse JSON output
        try:
            room_data = json.loads(result_text)
            return room_data
        except json.JSONDecodeError:
            # If Claude returns plain text instead of JSON
            return {"error": "Claude response not valid JSON", "raw": result_text}

    except Exception as e:
        # Fallback if Claude Vision fails
        return {"error": f"Claude Vision unavailable: {str(e)}"}


def show_rooms(room_data):
    """
    Display extracted room data neatly in Streamlit.
    """
    if isinstance(room_data, list):
        st.subheader("Extracted Room Data")
        st.table(room_data)  # Shows Room | Area_m2 neatly
    else:
        st.error("Could not parse room data")
        st.write(room_data)


