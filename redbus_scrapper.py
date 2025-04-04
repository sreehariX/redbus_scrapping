from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
import time
import json
import re
import csv
import os

def safe_find_text(element, by, value, default=None):
    """Safely find a sub-element and return its text, or default if not found."""
    try:
        return element.find_element(by, value).text
    except NoSuchElementException:
        return default

def safe_find_attribute(element, by, value, attribute, default=None):
    """Safely find a sub-element and return its attribute, or default if not found."""
    try:
        found = element.find_element(by, value)
        # Special handling for location: prefer title, fallback to text
        if attribute == 'title' and (value == ".dp-loc" or value == ".bp-loc"):
             title_val = found.get_attribute(attribute)
             return title_val if title_val else found.text
        return found.get_attribute(attribute)
    except NoSuchElementException:
        return default

def safe_extract_prices(element, selector, data_attr="data-price", exclude_values=None):
    """
    Safely extract price values from elements using a data attribute.
    
    Args:
        element: Parent element to search within
        selector: CSS selector to find price elements
        data_attr: Name of the data attribute containing the price value (default: "data-price")
        exclude_values: List of values to exclude (e.g., ["ALL"])
        
    Returns:
        List of floats representing prices, or empty list if none found
    """
    if exclude_values is None:
        exclude_values = ["ALL"]
        
    price_values = []
    try:
        price_elements = element.find_elements(By.CSS_SELECTOR, selector)
        for price_el in price_elements:
            price_text = price_el.get_attribute(data_attr)
            if price_text and price_text not in exclude_values:
                try:
                    # Remove any non-numeric characters and convert to float
                    price_clean = re.sub(r'[^\d.]', '', price_text)
                    price_values.append(float(price_clean))
                except ValueError:
                    print(f"Warning: Could not parse price '{price_text}'")
    except Exception as e:
        print(f"Error extracting prices with selector '{selector}': {e}")
    
    return price_values

def setup_driver(headless=False):
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--start-maximized')
    
    # Add options to bypass anti-scraping measures
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Add more realistic user agent
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    
    if headless:
        options.add_argument('--headless=new')  # Using newer headless mode
        options.add_argument('--window-size=1920,1080')  # Set window size in headless mode
    
    driver = webdriver.Chrome(options=options)
    
    # Execute CDP commands to bypass detection
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Overwrite the 'plugins' property to use a custom getter
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Overwrite the 'languages' property to use a custom getter
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        '''
    })
    
    return driver

def search_buses(from_city, to_city, target_month_year, target_day, output_folder=None, visible=False):
    """
    Search for buses between cities on a specific date and save the results.
    
    Args:
        from_city: Origin city
        to_city: Destination city
        target_month_year: Month and year (e.g., "Apr 2025")
        target_day: Day of month (e.g., "20")
        output_folder: Folder to save output files (default: current directory)
        visible: Whether to run the browser in visible mode (default: False)
    """
    driver = setup_driver(headless=not visible)  # Enable visible mode if requested
    
    # Set default output paths
    if output_folder:
        json_file_path = f"{output_folder}/bus_data.json"
        csv_file_path = f"{output_folder}/bus_data.csv"
    else:
        json_file_path = 'bus_data.json'
        csv_file_path = 'bus_data.csv'
    
    try:
        driver.get("https://www.redbus.in/")
        print("Opened RedBus website")
        
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "src"))
        )
        time.sleep(1)
        
        from_input = driver.find_element(By.ID, "src")
        from_input.clear()
        from_input.send_keys(from_city)
        
        try:
            first_suggestion_from = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "ul.sc-dnqmqq li:first-child"))
            )
            first_suggestion_from.click()
            print(f"Selected {from_city} as source")
        except TimeoutException:
            print(f"Error: Suggestion dropdown for '{from_city}' did not appear or wasn't clickable.")
            raise

        time.sleep(0.5)

        to_input = driver.find_element(By.ID, "dest")
        to_input.clear()
        to_input.send_keys(to_city)

        try:
            first_suggestion_to = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "ul.sc-dnqmqq li:first-child"))
            )
            first_suggestion_to.click()
            print(f"Selected {to_city} as destination")
        except TimeoutException:
            print(f"Error: Suggestion dropdown for '{to_city}' field did not appear or wasn't clickable.")
            raise

        time.sleep(0.5)
        
        try:
            calendar_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "onwardCal"))
            )
            driver.execute_script("arguments[0].click();", calendar_field)
            print("Clicked on calendar field")
        except (TimeoutException, ElementClickInterceptedException) as e:
             print(f"Error clicking calendar field: {e}")
             raise

        try:
            calendar_container_xpath = "//div[contains(@class,'DatePicker__MainBlock') or contains(@class,'sc-jzJRlG')]"
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, calendar_container_xpath))
            )
            print("Calendar container is visible")
        except TimeoutException:
            print("Error: Calendar container did not become visible.")
            raise

        max_attempts = 24
        attempts = 0
        while attempts < max_attempts:
            try:
                month_year_element_xpath = f"{calendar_container_xpath}//div[contains(@class,'DayNavigator__IconBlock')][position()=2]"
                current_month_year = WebDriverWait(driver, 2).until(
                    EC.visibility_of_element_located((By.XPATH, month_year_element_xpath))
                ).text
                print(f"Current calendar month: {current_month_year}")

                if target_month_year in current_month_year:
                    print(f"Found target month: {target_month_year}")
                    break
                else:
                    next_button_xpath = f"{calendar_container_xpath}//div[contains(@class,'DayNavigator__IconBlock')][position()=3]"
                    next_button = WebDriverWait(driver, 5).until(
                         EC.element_to_be_clickable((By.XPATH, next_button_xpath))
                    )
                    driver.execute_script("arguments[0].click();", next_button)
                    print("Clicked next month")
                    time.sleep(0.5)

            except (NoSuchElementException, TimeoutException) as e:
                print(f"Error navigating calendar months: {e}. Attempt {attempts+1}/{max_attempts}")
                time.sleep(1)

            attempts += 1
            if attempts == max_attempts:
                 print(f"Error: Could not navigate to {target_month_year} within {max_attempts} attempts.")
                 raise TimeoutException(f"Failed to find month {target_month_year}")

        try:
            day_xpath = f"//div[contains(@class,'DayTiles__CalendarDaysBlock') and not(contains(@class,'DayTiles__CalendarDaysBlock--inactive'))][text()='{target_day}'] | //span[contains(@class,'DayTiles__CalendarDaysSpan') and not(contains(@class,'DayTiles__CalendarDaysSpan--inactive'))][text()='{target_day}']"

            day_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, day_xpath))
            )
            driver.execute_script("arguments[0].click();", day_element)
            print(f"Selected day: {target_day}")
        except TimeoutException:
             print(f"Error: Could not find or click day '{target_day}' in the current month view.")
             try:
                 print("Trying simpler XPath for day selection...")
                 simple_day_xpath = f"//div[text()='{target_day}'] | //span[text()='{target_day}']"
                 day_elements = driver.find_elements(By.XPATH, simple_day_xpath)
                 clicked = False
                 for el in day_elements:
                     if el.is_displayed():
                         driver.execute_script("arguments[0].click();", el)
                         print(f"Selected day '{target_day}' using simpler XPath.")
                         clicked = True
                         break
                 if not clicked:
                     raise TimeoutException("Simpler XPath also failed.")
             except Exception as fallback_e:
                 print(f"Error selecting day with fallback XPath: {fallback_e}")
                 raise

        time.sleep(1)

        try:
            search_button = WebDriverWait(driver, 10).until(
                 EC.element_to_be_clickable((By.ID, "search_button"))
            )
            driver.execute_script("arguments[0].click();", search_button)
            print("Clicked Search Buses button")
        except (TimeoutException, ElementClickInterceptedException) as e:
            print(f"Error clicking Search button: {e}")
            try:
                 search_button_xpath = "//button[normalize-space()='SEARCH BUSES']"
                 search_button = WebDriverWait(driver, 5).until(
                      EC.element_to_be_clickable((By.XPATH, search_button_xpath))
                 )
                 driver.execute_script("arguments[0].click();", search_button)
                 print("Clicked Search Buses button using XPath.")
            except Exception as fallback_e:
                 print(f"Error clicking Search button with fallback XPath: {fallback_e}")
                 raise

        try:
            results_indicator_xpath = "//ul[contains(@class,'bus-items')] | //div[contains(@class,'result-section')] | //div[contains(@class,'travels')]"
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, results_indicator_xpath))
            )
            print("Search results page loaded.")

            print("\n--- PHASE 1: Dynamic View Buses button clicking ---")
            
            # Reset to top of page first
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            # Initial three scrolls as requested to potentially load buttons
            print("Performing initial three scrolls...")
            for i in range(3):
                # Scroll down progressively
                scroll_amount = 750 * (i + 1)
                driver.execute_script(f"window.scrollTo(0, {scroll_amount});")
                print(f"Initial scroll {i+1}/3 to position {scroll_amount} completed.")
                time.sleep(1.5) # Give a bit more time for elements to load
            
            # Scroll back to top before starting the loop
            driver.execute_script("window.scrollTo(0, 0);")
            print("Returned to top. Starting View Buses button click loop.")
            time.sleep(2)
            
            # Loop to find and click buttons one by one
            clicked_button_count = 0
            while True:
                try:
                    # Find all currently available "View Buses" buttons that are not "Hide Buses"
                    view_buses_xpath = "//div[contains(@class,'button') and contains(text(),'View Buses') and not(contains(text(), 'Hide'))]"
                    view_buses_buttons = driver.find_elements(By.XPATH, view_buses_xpath)
                    
                    current_button_count = len(view_buses_buttons)
                    print(f"Found {current_button_count} View Buses buttons remaining.")
                    
                    # If no buttons are found, exit the loop
                    if current_button_count == 0:
                        print("No more View Buses buttons found. Exiting loop.")
                        break
                        
                    # Target the first button in the list
                    button_to_click = view_buses_buttons[0]
                    
                    # Scroll the button into view
                    print("Scrolling to the next View Buses button...")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button_to_click)
                    time.sleep(1.5) # Wait for scroll to settle
                    
                    # Verify button is displayed before clicking
                    if not button_to_click.is_displayed():
                        print("Button is not displayed, skipping and trying next cycle.")
                        # Optional: Scroll slightly differently or wait longer?
                        driver.execute_script("window.scrollBy(0, 100);") # Small scroll adjust
            time.sleep(1)
                        continue # Go to next iteration of the loop
                        
                    # Click the button
                    button_text = button_to_click.text # Get text for logging
                    driver.execute_script("arguments[0].click();", button_to_click)
                    clicked_button_count += 1
                    print(f"Clicked View Buses button #{clicked_button_count}: '{button_text}'")
                    time.sleep(3)  # Wait for potential content loading
                    
                    # Scroll back to the top after clicking
                    print("Scrolling back to top...")
                    driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(2) # Wait before finding the next button
                    
                except NoSuchElementException:
                    # This might happen if the page structure changes unexpectedly
                    print("No more View Buses buttons found (NoSuchElementException). Exiting loop.")
                        break
                except Exception as e:
                    print(f"An error occurred during View Buses button processing: {e}")
                    # Check if the error is related to the element becoming stale
                    if "stale element reference" in str(e).lower():
                        print("Stale element reference encountered. Retrying search...")
                        time.sleep(1) # Short pause before retry
                        continue # Continue to next loop iteration to re-find elements
                else:
                        print("Unhandled error. Exiting loop to prevent infinite execution.")
                        break # Exit loop on unexpected error
            
            # Ensure we are at the top before Phase 2
            print("Final scroll to top before Phase 2.")
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            print(f"Completed Phase 1: Clicked {clicked_button_count} View Buses buttons total.")
            print("\n--- PHASE 2: Now scrolling to load all buses ---")
            
            # Set bus elements selector and scroll parameters
            bus_elements_selector = "ul.bus-items li.row-sec"
            scroll_pause_time = 2.0
            
            # Initialize tracking variables for the full scroll
            last_height = driver.execute_script("return document.body.scrollHeight")
            # Get initial bus count after button clicks and returning to top
            last_bus_count = len(driver.find_elements(By.CSS_SELECTOR, bus_elements_selector))
            consecutive_no_change = 0
            max_consecutive_no_change = 3
            
            # Do a complete scroll to load all buses
            while True:
                # Get current count before scrolling
                current_bus_count = len(driver.find_elements(By.CSS_SELECTOR, bus_elements_selector))
                
                # Scroll down significantly
                driver.execute_script("window.scrollBy(0, 1500);")
                time.sleep(scroll_pause_time)
                
                # Calculate new height and count
                new_height = driver.execute_script("return document.body.scrollHeight")
                new_bus_count = len(driver.find_elements(By.CSS_SELECTOR, bus_elements_selector))
                
                print(f"Scroll progress: Height {last_height}->{new_height}, Buses {current_bus_count}->{new_bus_count}")
                
                # Check if we've reached the end (no new height AND no new buses)
                if new_height == last_height and new_bus_count == current_bus_count:
                    consecutive_no_change += 1
                    print(f"No changes detected ({consecutive_no_change}/{max_consecutive_no_change})")
                    
                    if consecutive_no_change >= max_consecutive_no_change:
                        # Final full scroll to bottom to ensure everything is loaded
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1)
                        print("Confirmed: All buses loaded. Ending scroll.")
                        break
                else:
                    # Reset counter if either height or bus count changed
                    consecutive_no_change = 0
                
                # Update reference values
                last_height = new_height
                last_bus_count = new_bus_count

            print("\n--- Processing Bus Details ---")
            bus_elements = driver.find_elements(By.CSS_SELECTOR, bus_elements_selector)
            json_file_path = 'bus_data.json'
            # Initialize all_buses_data list to store results (will be populated from existing file if any)
            all_buses_data = []

            if not bus_elements:
                print("No bus details found on the page after scrolling.")
                try:
                    no_buses_xpath = "//*[contains(text(),'Oops! No buses found')] | //*[contains(text(),'No buses found')]"
                    no_buses_element = driver.find_element(By.XPATH, no_buses_xpath)
                    if no_buses_element.is_displayed():
                        print("Confirmed: 'No buses found' message visible on page.")
                except NoSuchElementException:
                    print("Could not find explicit 'No buses found' message on page.")

                try:
                    # with open(json_file_path, 'w', encoding='utf-8') as f:
                    #     json.dump({"status": "No results found"}, f, indent=4, ensure_ascii=False)
                    # print(f"Saved 'No results found' status to {json_file_path}")
                    print("JSON file saving is disabled. Not saving 'No results found' status.")
                    
                    # Create empty CSV file with headers only if it doesn't exist
                    csv_file_path = 'bus_data.csv'
                    if not os.path.exists(csv_file_path):
                        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                            fieldnames = ["Bus ID", "Bus Name", "Bus Type", "Departure Time", "Arrival Time", "Journey Duration", 
                                        "Lowest Price(INR)", "Highest Price(INR)", "Starting Point", "Destination",
                                        "Starting Point Parent", "Destination Point Parent"]
                            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                            writer.writeheader()
                        print(f"Created empty CSV file with headers: {csv_file_path}")
                    else:
                        print(f"CSV file {csv_file_path} already exists. Not overwriting.")
                except IOError as e:
                    print(f"Error writing empty results to files: {e}")

            else:
                try:
                    # Check if JSON file exists and load existing data
                    if os.path.exists(json_file_path) and os.path.getsize(json_file_path) > 0:
                        try:
                            # with open(json_file_path, 'r', encoding='utf-8') as f:
                            #     all_buses_data = json.load(f)
                            # if isinstance(all_buses_data, list):
                            #     print(f"Loaded {len(all_buses_data)} existing bus entries from {json_file_path}")
                            # else:
                            #     print(f"JSON file {json_file_path} does not contain a list. Creating new list.")
                            #     all_buses_data = []
                                all_buses_data = []
                            print("JSON file saving is disabled, initializing empty list for processing.")
                        except json.JSONDecodeError:
                            print(f"Error decoding existing JSON file. Creating new list.")
                            all_buses_data = []
                    else:
                        # Initialize new JSON file with empty list
                        # with open(json_file_path, 'w') as f:
                        #     json.dump([], f)
                        # print(f"Initialized new {json_file_path} for bus data.")
                        all_buses_data = []
                        print("JSON file saving is disabled, initializing empty list for processing.")
                    
                    # Initialize CSV file with headers only if it doesn't exist
                    csv_exists = os.path.exists(csv_file_path)
                    fieldnames = ["Bus ID", "Bus Name", "Bus Type", "Departure Time", "Arrival Time", "Journey Duration",
                                  "Lowest Price(INR)", "Highest Price(INR)", "Starting Point", "Destination",
                                  "Starting Point Parent", "Destination Point Parent"]
                    
                    # Get the starting bus ID by checking existing CSV file
                    starting_bus_id = 1
                    if csv_exists:
                        try:
                            row_count = 0
                            with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                                reader = csv.reader(csvfile)
                                header = next(reader, None) # Read and discard the header
                                if header: # Proceed only if header was successfully read
                                    # Count non-empty data rows accurately
                                    row_count = sum(1 for row in reader if any(field.strip() for field in row))
                                else: # Handle case where file might exist but be empty or headerless
                                    print(f"Warning: CSV file {csv_file_path} exists but seems empty or lacks a header.")
                                    row_count = 0

                            # The next ID is the count of existing data rows + 1
                                starting_bus_id = row_count + 1
                            print(f"Found existing CSV '{csv_file_path}' with {row_count} valid data entries. Will start next Bus ID from {starting_bus_id}")
                        except StopIteration: # Handles files with only a header
                             print(f"CSV file {csv_file_path} contains only a header. Starting next Bus ID from 1.")
                            starting_bus_id = 1
                        except Exception as e:
                            print(f"Error reading existing CSV '{csv_file_path}' to count rows: {e}. Will start with ID 1.")
                            starting_bus_id = 1 # Fallback
                    else:
                        # Create new CSV with headers
                        print(f"CSV file '{csv_file_path}' not found. Creating new file with headers.")
                        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                            writer.writeheader()
                        # print(f"Initialized {csv_file_path} with headers.") # Redundant log
                        starting_bus_id = 1 # Start from 1 for a new file

                except IOError as e:
                    print(f"Error initializing files: {e}")
                    starting_bus_id = 1 # Ensure a fallback if file init fails

                print(f"Found {len(bus_elements)} bus results after scrolling. Processing and saving starting from ID {starting_bus_id}...")
                for index, bus in enumerate(bus_elements):
                    # Assign the bus ID based on the calculated starting point and the current index
                    bus_id = starting_bus_id + index
                    print("-" * 30)
                    print(f"Processing Bus {index+1}/{len(bus_elements)} (Assigned ID: {bus_id})")

                    try:
                        bus_name = safe_find_text(bus, By.CSS_SELECTOR, ".travels", default="Not Found")
                        bus_type = safe_find_text(bus, By.CSS_SELECTOR, ".bus-type", default="Not Found")
                        dep_time = safe_find_text(bus, By.CSS_SELECTOR, ".dp-time", default="Not Found")
                        dep_loc = safe_find_attribute(bus, By.CSS_SELECTOR, ".dp-loc", 'title', default="Not Found")
                        arr_time = safe_find_text(bus, By.CSS_SELECTOR, ".bp-time", default="Not Found")
                        arr_loc = safe_find_attribute(bus, By.CSS_SELECTOR, ".bp-loc", 'title', default="Not Found")
                        duration = safe_find_text(bus, By.CSS_SELECTOR, ".dur", default="Not Found")

                        # Get the initial fare price for fallback
                        try:
                            initial_fare = bus.find_element(By.CSS_SELECTOR, ".fare .f-bold").text
                            # Convert to float for consistency, removing non-numeric characters
                            initial_fare_clean = re.sub(r'[^\d.]', '', initial_fare)
                            fare_price = float(initial_fare_clean) if initial_fare_clean else 0.0
                        except (NoSuchElementException, ValueError):
                            fare_price = 0.0

                        # Initialize lowest and highest price variables with the same initial price
                        lowest_price = fare_price
                        highest_price = fare_price

                        # Check for View Seats button to get more detailed pricing
                        try:
                            # Find and click View Seats button
                            view_seats_selectors = [
                                ".button.view-seats",
                                ".view-seats",
                                "div.button.view-seats",
                                "div.view-seats",
                                ".button:not(.hide-seats)",
                                "div.button:not(.hide-seats)"
                            ]
                            
                            view_seats_button = None
                            for selector in view_seats_selectors:
                                try:
                                    buttons = bus.find_elements(By.CSS_SELECTOR, selector)
                                    for btn in buttons:
                                        # Check if the button has correct text or is the right button
                                        btn_text = btn.text.strip()
                                        if btn.is_displayed() and ("VIEW SEATS" in btn_text.upper() or "View Seats" in btn_text):
                                            view_seats_button = btn
                                            break
                                    if view_seats_button:
                                        break
                                except Exception:
                                    continue
                            
                            # If we still haven't found the button, try a more general approach
                            if not view_seats_button:
                                try:
                                    view_seats_xpath = "//div[contains(@class, 'button') and (text()='View Seats' or text()='VIEW SEATS')]"
                                    view_buttons = bus.find_elements(By.XPATH, view_seats_xpath)
                                    if view_buttons:
                                        view_seats_button = view_buttons[0]
                                except Exception:
                                    pass
                            
                            if view_seats_button:
                                print(f"Found View Seats button for bus {bus_id}, clicking to get detailed pricing...")
                                driver.execute_script("arguments[0].click();", view_seats_button)
                                time.sleep(1.5)  # Wait for seat details to load
                                
                                # First, check for discount prices
                                try:
                                    # Check for discounted prices
                                    discount_price_values = safe_extract_prices(bus, ".discountPrice li.disPrice:not(.price-selected)")
                                    
                                    if discount_price_values:
                                        print(f"Found {len(discount_price_values)} discount prices: {discount_price_values}")
                                        lowest_price = min(discount_price_values)
                                        highest_price = max(discount_price_values)
                                        print(f"Discount prices - Lowest: {lowest_price}, Highest: {highest_price}")
                                    else:
                                        print("No discount prices found, checking for non-discount multi-fare prices")
                                        # Check for non-discount prices (multiFare)
                                        multi_fare_values = safe_extract_prices(bus, ".multiFare li.mulfare:not(.price-selected)")
                                        
                                        if multi_fare_values:
                                            print(f"Found {len(multi_fare_values)} multi-fare prices: {multi_fare_values}")
                                            lowest_price = min(multi_fare_values)
                                            highest_price = max(multi_fare_values)
                                            print(f"Multi-fare prices - Lowest: {lowest_price}, Highest: {highest_price}")
                                        else:
                                            # If neither discount nor multi-fare prices were found,
                                            # try more generic price selectors as a last resort
                                            all_price_values = safe_extract_prices(bus, "[data-price]:not([data-price='ALL'])")
                                            if all_price_values:
                                                print(f"Found {len(all_price_values)} generic prices: {all_price_values}")
                                                lowest_price = min(all_price_values)
                                                highest_price = max(all_price_values)
                                            
                                except Exception as price_error:
                                    print(f"Error extracting detailed prices: {price_error}")
                                    # Keep the fallback price if detailed extraction failed
                                
                                # Find and click Hide Seats button to close the expanded section
                                try:
                                    hide_seats_selectors = [
                                        ".hideSeats",
                                        ".hide-seats",
                                        "div.hideSeats",
                                        "div.hide-seats",
                                        ".button.hideSeats",
                                        ".button.hide-seats"
                                    ]
                                    
                                    hide_button_clicked = False
                                    for selector in hide_seats_selectors:
                                        try:
                                            hide_buttons = bus.find_elements(By.CSS_SELECTOR, selector)
                                            for btn in hide_buttons:
                                                if btn.is_displayed():
                                                    print(f"Clicking Hide Seats button ({selector}) to close expanded section")
                                                    driver.execute_script("arguments[0].click();", btn)
                                                    time.sleep(0.5)  # Short wait for UI to update
                                                    hide_button_clicked = True
                                                    break
                                            if hide_button_clicked:
                                                break
                                        except Exception:
                                            continue
                                    
                                    # If we couldn't find a specific hide button, try more generic approaches
                                    if not hide_button_clicked:
                                        # Try to find by text
                                        hide_xpath = "//*[contains(text(), 'HIDE SEATS') or contains(text(), 'Hide Seats')]"
                                        hide_elements = bus.find_elements(By.XPATH, hide_xpath)
                                        if hide_elements:
                                            for el in hide_elements:
                                                if el.is_displayed():
                                                    driver.execute_script("arguments[0].click();", el)
                                                    print("Clicked on hide button found by text")
                                                    time.sleep(0.5)
                                                    hide_button_clicked = True
                                                    break
                                    
                                    # Last resort - just scroll away from this bus element to force UI to collapse
                                    if not hide_button_clicked:
                                        print("Could not find hide button - scrolling to collapse the section")
                                        driver.execute_script("arguments[0].scrollIntoView(false);", bus)
                                        time.sleep(0.5)
                                        
                                except Exception as hide_error:
                                    print(f"Error handling hide seats: {hide_error}")
                            else:
                                print(f"Could not find View Seats button for bus {bus_id}")
                        
                        except Exception as seats_error:
                            print(f"Error in View Seats handling for bus {bus_id}: {seats_error}")
                            # Continue with the fallback prices if detailed extraction failed

                        start_point = dep_loc if dep_loc != "Not Found" else from_city
                        end_point = arr_loc if arr_loc != "Not Found" else to_city

                        bus_data = {
                            "Bus ID": bus_id,
                            "Bus Name": bus_name,
                            "Bus Type": bus_type,
                            "Departure Time": dep_time,
                            "Arrival Time": arr_time,
                            "Journey Duration": duration,
                            "Lowest Price(INR)": lowest_price,
                            "Highest Price(INR)": highest_price,
                            "Starting Point": start_point,
                            "Destination": end_point,
                            "Starting Point Parent": from_city,
                            "Destination Point Parent": to_city
                        }

                        print(f"Bus ID: {bus_id}")
                        print(f"Bus Name: {bus_name}")
                        print(f"Bus Type: {bus_type}")
                        print(f"Departure Time: {dep_time}")
                        print(f"Arrival Time: {arr_time}")
                        print(f"Journey Duration: {duration}")
                        print(f"Lowest Price(INR): {lowest_price}")
                        print(f"Highest Price(INR): {highest_price}")
                        print(f"Starting Point: {start_point}")
                        print(f"Destination: {end_point}")
                        print(f"Starting Point Parent: {from_city}")
                        print(f"Destination Point Parent: {to_city}")

                        all_buses_data.append(bus_data)

                        # try:
                        #     with open(json_file_path, 'w', encoding='utf-8') as f:
                        #         json.dump(all_buses_data, f, indent=4, ensure_ascii=False)
                        # except IOError as e:
                        #     print(f"Error writing to JSON file for bus {bus_id}: {e}")
                        # except Exception as e:
                        #     print(f"An unexpected error occurred during JSON writing for bus {bus_id}: {e}")
                            
                        # Append this bus data to CSV file
                        try:
                            # Ensure we use the csv_file_path defined at the function start
                            with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                                # Use the consistent, CORRECTED fieldnames list
                                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                                # DO NOT write the header when appending
                                writer.writerow(bus_data)
                            print(f"Bus {bus_id} data appended to CSV file {csv_file_path}")
                        except Exception as csv_error:
                            print(f"Error appending bus {bus_id} to CSV file: {csv_error}")

                    except Exception as e:
                        print(f"ERROR processing bus {bus_id}: {e}")
                        print("Attempting to continue with the next bus...")

                print("-" * 30)
                print(f"Finished processing {len(all_buses_data)} buses. Full data saved to CSV file {csv_file_path}")

        except TimeoutException:
            print("Error: Search results page structure did not load within the timeout period.")
            try:
                # with open(json_file_path, 'w', encoding='utf-8') as f:
                #     json.dump({"status": "Error - Results page did not load"}, f, indent=4, ensure_ascii=False)
                print("JSON file saving is disabled. Not saving error status.")
            except IOError as e:
                 print(f"Error writing error status to JSON: {e}")

    except Exception as e:
         print(f"An unexpected error occurred: {e}")
         timestamp = time.strftime("%Y%m%d-%H%M%S")
         driver.save_screenshot(f'error_screenshot_{timestamp}.png')
         print(f"Screenshot saved as error_screenshot_{timestamp}.png")

    finally:
        print("Quitting WebDriver.")
        if 'driver' in locals() and driver:
             driver.quit()

def process_multiple_routes(routes_list, target_month_year, target_day, visible=False):
    """
    Process multiple routes in sequence, appending all data to a single CSV file.
    
    Args:
        routes_list: List of tuples with (from_city, to_city)
        target_month_year: Month and year for all searches (e.g., "Apr 2025")
        target_day: Day of month for all searches (e.g., "20")
        visible: Whether to run the browser in visible mode (default: False)
    """
    total_routes = len(routes_list)
    
    print(f"\n{'='*50}")
    print(f"Starting batch processing of {total_routes} routes")
    print(f"Date for all routes: {target_month_year} {target_day}")
    print(f"Browser mode: {'Visible' if visible else 'Headless'}")
    print("Data will be appended to 'bus_data.csv' in the main directory.") # Added info
    print(f"{'='*50}\n")
    
    # Define the single CSV file path (used for initial check/creation)
    main_csv_file_path = 'bus_data.csv'
    fieldnames = ["Bus ID", "Bus Name", "Bus Type", "Departure Time", "Arrival Time", "Journey Duration",
                  "Lowest Price(INR)", "Highest Price(INR)", "Starting Point", "Destination",
                  "Starting Point Parent", "Destination Point Parent"]

    # Check if the main CSV exists, create with header if not
    if not os.path.exists(main_csv_file_path):
        try:
            with open(main_csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
            print(f"Created main CSV file '{main_csv_file_path}' with headers.")
        except IOError as e:
            print(f"ERROR: Could not create main CSV file '{main_csv_file_path}': {e}")
            print("Aborting batch processing.")
            return # Stop if we can't create the main file

    for index, (from_city, to_city) in enumerate(routes_list, 1):
        # REMOVED: route_folder creation
        # route_folder = f"{from_city}_to_{to_city}"
        # os.makedirs(route_folder, exist_ok=True)
        
        print(f"\n{'='*50}")
        print(f"Processing route {index}/{total_routes}: {from_city} to {to_city}")
        print(f"{'='*50}\n")
        
        try:
            # Call search_buses WITHOUT output_folder argument
            search_buses(
                from_city=from_city,
                to_city=to_city,
                target_month_year=target_month_year,
                target_day=target_day,
                # output_folder=route_folder, # REMOVED
                visible=visible
            )
            print(f"\nCompleted route {index}/{total_routes}: {from_city} to {to_city}")
            # REMOVED: message about saving to folder
            # print(f"Data saved in folder: {route_folder}")
            
        except Exception as e:
            print(f"\nERROR processing route {from_city} to {to_city}: {e}")
            print("Continuing with next route...\n")
            
        # Add a delay between routes to avoid overloading the server
        print("Waiting 5 seconds before processing next route...")
        time.sleep(5)
    
    print(f"\n{'='*50}")
    print(f"Batch processing completed. Processed {total_routes} routes.")
    print(f"All data appended to '{main_csv_file_path}'.") # Updated final message
    print(f"{'='*50}\n")

if __name__ == "__main__":
    # Parse the route list
    routes_to_process = [
        ("Delhi", "Manali"),
        ("Delhi", "Rishikesh"),
        ("Delhi", "Shimla"),
        ("Delhi", "Nainital"),
        ("Delhi", "Katra"),
        ("Bangalore", "Goa"),
        ("Bangalore", "Hyderabad"),
        ("Bangalore", "Tirupathi"),
        ("Bangalore", "Chennai"),
        ("Bangalore", "Pondicherry"),
        ("Hyderabad", "Bangalore"),
        ("Hyderabad", "Goa"),
        ("Hyderabad", "Srisailam"),
        ("Hyderabad", "Vijayawada"),
        ("Hyderabad", "Tirupathi"),
        ("Pune", "Goa"),
        ("Pune", "Mumbai"),
        ("Pune", "Nagpur"),
        ("Pune", "Kolhapur"),
        ("Pune", "Nashik"),
        ("Mumbai", "Goa"),
        ("Mumbai", "Pune"),
        ("Mumbai", "Shirdi"),
        ("Mumbai", "Mahabaleshwar"),
        ("Mumbai", "Kolhapur"),
        ("Kolkata", "Digha"),
        ("Kolkata", "Siliguri"),
        ("Kolkata", "Puri"),
        ("Kolkata", "Bakkhali"),
        ("Kolkata", "Mandarmani"),
        ("Chennai", "Bangalore"),
        ("Chennai", "Pondicherry"),
        ("Chennai", "Coimbatore"),
        ("Chennai", "Madurai"),
        ("Chennai", "Tirupathi"),
        ("Chandigarh", "Manali"),
        ("Chandigarh", "Shimla"),
        ("Chandigarh", "Delhi"),
        ("Chandigarh", "Dehradun"),
        ("Chandigarh", "Amritsar"),
        ("Coimbatore", "Chennai"),
        ("Coimbatore", "Bangalore"),
        ("Coimbatore", "Ooty"),
        ("Coimbatore", "Tiruchendur"),
        ("Coimbatore", "Madurai"),
        ("Agra", "Bareilly"),
        ("Hisar", "Chandigarh"),
        ("Ayodhya", "Varanasi"),
        ("Lucknow", "Ballia"),
        ("Lucknow", "Moradabad"),
        ("Rajkot", "Dwarka"),
        ("Siliguri", "Gangtok"),
        ("Ahmedabad", "Goa"),
        ("Ahmedabad", "Kanpur"),
        ("Akola", "Pune"),
        ("Delhi", "Dehradun"),
        ("Delhi", "Haridwar"),
        ("Dehradun", "Delhi"),
        ("Delhi", "Agra"),
        ("Delhi", "Varanasi")
    ]
    
    # Set common date for all routes
    target_month_year = "Apr 2025"
    target_day = "20"
    
    # Parse command line arguments
    import sys
    
    visible_browser = "--visible" in sys.argv
    single_route = "--single" in sys.argv
    
    if single_route:
        # Process just a single route for testing
        print("Running in single route mode (for testing)")
        print(f"Browser mode: {'Visible' if visible_browser else 'Headless'}")
        input_from_city = "Mumbai"
        input_to_city = "Thane"
        search_buses(input_from_city, input_to_city, target_month_year, target_day, visible=visible_browser)
    else:
        # Process all routes
        process_multiple_routes(routes_to_process, target_month_year, target_day, visible=visible_browser)