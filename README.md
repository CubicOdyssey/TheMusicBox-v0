# NFC Music Box

A Raspberry Pi-powered music box that plays audio files when NFC tags are detected. The system allows you to associate NFC tags with music files and control playback using physical buttons.

## Features

- NFC tag detection and music playback
- Physical button controls for volume and play/pause
- Automatic playback when NFC tag is present
- Automatic stop when NFC tag is removed
- Support for multiple audio formats (MP3, WAV, OGG, FLAC)
- Volume control with up/down buttons
- Play/pause toggle button
- Thread-safe audio playback management
- Persistent NFC tag to audio file associations

## Hardware Requirements

- Raspberry Pi (any model with GPIO pins)
- PN532 NFC/RFID controller (I2C configuration)
- Push buttons (x3)
- NFC tags
- Speakers or audio output device

## Software Requirements

```
RPi.GPIO==0.7.1
pygame==2.5.2
adafruit-circuitpython-pn532==2.4.2
rx==3.2.0 
python-dotenv==1.0.0
adafruit-blinka==8.32.0
```

## Installation

1. Clone this repository:
```bash
git clone [repository-url]
cd nfc-music-box
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Connect the hardware:
   - Connect the PN532 NFC reader to the I2C pins (SCL and SDA)
   - Connect buttons to GPIO pins:
     - Volume Up: GPIO 22
     - Volume Down: GPIO 27
     - Play/Pause: GPIO 17

4. Create a `music` directory in the project root and add your audio files:
```bash
mkdir music
```

## Usage

### 1. Associate NFC Tags with Music Files

Run the association script to link NFC tags with your music files:

```bash
python association.py
```

Follow the on-screen instructions to scan NFC tags for each music file. The associations will be saved in `nfc_data.json`.

### 2. Run the Music Box

Start the main application:

```bash
python app.py
```

The system will now:
- Detect NFC tags when present
- Play associated audio files automatically
- Respond to button controls for volume and playback
- Stop playback when tags are removed

### Controls

- **Volume Up Button (GPIO 22)**: Increases volume by 10%
- **Volume Down Button (GPIO 27)**: Decreases volume by 10%
- **Play/Pause Button (GPIO 17)**: Toggles between play and pause states

## Project Structure

- `app.py`: Main application with audio playback and NFC detection logic
- `association.py`: Tool for associating NFC tags with audio files
- `nfc_data.json`: Stores NFC tag to audio file mappings
- `requirements.txt`: Python package dependencies

## Technical Details

### Audio Player Features

- Thread-safe command queue for audio operations
- State management (PLAYING, PAUSED, STOPPED)
- Volume control (0-100%)
- Automatic cleanup on exit

### NFC Detection

- Continuous scanning for NFC tags
- Debouncing and cooldown periods
- Error handling for failed reads
- Support for multiple tag formats

## Troubleshooting

1. **NFC Reader Not Detected**
   - Check I2C connections
   - Verify I2C is enabled in Raspberry Pi configuration
   - Ensure correct permissions for I2C device

2. **Audio Not Playing**
   - Check audio output configuration
   - Verify file paths in `nfc_data.json`
   - Check file format compatibility

3. **Buttons Not Responding**
   - Verify GPIO pin connections
   - Check for correct pull-up/pull-down resistor configuration
   - Verify button cooldown period

## Contributing

Contributions are welcome! Please feel free to submit pull requests or create issues for bugs and feature requests.

## License
MIT

## Acknowledgements

- Built using Adafruit's PN532 library
- Pygame for audio playback
- RPi.GPIO for button control