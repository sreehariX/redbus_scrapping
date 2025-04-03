from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
import time
import json

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

def setup_driver(headless=False):
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--start-maximized')
    # options.add_argument('--headless') to run without browser being shown
    
    return webdriver.Chrome(options=options)

def search_buses(from_city, to_city, target_month_year, target_day):
    driver = setup_driver(headless=False)
    
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

            print("\n--- Scrolling to load all buses ---")
            last_height = driver.execute_script("return document.body.scrollHeight")
            bus_elements_selector = "ul.bus-items li.row-sec"
            scroll_pause_time = 2.0
            max_scroll_attempts = 15
            scroll_attempts = 0

            while scroll_attempts < max_scroll_attempts:
                buses_before_scroll = len(driver.find_elements(By.CSS_SELECTOR, bus_elements_selector))
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause_time)
                new_height = driver.execute_script("return document.body.scrollHeight")
                buses_after_scroll = len(driver.find_elements(By.CSS_SELECTOR, bus_elements_selector))

                print(f"Scroll attempt {scroll_attempts+1}: Height {last_height}->{new_height}, Buses {buses_before_scroll}->{buses_after_scroll}")

                if new_height == last_height and buses_after_scroll == buses_before_scroll:
                    print("Reached bottom and no new buses loaded.")
                    break

                last_height = new_height
                scroll_attempts += 1
                if scroll_attempts == max_scroll_attempts:
                    print("Warning: Reached max scroll attempts, might not have loaded all buses.")

            print("\n--- Processing Bus Details ---")
            bus_elements = driver.find_elements(By.CSS_SELECTOR, bus_elements_selector)
            json_file_path = 'bus_data.json'
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
                    with open(json_file_path, 'w', encoding='utf-8') as f:
                        json.dump({"status": "No results found"}, f, indent=4, ensure_ascii=False)
                    print(f"Saved 'No results found' status to {json_file_path}")
                except IOError as e:
                    print(f"Error writing 'No results found' to JSON file {json_file_path}: {e}")

            else:
                try:
                    with open(json_file_path, 'w') as f:
                        json.dump([], f)
                    print(f"Initialized/Cleared {json_file_path} for bus data.")
                except IOError as e:
                    print(f"Error initializing JSON file {json_file_path}: {e}")

                print(f"Found {len(bus_elements)} bus results after scrolling. Processing and saving...")
                for index, bus in enumerate(bus_elements):
                    bus_id = index + 1
                    print("-" * 30)
                    print(f"Processing Bus {bus_id}/{len(bus_elements)}")

                    try:
                        bus_name = safe_find_text(bus, By.CSS_SELECTOR, ".travels", default="Not Found")
                        dep_time = safe_find_text(bus, By.CSS_SELECTOR, ".dp-time", default="Not Found")
                        dep_loc = safe_find_attribute(bus, By.CSS_SELECTOR, ".dp-loc", 'title', default="Not Found")
                        arr_time = safe_find_text(bus, By.CSS_SELECTOR, ".bp-time", default="Not Found")
                        arr_loc = safe_find_attribute(bus, By.CSS_SELECTOR, ".bp-loc", 'title', default="Not Found")
                        duration = safe_find_text(bus, By.CSS_SELECTOR, ".dur", default="Not Found")

                        try:
                            fare = bus.find_element(By.CSS_SELECTOR, ".fare .f-bold").text
                            fare_price_str = f"INR {fare}"
                        except NoSuchElementException:
                            fare_price_str = "Not Found"

                        start_point = dep_loc if dep_loc != "Not Found" else from_city
                        end_point = arr_loc if arr_loc != "Not Found" else to_city

                        bus_data = {
                            "Bus ID": bus_id,
                            "Bus Name": bus_name,
                            "Departure": dep_time,
                            "Journey Duration": duration,
                            "Fare Price": fare_price_str,
                            "Starting Point": start_point,
                            "Destination": end_point
                        }

                        print(f"Bus ID: {bus_id}")
                        print(f"Bus Name: {bus_name}")
                        print(f"Departure: {dep_time}")
                        print(f"Journey Duration: {duration}")
                        print(f"Fare Price: {fare_price_str}")
                        print(f"Starting Point: {start_point}")
                        print(f"Destination: {end_point}")

                        all_buses_data.append(bus_data)

                        try:
                            with open(json_file_path, 'w', encoding='utf-8') as f:
                                json.dump(all_buses_data, f, indent=4, ensure_ascii=False)
                        except IOError as e:
                            print(f"Error writing to JSON file for bus {bus_id}: {e}")
                        except Exception as e:
                            print(f"An unexpected error occurred during JSON writing for bus {bus_id}: {e}")

                    except Exception as e:
                        print(f"ERROR processing bus {bus_id}: {e}")
                        print("Attempting to continue with the next bus...")

                print("-" * 30)
                print(f"Finished processing {len(all_buses_data)} buses. Full data saved to {json_file_path}")

        except TimeoutException:
            print("Error: Search results page structure did not load within the timeout period.")
            try:
                 with open(json_file_path, 'w', encoding='utf-8') as f:
                     json.dump({"status": "Error - Results page did not load"}, f, indent=4, ensure_ascii=False)
            except IOError as e:
                 print(f"Error writing error status to JSON: {e}")

        input("Press Enter to close the browser...")

    except Exception as e:
         print(f"An unexpected error occurred: {e}")
         timestamp = time.strftime("%Y%m%d-%H%M%S")
         driver.save_screenshot(f'error_screenshot_{timestamp}.png')
         print(f"Screenshot saved as error_screenshot_{timestamp}.png")

    finally:
        print("Quitting WebDriver.")
        if 'driver' in locals() and driver:
             driver.quit()

if __name__ == "__main__":
    input_from_city = "Powai"
    input_to_city = "Thane"
    input_month_year = "Apr 2025"
    input_day = "25"

    search_buses(input_from_city, input_to_city, input_month_year, input_day)