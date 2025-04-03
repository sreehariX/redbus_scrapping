# RedBus Scraper

A Python-based web scraper using selenium for extracting bus information from redbus and saves the results to a JSON file.

# Youtube Demo

[![Redbus Scrapper](https://github.com/user-attachments/assets/083b609c-1502-474d-b307-98a637f406d6)](https://youtu.be/mC7iDDJSs4Y?si=EuDjwMF5VrP_8onU)

## Features

- Search for buses between any two cities on RedBus.in
- automatically navigates through the calendar to select future dates based on user input
- Extract infromation of each bus:
  - Bus name
  - Departure and arrival times
  - Journey duration
  - Fare price
  - Starting and destination points
- Save all results to a structured JSON file
- Handles pagination through scrolling to load all available buses

## Requirements

- Python 3.6+
- Selenium WebDriver
- Chrome browser
- ChromeDriver (compatible with your Chrome version)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/sreehariX/redbus_scrapping.git
   cd redbus_scrapper
   ```

2. Install required Python packages:
   ```
   pip install selenium
   ```

3. Download the appropriate [ChromeDriver](https://sites.google.com/chromium.org/driver/) for your Chrome version and ensure it's in your PATH.

## Usage

1. Open `redbus_scrapper.py` and modify the following variables at the bottom of the file:
   ```python
   input_from_city = "Your Source City"
   input_to_city = "Your Destination City"
   input_month_year = "Month Year" # e.g., "Apr 2025"
   input_day = "Day" # e.g., "25"
   ```

2. Run the script:
   ```
   python redbus_scrapper.py
   ```

3. The script will:
   - Open a Chrome browser window
   - Navigate to redbus.in
   - Input your source and destination
   - Select the specified date
   - Search for buses
   - Extract and save bus information to `bus_data.json`

4. Press Enter when prompted to close the browser.

## Output

The script generates a JSON file (`bus_data.json`) with the following structure:

```json
[
  {
    "Bus ID": 1,
    "Bus Name": "Operator Name",
    "Departure": "00:00",
    "Journey Duration": "0h 0m",
    "Fare Price": "INR 000",
    "Starting Point": "Source",
    "Destination": "Destination"
  },
  ...
]
```

## Error Handling

The scripts has error handling:
- Takes screenshots on error
- Reports issues with finding elements
- Handles cases where no buses are found
- Implements multiple fallback strategies for calendar navigation

If the destination is empty in redus in json its saves nothing
![image](https://github.com/user-attachments/assets/630a91ab-a1f9-481a-96e8-b9b81a3f1351)

![image](https://github.com/user-attachments/assets/ad1e69f4-0833-4532-a4ec-cdc748c5f98b)



## Notes

- The script uses a visible browser window by default. For headless operation, modify the `setup_driver()` function.
- For large result sets, the script may take some time to scroll and load all buses.

