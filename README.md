# Trackmania Shadow Calculator

This script is designed for Trackmania2020. It automates the process of calculating shadows for a large number of custom maps, meaning you don't have to switch between them to render them, by directly interfacing with the Trackmania executable.

## Overview

The script primarily ensures it is operated within the correct directory, identifies the location of `Trackmania.exe`, and initiates the game with specific parameters to compute shadows for custom maps. This process requires closing any running instances of Trackmania to prevent file access conflicts.

## Prerequisites

- Windows operating system
- [Trackmania](http://trackmania.com/) game installed
- Custom maps created and saved in a folder named 'Maps'

## How It Works

1. **Set Up the Script:**
   - Place the script in the 'Maps' folder where your custom maps are located.
     - This should be `C:\Users\[username]\Documents\Trackmania\Maps`

2. **Run the Script:**
   - Double-click on the script to run it.
   - If running for the first time, it will ask for the path to `Trackmania.exe` if it cannot find it automatically.

3. **Specify Map Folder:**
   - When prompted, type the name of the folder (located within the 'Maps' directory) that you want to calculate shadows for.

4. **Wait for Completion:**
   - The script will close Trackmania if it is running, compute the shadows, and then finish. Trackmania will close again after the computation is complete.

Please ensure you save all changes in Trackmania before running this script as it will force-close the game before starting the shadow calculation.

## License

The Unlicense
