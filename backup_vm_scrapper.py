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
import concurrent.futures

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

def search_buses(from_city, to_city, target_month_year, target_day, csv_file_path, visible=False):
    """
    Search for buses between cities on a specific date and save the results.
    
    Args:
        from_city: Origin city
        to_city: Destination city
        target_month_year: Month and year (e.g., "Apr 2025")
        target_day: Day of month (e.g., "20")
        csv_file_path: Path to the CSV file to save results for this specific route
        visible: Whether to run the browser in visible mode (default: False)
    """
    print(f"[{from_city} to {to_city}] Starting search process...")
    driver = None
    try:
        driver = setup_driver(headless=not visible)  # Enable visible mode if requested
        driver.get("https://www.redbus.in/")
        print(f"[{from_city} to {to_city}] Opened RedBus website")

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
            print(f"[{from_city} to {to_city}] Selected {from_city} as source")
        except TimeoutException:
            print(f"[{from_city} to {to_city}] Error: Suggestion dropdown for '{from_city}' did not appear or wasn't clickable.")
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
            print(f"[{from_city} to {to_city}] Selected {to_city} as destination")
        except TimeoutException:
            print(f"[{from_city} to {to_city}] Error: Suggestion dropdown for '{to_city}' field did not appear or wasn't clickable.")
            raise

        time.sleep(0.5)

        try:
            calendar_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "onwardCal"))
            )
            driver.execute_script("arguments[0].click();", calendar_field)
            print(f"[{from_city} to {to_city}] Clicked on calendar field")
        except (TimeoutException, ElementClickInterceptedException) as e:
             print(f"[{from_city} to {to_city}] Error clicking calendar field: {e}")
             raise

        try:
            calendar_container_xpath = "//div[contains(@class,'DatePicker__MainBlock') or contains(@class,'sc-jzJRlG')]"
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, calendar_container_xpath))
            )
            print(f"[{from_city} to {to_city}] Calendar container is visible")
        except TimeoutException:
            print(f"[{from_city} to {to_city}] Error: Calendar container did not become visible.")
            raise

        max_attempts = 24
        attempts = 0
        while attempts < max_attempts:
            try:
                month_year_element_xpath = f"{calendar_container_xpath}//div[contains(@class,'DayNavigator__IconBlock')][position()=2]"
                current_month_year = WebDriverWait(driver, 2).until(
                    EC.visibility_of_element_located((By.XPATH, month_year_element_xpath))
                ).text
                print(f"[{from_city} to {to_city}] Current calendar month: {current_month_year}")

                if target_month_year in current_month_year:
                    print(f"[{from_city} to {to_city}] Found target month: {target_month_year}")
                    break
                else:
                    next_button_xpath = f"{calendar_container_xpath}//div[contains(@class,'DayNavigator__IconBlock')][position()=3]"
                    next_button = WebDriverWait(driver, 5).until(
                         EC.element_to_be_clickable((By.XPATH, next_button_xpath))
                    )
                    driver.execute_script("arguments[0].click();", next_button)
                    print(f"[{from_city} to {to_city}] Clicked next month")
                    time.sleep(0.5)

            except (NoSuchElementException, TimeoutException) as e:
                print(f"[{from_city} to {to_city}] Error navigating calendar months: {e}. Attempt {attempts+1}/{max_attempts}")
                time.sleep(1)

            attempts += 1
            if attempts == max_attempts:
                 print(f"[{from_city} to {to_city}] Error: Could not navigate to {target_month_year} within {max_attempts} attempts.")
                 raise TimeoutException(f"Failed to find month {target_month_year}")

        try:
            day_xpath = f"//div[contains(@class,'DayTiles__CalendarDaysBlock') and not(contains(@class,'DayTiles__CalendarDaysBlock--inactive'))][text()='{target_day}'] | //span[contains(@class,'DayTiles__CalendarDaysSpan') and not(contains(@class,'DayTiles__CalendarDaysSpan--inactive'))][text()='{target_day}']"

            day_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, day_xpath))
            )
            driver.execute_script("arguments[0].click();", day_element)
            print(f"[{from_city} to {to_city}] Selected day: {target_day}")
        except TimeoutException:
             print(f"[{from_city} to {to_city}] Error: Could not find or click day '{target_day}' in the current month view.")
             try:
                 print(f"[{from_city} to {to_city}] Trying simpler XPath for day selection...")
                 simple_day_xpath = f"//div[text()='{target_day}'] | //span[text()='{target_day}']"
                 day_elements = driver.find_elements(By.XPATH, simple_day_xpath)
                 clicked = False
                 for el in day_elements:
                     if el.is_displayed():
                         driver.execute_script("arguments[0].click();", el)
                         print(f"[{from_city} to {to_city}] Selected day '{target_day}' using simpler XPath.")
                         clicked = True
                         break
                 if not clicked:
                     raise TimeoutException("Simpler XPath also failed.")
             except Exception as fallback_e:
                 print(f"[{from_city} to {to_city}] Error selecting day with fallback XPath: {fallback_e}")
                 raise

        time.sleep(1)

        try:
            search_button = WebDriverWait(driver, 10).until(
                 EC.element_to_be_clickable((By.ID, "search_button"))
            )
            driver.execute_script("arguments[0].click();", search_button)
            print(f"[{from_city} to {to_city}] Clicked Search Buses button")
        except (TimeoutException, ElementClickInterceptedException) as e:
            print(f"[{from_city} to {to_city}] Error clicking Search button: {e}")
            try:
                 search_button_xpath = "//button[normalize-space()='SEARCH BUSES']"
                 search_button = WebDriverWait(driver, 5).until(
                      EC.element_to_be_clickable((By.XPATH, search_button_xpath))
                 )
                 driver.execute_script("arguments[0].click();", search_button)
                 print(f"[{from_city} to {to_city}] Clicked Search Buses button using XPath.")
            except Exception as fallback_e:
                 print(f"[{from_city} to {to_city}] Error clicking Search button with fallback XPath: {fallback_e}")
                 raise

        try:
            results_indicator_xpath = "//ul[contains(@class,'bus-items')] | //div[contains(@class,'result-section')] | //div[contains(@class,'travels')]"
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, results_indicator_xpath))
            )
            print(f"[{from_city} to {to_city}] Search results page loaded.")

            print(f"\n[{from_city} to {to_city}] --- PHASE 1: Dynamic View Buses button clicking ---")

            # Reset to top of page first
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)

            # Initial three scrolls as requested to potentially load buttons
            print(f"[{from_city} to {to_city}] Performing initial three scrolls...")
            for i in range(3):
                # Scroll down progressively
                scroll_amount = 750 * (i + 1)
                driver.execute_script(f"window.scrollTo(0, {scroll_amount});")
                print(f"[{from_city} to {to_city}] Initial scroll {i+1}/3 to position {scroll_amount} completed.")
                time.sleep(1.5) # Give a bit more time for elements to load

            # Scroll back to top before starting the loop
            driver.execute_script("window.scrollTo(0, 0);")
            print(f"[{from_city} to {to_city}] Returned to top. Starting View Buses button click loop.")
            time.sleep(2)

            # Loop to find and click buttons one by one
            clicked_button_count = 0
            while True:
                try:
                    # Find all currently available "View Buses" buttons that are not "Hide Buses"
                    view_buses_xpath = "//div[contains(@class,'button') and contains(text(),'View Buses') and not(contains(text(), 'Hide'))]"
                    view_buses_buttons = driver.find_elements(By.XPATH, view_buses_xpath)

                    current_button_count = len(view_buses_buttons)
                    print(f"[{from_city} to {to_city}] Found {current_button_count} View Buses buttons remaining.")

                    # If no buttons are found, exit the loop
                    if current_button_count == 0:
                        print(f"[{from_city} to {to_city}] No more View Buses buttons found. Exiting loop.")
                        break

                    # Target the first button in the list
                    button_to_click = view_buses_buttons[0]

                    # Scroll the button into view
                    print(f"[{from_city} to {to_city}] Scrolling to the next View Buses button...")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button_to_click)
                    time.sleep(1.5) # Wait for scroll to settle

                    # Verify button is displayed before clicking
                    if not button_to_click.is_displayed():
                        print(f"[{from_city} to {to_city}] Button is not displayed, skipping and trying next cycle.")
                        # Optional: Scroll slightly differently or wait longer?
                        driver.execute_script("window.scrollBy(0, 100);") # Small scroll adjust
                        time.sleep(1) # Correctly indented sleep
                        continue # Go to next iteration of the loop

                    # Click the button
                    button_text = button_to_click.text # Get text for logging
                    driver.execute_script("arguments[0].click();", button_to_click)
                    clicked_button_count += 1
                    print(f"[{from_city} to {to_city}] Clicked View Buses button #{clicked_button_count}: '{button_text}'")
                    time.sleep(3)  # Wait for potential content loading

                    # Scroll back to the top after clicking
                    print(f"[{from_city} to {to_city}] Scrolling back to top...")
                    driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(2) # Wait before finding the next button

                except NoSuchElementException:
                    # This might happen if the page structure changes unexpectedly
                    print(f"[{from_city} to {to_city}] No more View Buses buttons found (NoSuchElementException). Exiting loop.")
                    break # Correctly indented break
                except Exception as e:
                    print(f"[{from_city} to {to_city}] An error occurred during View Buses button processing: {e}")
                    # Check if the error is related to the element becoming stale
                    if "stale element reference" in str(e).lower():
                        print(f"[{from_city} to {to_city}] Stale element reference encountered. Retrying search...")
                        time.sleep(1) # Short pause before retry
                        continue # Continue to next loop iteration to re-find elements
                    else:
                        print(f"[{from_city} to {to_city}] Unhandled error. Exiting loop to prevent infinite execution.")
                        break # Exit loop on unexpected error


            # Ensure we are at the top before Phase 2
            print(f"[{from_city} to {to_city}] Final scroll to top before Phase 2.")
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)

            print(f"[{from_city} to {to_city}] Completed Phase 1: Clicked {clicked_button_count} View Buses buttons total.")
            print(f"\n[{from_city} to {to_city}] --- PHASE 2: Now scrolling to load all buses ---")

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

                print(f"[{from_city} to {to_city}] Scroll progress: Height {last_height}->{new_height}, Buses {current_bus_count}->{new_bus_count}")

                # Check if we've reached the end (no new height AND no new buses)
                if new_height == last_height and new_bus_count == current_bus_count:
                    consecutive_no_change += 1
                    print(f"[{from_city} to {to_city}] No changes detected ({consecutive_no_change}/{max_consecutive_no_change})")

                    if consecutive_no_change >= max_consecutive_no_change:
                        # Final full scroll to bottom to ensure everything is loaded
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1)
                        print(f"[{from_city} to {to_city}] Confirmed: All buses loaded. Ending scroll.")
                        break
                else:
                    # Reset counter if either height or bus count changed
                    consecutive_no_change = 0

                # Update reference values
                last_height = new_height
                last_bus_count = new_bus_count

            print(f"\n[{from_city} to {to_city}] --- Processing Bus Details ---")
            bus_elements = driver.find_elements(By.CSS_SELECTOR, bus_elements_selector)

            if not bus_elements:
                print(f"[{from_city} to {to_city}] No bus details found on the page after scrolling.")
                try:
                    no_buses_xpath = "//*[contains(text(),'Oops! No buses found')] | //*[contains(text(),'No buses found')]"
                    no_buses_element = driver.find_element(By.XPATH, no_buses_xpath)
                    if no_buses_element.is_displayed():
                        print(f"[{from_city} to {to_city}] Confirmed: 'No buses found' message visible on page.")
                except NoSuchElementException:
                    print(f"[{from_city} to {to_city}] Could not find explicit 'No buses found' message on page.")

                # Create empty CSV file with headers only if it doesn't exist
                if not os.path.exists(csv_file_path):
                    try:
                        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                            fieldnames = ["Bus ID", "Bus Name", "Bus Type", "Departure Time", "Arrival Time", "Journey Duration",
                                        "Lowest Price(INR)", "Highest Price(INR)", "Starting Point", "Destination",
                                        "Starting Point Parent", "Destination Point Parent"]
                            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                            writer.writeheader()
                        print(f"[{from_city} to {to_city}] Created empty CSV file with headers: {csv_file_path}")
                    except IOError as e:
                        print(f"[{from_city} to {to_city}] Error creating empty CSV file {csv_file_path}: {e}")
                else:
                    print(f"[{from_city} to {to_city}] CSV file {csv_file_path} already exists. Will append if results are found later (but none found now).")

            else:
                # Initialize CSV file: Check existence and write header if needed
                fieldnames = ["Bus ID", "Bus Name", "Bus Type", "Departure Time", "Arrival Time", "Journey Duration",
                              "Lowest Price(INR)", "Highest Price(INR)", "Starting Point", "Destination",
                              "Starting Point Parent", "Destination Point Parent"]
                csv_exists = os.path.exists(csv_file_path)
                try:
                    # Open in append mode ('a') which creates the file if it doesn't exist
                    # We handle header writing explicitly below
                    with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        # Write header only if the file didn't exist before opening in append mode
                        if not csv_exists or os.path.getsize(csv_file_path) == 0:
                            writer.writeheader()
                            print(f"[{from_city} to {to_city}] Created/Found empty CSV file. Added headers to: {csv_file_path}")
                        else:
                             print(f"[{from_city} to {to_city}] CSV file {csv_file_path} exists and is not empty. Appending data.")

                except IOError as e:
                    print(f"[{from_city} to {to_city}] Error preparing CSV file {csv_file_path}: {e}")
                    raise # Re-raise the error to stop processing for this route

                print(f"[{from_city} to {to_city}] Found {len(bus_elements)} bus results after scrolling. Processing and saving to {csv_file_path}...")
                for index, bus in enumerate(bus_elements):
                    # Assign the bus ID starting from 1 for this specific file
                    bus_id = index + 1
                    # print("-" * 30) # Reduce log noise
                    # print(f"Processing Bus {index+1}/{len(bus_elements)} (Assigned ID: {bus_id})")

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
                                    view_seats_xpath = ".//div[contains(@class, 'button') and (contains(normalize-space(),'View Seats') or contains(normalize-space(),'VIEW SEATS'))]" # Use .// to search within bus context
                                    view_buttons = bus.find_elements(By.XPATH, view_seats_xpath)
                                    # Find the first visible button among potential matches
                                    for btn in view_buttons:
                                        if btn.is_displayed():
                                            view_seats_button = btn
                                            break
                                except Exception:
                                    pass

                            if view_seats_button:
                                # print(f"[{from_city} to {to_city}] Found View Seats button for bus {bus_id}, clicking...") # Reduce noise
                                driver.execute_script("arguments[0].click();", view_seats_button)
                                time.sleep(1.5)  # Wait for seat details to load

                                # First, check for discount prices
                                try:
                                    # Check for discounted prices
                                    discount_price_values = safe_extract_prices(bus, ".discountPrice li.disPrice:not(.price-selected)")

                                    if discount_price_values:
                                        # print(f"Found {len(discount_price_values)} discount prices: {discount_price_values}")
                                        lowest_price = min(discount_price_values)
                                        highest_price = max(discount_price_values)
                                        # print(f"Discount prices - Lowest: {lowest_price}, Highest: {highest_price}")
                                    else:
                                        # print("No discount prices found, checking for non-discount multi-fare prices")
                                        # Check for non-discount prices (multiFare)
                                        multi_fare_values = safe_extract_prices(bus, ".multiFare li.mulfare:not(.price-selected)")

                                        if multi_fare_values:
                                            # print(f"Found {len(multi_fare_values)} multi-fare prices: {multi_fare_values}")
                                            lowest_price = min(multi_fare_values)
                                            highest_price = max(multi_fare_values)
                                            # print(f"Multi-fare prices - Lowest: {lowest_price}, Highest: {highest_price}")
                                        else:
                                            # If neither discount nor multi-fare prices were found,
                                            # try more generic price selectors as a last resort
                                            all_price_values = safe_extract_prices(bus, "[data-price]:not([data-price='ALL'])")
                                            if all_price_values:
                                                # print(f"Found {len(all_price_values)} generic prices: {all_price_values}")
                                                lowest_price = min(all_price_values)
                                                highest_price = max(all_price_values)

                                except Exception as price_error:
                                    print(f"[{from_city} to {to_city}] Error extracting detailed prices for bus {bus_id}: {price_error}")
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
                                            # Search within the bus element context
                                            hide_buttons = bus.find_elements(By.CSS_SELECTOR, selector)
                                            for btn in hide_buttons:
                                                if btn.is_displayed():
                                                    # print(f"[{from_city} to {to_city}] Clicking Hide Seats button ({selector})") # Reduce noise
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
                                        # Try to find by text within bus context
                                        hide_xpath = ".//*[contains(text(), 'HIDE SEATS') or contains(text(), 'Hide Seats')]"
                                        hide_elements = bus.find_elements(By.XPATH, hide_xpath)
                                        if hide_elements:
                                            for el in hide_elements:
                                                if el.is_displayed():
                                                    driver.execute_script("arguments[0].click();", el)
                                                    # print(f"[{from_city} to {to_city}] Clicked on hide button found by text") # Reduce noise
                                                    time.sleep(0.5)
                                                    hide_button_clicked = True
                                                    break

                                    # Last resort - just scroll away from this bus element to force UI to collapse
                                    if not hide_button_clicked:
                                        # print(f"[{from_city} to {to_city}] Could not find hide button - scrolling to collapse") # Reduce noise
                                        driver.execute_script("arguments[0].scrollIntoView(false);", bus)
                                        time.sleep(0.5)

                                except Exception as hide_error:
                                    print(f"[{from_city} to {to_city}] Error handling hide seats for bus {bus_id}: {hide_error}")
                            else:
                                print(f"[{from_city} to {to_city}] Could not find View Seats button for bus {bus_id}")

                        except Exception as seats_error:
                            print(f"[{from_city} to {to_city}] Error in View Seats handling for bus {bus_id}: {seats_error}")
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

                        # Log details less frequently or only on error to reduce noise in parallel runs
                        # print(f"Bus ID: {bus_id}")
                        # print(f"Bus Name: {bus_name}")
                        # ... (rest of print statements)

                        # Append this bus data to the specific CSV file
                        try:
                            with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                                writer.writerow(bus_data)
                            # print(f"Bus {bus_id} data appended to CSV file {csv_file_path}") # Reduce noise
                        except Exception as csv_error:
                            print(f"[{from_city} to {to_city}] Error appending bus {bus_id} to CSV file {csv_file_path}: {csv_error}")

                    except Exception as e:
                        print(f"[{from_city} to {to_city}] ERROR processing bus index {index} (Assigned ID: {bus_id}): {e}")
                        print(f"[{from_city} to {to_city}] Attempting to continue with the next bus...")

                print("-" * 30)
                print(f"[{from_city} to {to_city}] Finished processing {len(bus_elements)} buses. Data saved to {csv_file_path}")

        except TimeoutException:
            print(f"[{from_city} to {to_city}] Error: Search results page structure did not load within the timeout period.")
            # Optionally write an error status to the specific CSV if needed
        except IOError as e:
             print(f"[{from_city} to {to_city}] IO Error during file handling for {csv_file_path}: {e}")
             # Error was already raised during CSV prep, this is just a final catch

    except Exception as e:
         print(f"[{from_city} to {to_city}] An unexpected error occurred: {e}")
         timestamp = time.strftime("%Y%m%d-%H%M%S")
         if driver:
             try:
                screenshot_path = f'error_screenshot_{from_city}_to_{to_city}_{timestamp}.png'
                driver.save_screenshot(screenshot_path)
                print(f"[{from_city} to {to_city}] Screenshot saved as {screenshot_path}")
             except Exception as ss_error:
                 print(f"[{from_city} to {to_city}] Failed to save screenshot: {ss_error}")
         # Re-raise the exception so the ThreadPoolExecutor knows the task failed
         raise

    finally:
        print(f"[{from_city} to {to_city}] Quitting WebDriver.")
        if driver:
             driver.quit()


def process_multiple_routes(routes_list, target_month_year, target_day, visible=False):
    """
    Process multiple routes in PARALLEL, saving data for each route to a separate CSV file.

    Args:
        routes_list: List of tuples with (from_city, to_city)
        target_month_year: Month and year for all searches (e.g., "Apr 2025")
        target_day: Day of month for all searches (e.g., "20")
        visible: Whether to run the browser in visible mode (default: False)
    """
    total_routes = len(routes_list)

    print(f"\n{'='*50}")
    print(f"Starting PARALLEL batch processing of {total_routes} routes")
    print(f"Date for all routes: {target_month_year} {target_day}")
    print(f"Browser mode: {'Visible' if visible else 'Headless'}")
    print("Data for each route will be saved to a separate '{from_city}_to_{to_city}.csv' file.")
    print(f"{'='*50}\n")

    # Use ThreadPoolExecutor for parallel processing
    # Determine max_workers based on CPU or a reasonable default like 4-8
    # Too many workers might consume too much RAM/CPU or trigger anti-scraping
    max_workers = min(os.cpu_count() or 1, 4) # Limit to 4 workers initially, can be adjusted
    print(f"Using up to {max_workers} parallel workers.")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {} # Use a dictionary to map futures to route info for better error reporting
        for index, (from_city, to_city) in enumerate(routes_list, 1):
            # Define the specific CSV file path for this route
            route_csv_file_path = f"{from_city}_to_{to_city}.csv"
            route_info = f"{from_city} to {to_city}"

            print(f"Submitting route {index}/{total_routes}: {route_info} (Output: {route_csv_file_path})")

            # Submit the search_buses function to the executor
            # Pass the specific csv_file_path for this route
            future = executor.submit(
                search_buses,
                from_city=from_city,
                to_city=to_city,
                target_month_year=target_month_year,
                target_day=target_day,
                csv_file_path=route_csv_file_path, # Pass the specific CSV path
                visible=visible
            )
            futures[future] = route_info # Map future to route info

        # Wait for all futures to complete and handle results/exceptions
        print("\nWaiting for all routes to complete...")
        completed_count = 0
        failed_count = 0
        for future in concurrent.futures.as_completed(futures):
            route_info = futures[future]
            try:
                # Retrieve result (search_buses doesn't return anything, but calling result() checks for exceptions)
                future.result()
                print(f"[{route_info}] Processing completed successfully.")
                completed_count += 1
            except Exception as e:
                # Log errors from parallel tasks
                print(f"!!! ERROR processing route [{route_info}]: {e} !!!")
                failed_count += 1


    print(f"\n{'='*50}")
    print(f"Batch processing finished.")
    print(f" - Successfully completed routes: {completed_count}")
    print(f" - Failed routes: {failed_count}")
    print(f"Total routes submitted: {total_routes}")
    print(f"Results are saved in separate CSV files named '{{from_city}}_to_{{to_city}}.csv'.")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    # Parse the route list
    routes_to_process = [
        # ("Delhi", "Manali"),
        # ("Delhi", "Rishikesh"),
        # ("Delhi", "Shimla"),
        # ("Delhi", "Nainital"),
        # ("Delhi", "Katra"),
        # ("Bangalore", "Goa"),
        # ("Bangalore", "Hyderabad"),
        # ("Bangalore", "Tirupathi"),
        # ("Bangalore", "Chennai"),
        # ("Bangalore", "Pondicherry"),
        # ("Hyderabad", "Bangalore"),
        # ("Hyderabad", "Goa"),
        # ("Hyderabad", "Srisailam"),
        # ("Hyderabad", "Vijayawada"),
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
        # Process all routes in parallel
        process_multiple_routes(routes_to_process, target_month_year, target_day, visible=visible_browser)