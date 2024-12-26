import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz

# Initialize session state for storing data (in-memory)
if 'employees' not in st.session_state:
    st.session_state.employees = pd.DataFrame(columns=['Employee ID', 'Employee Name', 'Department', 'Manager', 'Working Hours Start', 'Working Hours End'])
    st.session_state.attendance = pd.DataFrame(columns=['Employee ID', 'Employee Name', 'Date', 'Clock In', 'Clock Out', 'Worked Hours', 'Status', 'Country', 'Remarks'])
    st.session_state.next_employee_id = 1
    st.session_state.next_attendance_id = 1

# Function to get the current time in UTC and convert to local time
def get_local_time(timezone_str):
    utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)  # Get UTC time
    local_time = utc_now.astimezone(pytz.timezone(timezone_str))  # Convert to local time
    return local_time

# Clock In function with time zone handling
def clock_in_time(employee_name, remarks, user_timezone):
    # Get the current time in UTC and convert to user's local time
    local_time = get_local_time(user_timezone)
    clock_in_time = local_time.strftime('%Y-%m-%d %H:%M:%S')

    # Find the employee details
    employee = st.session_state.employees[st.session_state.employees['Employee Name'] == employee_name].iloc[0]
    employee_id = employee['Employee ID']
    scheduled_start_time_str = employee['Working Hours Start']
    scheduled_start_time = datetime.strptime(f"{datetime.today().strftime('%Y-%m-%d')} {scheduled_start_time_str}", '%Y-%m-%d %H:%M:%S')

    # Convert scheduled start time to UTC for comparison
    scheduled_start_time_utc = pytz.timezone(user_timezone).localize(scheduled_start_time).astimezone(pytz.utc)

    # Calculate the grace period (30 minutes after the scheduled start time)
    grace_period_end_time = scheduled_start_time_utc + timedelta(minutes=30)

    # Convert clock-in time to UTC
    clock_in_time_utc = local_time.astimezone(pytz.utc)

    # Check if the clock-in time is after the grace period
    if clock_in_time_utc > grace_period_end_time:
        status = 'Late'
    else:
        status = 'On Time'

    # Create the attendance record
    attendance_record = {
        'Employee ID': employee_id,
        'Employee Name': employee_name,
        'Date': datetime.today().strftime('%Y-%m-%d'),
        'Clock In': clock_in_time,
        'Clock Out': None,
        'Worked Hours': None,
        'Status': status,
        'Country': 'Unknown',  # You can use geolocation here if required
        'Remarks': remarks
    }

    # Add the clock-in record to attendance
    st.session_state.attendance = pd.concat([st.session_state.attendance, pd.DataFrame([attendance_record])], ignore_index=True)
    st.success(f"{employee_name} clocked in at {clock_in_time}. Status: {status}")

# Clock Out function (same UTC and local time logic)
def clock_out_time(employee_name, remarks, user_timezone):
    local_time = get_local_time(user_timezone)
    clock_out_time = local_time.strftime('%Y-%m-%d %H:%M:%S')

    # Find the employee and the clock-in record
    employee = st.session_state.employees[st.session_state.employees['Employee Name'] == employee_name].iloc[0]
    employee_id = employee['Employee ID']
    clock_in_record = st.session_state.attendance[(
        st.session_state.attendance['Employee ID'] == employee_id) & 
        (st.session_state.attendance['Clock Out'].isna())
    ]

    if not clock_in_record.empty:
        clock_in_time = datetime.strptime(clock_in_record.iloc[0]['Clock In'], '%Y-%m-%d %H:%M:%S')
        clock_out_time = datetime.strptime(clock_out_time, '%Y-%m-%d %H:%M:%S')

        # Calculate worked hours
        worked_hours = (clock_out_time - clock_in_time).total_seconds() / 3600  # Convert seconds to hours

        # Update the attendance record with clock-out time, worked hours, and remarks
        st.session_state.attendance.loc[st.session_state.attendance['Employee ID'] == employee_id, 'Clock Out'] = clock_out_time
        st.session_state.attendance.loc[st.session_state.attendance['Employee ID'] == employee_id, 'Worked Hours'] = worked_hours
        st.session_state.attendance.loc[st.session_state.attendance['Employee ID'] == employee_id, 'Remarks'] = remarks

        st.success(f"{employee_name} clocked out at {clock_out_time}, worked {worked_hours:.2f} hours.")

# Main UI function
def main():
    st.title("Employee Attendance Tracker")
    
    menu = ["Add Employee", "Clock In/Out", "View Attendance", "Who is still late?"]
    choice = st.sidebar.selectbox("Select an Option", menu)
    
    if choice == "Add Employee":
        add_employee()
    elif choice == "Clock In/Out":
        employee_name = st.selectbox("Select Employee", st.session_state.employees['Employee Name'])
        remarks = st.text_input("Enter Remarks")
        user_timezone = st.selectbox("Select Your Time Zone", pytz.all_timezones)  # Time zone selection

        action = st.radio("Clock Action", ["Clock In", "Clock Out"])

        if action == "Clock In":
            if st.button("Clock In"):
                clock_in_time(employee_name, remarks, user_timezone)
        elif action == "Clock Out":
            if st.button("Clock Out"):
                clock_out_time(employee_name, remarks, user_timezone)
    elif choice == "View Attendance":
        st.write("### Employee Attendance List")
        st.dataframe(st.session_state.attendance)
    elif choice == "Who is still late?":
        st.write("### Check Who is Still Late or Not Clocked In")

        # Add a "Refresh" button to check for late employees
        if st.button("Refresh Late Employees List"):
            check_late_employees()

if __name__ == "__main__":
    main()
