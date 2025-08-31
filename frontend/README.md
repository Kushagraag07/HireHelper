# HireHelper Frontend

## ElevenLabs Integration

This project now includes ElevenLabs integration for natural-sounding AI voices during interviews. The AI interviewer will use high-quality, human-like voices instead of the browser's robotic speech synthesis.

### Setup

1. **Get an ElevenLabs API Key:**
   - Visit [ElevenLabs](https://elevenlabs.io/)
   - Sign up for a free account
   - Get your API key from the dashboard

2. **Configure the API Key:**
   - Create a `.env.local` file in the frontend directory
   - Add your API key:
   ```
   NEXT_PUBLIC_ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
   ```

3. **Available Voices:**
   - **Rachel** (Default) - Professional female voice, perfect for interviews
   - **Domi** - Professional male voice, clear and authoritative
   - **Bella** - Friendly female voice, warm and approachable
   - **Arnold** - Professional male voice, confident and clear

### Features

- **Voice Selection:** Users can choose their preferred AI interviewer voice during setup
- **Fallback Support:** If ElevenLabs is unavailable, the system falls back to browser speech synthesis
- **Professional Quality:** Much more natural and engaging than standard TTS
- **Interview-Optimized:** Voices are specifically chosen for professional interview scenarios

### Usage

During the interview setup process, users will see a "Voice Selection" step where they can choose their preferred AI interviewer voice. The selected voice will be used throughout the entire interview session.

## Development

```bash
# Install dependencies
pnpm install

# Run development server
pnpm dev

# Build for production
pnpm build
```
