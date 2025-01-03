import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz

# Initialize session state for storing data (in-memory)
if 'employees' not in st.session_state:
    st.session_state.employees = pd.DataFrame(columns=['Employee ID', 'Employee Name', 'Department', 'Manager', 'Working Hours Start', 'Working Hours End', 'Timezone'])
    st.session_state.attendance = pd.DataFrame(columns=['Employee ID', 'Employee Name', 'Date', 'Clock In', 'Clock Out', 'Worked Hours', 'Status', 'Remarks'])
    st.session_state.next_employee_id = 1
    st.session_state.next_attendance_id = 1

# Add Employee function using Excel file upload
def add_employee():
    st.write("### Upload Employee Excel File")

    # Allow user to upload an Excel file
    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx"])

    if uploaded_file is not None:
        try:
            # Read the Excel file into a DataFrame
            new_employees = pd.read_excel(uploaded_file)

            # Validate columns
            required_columns = ['Employee Name', 'Department', 'Manager', 'Working Hours Start', 'Working Hours End']
            if not all(col in new_employees.columns for col in required_columns):
                st.error(f"The Excel file is missing one or more required columns: {required_columns}")
                return

            # Add Employee ID column
            new_employees['Employee ID'] = range(st.session_state.next_employee_id, st.session_state.next_employee_id + len(new_employees))

            # Add a default timezone (can be changed later on the Clock In/Out page)
            new_employees['Timezone'] = 'UTC'  # Default timezone (change as needed)

            # Update the employees DataFrame
            st.session_state.employees = pd.concat([st.session_state.employees, new_employees], ignore_index=True)
            st.session_state.next_employee_id += len(new_employees)

            st.success(f"{len(new_employees)} employee(s) added successfully from the file!")

        except Exception as e:
            st.error(f"Error reading the file: {e}")

    # Show the list of current employees
    st.write("### Current Employees List")
    st.dataframe(st.session_state.employees[['Employee ID', 'Employee Name', 'Department', 'Manager', 'Working Hours Start', 'Working Hours End', 'Timezone']])

# Function to get the current time in the employee's selected timezone
def get_time_in_timezone(timezone_str):
    tz = pytz.timezone(timezone_str)
    return datetime.now(tz)

# Clock In function with timezone handling
def clock_in_time(employee_name, remarks):
    # Check if the employee has already clocked in today
    today = datetime.today().strftime('%Y-%m-%d')
    attendance = st.session_state.attendance[(
        st.session_state.attendance['Employee Name'] == employee_name) & 
        (st.session_state.attendance['Date'] == today)
    ]

    if not attendance.empty:
        st.warning(f"{employee_name} has already clocked in today!")
        return  # Prevent duplicate clock-in

    # Get the employee details
    employee = st.session_state.employees[st.session_state.employees['Employee Name'] == employee_name].iloc[0]
    employee_id = employee['Employee ID']
    scheduled_start_time_str = employee['Working Hours Start']
    timezone_str = employee['Timezone']  # Get the employee's timezone

    # Get current local time in the employee's timezone
    local_time = get_time_in_timezone(timezone_str)
    clock_in = local_time.strftime('%Y-%m-%d %H:%M:%S')

    # Convert the scheduled start time to a datetime object (including seconds if needed)
    scheduled_start_time = datetime.strptime(f"{datetime.today().strftime('%Y-%m-%d')} {scheduled_start_time_str}", '%Y-%m-%d %H:%M:%S')

    # Calculate the grace period (30 minutes after the scheduled start time)
    grace_period_end_time = scheduled_start_time + timedelta(minutes=30)

    # Convert clock-in time to datetime object for comparison
    clock_in_time = datetime.strptime(clock_in, '%Y-%m-%d %H:%M:%S')

    # Determine if the employee is late
    if clock_in_time > grace_period_end_time:
        status = 'Late'
    else:
        status = 'On Time'

    # Create a new attendance record
    attendance_record = {
        'Employee ID': employee_id,
        'Employee Name': employee_name,
        'Date': today,
        'Clock In': clock_in,
        'Clock Out': None,
        'Worked Hours': None,
        'Status': status,
        'Remarks': remarks
    }

    # Add the record to the attendance DataFrame
    st.session_state.attendance = pd.concat([st.session_state.attendance, pd.DataFrame([attendance_record])], ignore_index=True)

    st.success(f"{employee_name} clocked in at {clock_in}. Status: {status}")

# Clock Out function with timezone handling
def clock_out_time(employee_name, remarks):
    clock_out = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Find the employee
    employee = st.session_state.employees[st.session_state.employees['Employee Name'] == employee_name].iloc[0]
    employee_id = employee['Employee ID']
    timezone_str = employee['Timezone']  # Get the employee's timezone

    # Get current local time in the employee's timezone
    local_time = get_time_in_timezone(timezone_str)
    clock_out = local_time.strftime('%Y-%m-%d %H:%M:%S')

    # Find the corresponding clock-in record from the attendance DataFrame
    clock_in_record = st.session_state.attendance[(
        st.session_state.attendance['Employee ID'] == employee_id) &
        (st.session_state.attendance['Clock Out'].isna())
    ]
    
    if clock_in_record.empty:
        st.error(f"{employee_name} has not clocked in today!")
        return  # Prevent clock-out if no clock-in record is found

    clock_in_record = clock_in_record.iloc[0]  # Access the first record safely

    clock_in_time = datetime.strptime(clock_in_record['Clock In'], '%Y-%m-%d %H:%M:%S')
    clock_out_time = datetime.strptime(clock_out, '%Y-%m-%d %H:%M:%S')

    # Calculate worked hours
    worked_hours = (clock_out_time - clock_in_time).total_seconds() / 3600  # Convert seconds to hours

    # Update the attendance record with clock-out time, worked hours, and status
    st.session_state.attendance.loc[st.session_state.attendance['Employee ID'] == employee_id, 'Clock Out'] = clock_out
    st.session_state.attendance.loc[st.session_state.attendance['Employee ID'] == employee_id, 'Worked Hours'] = worked_hours
    st.session_state.attendance.loc[st.session_state.attendance['Employee ID'] == employee_id, 'Remarks'] = remarks

    st.success(f"{employee_name} clocked out at {clock_out}, worked {worked_hours:.2f} hours.")

# Function to check employees who have not clocked in today
def check_not_clocked_in():
    not_clocked_in = []
    today = datetime.today().strftime('%Y-%m-%d')

    # Loop through each employee and check if they've clocked in today
    for _, row in st.session_state.employees.iterrows():
        employee_name = row['Employee Name']
        
        # Find if the employee has clocked in today
        attendance = st.session_state.attendance[(
            st.session_state.attendance['Employee Name'] == employee_name) & 
            (st.session_state.attendance['Date'] == today)
        ]
        
        if attendance.empty:
            # If no clock-in found, add the employee to "not clocked in" list
            not_clocked_in.append(employee_name)

    # Display employees who haven't clocked in yet
    if not_clocked_in:
        st.write(f"### Employees who haven't clocked in yet ({len(not_clocked_in)})")
        st.write(", ".join(not_clocked_in))
    else:
        st.success("All employees have clocked in today!")

# Main UI function
def main():
    st.title("Employee Attendance Tracker")
    
    menu = ["Add Employee", "Clock In/Out", "View Attendance", "Who is still not clocked in?"]
    choice = st.sidebar.selectbox("Select an Option", menu)
    
    if choice == "Add Employee":
        add_employee()
    elif choice == "Clock In/Out":
        employee_name = st.selectbox("Select Employee", st.session_state.employees['Employee Name'])
        remarks = st.text_input("Enter Remarks")
        timezone = st.selectbox("Select Timezone", pytz.all_timezones)  # Allow the user to select the timezone

        # Update the employee's timezone when the user selects a new one
        st.session_state.employees.loc[st.session_state.employees['Employee Name'] == employee_name, 'Timezone'] = timezone
        
        action = st.radio("Clock Action", ["Clock In", "Clock Out"])

        if action == "Clock In":
            if st.button("Clock In"):
                clock_in_time(employee_name, remarks)
        elif action == "Clock Out":
            if st.button("Clock Out"):
                clock_out_time(employee_name, remarks)
    elif choice == "View Attendance":
        st.write("### Employee Attendance List")
        st.dataframe(st.session_state.attendance)
    elif choice == "Who is still not clocked in?":
        check_not_clocked_in()

if __name__ == "__main__":
    main()
