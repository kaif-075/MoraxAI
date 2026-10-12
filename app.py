import time
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
import os
from datetime import datetime, time as dt_time
import mysql.connector
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
CORS(
    app,
    supports_credentials=True,
    origins=["http://127.0.0.1:5500"]
    )

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password= os.getenv("DB_PASSWORD"),
    database="scheduler"
)

cursor = db.cursor(dictionary=True)
# ---------------------------------------------------------------------------
# SBTET RESULT AUTOMATION
# ---------------------------------------------------------------------------
SBTET_URL = "https://sbtet.ap.gov.in/APSBTET/gradeWiseResults.do"
SBTET_DRIVER_PATH = r"C:\WebDriver\msedgedriver.exe"
SBTET_MONTH_YEAR = os.getenv("SBTET_MONTH_YEAR", "MA26")


def clean_sbtet_text(value):
    """Normalize whitespace returned by Selenium."""
    if value is None:
        return ""
    return " ".join(value.replace("\xa0", " ").split()).strip()


def get_sbtet_numeric_value(value):
    """Convert simple numeric marks to int/float and keep other text as-is."""
    value = clean_sbtet_text(value)

    if value in ("", "-", "--", "NA", "N/A"):
        return ""

    if re.fullmatch(r"-?\d+", value):
        return int(value)

    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)

    return value


def ensure_sbtet_subject_table():
    """Create the paper-wise result table if it does not already exist."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sbtet_subject_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            pin VARCHAR(30) NOT NULL,
            semester INT NOT NULL,
            month_year VARCHAR(20) NOT NULL,
            paper_no VARCHAR(20) NOT NULL,
            external_marks VARCHAR(20),
            internal_marks VARCHAR(20),
            total_marks VARCHAR(20),
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_sbtet_subject (pin, semester, month_year, paper_no)
        )
    """)
    db.commit()


def save_sbtet_subject_results(pin, semester, month_year, papers):
    """Insert/update paper-wise marks in MySQL."""
    ensure_sbtet_subject_table()

    for paper_no, paper_data in papers.items():
        cursor.execute("""
            INSERT INTO sbtet_subject_results
            (
                pin,
                semester,
                month_year,
                paper_no,
                external_marks,
                internal_marks,
                total_marks
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON DUPLICATE KEY UPDATE
                external_marks = VALUES(external_marks),
                internal_marks = VALUES(internal_marks),
                total_marks = VALUES(total_marks),
                fetched_at = CURRENT_TIMESTAMP
        """, (
            pin,
            semester,
            month_year,
            paper_no,
            paper_data.get("external", ""),
            paper_data.get("internal", ""),
            paper_data.get("total", "")
        ))

    db.commit()


def fetch_sbtet_result(pin, semester):
    """Fetch the current student's SBTET result using the latest portal flow."""

    options = webdriver.EdgeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")

    driver = webdriver.Edge(
        service=Service(SBTET_DRIVER_PATH),
        options=options
    )

    wait = WebDriverWait(driver, 15)

    try:
        driver.get(SBTET_URL)

        # -------------------------
        # PIN
        # -------------------------
        pin_box = wait.until(
            EC.presence_of_element_located((By.NAME, "aadhar1"))
        )
        pin_box.clear()
        pin_box.send_keys(pin)

        # -------------------------
        # MONTH / YEAR
        # -------------------------
        month_dropdown = wait.until(
            EC.presence_of_element_located((By.ID, "feesmonthyear"))
        )
        Select(month_dropdown).select_by_visible_text(SBTET_MONTH_YEAR)

        # -------------------------
        # SEMESTER
        # -------------------------
        semester_text = f"{semester}SEM"

        semester_dropdown = wait.until(
            EC.presence_of_element_located((By.ID, "grade2"))
        )
        Select(semester_dropdown).select_by_visible_text(semester_text)

        # -------------------------
        # SUBMIT
        # -------------------------
        submit_button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "input[type='button'][value='SUBMIT']")
            )
        )
        submit_button.click()

        # The portal loads the result after submission. Give the page a moment,
        # then use an explicit wait for the result's Name field.
        time.sleep(1)

        page_text = driver.page_source.upper()
        error_messages = [
            "NOT REGISTERED",
            "REGISTERED BUT NOT ELIGIBLE",
            "NO RECORDS",
            "NO RECORD FOUND",
            "NO RESULTS FOUND"
        ]

        if any(message in page_text for message in error_messages):
            return {
                "success": False,
                "error": "No results found."
            }

        try:
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//th[normalize-space()='Name']")
                )
            )
        except Exception:
            pass

        # -------------------------
        # SUMMARY DETAILS
        # -------------------------
        try:
            name = clean_sbtet_text(
                driver.find_element(
                    By.XPATH,
                    "//th[normalize-space()='Name']/following-sibling::td[1]"
                ).text
            )
        except Exception:
            name = ""

        try:
            branch = clean_sbtet_text(
                driver.find_element(
                    By.XPATH,
                    "//th[normalize-space()='Branch Name']/following-sibling::td[1]"
                ).text
            )
        except Exception:
            branch = ""

        try:
            grand_total = get_sbtet_numeric_value(
                driver.find_element(
                    By.XPATH,
                    "//th[normalize-space()='Grand Total']/following-sibling::td[1]"
                ).text
            )
        except Exception:
            grand_total = ""

        try:
            gpa = clean_sbtet_text(
                driver.find_element(
                    By.XPATH,
                    "//th[normalize-space()='GPA']/following-sibling::td[1]"
                ).text
            )
        except Exception:
            gpa = ""

        try:
            result_status = clean_sbtet_text(
                driver.find_element(
                    By.XPATH,
                    "//th[normalize-space()='Result']/following-sibling::td[1]"
                ).text
            )
        except Exception:
            result_status = ""

        # -------------------------
        # PAPER-WISE MARKS
        # -------------------------
        papers = {}

        tables = driver.find_elements(By.CSS_SELECTOR, "#printDiv table")
        result_table = None

        for table in tables:
            table_text = clean_sbtet_text(table.text).upper()
            if "PAPER" in table_text and "EXTERNAL" in table_text:
                result_table = table
                break

        # Fallback for small markup changes on the portal.
        if result_table is None:
            tables = driver.find_elements(By.TAG_NAME, "table")
            for table in tables:
                table_text = clean_sbtet_text(table.text).upper()
                if "PAPER" in table_text and "EXTERNAL" in table_text:
                    result_table = table
                    break

        if result_table is not None:
            rows = result_table.find_elements(By.TAG_NAME, "tr")

            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "th")
                cells += row.find_elements(By.TAG_NAME, "td")

                if len(cells) < 4:
                    continue

                values = [clean_sbtet_text(cell.text) for cell in cells]

                # Paper numbers are expected to look like 401, 402, etc.
                if not re.fullmatch(r"\d{3,4}", values[0]):
                    continue

                paper_no = values[0]
                papers[paper_no] = {
                    "external": get_sbtet_numeric_value(values[1]),
                    "internal": get_sbtet_numeric_value(values[2]),
                    "total": get_sbtet_numeric_value(values[3])
                }

        # If even the student name cannot be read, treat the fetch as failed.
        if not name:
            return {
                "success": False,
                "error": "Student result could not be read."
            }

        # -------------------------
        # SAVE SUMMARY
        # -------------------------
        cursor.execute("""
            INSERT INTO sbtet_results
            (
                pin,
                semester,
                student_name,
                grand_total,
                gpa,
                result_status
            )
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            pin,
            semester,
            name,
            grand_total,
            gpa,
            result_status
        ))
        db.commit()

        # -------------------------
        # SAVE PAPER-WISE MARKS
        # -------------------------
        if papers:
            save_sbtet_subject_results(
                pin,
                semester,
                SBTET_MONTH_YEAR,
                papers
            )

        return {
            "success": True,
            "name": name,
            "branch": branch,
            "grand_total": grand_total,
            "gpa": gpa,
            "result": result_status,
            "month_year": SBTET_MONTH_YEAR,
            "semester": semester,
            "papers": papers
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        try:
            driver.quit()
        except Exception:
            pass

def get_next_class(semester):

    periods = {
        1: (dt_time(9,30), dt_time(10,20)),
        2: (dt_time(10,20), dt_time(11,10)),
        3: (dt_time(11,20), dt_time(12,10)),
        4: (dt_time(12,10), dt_time(13,0)),
        5: (dt_time(13,40), dt_time(14,30)),
        6: (dt_time(14,30), dt_time(15,20)),
        7: (dt_time(15,20), dt_time(16,10))
    }

    current_time = datetime.now().time()
    today = datetime.now().strftime("%A")
    
    next_period = None

    for period, (start, _) in periods.items():

        if current_time < start:
            next_period = period
            break

    if not next_period:
        return "No more classes for today "

    cursor.execute("""
        SELECT subject
        FROM timetable
        WHERE semester=%s
        AND day_name=%s
        AND period_no=%s
    """,(semester, today, str(next_period)))

    result = cursor.fetchone()

    if result:
        return f"{result['subject']} (P{next_period})"

    return "No class found"
def get_performance(pin):

    cursor.execute("""
        SELECT subject, final_avg
        FROM marks
        WHERE pin=%s
    """,(pin,))

    results = cursor.fetchall()

    if not results:
        return {
            "performance":"No Data",
            "weak_subject":"N/A",
            "overall":0
        }

    total = 0
    lowest_marks = 999
    weak_subject = "N/A"

    for row in results:

        total += row['final_avg']

        if row['final_avg'] < lowest_marks:

            lowest_marks = row['final_avg']
            weak_subject = row['subject']

    overall = round(total / len(results),2)

    if overall >= 35:
        performance = "Excellent"

    elif overall >= 28:
        performance = "Good"

    else:
        performance = "Average"

    return {
        "performance":performance,
        "weak_subject":weak_subject,
        "overall":overall
    }


@app.route('/login', methods=['POST'])
def login():

    data = request.get_json()

    pin = data.get("pin")
    password = data.get("password")


    cursor.execute(
        """
        SELECT pin,name
        FROM student_data
        WHERE pin=%s
        AND password=%s
        """,
        (pin, password)
    )

    student = cursor.fetchone()


    if student:

        session['pin'] = student['pin']
        session['name'] = student['name']


        return jsonify({
            "success": True,
            "message": "Login successful"
        })


    return jsonify({
        "success": False,
        "message": "Invalid credentials"
    })

@app.route('/profile',methods=['GET'])
def profile():
    if 'pin' not in session:
        return jsonify({
            "success":False
        })
    cursor.execute("""
                   SELECT name,pin,branch,attendance,semester
                   FROM student_data
                   WHERE pin=%s
                   """,(session['pin'],))
    student = cursor.fetchone()
    return jsonify({
        "success":True,
        "name":student['name'],
        "pin":student['pin'],
        "branch":student['branch'],
        "semester":student['semester'],
        "attendance":student['attendance']
    })
@app.route("/notifications", methods=["GET"])
def notifications():
    if "pin" not in session:
        return jsonify({
            "success": False,
            "message": "Login required"
        })

    pin = session["pin"]

    cursor.execute("""
        SELECT branch, semester
        FROM student_data
        WHERE pin=%s
    """, (pin,))

    student = cursor.fetchone()

    if not student:
        return jsonify({
            "success": False,
            "message": "Student not found"
        })

    branch = student["branch"]
    semester = str(student["semester"])

    cursor.execute("""
        SELECT
            id,
            title,
            message,
            category,
            created_at
        FROM notifications
        WHERE is_active=TRUE
        AND (
            target_branch='ALL'
            OR target_branch=%s
        )
        AND (
            target_semester='ALL'
            OR target_semester=%s
        )
        ORDER BY created_at DESC
    """, (branch, semester))

    notifications = cursor.fetchall()

    return jsonify({
        "success": True,
        "notifications": notifications
    })

@app.route('/logout',methods=['POST'])
def logout():
    session.clear()
    return jsonify({
        "success":True
    })

@app.route('/chat', methods=['POST'])
def chat():

    if 'pin' not in session:
     return jsonify({
        "reply":"Please Login first"
    })

    data = request.get_json()

    user_message = data.get("message","").lower()


    pin = session.get('pin')
    
    if "hai" in user_message or "hello" in user_message or "hi" in user_message or "hey" in user_message:
        return jsonify({"reply": f"Hai, How is it going...?"})
    
    elif "pin" in user_message:
        return jsonify({"reply":f"Your PIN : {pin}"})
    
    elif "who teaches" in user_message or "who is handling" in user_message:
        cursor.execute("""
                       SELECT subject,staff_name,subject_code
                       FROM subjects
                       """)
        subjects = cursor.fetchall()
        for row in subjects:
            if row['subject'].lower() in user_message:
                return jsonify({
                    "reply":f"{row['subject']} is handled by {row['staff_name']}\n Subject Code : {row['subject_code']}"
                })
        return jsonify({
            "reply":"Subject Not Found"
            })
    elif "previous year papers" in user_message or "semester papers" in user_message:
        cursor.execute("""
            SELECT semester,branch
            FROM student_data
            WHERE pin=%s
            """,(pin,))
        student = cursor.fetchone()
        semester = student['semester']
        branch = student['branch']

        cursor.execute("""
            SELECT link 
            FROM papers
            WHERE branch=%s
            AND semester=%s
            """,(branch,semester))
        result=cursor.fetchone()
        if result:
            return jsonify({
            "reply": "Download Previous year papers",
            "url":result['link'],
            "link_text":"Click here"
             })
        else:
            return jsonify({"reply":"No previous paper found..."})
    elif "semester results" in user_message or "my result" in user_message or "semester marks" in user_message:
            cursor.execute("""
                SELECT semester
                FROM student_data
                WHERE pin=%s
                """,(pin,))

            student = cursor.fetchone()

            semester = student['semester']

            result = fetch_sbtet_result(
                pin,
                semester
                )

            if result['success']:

                return jsonify({
                "type":"sbtet_result",
                "title":"SBTET Result",
                "data":result
                })

            else:

                return jsonify({
                "reply":
                "Unable to fetch result.\n"
                + result['error']
                })
    elif "list all teachers" in user_message or "list teachers" in user_message or "my class faculty" in user_message:

        cursor.execute("""
            SELECT subject,staff_name,subject_code
            FROM subjects
            """)

        result = cursor.fetchall()

        return jsonify({
        "type":"teachers",
        "title":"Faculty Information",
        "data":result
    })
    elif "today classes" in user_message or "today class" in user_message:
        cursor.execute("""
        SELECT semester
        FROM student_data
        WHERE pin=%s
        """,(pin,))

        student = cursor.fetchone()
        semester = student['semester']
        
        today = datetime.now().strftime("%A")

        if today == "Sunday":
            return jsonify({"reply":f"It's Sunday Enjoy the day.....!"})
        
        else :

            cursor.execute("""
                SELECT period_no, subject
                FROM timetable
                WHERE semester=%s
                AND day_name=%s
                ORDER BY period_no
                """,(semester,today))

            classes = cursor.fetchall()
            return jsonify({
            "type":"today_classes",
            "title":f"{today} Classes",
            "data":classes
            })

    elif "attendance" in user_message:

        cursor.execute(
            """
            SELECT attendance
            FROM student_data
            WHERE pin=%s
            """,
            (pin,)
        )

        result = cursor.fetchone()
        if result['attendance'] <= 80 and result['attendance'] >=75:
            return jsonify({
            "reply":
            f"Your attendance is {result['attendance']}%\n You should be continue to college"})
        elif result['attendance'] <=75:
             return jsonify({
             "reply":
             f"Your attendance is {result['attendance']}%\n You must be continue to college otherwise you will be in condonation"})
        else:
             return jsonify({
             "reply":
             f"Your attendance is {result['attendance']}%"})
        
    elif "my details" in user_message:
        cursor.execute(
            """
            SELECT pin,name,branch
            FROM student_data
            WHERE pin=%s
            """,
            (pin,)
        )
        result = cursor.fetchone()
        return jsonify({"reply": f"PIN : {result['pin']} \nName : {result['name']} \nBranch : {result['branch']}"})
    elif "next class" in user_message or "upcoming class" in user_message:

        cursor.execute("""
        SELECT semester
        FROM student_data
        WHERE pin=%s
        """,(pin,))

        student = cursor.fetchone()
        today = datetime.now().strftime("%A")
        if today == "Sunday":
            return jsonify({"reply":f"It's Sunday Enjoy the day.....!"})
        else:

            next_class = get_next_class(student['semester'])

            return jsonify({
            "reply":f"Your next class is {next_class}"
            })
    elif "branch" in user_message:
        cursor.execute(
            """
            SELECT branch 
            FROM student_data
            WHERE pin=%s
            """,
            (pin,)
        )
        result = cursor.fetchone()
        return jsonify({
            "reply":f"You are in {result['branch']} Branch"
        })
    elif "timetable" in user_message or "time table" in user_message:
        cursor.execute("""
            SELECT semester
            FROM student_data
            WHERE pin=%s
            """,(pin,))

        student = cursor.fetchone()

        semester = student['semester']

        cursor.execute("""
            SELECT *
            FROM timetable
            WHERE semester=%s
            """,(semester,))
    
        result = cursor.fetchall()
    
        return jsonify({
        "type":"timetable",
        "title":f"Semester {semester} Timetable",
        "data":result
        })
    elif "name" in user_message:

        cursor.execute(
            """
            SELECT name
            FROM student_data
            WHERE pin=%s
            """,
            (pin,)
        )

        result = cursor.fetchone()

        return jsonify({
            "reply":
            f"Your name is {result['name']}"
        })
    elif "how am i doing" in user_message or "performance" in user_message  or "analyze" in user_message or "work hard" in user_message:

        analysis = get_performance(pin)

        reply = f"""Overall Performance : {analysis['performance']}
        Average Marks : {analysis['overall']}
        Weak Subject : {analysis['weak_subject']}
        """
        return jsonify({
        "reply":reply
        })
    elif "mid1" in user_message or "mid-1" in user_message or "mid_1" in user_message or "mid 1" in user_message:
        cursor.execute(
            """
            SELECT subject,mid1,mid1_avg
            FROM marks
            WHERE pin=%s
            """,
            (pin,)
        )

        result = cursor.fetchall()

        return jsonify({
            "type":"MID-1_Marks",
            "title":"MID-1 Marks",
            "data":result
        })
    
    elif "mid2" in user_message or "mid-2" in user_message or "mid_2" in user_message or "mid 2" in user_message:
        cursor.execute(
            """
            SELECT subject,mid2,mid2_avg
            FROM marks
            WHERE pin=%s
            """,
            (pin,)
        )
        result = cursor.fetchall()
        return jsonify({
            "type":"MID-2_Marks",
            "title":"MID-2 Marks",
            "data":result
        })

    elif "mid" in user_message or "midterm" in user_message:

        cursor.execute(
            """
            SELECT subject,mid1,mid2,final_avg
            FROM marks
            WHERE pin=%s
            """,
            (pin,)
        )

        result = cursor.fetchall()

        return jsonify({
          "type":"MID_Marks",
          "title":"MID Marks",
          "data":result
        })


    else:

        return jsonify({
            "reply":
            "Sorry, I couldn't understand."
        })
if __name__ == '__main__':
    app.run(debug=True, port=5000)
