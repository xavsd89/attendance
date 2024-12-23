import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
import streamlit.components.v1 as components

# Initialize session state for storing data (in-memory)
if 'employees' not in st.session_state:
    st.session_state.employees = pd.DataFrame(columns=['Employee ID', 'Employee Name', 'Department', 'Manager', 'Working Hours Start', 'Working Hours End'])
    st.session_state.attendance = pd.DataFrame(columns=['Employee ID', 'Employee Name', 'Date', 'Clock In', 'Clock Out', 'Worked Hours', 'Status', 'Country'])
    st.session_state.next_employee_id = 1
    st.session_state.next_attendance_id = 1

# Helper functions
def format_date(date_str):
    try:
        return datetime.strptime(date_str, "%d:%m:%Y").strftime("%d:%m:%Y")
    except:
        return None

def calculate_worked_hours(clock_in, clock_out):
    return (clock_out - clock_in).seconds / 3600

def is_late(clock_in, start_time):
    return clock_in > start_time

def clock_in_time(employee_name):
    if not employee_name:
        st.error("Error: Please select an employee to clock in.")
        return
    
    # Find employee ID based on employee name
    employee_id = st.session_state.employees[st.session_state.employees['Employee Name'] == employee_name]['Employee ID'].iloc[0]

    # Capture location when clocking in
    location = get_location_from_js()

    clock_in = datetime.now()
    new_attendance_record = {
        'Employee ID': employee_id,
        'Employee Name': employee_name,
        'Date': clock_in.date(),
        'Clock In': clock_in,
        'Clock Out': None,
        'Worked Hours': None,
        'Status': 'Clocked In',
        'Country': location  # Use country name instead of lat/lng
    }
    # Use pd.concat instead of append
    st.session_state.attendance = pd.concat([st.session_state.attendance, pd.DataFrame([new_attendance_record])], ignore_index=True)
    st.success(f"Clocked in at {clock_in.strftime('%H:%M:%S')}. Location: {location}")

def clock_out_time(employee_name):
    if not employee_name:
        st.error("Error: Please select an employee to clock out.")
        return

    # Find employee ID based on employee name
    employee_id = st.session_state.employees[st.session_state.employees['Employee Name'] == employee_name]['Employee ID'].iloc[0]

    # Capture location when clocking out
    location = get_location_from_js()

    clock_out = datetime.now()

    # Ensure employee has a clock-in record
    record = st.session_state.attendance[st.session_state.attendance['Employee Name'] == employee_name]

    if record.empty:
        st.error(f"No clock-in record found for Employee {employee_name}. Please clock in first before clocking out.")
        return

    clock_in_time = record['Clock In'].iloc[-1]  # Safely get the last clock-in record
    worked_hours = calculate_worked_hours(clock_in_time, clock_out)

    # Determine if the employee was late
    employee_working_hours = st.session_state.employees[st.session_state.employees['Employee Name'] == employee_name]
    working_hours_start = datetime.strptime(employee_working_hours['Working Hours Start'].iloc[0], "%H:%M")
    late = is_late(clock_in_time, working_hours_start)
    status = 'Late' if late else 'On Time'

    # Update clock-out record
    st.session_state.attendance.at[record.index[-1], 'Clock Out'] = clock_out
    st.session_state.attendance.at[record.index[-1], 'Worked Hours'] = worked_hours
    st.session_state.attendance.at[record.index[-1], 'Status'] = status
    st.session_state.attendance.at[record.index[-1], 'Country'] = location  # Update country

    st.success(f"Clocked out at {clock_out.strftime('%H:%M:%S')}, Worked Hours: {worked_hours:.2f}, Status: {status}. Location: {location}")

# Function to get location via JavaScript (using Streamlit Components) and reverse geocode to country
def get_location_from_js():
    # If you're running locally, you can manually input a location.
    if st.session_state.get('is_local', False):
        # Manually input country when running locally (during development).
        return st.text_input("Enter Country (for local testing)", value="Malaysia")

    # Otherwise, attempt to use Geolocation for live environments
    location_js = """
    <script>
        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    const latitude = position.coords.latitude;
                    const longitude = position.coords.longitude;
                    window.parent.postMessage({latitude: latitude, longitude: longitude}, "*");
                });
            } else {
                alert("Geolocation is not supported by this browser.");
            }
        }
        getLocation();
    </script>
    """

    components.html(location_js)

    # Default fallback if geolocation is not available
    location = {'latitude': 0, 'longitude': 0, 'country': 'Unknown'}
    
    # Reverse geocoding to get country name from latitude/longitude
    geolocator = Nominatim(user_agent="attendance-tool")
    location_info = geolocator.reverse((location['latitude'], location['longitude']), language='en', exactly_one=True)
    if location_info:
        location = location_info.raw.get('address', {}).get('country', 'Unknown')
    
    return location

# Add Employee function with department and manager info
def add_employee():
    with st.form(key='add_employee_form'):
        emp_name = st.text_input('Employee Name')
        emp_dept = st.text_input('Department')
        emp_mgr = st.text_input('Manager Name')
        emp_start = st.text_input('Working Hours Start (HH:MM)', '09:00')
        emp_end = st.text_input('Working Hours End (HH:MM)', '18:00')
        
        submit_button = st.form_submit_button(label='Add Employee')

        if submit_button:
            # Check for duplicate employee based on Employee Name
            if emp_name in st.session_state.employees['Employee Name'].values:
                st.error(f"Employee with name {emp_name} already exists!")
                return
            
            if not emp_name or not emp_dept or not emp_mgr or not emp_start or not emp_end:
                st.error("Please fill in all fields!")
                return

            new_employee = {
                'Employee ID': st.session_state.next_employee_id,
                'Employee Name': emp_name,
                'Department': emp_dept,
                'Manager': emp_mgr,
                'Working Hours Start': emp_start,
                'Working Hours End': emp_end
            }
            # Use pd.concat instead of append
            st.session_state.employees = pd.concat([st.session_state.employees, pd.DataFrame([new_employee])], ignore_index=True)
            st.session_state.next_employee_id += 1

            st.success(f"Employee {emp_name} added successfully!")

    # Show the list of current employees
    st.write("### Current Employees List")
    st.dataframe(st.session_state.employees[['Employee ID', 'Employee Name', 'Department', 'Manager', 'Working Hours Start', 'Working Hours End']])

# View Attendance Records
def view_attendance():
    st.write("### Attendance Records")
    current_time = datetime.now()
    grace_period = timedelta(minutes=30)
    
    # Add a 'Status' based on clock-in time
    for idx, record in st.session_state.attendance.iterrows():
        employee_name = record['Employee Name']
        employee_id = record['Employee ID']
        working_hours_start = datetime.strptime(st.session_state.employees[st.session_state.employees['Employee Name'] == employee_name]['Working Hours Start'].iloc[0], "%H:%M")
        clock_in_time = record['Clock In']
        
        if clock_in_time:
            # If the clock-in time is more than 30 minutes late
            if clock_in_time > (working_hours_start + grace_period):
                st.session_state.attendance.at[idx, 'Status'] = 'Late'
            else:
                st.session_state.attendance.at[idx, 'Status'] = 'On Time'
    
    st.dataframe(st.session_state.attendance)

# Late Employees Check (Refresh Button)
def check_late_employees():
    st.write("### Not Yet Check In Employees")
    current_time = datetime.now()
    late_employees = []
    
    # Check if employees are late based on their working start time and current time
    for idx, employee in st.session_state.employees.iterrows():
        working_hours_start = datetime.strptime(employee['Working Hours Start'], "%H:%M")
        grace_period = timedelta(minutes=30)
        
        # If the current time is more than 30 minutes past their working start time and they're not clocked in
        if current_time > (working_hours_start + grace_period):
            attendance_record = st.session_state.attendance[
                (st.session_state.attendance['Employee ID'] == employee['Employee ID']) & 
                (st.session_state.attendance['Date'] == current_time.date())
            ]
            
            if attendance_record.empty:
                late_employees.append(employee['Employee Name'])
    
    if late_employees:
        st.write(f"The following employees are running late and have not clocked in:")
        for emp in late_employees:
            st.write(emp)
    else:
        st.write("No employees are running late.")

# Main UI
def main():
    st.title("Employee Attendance Tracker")
    
    menu = ["Add Employee", "Clock In/Out", "View Attendance", "Who is still late?"]
    choice = st.sidebar.selectbox("Select an Option", menu)
    
    if choice == "Add Employee":
        add_employee()
    elif choice == "Clock In/Out":
        employee_name = st.selectbox("Select Employee", st.session_state.employees['Employee Name'])
        action = st.radio("Select Action", ("Clock In", "Clock Out"))
        remarks = st.text_area("Remarks")
        
        if action == "Clock In":
            if st.button(f"Clock In {employee_name}"):
                clock_in_time(employee_name)
        elif action == "Clock Out":
            if st.button(f"Clock Out {employee_name}"):
                clock_out_time(employee_name)
    elif choice == "View Attendance":
        view_attendance()
    elif choice == "Who is still late?":
        if st.button("Refresh Late Employees"):
            check_late_employees()

if __name__ == "__main__":
    main()
