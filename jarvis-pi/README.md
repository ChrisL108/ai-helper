# Jarviz

This repository contains the code for the Jarvis project, which includes a personal AI assistant and a web interface built with Next.js.

## Project Structure

- **jarvis-pi**: Contains the code for the AI assistant, which includes voice recognition, text-to-speech, and command processing.
- **jarviz**: (Coming Soon) - Electron desktop app for interacting with the assistant.

## Getting Started

### Prerequisites

- Python 3.x

### Setting Up the Python Environment

1. **Create a Virtual Environment**

   It's recommended to create a virtual environment to manage dependencies. You can create one named `venv`:

   ```bash
   python -m venv venv
   ```

2. **Activate the Virtual Environment**

   - On Windows:

     ```bash
     .\venv\Scripts\activate
     ```

   - On macOS and Linux:

     ```bash
     source venv/bin/activate
     ```

3. **Install Python Dependencies**

   Navigate to the `jarvis-pi` directory and install the required packages:

   ```bash
   cd jarvis-pi
   pip install -r requirements.txt
   ```

4. **Set Environment Variables**

   Ensure you set the appropriate environment variables in your virtual environment. You can do this by creating a `.env` file in the `jarvis-pi` directory with the necessary variables, such as `YOUTUBE_API_KEY` and `OPENAI_API_KEY`.


## Learn More

To learn more about the technologies used in this project, check out the following resources:

- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
