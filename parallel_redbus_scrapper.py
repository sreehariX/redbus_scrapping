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
    
    # Add options to prevent tab crashes due to memory issues
    options.add_argument('--disable-extensions')  # Disable extensions to reduce memory usage
    options.add_argument('--disable-popup-blocking')  # Prevent popups which can consume memory
    options.add_argument('--disable-gpu')  # Reduce GPU memory usage
    options.add_argument('--disable-infobars')  # Save some UI memory
    
    # Memory management options
    options.add_argument('--js-flags=--expose-gc')  # Enable garbage collection exposure
    options.add_argument('--aggressive-cache-discard')  # Aggressive cache management
    options.add_argument('--disable-cache')  # Disable browser cache to save memory
    options.add_argument('--disable-application-cache')  # Disable application cache
    options.add_argument('--disable-network-http-use-cache')  # Don't use HTTP cache
    options.add_argument('--disable-offline-load-stale-cache')  # Don't load stale cache
    
    # Process model options
    options.add_argument('--single-process')  # Use a single process to reduce overhead
    options.add_argument('--process-per-site')  # One process per site instead of per tab
    
    # Add options to bypass anti-scraping measures
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Set a page size limit to help prevent memory issues
    options.add_argument('--disk-cache-size=1')  # Minimum disk cache
    
    # Add more realistic user agent
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    
    if headless:
        options.add_argument('--headless=new')  # Using newer headless mode
        options.add_argument('--window-size=1920,1080')  # Set window size in headless mode
    
    driver = webdriver.Chrome(options=options)
    
    # Set page load strategy to reduce resource usage
    driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.css", "*.woff", "*.woff2"]})
    driver.execute_cdp_cmd('Network.enable', {})
    
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
            
            // Add a periodic garbage collection call to free up memory
            setInterval(() => {
                if (window.gc) {
                    window.gc();
                }
            }, 60000); // Run GC every minute
        '''
    })
    
    return driver

def search_buses(from_city, to_city, target_month_year, target_day, csv_file_path, visible=False, max_retries=10):
    """
    Search for buses between cities on a specific date and save the results.
    
    Args:
        from_city: Origin city
        to_city: Destination city
        target_month_year: Month and year (e.g., "Apr 2025")
        target_day: Day of month (e.g., "20")
        csv_file_path: Path to the CSV file to save results for this specific route
        visible: Whether to run the browser in visible mode (default: False)
        max_retries: Maximum number of retries for connection issues (default: 3)
    """
    print(f"[{from_city} to {to_city}] Starting search process...")
    driver = None
    retry_count = 0
    
    while retry_count <= max_retries:
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

                # Initial scrolls to load content
                print(f"[{from_city} to {to_city}] Performing initial scrolls to preload content...")
                # First a full scroll to bottom and back to ensure page is fully loaded
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)
                
                # Then do progressive scrolls as before
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
                find_button_attempts = 0
                max_find_attempts = 10  # Maximum number of attempts to find buttons
                
                while find_button_attempts < max_find_attempts:
                    try:
                        # Find all currently available "View Buses" buttons that are not "Hide Buses"
                        view_buses_xpath = "//div[contains(@class,'button') and contains(text(),'View Buses') and not(contains(text(), 'Hide'))]"
                        view_buses_buttons = driver.find_elements(By.XPATH, view_buses_xpath)

                        current_button_count = len(view_buses_buttons)
                        print(f"[{from_city} to {to_city}] Found {current_button_count} View Buses buttons remaining.")

                        # If no buttons are found, retry a few times before exiting
                        if current_button_count == 0:
                            find_button_attempts += 1
                            if find_button_attempts >= max_find_attempts:
                                print(f"[{from_city} to {to_city}] No more View Buses buttons found after {find_button_attempts} attempts. Exiting loop.")
                                break
                            else:
                                print(f"[{from_city} to {to_city}] No buttons found, attempt {find_button_attempts}/{max_find_attempts}. Scrolling to refresh...")
                                # Try scrolling up and down to refresh the view
                                driver.execute_script("window.scrollTo(0, 0);")
                                time.sleep(1)
                                driver.execute_script("window.scrollBy(0, 500);")
                                time.sleep(1)
                                continue

                        # Reset find attempts counter since we found buttons
                        find_button_attempts = 0
                        
                        # Target the first button in the list
                        button_to_click = view_buses_buttons[0]

                        # Scroll the button into view
                        print(f"[{from_city} to {to_city}] Scrolling to the next View Buses button...")
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button_to_click)
                        time.sleep(1.5) # Wait for scroll to settle

                        # Verify button is displayed before clicking
                        if not button_to_click.is_displayed():
                            print(f"[{from_city} to {to_city}] Button is not displayed, skipping and trying next cycle.")
                            # Scroll slightly differently and wait longer
                            driver.execute_script("window.scrollBy(0, 100);") # Small scroll adjust
                            time.sleep(2) # Longer wait time
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
                print(f"[{from_city} to {to_city}] Final scroll to top before combined scrolling and processing phase.")
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)

                print(f"[{from_city} to {to_city}] Completed Phase 1: Clicked {clicked_button_count} View Buses buttons total.")
                print(f"\n[{from_city} to {to_city}] --- Starting Combined Scrolling and Processing Phase ---")

                # Set bus elements selector and scroll parameters
                bus_elements_selector = "ul.bus-items li.row-sec"
                scroll_pause_time = 2.0
                processed_bus_ids = set()  # Track already processed bus IDs to avoid duplicates

                # Try to find the total buses count from the header
                total_buses_expected = 0
                try:
                    buses_found_element = driver.find_element(By.CSS_SELECTOR, "span.f-bold.busFound")
                    buses_found_text = buses_found_element.text
                    # Extract number from text like "231 Buses"
                    matches = re.search(r'(\d+)\s+Buses', buses_found_text)
                    if matches:
                        total_buses_expected = int(matches.group(1))
                        print(f"[{from_city} to {to_city}] Found total expected buses count: {total_buses_expected} buses")
                    else:
                        print(f"[{from_city} to {to_city}] Could not extract number from busFound text: '{buses_found_text}'")
                except NoSuchElementException:
                    print(f"[{from_city} to {to_city}] No bus count header found, will use scroll-based loading")
                except Exception as e:
                    print(f"[{from_city} to {to_city}] Error getting bus count: {e}")

                # Initialize CSV file with header if needed
                fieldnames = ["Bus ID", "Bus Name", "Bus Type", "Departure Time", "Arrival Time", "Journey Duration",
                             "Lowest Price(INR)", "Highest Price(INR)", "Starting Point", "Destination",
                             "Starting Point Parent", "Destination Point Parent"]
                
                if not os.path.exists(csv_file_path) or os.path.getsize(csv_file_path) == 0:
                    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        print(f"[{from_city} to {to_city}] Created new CSV file with headers: {csv_file_path}")

                # Initialize tracking variables for the combined scroll & process approach
                last_height = driver.execute_script("return document.body.scrollHeight")
                consecutive_no_change = 0
                max_consecutive_no_change = 6
                total_scrolls = 0
                max_scrolls = 30  # Safety limit on total scrolls
                processed_count = 0
                buses_match_target = False

                # Begin combined scrolling & processing loop
                while total_scrolls < max_scrolls:
                    total_scrolls += 1
                    
                    # Get current visible buses count
                    current_visible_buses = driver.find_elements(By.CSS_SELECTOR, bus_elements_selector)
                    current_visible_count = len(current_visible_buses)
                    
                    # Process all currently visible buses that we haven't processed yet
                    newly_processed = 0
                    for idx, bus in enumerate(current_visible_buses):
                        try:
                            # Process the bus and get both data and identifier
                            bus_data, bus_identifier = process_bus_element(bus, processed_count + newly_processed + 1, from_city, to_city, driver)
                            
                            # Only save and count if we got valid data and haven't processed this bus before
                            if bus_data and bus_identifier and bus_identifier not in processed_bus_ids:
                                # Save to CSV
                                with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                                    writer.writerow(bus_data)
                                
                                newly_processed += 1
                                processed_bus_ids.add(bus_identifier)
                        except Exception as e:
                            print(f"[{from_city} to {to_city}] Error processing bus during scroll #{total_scrolls}: {e}")
                    
                    # Update total processed count
                    processed_count += newly_processed
                    
                    # Print progress
                    print(f"[{from_city} to {to_city}] Scroll #{total_scrolls}: Processed {newly_processed} new buses. Total processed: {processed_count}/{total_buses_expected if total_buses_expected > 0 else '?'}")
                    
                    # Check if we've reached the expected count
                    if total_buses_expected > 0 and processed_count == total_buses_expected:
                        buses_match_target = True
                        print(f"[{from_city} to {to_city}] SUCCESS: Found exact match! Processed {processed_count}/{total_buses_expected} buses.")
                        break
                    
                    # Scroll down
                    driver.execute_script("window.scrollBy(0, 1500);")
                    time.sleep(scroll_pause_time)
                    
                    # Calculate new height and bus count
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    new_visible_buses = driver.find_elements(By.CSS_SELECTOR, bus_elements_selector)
                    new_visible_count = len(new_visible_buses)
                    
                    # Check if anything changed after scrolling
                    if new_height == last_height and new_visible_count == current_visible_count and newly_processed == 0:
                        consecutive_no_change += 1
                        print(f"[{from_city} to {to_city}] No changes detected ({consecutive_no_change}/{max_consecutive_no_change})")
                        
                        # If we've found the target number of buses, we can stop
                        if total_buses_expected > 0 and processed_count == total_buses_expected:
                            buses_match_target = True
                            print(f"[{from_city} to {to_city}] SUCCESS: Found exact match! Processed {processed_count}/{total_buses_expected} buses.")
                            break
                        
                        # Check if we should perform final scrolling
                        if consecutive_no_change >= max_consecutive_no_change:
                            print(f"[{from_city} to {to_city}] Reached max consecutive no change. Performing final scroll sequence...")
                            
                            # Try different scroll techniques to ensure we've loaded all buses
                            for i in range(3):
                                # Scroll to bottom
                                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                time.sleep(2)
                                
                                # Process any newly visible buses
                                final_buses = driver.find_elements(By.CSS_SELECTOR, bus_elements_selector)
                                final_processed = 0
                                
                                for bus in final_buses:
                                    try:
                                        bus_data, bus_identifier = process_bus_element(bus, processed_count + final_processed + 1, from_city, to_city, driver)
                                        if bus_data and bus_identifier and bus_identifier not in processed_bus_ids:
                                            with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                                                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                                                writer.writerow(bus_data)
                                            final_processed += 1
                                            processed_bus_ids.add(bus_identifier)
                                    except Exception as e:
                                        print(f"[{from_city} to {to_city}] Error in final scroll processing: {e}")
                                
                                if final_processed > 0:
                                    processed_count += final_processed
                                    print(f"[{from_city} to {to_city}] Final scroll technique #{i+1} found {final_processed} more buses. Total now: {processed_count}/{total_buses_expected if total_buses_expected > 0 else '?'}")
                                
                                # Check if we've hit the target
                                if total_buses_expected > 0 and processed_count == total_buses_expected:
                                    buses_match_target = True
                                    print(f"[{from_city} to {to_city}] SUCCESS: Found exact match after final scroll! Processed {processed_count}/{total_buses_expected} buses.")
                                    break
                                
                                # Scroll back to top and then bottom again
                                driver.execute_script("window.scrollTo(0, 0);")
                                time.sleep(1)
                                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                time.sleep(2)
                            
                            # Report final status
                            if total_buses_expected > 0:
                                if processed_count == total_buses_expected:
                                    print(f"[{from_city} to {to_city}] SUCCESS: All expected buses processed exactly! ({processed_count}/{total_buses_expected})")
                                elif processed_count > total_buses_expected:
                                    print(f"[{from_city} to {to_city}] WARNING: Processed more buses ({processed_count}) than expected ({total_buses_expected})")
                                else:
                                    print(f"[{from_city} to {to_city}] WARNING: Only processed {processed_count}/{total_buses_expected} buses after all attempts.")
                            
                            print(f"[{from_city} to {to_city}] Combined scrolling & processing complete. Total buses processed: {processed_count}")
                            break
                    else:
                        # Reset no change counter if anything changed
                        consecutive_no_change = 0
                    
                    # Update reference values
                    last_height = new_height
                
                # Check if we hit the max scrolls limit
                if total_scrolls >= max_scrolls:
                    print(f"[{from_city} to {to_city}] WARNING: Reached maximum scroll limit ({max_scrolls})")
                    if total_buses_expected > 0:
                        if processed_count == total_buses_expected:
                            buses_match_target = True
                            print(f"[{from_city} to {to_city}] SUCCESS: Processed exact match at scroll limit! {processed_count}/{total_buses_expected} buses")
                        else:
                            print(f"[{from_city} to {to_city}] Did not reach target bus count. Processed {processed_count}/{total_buses_expected} buses.")
                    else:
                        print(f"[{from_city} to {to_city}] Processed {processed_count} buses (unknown total).")
                
                # Final summary
                if total_buses_expected > 0:
                    if buses_match_target:
                        print(f"[{from_city} to {to_city}] ✓ FINAL RESULT: Successfully processed exact match of {processed_count}/{total_buses_expected} buses!")
                    else:
                        print(f"[{from_city} to {to_city}] ✗ FINAL RESULT: Could not process exact match. Processed {processed_count}/{total_buses_expected} buses.")
                
                print(f"\n[{from_city} to {to_city}] --- Finished processing {processed_count} buses. All data saved to {csv_file_path}")
                # Successfully processed all buses, break the main retry loop
                break

            except (TimeoutException, ConnectionRefusedError, ConnectionError, ConnectionAbortedError, ConnectionResetError) as conn_error:
                retry_count += 1
                print(f"[{from_city} to {to_city}] Connection error: {conn_error}. Retry attempt {retry_count}/{max_retries}")
                if retry_count <= max_retries:
                    # Close the previous driver if exists
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
                        driver = None
                    time.sleep(5 * retry_count)  # Incrementally longer delay between retries
                else:
                    print(f"[{from_city} to {to_city}] Failed after {max_retries} retry attempts.")
                    # Write error row to CSV file
                    try:
                        # Ensure the CSV file exists with headers
                        fieldnames = ["Bus ID", "Bus Name", "Bus Type", "Departure Time", "Arrival Time", "Journey Duration",
                                     "Lowest Price(INR)", "Highest Price(INR)", "Starting Point", "Destination",
                                     "Starting Point Parent", "Destination Point Parent"]
                        
                        # Create file with header if it doesn't exist
                        if not os.path.exists(csv_file_path):
                            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                                writer.writeheader()
                        
                        # Write error row
                        with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                            error_row = {field: "error" for field in fieldnames}
                            error_row["Bus ID"] = "error"
                            error_row["Bus Name"] = f"ERROR: Route cancelled due to timeout"  # No exception variable available
                            error_row["Starting Point Parent"] = from_city
                            error_row["Destination Point Parent"] = to_city
                            writer.writerow(error_row)
                        print(f"[{from_city} to {to_city}] Added error row to CSV file {csv_file_path}")
                    except Exception as csv_error:
                        print(f"[{from_city} to {to_city}] Error writing error row to CSV: {csv_error}")
                    
                    raise  # Re-raise the error after max retries
                
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
                    
                # For non-connection errors, retry based on retry count
                retry_count += 1
                if retry_count <= max_retries:
                    print(f"[{from_city} to {to_city}] Retrying entire process (Attempt {retry_count}/{max_retries})")
                    # Close the previous driver if exists
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
                        driver = None
                    time.sleep(5 * retry_count)  # Incrementally longer delay between retries
                else:
                    print(f"[{from_city} to {to_city}] Failed after {max_retries} retry attempts.")
                    # Write error row to CSV file
                    try:
                        # Ensure the CSV file exists with headers
                        fieldnames = ["Bus ID", "Bus Name", "Bus Type", "Departure Time", "Arrival Time", "Journey Duration",
                                     "Lowest Price(INR)", "Highest Price(INR)", "Starting Point", "Destination",
                                     "Starting Point Parent", "Destination Point Parent"]
                        
                        # Create file with header if it doesn't exist
                        if not os.path.exists(csv_file_path):
                            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                                writer.writeheader()
                        
                        # Write error row
                        with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                            error_row = {field: "error" for field in fieldnames}
                            error_row["Bus ID"] = "error"
                            error_row["Bus Name"] = f"ERROR: {str(e)[:100]}"  # Use e which is in scope
                            error_row["Starting Point Parent"] = from_city
                            error_row["Destination Point Parent"] = to_city
                            writer.writerow(error_row)
                        print(f"[{from_city} to {to_city}] Added error row to CSV file {csv_file_path}")
                    except Exception as csv_error:
                        print(f"[{from_city} to {to_city}] Error writing error row to CSV: {csv_error}")
                    
                    raise  # Re-raise the error after max retries

            finally:
                # Only quit the driver in the finally block if we're done with all retries or successful
                if driver and (retry_count > max_retries or retry_count == 0):
                    print(f"[{from_city} to {to_city}] Quitting WebDriver.")
                    driver.quit()

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
                    
            # For non-connection errors, retry based on retry count
            retry_count += 1
            if retry_count <= max_retries:
                print(f"[{from_city} to {to_city}] Retrying entire process (Attempt {retry_count}/{max_retries})")
                # Close the previous driver if exists
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = None
                time.sleep(5 * retry_count)  # Incrementally longer delay between retries
            else:
                print(f"[{from_city} to {to_city}] Failed after {max_retries} retry attempts.")
                # Write error row to CSV file
                try:
                    # Ensure the CSV file exists with headers
                    fieldnames = ["Bus ID", "Bus Name", "Bus Type", "Departure Time", "Arrival Time", "Journey Duration",
                                 "Lowest Price(INR)", "Highest Price(INR)", "Starting Point", "Destination",
                                 "Starting Point Parent", "Destination Point Parent"]
                        
                    # Create file with header if it doesn't exist
                    if not os.path.exists(csv_file_path):
                        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                            writer.writeheader()
                        
                    # Write error row
                    with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        error_row = {field: "error" for field in fieldnames}
                        error_row["Bus ID"] = "error"
                        error_row["Bus Name"] = f"ERROR: {str(e)[:100]}"  # Use e which is in scope
                        error_row["Starting Point Parent"] = from_city
                        error_row["Destination Point Parent"] = to_city
                        writer.writerow(error_row)
                    print(f"[{from_city} to {to_city}] Added error row to CSV file {csv_file_path}")
                except Exception as csv_error:
                    print(f"[{from_city} to {to_city}] Error writing error row to CSV: {csv_error}")
                
                raise  # Re-raise the error after max retries

        finally:
            # Only quit the driver in the finally block if we're done with all retries or successful
            if driver and (retry_count > max_retries or retry_count == 0):
                print(f"[{from_city} to {to_city}] Quitting WebDriver.")
                driver.quit()

def check_route_failed(csv_file_path):
    """
    Check if a route's CSV file exists and contains an error row.
    
    Args:
        csv_file_path: Path to the CSV file
        
    Returns:
        bool: True if route previously failed (has error row), False otherwise
    """
    # If file doesn't exist, route hasn't been processed yet
    if not os.path.exists(csv_file_path):
        return False
    
    try:
        # Check if file contains an error row
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header row
            for row in reader:
                # Check if any row contains "error" in Bus ID field (first column)
                if row and row[0] == "error":
                    return True
    except Exception as e:
        print(f"Error checking route failure status in {csv_file_path}: {e}")
    
    return False

def process_multiple_routes(routes_list, target_month_year, target_day, visible=False, max_retries=10, skip_failed=True):
    """
    Process multiple routes in PARALLEL, saving data for each route to a separate CSV file.

    Args:
        routes_list: List of tuples with (from_city, to_city)
        target_month_year: Month and year for all searches (e.g., "Apr 2025")
        target_day: Day of month for all searches (e.g., "20")
        visible: Whether to run the browser in visible mode (default: False)
        max_retries: Maximum number of retries for connection issues (default: 10)
        skip_failed: Whether to skip routes that previously failed (default: True)
    """
    total_routes = len(routes_list)
    routes_to_process = []
    skipped_routes = []

    print(f"\n{'='*50}")
    print(f"Starting PARALLEL batch processing of {total_routes} routes")
    print(f"Date for all routes: {target_month_year} {target_day}")
    print(f"Browser mode: {'Visible' if visible else 'Headless'}")
    print(f"Max retries per route: {max_retries}")
    print(f"Skip previously failed routes: {skip_failed}")
    print("Data for each route will be saved to a separate '{from_city}_to_{to_city}.csv' file.")
    print(f"{'='*50}\n")

    # First, check all routes to see which ones should be skipped
    if skip_failed:
        print("Checking for previously failed routes to skip...")
        for from_city, to_city in routes_list:
            route_csv_file_path = f"{from_city}_to_{to_city}.csv"
            route_info = f"{from_city} to {to_city}"
            
            if check_route_failed(route_csv_file_path):
                print(f"Skipping previously failed route: {route_info}")
                skipped_routes.append((from_city, to_city))
            else:
                routes_to_process.append((from_city, to_city))
        
        print(f"Routes to process: {len(routes_to_process)} | Skipped routes: {len(skipped_routes)}")
    else:
        # Process all routes if not skipping failed ones
        routes_to_process = routes_list
        print(f"Processing all {len(routes_to_process)} routes (not skipping any failed routes)")
    
    if not routes_to_process:
        print("No routes to process. Exiting.")
        return

    # Use ThreadPoolExecutor for parallel processing
    # Use fewer workers to reduce memory pressure
    max_workers = min(os.cpu_count() or 1, 3)  # Reduce to 3 max workers to prevent memory issues
    print(f"Using up to {max_workers} parallel workers.")

    # Execute routes in batches to prevent submitting all at once
    # This allows for better handling of failed routes in the current run
    completed_count = 0
    failed_count = 0
    active_routes = set()  # Track routes currently being processed
    routes_queue = list(routes_to_process)  # Queue of routes to process
    
    print(f"\nProcessing routes in batches with max {max_workers} concurrent routes...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Initial submission of batch
        futures_to_routes = {}  # Map futures to route info
        
        # Fill the initial worker pool
        while routes_queue and len(futures_to_routes) < max_workers:
            from_city, to_city = routes_queue.pop(0)
            route_csv_file_path = f"{from_city}_to_{to_city}.csv"
            route_info = f"{from_city} to {to_city}"
            
            print(f"Starting route: {route_info} (Output: {route_csv_file_path})")
            active_routes.add((from_city, to_city))
            
            future = executor.submit(
                search_buses,
                from_city=from_city,
                to_city=to_city,
                target_month_year=target_month_year,
                target_day=target_day,
                csv_file_path=route_csv_file_path,
                visible=visible,
                max_retries=max_retries
            )
            futures_to_routes[future] = (from_city, to_city, route_info)
        
        # Process futures as they complete and add new ones from the queue
        while futures_to_routes:
            try:
                # Wait for the next future to complete with a timeout to prevent hanging
                done, not_done = concurrent.futures.wait(
                    futures_to_routes, 
                    timeout=3600,  # 1 hour timeout per route
                    return_when=concurrent.futures.FIRST_COMPLETED
                )
                
                # If no futures completed within timeout, force cancel some
                if not done and not_done:
                    print("WARNING: No routes completed within timeout. Forcing cancellation of one route.")
                    # Pick the first route to cancel
                    future_to_cancel = list(not_done)[0]
                    from_city, to_city, route_info = futures_to_routes[future_to_cancel]
                    
                    print(f"Cancelling route: {route_info} due to timeout")
                    future_to_cancel.cancel()
                    
                    # Write error to CSV
                    csv_file_path = f"{from_city}_to_{to_city}.csv"
                    try:
                        # Ensure the CSV file exists with headers
                        fieldnames = ["Bus ID", "Bus Name", "Bus Type", "Departure Time", "Arrival Time", "Journey Duration",
                                      "Lowest Price(INR)", "Highest Price(INR)", "Starting Point", "Destination",
                                      "Starting Point Parent", "Destination Point Parent"]
                        
                        # Create file with header if it doesn't exist
                        if not os.path.exists(csv_file_path):
                            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                                writer.writeheader()
                        
                        # Write error row
                        with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                            error_row = {field: "error" for field in fieldnames}
                            error_row["Bus ID"] = "error"
                            error_row["Bus Name"] = f"ERROR: Route cancelled due to timeout"  # No exception variable available
                            error_row["Starting Point Parent"] = from_city
                            error_row["Destination Point Parent"] = to_city
                            writer.writerow(error_row)
                        print(f"Added error row to CSV file {csv_file_path} for cancelled route")
                    except Exception as csv_error:
                        print(f"Error writing error row to CSV for cancelled route: {csv_error}")
                    
                    # Remove from tracking
                    del futures_to_routes[future_to_cancel]
                    active_routes.remove((from_city, to_city))
                    failed_count += 1
                    
                    # Start a new route if any are available
                    if routes_queue:
                        next_from_city, next_to_city = routes_queue.pop(0)
                        start_new_route(executor, futures_to_routes, active_routes, next_from_city, next_to_city, 
                                       target_month_year, target_day, visible, max_retries)
                    
                    continue
                
                # Process completed futures
                for future in done:
                    from_city, to_city, route_info = futures_to_routes[future]
                    
                    try:
                        future.result()  # This will raise exceptions from the task
                        print(f"[{route_info}] Processing completed successfully.")
                        completed_count += 1
                    except Exception as e:
                        print(f"!!! ERROR processing route [{route_info}]: {e} !!!")
                        failed_count += 1
                        # Note: Error row is added to CSV in search_buses function
                    
                    # Remove the completed future
                    del futures_to_routes[future]
                    active_routes.remove((from_city, to_city))
                    
                    # Start a new route if any are available
                    if routes_queue:
                        next_from_city, next_to_city = routes_queue.pop(0)
                        start_new_route(executor, futures_to_routes, active_routes, next_from_city, next_to_city, 
                                       target_month_year, target_day, visible, max_retries)
            
            except KeyboardInterrupt:
                print("\nKeyboard interrupt detected. Shutting down gracefully...")
                # Cancel all pending futures
                for future in futures_to_routes:
                    future.cancel()
                break
            except Exception as e:
                print(f"Error in route processing loop: {e}")
                # Continue processing remaining routes
    
    print(f"\n{'='*50}")
    print(f"Batch processing finished.")
    print(f" - Successfully completed routes: {completed_count}")
    print(f" - Failed routes in this run: {failed_count}")
    if skip_failed:
        print(f" - Skipped previously failed routes: {len(skipped_routes)}")
    print(f"Total routes processed: {completed_count + failed_count}")
    print(f"Total routes in original list: {total_routes}")
    print(f"Results are saved in separate CSV files named '{{from_city}}_to_{{to_city}}.csv'.")
    print(f"Note: For failed routes, an 'error' row has been added to the CSV file.")
    print(f"{'='*50}\n")

def start_new_route(executor, futures_to_routes, active_routes, from_city, to_city, 
                   target_month_year, target_day, visible, max_retries):
    """Helper function to start a new route and add it to tracking."""
    route_csv_file_path = f"{from_city}_to_{to_city}.csv"
    route_info = f"{from_city} to {to_city}"
    
    print(f"Starting route: {route_info} (Output: {route_csv_file_path})")
    active_routes.add((from_city, to_city))
    
    future = executor.submit(
        search_buses,
        from_city=from_city,
        to_city=to_city,
        target_month_year=target_month_year,
        target_day=target_day,
        csv_file_path=route_csv_file_path,
        visible=visible,
        max_retries=max_retries
    )
    futures_to_routes[future] = (from_city, to_city, route_info)
    return future

def process_bus_element(bus, bus_id, from_city, to_city, driver):
    """Process a single bus element and return its data
    
    Args:
        bus: The WebElement representing the bus
        bus_id: ID to assign to this bus
        from_city: Origin city
        to_city: Destination city
        driver: WebDriver instance
        
    Returns:
        tuple: (bus_data_dict, bus_identifier) if successful, (None, None) if failed
    """
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
                # Click the button
                driver.execute_script("arguments[0].click();", view_seats_button)
                time.sleep(1.5)  # Wait for seat details to load

                # First, check for discount prices
                try:
                    # Check for discounted prices
                    discount_price_values = safe_extract_prices(bus, ".discountPrice li.disPrice:not(.price-selected)")

                    if discount_price_values:
                        lowest_price = min(discount_price_values)
                        highest_price = max(discount_price_values)
                    else:
                        # Check for non-discount prices (multiFare)
                        multi_fare_values = safe_extract_prices(bus, ".multiFare li.mulfare:not(.price-selected)")

                        if multi_fare_values:
                            lowest_price = min(multi_fare_values)
                            highest_price = max(multi_fare_values)
                        else:
                            # If neither discount nor multi-fare prices were found,
                            # try more generic price selectors as a last resort
                            all_price_values = safe_extract_prices(bus, "[data-price]:not([data-price='ALL'])")
                            if all_price_values:
                                lowest_price = min(all_price_values)
                                highest_price = max(all_price_values)

                except Exception as price_error:
                    print(f"Error extracting detailed prices for bus {bus_id}: {price_error}")
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
                                    time.sleep(0.5)
                                    hide_button_clicked = True
                                    break

                    # Last resort - just scroll away from this bus element to force UI to collapse
                    if not hide_button_clicked:
                        driver.execute_script("arguments[0].scrollIntoView(false);", bus)
                        time.sleep(0.5)

                except Exception as hide_error:
                    print(f"Error handling hide seats for bus {bus_id}: {hide_error}")
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

        # Create a unique identifier for this bus
        bus_identifier = f"{bus_name}_{bus_type}_{dep_time}"
        
        return (bus_data, bus_identifier)
        
    except Exception as e:
        print(f"ERROR processing bus ID {bus_id}: {e}")
        return (None, None)

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
        # ("Hyderabad", "Tirupathi"),
        # ("Pune", "Goa"),
        # ("Pune", "Mumbai"),
        # ("Pune", "Nagpur"),
        # ("Pune", "Kolhapur"),
        # ("Pune", "Nashik"),
        # ("Mumbai", "Goa"),
        # ("Mumbai", "Pune"),
        # ("Mumbai", "Shirdi"), done
        # ("Mumbai", "Mahabaleshwar"), done
        # ("Mumbai", "Kolhapur"), error 191
        # ("Kolkata", "Digha"), error 255
        # ("Kolkata", "Siliguri"), done
        # ("Kolkata", "Puri"), done
        # ("Kolkata", "Bakkhali"), done 
        # ("Kolkata", "Mandarmani"), done
    #     ("Chennai", "Bangalore"),
    #     # ("Chennai", "Pondicherry"),done
    #     ("Chennai", "Coimbatore"),
    #     ("Chennai", "Madurai"),
    # #     ("Chennai", "Tirupathi"),
    #     ("Chandigarh", "Manali"),
    # #     ("Chandigarh", "Shimla"),
    #     ("Chandigarh", "Delhi"),
    # #     ("Chandigarh", "Dehradun"),
    # #     ("Chandigarh", "Amritsar"),
    #     ("Coimbatore", "Chennai"),
    #     ("Coimbatore", "Bangalore"),
    #     ("Coimbatore", "Ooty"),
    #     ("Coimbatore", "Tiruchendur"),
    #     ("Coimbatore", "Madurai"),
    #     ("Agra", "Bareilly"),
    #     ("Hisar", "Chandigarh"),
    #     ("Ayodhya", "Varanasi"),
    #     ("Lucknow", "Ballia"),
    #     ("Lucknow", "Moradabad"),
    #     ("Rajkot", "Dwarka"),
    #     ("Siliguri", "Gangtok"),
    #     ("Ahmedabad", "Goa"),
    #     ("Ahmedabad", "Kanpur"),
    #     ("Akola", "Pune"),
        ("Delhi", "Dehradun"),
        ("Delhi", "Haridwar"),
        ("Dehradun", "Delhi"),
        ("Delhi", "Agra"),
    #     ("Delhi", "Varanasi")
    ]
    
    # Set common date for all routes
    target_month_year = "Apr 2025"
    target_day = "20"
    
    # Parse command line arguments
    import sys
    
    visible_browser = "--visible" in sys.argv
    single_route = "--single" in sys.argv
    max_retries = 5  # Default max retries
    skip_failed_routes = not ("--no-skip" in sys.argv)  # Skip failed routes by default
    
    # Check for custom max retries argument
    for arg in sys.argv:
        if arg.startswith("--retries="):
            try:
                max_retries = int(arg.split("=")[1])
                print(f"Setting max retries to {max_retries}")
            except:
                print(f"Invalid retries value, using default {max_retries}")
    
    if single_route:
        # Process just a single route for testing
        print("Running in single route mode (for testing)")
        print(f"Browser mode: {'Visible' if visible_browser else 'Headless'}")
        print(f"Max retries: {max_retries}")
        input_from_city = "Delhi"
        input_to_city = "Dehradun"
        csv_file_path = f"{input_from_city}_to_{input_to_city}.csv"
        
        # Check if route previously failed and confirm whether to proceed
        if skip_failed_routes and check_route_failed(csv_file_path):
            print(f"Route {input_from_city} to {input_to_city} previously failed.")
            proceed = input("Do you want to proceed anyway? (y/n): ")
            if proceed.lower() != 'y':
                print("Exiting without processing route.")
                sys.exit(0)
        
        search_buses(input_from_city, input_to_city, target_month_year, target_day, csv_file_path, visible=visible_browser, max_retries=max_retries)
    else:
        # Process all routes in parallel
        process_multiple_routes(routes_to_process, target_month_year, target_day, visible=visible_browser, max_retries=max_retries, skip_failed=skip_failed_routes)