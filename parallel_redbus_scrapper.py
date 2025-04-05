from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException, WebDriverException
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
                results_indicator_xpath = "//ul[contains(@class,'bus-items')] | //div[contains(@class,'result-section')] | //div[contains(@class,'travels')] | //span[contains(@class, 'busFound')]"
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, results_indicator_xpath))
                )
                print(f"[{from_city} to {to_city}] Search results page loaded.")

                print(f"\n[{from_city} to {to_city}] --- PHASE 1: Dynamic View Buses button clicking --- (May be skipped if not necessary)")

                # Reset to top of page first
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2) # Increased wait

                # *** Conditional "View Buses" Clicking ***
                view_buses_xpath = "//div[contains(@class,'button') and contains(text(),'View Buses') and not(contains(text(), 'Hide'))]"
                initial_view_buttons = []
                try:
                    # Use a short wait to see if these buttons exist quickly
                    initial_view_buttons = WebDriverWait(driver, 3).until(
                        EC.presence_of_all_elements_located((By.XPATH, view_buses_xpath))
                    )
                except TimeoutException:
                     print(f"[{from_city} to {to_city}] No initial 'View Buses' buttons found quickly.")
                     initial_view_buttons = [] # Ensure it's empty

                if initial_view_buttons:
                    print(f"[{from_city} to {to_city}] Found {len(initial_view_buttons)} initial 'View Buses' buttons. Proceeding to click them.")
                    # ... (Keep the scrolling and clicking loop for View Buses as it was) ...
                    # ... but ensure delays inside this loop are sufficient (e.g., time.sleep(3) after click) ...
                    print(f"[{from_city} to {to_city}] Completed Phase 1 clicking.")
                else:
                    print(f"[{from_city} to {to_city}] No initial 'View Buses' buttons found. Skipping Phase 1 clicking.")


                # Ensure we are at the top before Phase 2
                print(f"[{from_city} to {to_city}] Final scroll to top before Phase 2.")
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1.5) # Slightly increased wait

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
                        # Only create/check the file once
                        if not csv_exists or os.path.getsize(csv_file_path) == 0:
                            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                                writer.writeheader()
                                print(f"[{from_city} to {to_city}] Created new CSV file with headers: {csv_file_path}")
                        else:
                            print(f"[{from_city} to {to_city}] CSV file {csv_file_path} exists. Will append data.")
                    except IOError as e:
                        print(f"[{from_city} to {to_city}] Error preparing CSV file {csv_file_path}: {e}")
                        raise # Re-raise the error to stop processing for this route

                print(f"[{from_city} to {to_city}] Found {len(bus_elements)} bus results after scrolling. Processing and saving to {csv_file_path}...")
                for index, bus in enumerate(bus_elements):
                    bus_processed = False
                    bus_retry_count = 0 # Retries for THIS specific bus item if needed (optional, maybe remove)

                    # Remove the inner bus_retry_count loop unless specifically needed
                    # The main retry loop handles larger errors like tab crashes.
                    # while not bus_processed and bus_retry_count <= max_retries: # Consider removing this inner loop

                    try:
                        bus_id = index + 1
                        # ... (extract basic bus details: name, type, time, etc.) ...

                        # --- View Seats Logic ---
                        view_seats_button = None
                        try:
                            # Try finding the button within the bus context more reliably
                            view_seats_xpath_relative = ".//div[contains(@class, 'button') and (contains(normalize-space(),'View Seats') or contains(normalize-space(),'VIEW SEATS'))]"
                            # Wait briefly for the button within the bus element
                            view_seats_button = WebDriverWait(bus, 5).until(
                                EC.element_to_be_clickable((By.XPATH, view_seats_xpath_relative))
                            )
                        except TimeoutException:
                            # Fallback to previous selectors if the wait fails
                            view_seats_selectors = [ # Keep your existing selectors as fallback
                                ".button.view-seats", ".view-seats", "div.button.view-seats",
                                "div.view-seats", ".button:not(.hide-seats)", "div.button:not(.hide-seats)"
                            ]
                            for selector in view_seats_selectors:
                                try:
                                    buttons = bus.find_elements(By.CSS_SELECTOR, selector)
                                    for btn in buttons:
                                        btn_text = btn.text.strip()
                                        if btn.is_displayed() and ("VIEW SEATS" in btn_text.upper() or "View Seats" in btn_text):
                                            view_seats_button = btn
                                            break
                                    if view_seats_button: break
                                except Exception: continue
                        except Exception as find_err:
                            print(f"[{from_city} to {to_city}] Error finding view seats button for bus {bus_id}: {find_err}")


                        if view_seats_button:
                            try:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", view_seats_button)
                                time.sleep(0.5)
                                driver.execute_script("arguments[0].click();", view_seats_button)
                                time.sleep(2.5)  # *** Increased wait after clicking View Seats ***

                                # ... (Extract prices logic - keep as is) ...

                                # --- Hide Seats Logic ---
                                hide_button_clicked = False
                                try:
                                    # Try finding hide button more reliably
                                    hide_xpath_relative = ".//div[contains(@class, 'hideSeats') or contains(@class, 'hide-seats') or contains(text(), 'Hide Seats') or contains(text(), 'HIDE SEATS')]"
                                    # Wait briefly for hide button
                                    hide_button = WebDriverWait(bus, 5).until(
                                        EC.element_to_be_clickable((By.XPATH, hide_xpath_relative))
                                    )
                                    if hide_button and hide_button.is_displayed():
                                         driver.execute_script("arguments[0].click();", hide_button)
                                         time.sleep(1.0) # *** Wait after clicking Hide Seats ***
                                         hide_button_clicked = True
                                except TimeoutException:
                                    # Fallback to previous selectors/scroll if wait fails
                                    print(f"[{from_city} to {to_city}] Could not find hide button via wait for bus {bus_id}, trying fallbacks...")
                                    # ... (Keep your existing hide button fallback logic here - selectors, text search, scroll) ...
                                    # ... Ensure there's a time.sleep(1.0) after any successful hide click in fallbacks ...
                                except Exception as hide_err:
                                     print(f"[{from_city} to {to_city}] Error clicking hide seats for bus {bus_id}: {hide_err}")

                                if not hide_button_clicked:
                                     print(f"[{from_city} to {to_city}] Failed to click hide seats for bus {bus_id} after fallbacks.")
                                     # Might need to scroll away to ensure it collapses
                                     driver.execute_script("arguments[0].scrollIntoView(false);", bus)
                                     time.sleep(0.5)

                            except Exception as seats_processing_error:
                                print(f"[{from_city} to {to_city}] Error during view/hide seats processing for bus {bus_id}: {seats_processing_error}")
                                # Attempt to hide if possible, otherwise scroll away
                                try:
                                    # Minimal attempt to close
                                    hide_xpath = ".//*[contains(text(), 'HIDE SEATS') or contains(text(), 'Hide Seats')]"
                                    hide_elements = bus.find_elements(By.XPATH, hide_xpath)
                                    for el in hide_elements:
                                        if el.is_displayed():
                                            driver.execute_script("arguments[0].click();", el)
                                            time.sleep(0.5)
                                            break
                                except:
                                    driver.execute_script("arguments[0].scrollIntoView(false);", bus) # Scroll away as last resort
                                    time.sleep(0.5)

                        else:
                            print(f"[{from_city} to {to_city}] Could not find/click View Seats button for bus {bus_id}")

                        # ... (Prepare bus_data dictionary) ...

                        # Write to CSV
                        try:
                            with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
                                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                                writer.writerow(bus_data)
                            # print(f"[{from_city} to {to_city}] Bus {bus_id} data saved.") # Reduce noise
                            bus_processed = True
                        except Exception as csv_error:
                            print(f"[{from_city} to {to_city}] Error saving bus {bus_id} to CSV: {csv_error}")
                            # Decide if CSV write error should trigger main retry or just log
                            # For now, let it propagate to the outer loop if critical


                    except Exception as e:
                        print(f"[{from_city} to {to_city}] ERROR processing bus index {index} (ID: {bus_id}): {e}")
                        # Let this error propagate to the main retry loop by re-raising
                        raise e

                    # *** Add small delay between processing buses ***
                    time.sleep(0.15) # Adjust as needed (0.1 to 0.3 seconds)


                print("-" * 30)
                print(f"[{from_city} to {to_city}] Finished processing {len(bus_elements)} buses. Data saved to {csv_file_path}")
                # Successfully processed all buses, break the main retry loop
                break # Exit the while retry_count loop

            # --- Exception Handling for the Main Processing Block ---
            except (TimeoutException, ConnectionRefusedError, ConnectionError, ConnectionAbortedError, ConnectionResetError) as conn_error:
                retry_count += 1
                print(f"[{from_city} to {to_city}] Connection error: {conn_error}. Retry attempt {retry_count}/{max_retries}")
                # ... (keep existing connection error retry logic) ...
            except WebDriverException as wde: # *** Catch WebDriverException ***
                 retry_count += 1
                 # *** Check for Tab Crash specifically ***
                 if "tab crashed" in str(wde).lower():
                     print(f"[{from_city} to {to_city}] TAB CRASH DETECTED. Retry attempt {retry_count}/{max_retries}. Error: {wde}")
                 else:
                     print(f"[{from_city} to {to_city}] WebDriverException: {wde}. Retry attempt {retry_count}/{max_retries}")
                 # ... (keep existing retry logic: quit driver, sleep, etc.) ...
            except Exception as e:
                retry_count += 1
                print(f"[{from_city} to {to_city}] An unexpected error occurred during processing: {e}. Retry attempt {retry_count}/{max_retries}")
                # ... (keep existing generic error retry logic: screenshot, quit driver, sleep, etc.) ...

        # --- Outer Exception Handling (e.g., initial page load fails) ---
        except (WebDriverException, TimeoutException, ConnectionError) as initial_error:
             retry_count += 1
             print(f"[{from_city} to {to_city}] Initial setup/connection error: {initial_error}. Retry attempt {retry_count}/{max_retries}")
             if driver:
                 try: driver.quit()
                 except: pass
                 driver = None
             if retry_count > max_retries:
                  print(f"[{from_city} to {to_city}] Failed initial setup after {max_retries} retries.")
                  # Write error row (ensure this logic is robust)
                  # ... (keep existing logic to write error row to CSV on final failure) ...
                  raise initial_error # Re-raise after handling
             time.sleep(5 * retry_count) # Exponential backoff

        except Exception as outer_e:
            # Handle unexpected errors outside the main processing try-block
            print(f"[{from_city} to {to_city}] A critical unexpected error occurred: {outer_e}")
            if driver:
                try:
                     # Save screenshot if possible
                     timestamp = time.strftime("%Y%m%d-%H%M%S")
                     screenshot_path = f'critical_error_screenshot_{from_city}_to_{to_city}_{timestamp}.png'
                     driver.save_screenshot(screenshot_path)
                     print(f"[{from_city} to {to_city}] Screenshot saved as {screenshot_path}")
                except Exception as ss_error:
                     print(f"[{from_city} to {to_city}] Failed to save screenshot during critical error: {ss_error}")
            # Write error row
            # ... (keep existing logic to write error row to CSV on final failure) ...
            raise outer_e # Re-raise the critical error

        finally:
            # Ensure driver is quit if it exists and we are done retrying or succeeded
            if driver and (retry_count > max_retries or (retry_count == 0 and 'bus_elements' in locals())): # Quit if failed all retries OR succeeded on first try
                 try:
                     print(f"[{from_city} to {to_city}] Quitting WebDriver in finally block.")
                     driver.quit()
                 except Exception as quit_error:
                     print(f"[{from_city} to {to_city}] Error quitting WebDriver: {quit_error}")
                 driver = None # Ensure driver is None after quitting

    # Final check: if loop finished due to max_retries, ensure error is recorded
    if retry_count > max_retries:
        print(f"[{from_city} to {to_city}] Process failed finally after {max_retries} retries.")
        # Ensure error row is written if not already done by exception blocks
        try:
            if not check_route_failed(csv_file_path): # Avoid duplicate error rows
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
                     # Try to get the last error message if possible
                     last_error_msg = "Max retries exceeded"
                     # Note: Accessing the specific error that caused the last retry failure here is tricky.
                     # We'll use a generic message. The logs should contain the specific error.
                     error_row["Bus Name"] = f"ERROR: {last_error_msg}"
                     error_row["Starting Point Parent"] = from_city
                     error_row["Destination Point Parent"] = to_city
                     writer.writerow(error_row)
                 print(f"[{from_city} to {to_city}] Added final error row to CSV file {csv_file_path}")
        except Exception as final_csv_error:
             print(f"[{from_city} to {to_city}] Error writing final error row to CSV: {final_csv_error}")

def check_route_failed(csv_file_path):
    """
    Check if a route's CSV file exists and contains an error row.
    """
    if not os.path.exists(csv_file_path):
        return False
    if os.path.getsize(csv_file_path) == 0: # Handle empty files
        return False

    try:
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            try:
                header = next(reader) # Check if header exists
                if not header: return False # Empty header means invalid file
            except StopIteration:
                return False # File is empty or has no header

            for row in reader:
                # Check if the row is not empty and the first column is exactly "error"
                if row and len(row) > 0 and row[0].strip() == "error":
                    return True
    except Exception as e:
        print(f"Error checking route failure status in {csv_file_path}: {e}")
        # Treat check error as "not failed" to avoid skipping unnecessarily
        return False

    return False

def process_multiple_routes(routes_list, target_month_year, target_day, visible=False, max_retries=10, skip_failed=True):
    """
    Process multiple routes in PARALLEL, saving data for each route to a separate CSV file.

    Args:
        routes_list: List of tuples with (from_city, to_city)
        target_month_year: Month and year for all searches (e.g., "Apr 2025")
        target_day: Day of month for all searches (e.g., "20")
        visible: Whether to run the browser in visible mode (default: False)
        max_retries: Maximum number of retries for connection issues (default: 3)
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
    # Determine max_workers based on CPU or a reasonable default like 4-8
    # Too many workers might consume too much RAM/CPU or trigger anti-scraping
    max_workers = min(os.cpu_count() or 1, 4) # Limit to 4 workers initially, can be adjusted
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
            # Wait for the next future to complete
            done, _ = concurrent.futures.wait(
                futures_to_routes, 
                return_when=concurrent.futures.FIRST_COMPLETED
            )
            
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
                    next_route_csv_file_path = f"{next_from_city}_to_{next_to_city}.csv"
                    next_route_info = f"{next_from_city} to {next_to_city}"
                    
                    print(f"Starting route: {next_route_info} (Output: {next_route_csv_file_path})")
                    active_routes.add((next_from_city, next_to_city))
                    
                    next_future = executor.submit(
                        search_buses,
                        from_city=next_from_city,
                        to_city=next_to_city,
                        target_month_year=target_month_year,
                        target_day=target_day,
                        csv_file_path=next_route_csv_file_path,
                        visible=visible,
                        max_retries=max_retries
                    )
                    futures_to_routes[next_future] = (next_from_city, next_to_city, next_route_info)
    
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

if __name__ == "__main__":
    # Parse the route list
    routes_to_process = [
        # # ("Delhi", "Manali"),
        # # ("Delhi", "Rishikesh"),
        # # ("Delhi", "Shimla"),
        # # ("Delhi", "Nainital"),
        # # ("Delhi", "Katra"),
        # # ("Bangalore", "Goa"),
        # # ("Bangalore", "Hyderabad"),
        # # ("Bangalore", "Tirupathi"),
        # # ("Bangalore", "Chennai"),
        # # ("Bangalore", "Pondicherry"),
        # # ("Hyderabad", "Bangalore"),
        # # ("Hyderabad", "Goa"),
        # # ("Hyderabad", "Srisailam"),
        # # ("Hyderabad", "Vijayawada"),
        # # ("Hyderabad", "Tirupathi"),
        # # ("Pune", "Goa"),
        # # ("Pune", "Mumbai"),
        # # ("Pune", "Nagpur"),
        # # ("Pune", "Kolhapur"),
        # # ("Pune", "Nashik"),
        # # ("Mumbai", "Goa"),
        # # ("Mumbai", "Pune"),
        # # ("Mumbai", "Shirdi"), done
        # # ("Mumbai", "Mahabaleshwar"), done
        # # ("Mumbai", "Kolhapur"), error 191
        # # ("Kolkata", "Digha"), error 255
        # # ("Kolkata", "Siliguri"), done
        # # ("Kolkata", "Puri"), done
        # # ("Kolkata", "Bakkhali"), done 
        # # ("Kolkata", "Mandarmani"), done
        # # ("Chennai", "Bangalore"),  error 160
        # # ("Chennai", "Pondicherry"),done
        # # ("Chennai", "Coimbatore"), 156
        # # ("Chennai", "Madurai"), 321
        # ("Chennai", "Tirupathi"),
        # # ("Chandigarh", "Manali"),
        # ("Chandigarh", "Shimla"),
        # # ("Chandigarh", "Delhi"),
        # ("Chandigarh", "Dehradun"),
        # ("Chandigarh", "Amritsar"),
        # # ("Coimbatore", "Chennai"),
        # # ("Coimbatore", "Bangalore"),
        # ("Coimbatore", "Ooty"),
        # ("Coimbatore", "Tiruchendur"),
        # ("Coimbatore", "Madurai"),
        # ("Agra", "Bareilly"),
        # ("Hisar", "Chandigarh"),
        # ("Ayodhya", "Varanasi"),
        # ("Lucknow", "Ballia"),
        # ("Lucknow", "Moradabad"),
        # ("Rajkot", "Dwarka"),
        # ("Siliguri", "Gangtok"),
        # ("Ahmedabad", "Goa"),
        # ("Ahmedabad", "Kanpur"),
        # ("Akola", "Pune"),
        ("Delhi", "Dehradun"),
        ("Delhi", "Haridwar"),
        ("Dehradun", "Delhi"),
        ("Delhi", "Agra"),
        # ("Delhi", "Varanasi")
    ]
    
    # Set common date for all routes
    target_month_year = "Apr 2025"
    target_day = "20"
    
    # Parse command line arguments
    import sys
    
    visible_browser = "--visible" in sys.argv
    single_route = "--single" in sys.argv
    max_retries = 3  # Default max retries
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
        input_from_city = "Mumbai"
        input_to_city = "Thane"
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