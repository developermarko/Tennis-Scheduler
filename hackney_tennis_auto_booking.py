#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
import time
from prettytable import PrettyTable
#from IPython.display import display, HTML
import json
import os

# Array of parks to cycle through
parks = [
    "LondonFieldsPark",
    "ClissoldParkHackney",
    "HackneyDowns",
    "AskeGardens",
    "MillfieldsParkMiddlesex",
    "SpringHillParkTennis"
]

# Function to get the date for a specific number of days in the future in full date and month name and day and day of week
def get_future_date(days_from_now):
    date = (datetime.today() + timedelta(days=days_from_now))
    return date.strftime('%Y-%m-%d')

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run Chrome in headless mode
chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems

# Initialize the WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# Dictionary to store results {park: {date: [available slots]}}
park_data = {}

try:
    for park in parks:
        park_data[park] = {}  # Initialize the dictionary for the park
        
        for day in range(7):  # Iterate from today (0) to the next 6 days (6)
            # Get the date for today and the next 6 days
            # Need to add if statement to check if it's past 8PM currently to start checking for tomorrow onward, as it sometimes sends slots from earlier in the day, seems to be after 8PM
            if datetime.today().strftime('%H:%M') > '20:00':
                date_str = get_future_date(day+1) #for input in the URL and eventually output html
            else:
                date_str = get_future_date(day) #for input in the URL and eventually output html
                
            url = f"https://clubspark.lta.org.uk/{park}/Booking/BookByDate#?date={date_str}&role=guest"
            driver.get(url)
            time.sleep(1)
    
            # Wait for the element to be present
            wait = WebDriverWait(driver, 20)  # Increased wait time
    
            try:
                # Wait for the date header to appear
                date_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'pull-left')))
    
                while True:
                    try:
                        # Locate the table with class 'booking-sheet clearfix'
                        table = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'booking-sheet.clearfix')))
                        
                        # Locate all cells with the class 'book-interval not-booked'
                        not_booked_cells = table.find_elements(By.CLASS_NAME, 'book-interval.not-booked')

                        # Initialize an empty list for storing available slots for this day
                        park_data[park][date_str] = []

                        if not_booked_cells:
                            for cell in not_booked_cells:
                                available_slot_element = cell.find_element(By.CLASS_NAME, 'available-booking-slot')
                                available_slot_inner_html = available_slot_element.get_attribute('innerHTML').strip()
                                
                                cost_element = cell.find_element(By.CLASS_NAME, 'cost')
                                cost_text = cost_element.text.strip()

                                # Only append non-free and non-empty slots
                                if cost_text and cost_text.lower() != "free":
                                    park_data[park][date_str].append(f"{available_slot_inner_html} (Cost: {cost_text}) (URL: {url})")
    
                        break  # Exit loop if successful
                    except StaleElementReferenceException:
                        print("Encountered stale element reference, retrying...")
                        time.sleep(1)
    
            except TimeoutException:
                print("Element not found within the given time.")

finally:
    driver.quit()  # Close the driver when done

# Helper function to extract the time slot and cost from slot text
def extract_time_cost_and_url(slot_text):
    try:
        time_part = slot_text.split(' ')[2]  # Extract '09:00 - 10:00'
        cost_part = slot_text.split('(Cost: ')[1].split(')')[0]  # Extract '£3.65'
        url_part = slot_text.split('(URL: ')[1].replace(')', '')  # Extract URL
        return time_part, cost_part, url_part
    except IndexError:
        return None, None, None

#Function to load and compare slots for updated availability
def load_and_compare_slots(file_path, live_data):
    """
    Loads saved booking slots from a file, compares them with live booking slots, 
    and returns a dictionary of new booking slots.
    
    Parameters:
        file_path (str): Path to the JSON file storing the previous booking slots.
        live_data (dict): Live booking slots data fetched from the website.
    
    Returns:
        dict: Dictionary containing new booking slots that were not in the saved file.
    """
    try:
        # Load the previously saved slots from the file
        with open(file_path, 'r') as file:
            saved_data = json.load(file)
    except FileNotFoundError:
        # If the file doesn't exist, assume there are no saved slots
        saved_data = {}

    # Compare live data with saved data
    new_slots = {}
    for location, dates in live_data.items():
        new_slots[location] = {}
        for date, slots in dates.items():
            # If the date exists in saved data, find new slots
            if location in saved_data and date in saved_data[location]:
                # Find the slots that are in live data but not in saved data
                new_slots[location][date] = [
                    slot for slot in slots if slot not in saved_data[location][date]
                ]
            else:
                # If the location or date doesn't exist in saved data, all slots are new
                new_slots[location][date] = slots

    # Remove empty entries (no new slots for a location/date)
    new_slots = {
        location: {date: slots for date, slots in dates.items() if slots}
        for location, dates in new_slots.items()
        if any(dates.values())
    }

    return new_slots

# Load the desired availability JSON to show filtered availability based on your exact preferences, not just all updates
with open("desired_availability.json", "r") as file:
    desired_availability = json.load(file)

# Helper function to check if a slot matches any of the desired availability criteria, only used for filtered availability updates, not all availability updates
def matches_desired_availability(location, day_of_week, time, desired_availability):
    # Check if the park exists in the data
    if location in desired_availability:
        # Check if the day exists for this park
        if day_of_week in desired_availability[location]:
            # Check if the time is available
            if time in desired_availability[location][day_of_week]:
                return True
    return False

#Function to load and compare slots for updated availability WITH FILTERS, so you either call this function or the one above with no _with_filter at the end, if you want general availability updates
def load_and_compare_slots_with_filter(file_path, live_data, desired_availability):
    """
    Loads saved booking slots, compares them with live booking slots, 
    and filters by desired availability.
    
    Parameters:
        file_path (str): Path to the JSON file storing the previous booking slots.
        live_data (dict): Live booking slots data fetched from the website.
        desired_availability (list): List of dictionaries specifying desired availability.
    
    Returns:
        dict: Dictionary containing new booking slots that match the desired availability.
    """
    try:
        # Load the previously saved slots from the file
        with open(file_path, 'r') as file:
            saved_data = json.load(file)
    except FileNotFoundError:
        # If the file doesn't exist, assume there are no saved slots
        saved_data = {}

    # Compare live data with saved data and filter by desired availability
    new_slots = {}
    for location, dates in live_data.items():
        new_slots[location] = {}
        for date, slots in dates.items():
            # If the date exists in saved data, find new slots
            if location in saved_data and date in saved_data[location]:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                filtered_slots = [
                    slot for slot in slots
                    if slot not in saved_data[location][date] and
                       matches_desired_availability(location, f'{date_obj.strftime("%A")}', extract_time_cost_and_url(slot)[0], desired_availability)  # **Filter slots incl. extract time from the slot**
                ]
                if filtered_slots:
                    new_slots[location][date] = filtered_slots
            else:
                # If the location or date doesn't exist in saved data, filter all slots
                filtered_slots = [
                    slot for slot in slots
                    if matches_desired_availability(location, f'{date_obj.strftime("%A")}', extract_time_cost_and_url(slot)[0], desired_availability)  # **Filter slots incl. extract time from the slot**
                ]
                if filtered_slots:
                    new_slots[location][date] = filtered_slots

    # Remove empty entries (no new slots for a location/date)
    new_slots = {
        location: {date: slots for date, slots in dates.items() if slots}
        for location, dates in new_slots.items()
        if any(dates.values())
    }

    return new_slots
# Output the updated availability with comparison if previous file exists to compare to, otherwise the avalability updates will just be an  empty dictionary
# And everything will be new
# If you want unfiltered, general hourly updates, then instead of calling load_and_compare_slots_with_filter, call without the "_with_filter" at the end
if os.path.exists("park_data.json"): 
    availability_updates = load_and_compare_slots_with_filter("park_data.json", park_data, desired_availability)
else:
    availability_updates = {}
    
# Write the updates to a new file IF there are updates (check if updates dictionary is empty)
# If not any updates, try and delete any old availability json file in the folder, so we don't send a redundant email (based on logic in other files) 
# First, check if the output is not empty
if availability_updates:  # This checks if the dictionary is not empty
    try:
        with open("availability_updates.html", "w") as file:
            #write the json data to the file in html to be emailed later
            for park, dates in availability_updates.items():
                # Write the park name to the HTML file
                file.write(f"<h2 style='color:#A8E1D4;'>{park}</h2>")  # Add park name in color
        
                # Start constructing the HTML table for this park
                html_table = "<table style='border-collapse: collapse; width: 100%;'><thead><tr>"
                html_table += "<th style='border: 1px solid #ddd; padding: 8px;'>Time Slot</th>"
        
                # Add the date headers to the table
                date_headers = list(dates.keys())
                for date in date_headers:
                    # Convert string to a datetime object
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
        
                    # Format to "Day of Week, Month Day"
                    formatted_date = date_obj.strftime('%a, %b %d')
        
                    html_table += f"<th style='border: 1px solid #ddd; padding: 8px;'>{formatted_date}</th>"
                html_table += "</tr></thead><tbody>"
        
                # Collect unique time slots
                unique_times = set()
                for slots in dates.values():
                    for slot in slots:
                        time, _, _ = extract_time_cost_and_url(slot)
                        if time:
                            unique_times.add(time)
        
                # Populate the rows using the unique time slots
                sorted_unique_times = sorted(list(unique_times))
                for time_slot in sorted_unique_times:
                    html_table += "<tr>"
                    html_table += f"<td style='border: 1px solid #ddd; padding: 8px;'>{time_slot}</td>"  # Time slot column
                    for date in date_headers:
                        found = False  # Track if a matching time slot is found for the current date
                        for slot in dates[date]:
                            time, cost, unique_url = extract_time_cost_and_url(slot)
                            if time == time_slot:
                                cost_link = f'<a href="{unique_url}" target="_blank">{cost}</a>'
                                html_table += f"<td style='border: 1px solid #ddd; padding: 8px;'>{cost_link}</td>"
                                found = True
                                break
                        if not found:
                            html_table += "<td style='border: 1px solid #ddd; padding: 8px;'></td>"  # Empty if no slot for that time on that date
                    html_table += "</tr>"
        
                html_table += "</tbody></table>"
        
                # Write the constructed table HTML to the file
                file.write(html_table)
            
    except Exception as e:
        print(f"Error saving availability updates: {e}")
else:
    # If there is no update, try deleting the file
    if os.path.exists("availability_updates.html"):
        try:
            os.remove("availability_updates.html")
        except Exception as e:
            print(f"Error deleting 'availability_updates.html': {e}")


# Open the output file in append mode
with open("output.html", "a") as f:
    # Loop through each park to generate HTML
    for park, dates in park_data.items():
        # Write the park name to the HTML file
        f.write(f"<h2 style='color:#A8E1D4;'>{park}</h2>")  # Add park name in color

        # Start constructing the HTML table for this park
        html_table = "<table style='border-collapse: collapse; width: 100%;'><thead><tr>"
        html_table += "<th style='border: 1px solid #ddd; padding: 8px;'>Time Slot</th>"

        # Add the date headers to the table
        date_headers = list(dates.keys())
        for date in date_headers:
            # Convert string to a datetime object
            date_obj = datetime.strptime(date, '%Y-%m-%d')

            # Format to "Day of Week, Month Day"
            formatted_date = date_obj.strftime('%a, %b %d')

            html_table += f"<th style='border: 1px solid #ddd; padding: 8px;'>{formatted_date}</th>"
        html_table += "</tr></thead><tbody>"

        # Collect unique time slots
        unique_times = set()
        for slots in dates.values():
            for slot in slots:
                time, _, _ = extract_time_cost_and_url(slot)
                if time:
                    unique_times.add(time)

        # Populate the rows using the unique time slots
        sorted_unique_times = sorted(list(unique_times))
        for time_slot in sorted_unique_times:
            html_table += "<tr>"
            html_table += f"<td style='border: 1px solid #ddd; padding: 8px;'>{time_slot}</td>"  # Time slot column
            for date in date_headers:
                found = False  # Track if a matching time slot is found for the current date
                for slot in dates[date]:
                    time, cost, unique_url = extract_time_cost_and_url(slot)
                    if time == time_slot:
                        cost_link = f'<a href="{unique_url}" target="_blank">{cost}</a>'
                        html_table += f"<td style='border: 1px solid #ddd; padding: 8px;'>{cost_link}</td>"
                        found = True
                        break
                if not found:
                    html_table += "<td style='border: 1px solid #ddd; padding: 8px;'></td>"  # Empty if no slot for that time on that date
            html_table += "</tr>"

        html_table += "</tbody></table>"

        # Write the constructed table HTML to the file
        f.write(html_table)

#after the comparison has been made, replace the park_data.json file with the new availability
try:
    with open("park_data.json", "w") as file:
        json.dump(park_data, file, indent=4)
except Exception as e:
    print(f"Error saving park_data: {e}")
