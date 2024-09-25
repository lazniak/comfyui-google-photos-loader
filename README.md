# Google Photos Loader for ComfyUI

![Google Photos Loader Example Workflow](Google_photo_loader_example_workflow.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/release/python-370/)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-compatible-brightgreen)](https://github.com/comfyanonymous/ComfyUI)

## Table of Contents

- [Description](#description)
- [Features](#features)
- [Installation](#installation)
- [Setting up Google Photos API](#setting-up-google-photos-api)
- [Usage](#usage)
- [Node Options](#node-options)
- [How to Get Album ID](#how-to-get-album-id)
- [Troubleshooting](#troubleshooting)
- [Dependencies and Licenses](#dependencies-and-licenses)
- [About the Creator](#about-the-creator)
- [License](#license)
- [Contributing](#contributing)
- [Support](#support)
- [To-Do List](#to-do-list)

## Description

The Google Photos Loader for ComfyUI is a custom node that allows users to seamlessly integrate Google Photos into their ComfyUI workflows. This powerful tool enables direct access to your Google Photos library, making it easy to list albums, load images from specific albums, and search for photos based on queries - all within your ComfyUI environment.

## Features

- 📁 List all Google Photos albums
- 🖼️ Load images from a specific album
- 🔍 Search for photos using queries (under development)
- 🛠️ Customize image loading options (size, cropping, etc.)
- 🔄 Sort images by creation time, filename, or randomly
- ⚡ Efficient caching mechanism for improved performance

## Installation

1. Ensure you have ComfyUI installed and set up.
2. Clone this repository into your ComfyUI's `custom_nodes` directory:
   ```bash
   cd /path/to/ComfyUI/custom_nodes
   git clone https://github.com/YourUsername/comfyui-google-photos-loader.git
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Setting up Google Photos API

To use this node, you need to set up a Google Cloud project and enable the Google Photos Library API:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Enable the Google Photos Library API for your project.
4. Create credentials (OAuth 2.0 Client ID) for a desktop application.
5. Download the client configuration and save it as `client_secrets.json` in the same directory as the custom node files.

## Usage

1. In ComfyUI, locate the new node called "Google Photos Images Loader 📷".
2. Drag and drop the node into your workflow canvas.
3. Connect this node to your workflow as needed.
4. Configure the node settings:
   - Choose an action: List Albums, Load from Album, or Search Photos
   - Set the maximum number of images to load
   - Specify size options and sorting criteria
   - For "Load from Album", provide the album ID (see [How to Get Album ID](#how-to-get-album-id))
   - For "Search Photos", enter your search query (feature under development)
5. Run your workflow. The node will authenticate with Google Photos on first use.

## Node Options

- **Action**: Choose between listing albums, loading from an album, or searching photos.
- **Max Images**: Set the maximum number of images to load (1-100).
- **Size Option**: Choose between original size, custom size, or scale to size.
- **Target Width/Height**: Set custom dimensions for resizing.
- **Target Size**: Set the target size for scaling.
- **Use Crop**: Enable/disable cropping to maintain aspect ratio.
- **Sort Criteria**: Sort by creation time or filename.
- **Sort Order**: Choose ascending, descending, or random order.

## How to Get Album ID

To get the Album ID:

1. Set the node's action to "List Albums".
2. Connect the log output to a "Show Text" node.
3. Run the workflow.
4. Scroll down in the "Show Text" node output to see the full list of your library albums with their IDs.
5. Copy the ID of the desired album.
6. Change the node's action to "Load from Album".
7. Paste the copied ID into the "album_id" input of the node.

## Troubleshooting

- If you encounter authentication issues, delete the `token.pickle` file in the node directory and rerun the workflow.
- Ensure your `client_secrets.json` file is correctly placed and formatted.
- Check the ComfyUI console for detailed logs if you enable the "Print Log" option in the node.

## Dependencies and Licenses

This project uses the following main dependencies:

1. **requests** (Apache 2.0 License) - Version: >=2.25.1
2. **Pillow** (HPND License) - Version: >=8.0.0
3. **numpy** (BSD 3-Clause License) - Version: >=1.19.5
4. **torch** (BSD 3-Clause License) - Version: >=1.7.0
5. **google-auth-oauthlib** (Apache 2.0 License) - Version: >=0.4.2
6. **google-auth** (Apache 2.0 License) - Version: >=1.24.0

For full license details, please refer to the individual package repositories.

## About the Creator

This ComfyUI CustomNode was created by Paul Lazniak (Paweł Łaźniak), also known as PabloGFX. Paul is a multifaceted professional with extensive experience in software development, filmmaking, VFX artistry, and entrepreneurship.

### Professional Background

Paul began his career in the early 2000s, working on various projects for prominent Polish TV stations such as MTV, TVN, and TVP. His expertise spans compositing, editing, special effects, and software development.

As an innovator in virtual reality (VR), Paul co-founded the VR Visio Group, which later evolved into Ignibit S.A., one of Poland's leading companies focused on virtual reality and immersive technologies.

### Current Ventures

Paul is currently involved in developing new projects through his companies:

- [HexArt](https://www.hexart.pl/): Combining cinematography with advanced digital technologies
- [Overbuilt Games](https://overbuiltgames.com/): Game development studio
- [Green Cave Studio](https://greencavestudio.com/): Creative digital solutions

### Content Creation and Education

Paul is a Polish-speaking content creator focusing on technology and digital tools. He provides tutorials and guides, particularly on topics such as Stable Diffusion and other AI-based tools.

### Contributions to Film and VR

Paul's contributions to the Polish film industry are documented in the [Polish Film Database](https://filmpolski.pl/fp/index.php?osoba=1162919). He is also known for his thought leadership in digital and virtual realities.

### Connect with Paul

- Website: [Lazniak.com](https://lazniak.com)
- YouTube: [@Lazniak](https://www.youtube.com/@Lazniak)
- Facebook: [PabloGFX](https://www.facebook.com/PabloGFX)
- Twitter: [@PabloGFX](https://x.com/PabloGFX)
- GitHub: [github.com/PabloGFX](https://github.com/PabloGFX)
- LinkedIn: [linkedin.com/in/paul-lazniak](https://www.linkedin.com/in/paul-lazniak)

To learn more about Paul's journey and work, check out his [bio video](https://www.youtube.com/watch?v=5KIcxuWEa4E).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Please ensure you follow our [Code of Conduct](CODE_OF_CONDUCT.md) and read our [Contributing Guidelines](CONTRIBUTING.md) before making a submission.

## Support

If you encounter any issues or have questions, please file an issue on the GitHub repository. For more detailed support or custom development inquiries, you can reach out to Paul directly through his social media channels or website.

## To-Do List

- Improve randomization feature
- Fully implement and enhance the Image Search feature with search query functionality

Note: The Image Search feature is currently under development. Contributions to improve this feature are welcome!

---

Enjoy using the Google Photos Loader in your ComfyUI workflows!
