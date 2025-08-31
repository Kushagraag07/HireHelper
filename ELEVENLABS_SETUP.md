# ElevenLabs Integration Setup Guide

## Overview

The HireHelper interview system now supports ElevenLabs for natural-sounding AI voices. This replaces the robotic browser speech synthesis with high-quality, human-like voices that are perfect for professional interviews.

## Quick Setup

### 1. Get ElevenLabs API Key

1. Visit [ElevenLabs](https://elevenlabs.io/)
2. Sign up for a free account
3. Navigate to your profile settings
4. Copy your API key

### 2. Configure Environment

1. In the `frontend` directory, create a `.env.local` file
2. Add your API key:
```bash
NEXT_PUBLIC_ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

### 3. Restart Development Server

```bash
# Stop the current server (Ctrl+C)
# Then restart
pnpm dev
```

## Available Voices

The system includes several professional voices optimized for interviews:

- **Rachel** (Default) - Professional female voice, warm and engaging
- **Domi** - Professional male voice, clear and authoritative  
- **Bella** - Friendly female voice, approachable and conversational
- **Arnold** - Professional male voice, confident and clear

## Features

### Voice Selection
- Users can choose their preferred AI interviewer voice during setup
- Voice selection is part of the interview preparation process
- Selected voice persists throughout the entire interview session

### Voice Testing
- Users can test each voice before selecting
- Click the test button next to each voice option
- Hear a sample: "Hello! This is a test of my voice. How do I sound?"

### Fallback Support
- If ElevenLabs is unavailable, the system automatically falls back to browser speech synthesis
- No interruption to the interview experience
- Clear indication when fallback is being used

### Professional Quality
- Much more natural and engaging than standard TTS
- Optimized for interview scenarios
- Reduces user fatigue and improves engagement

## Usage in Interviews

1. **Setup Phase**: Users select their preferred voice during interview preparation
2. **Interview Phase**: The selected voice is used for all AI interviewer responses
3. **Voice Indicator**: The current voice is displayed in the interview interface
4. **Consistent Experience**: Same voice throughout the entire session

## Troubleshooting

### API Key Issues
- Ensure the API key is correctly copied from ElevenLabs dashboard
- Check that the environment variable is properly set
- Restart the development server after adding the API key

### Voice Not Working
- Check browser console for error messages
- Verify ElevenLabs service status
- The system will automatically fall back to browser TTS if needed

### Performance Issues
- ElevenLabs responses may take 1-2 seconds to generate
- Audio quality is much higher than browser TTS
- Consider this trade-off for better user experience

## Cost Considerations

- ElevenLabs offers a free tier with 10,000 characters per month
- Typical interview uses approximately 500-1000 characters
- Free tier supports ~10-20 interviews per month
- Paid plans available for higher usage

## Security

- API key is stored in environment variables (not in code)
- No voice data is stored or transmitted beyond ElevenLabs
- All communication is encrypted via HTTPS
- API key should never be committed to version control

## Support

If you encounter issues:
1. Check the browser console for error messages
2. Verify your ElevenLabs API key is valid
3. Ensure you have sufficient character credits
4. Check ElevenLabs service status at their website
