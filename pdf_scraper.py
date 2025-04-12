def graybook_scraper(pdf):
    """Scrapes graybook pdf and returns csv and xlsx file"""
    from PyPDF2 import PdfReader
    import re
    import pandas as pd

    # Read in the pdf file
    reader = PdfReader(pdf)

    # List to store dictionaries of values for each employee
    employees = []

    # Iterate through each page
    for page in reader.pages:
        text = page.extract_text()

        # Skip irrelevant pages
        if "Employee Name" not in text:
            continue

        # Split into lines
        lines = text.split("\n")

        # Dictionary for employee data
        employee = {}

        # Go through each line
        for line in lines:
            # Check if line starts with name
            name_match = re.match(r"([A-Za-z-]+),\s([A-Za-z-]+)\s(?:[A-Z][a-z]*\s)*", line)

            if name_match:
                # Save previous employee's data
                if employee and "Name" in employee:
                    employees.append(employee)

                # New employee record
                employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                employee_total = None

                # Get remainder of line
                remainder = line[name_match.end():].strip()

                try:
                    value_finder(employee, remainder)
                except (AttributeError, IndexError):
                    continue
            else:
                if "Employee Total" not in line and "$" in line:
                    # Then 2nd job, need to add new row
                    try:
                        employee_total = {"Name": employee["Name"]}  # Save for total row
                    except KeyError:
                        print(line)
                        employee_total = None
                        continue
                    # Add previous employee row
                    employees.append(employee)
                    employee = {"Name": employee["Name"]}  # Only keep their name
                    try:
                        value_finder(employee, line)  # Add 2nd job values
                    except (AttributeError, IndexError):
                        continue

                elif "Employee Total" in line:
                    # Total for that employee
                    employees.append(employee)  # Add previous employee row
                    try:
                        employee = {"Name": employee_total["Name"]}  # Only keep their name
                    except TypeError:
                        continue
                    employee["Job Title"] = "Total for All Jobs"
                    total_values = re.findall(r"(\d+\.\d+)\s+(\d+\.\d+)\s+\$(\d{1,3}(?:,\d{3})*\.\d{2})\s+\$(\d{1,3}(?:,\d{3})*\.\d{2})", line)
                    try:
                        employee["Present FTE"] = float(total_values[0][0])
                        employee["Proposed FTE"] = float(total_values[0][1])
                        employee["Present Salary"] = float(total_values[0][2].replace(",", ""))
                        employee["Proposed Salary"] = float(total_values[0][3].replace(",", ""))
                    except IndexError:
                        print(line)
                                
        # If final employee of page, add
        if employee and "Name" in employee:
            employees.append(employee)

    return pd.DataFrame(employees)


def value_finder(employee, line):
    """Fetches values for an employee"""
    import re
    try:
        values = re.match(r"([A-Z,/&\s]+?)\s+(?:([A-W])\s)?([A-P]{2})\s+\d+\.\d+", line)
        employee["Job Title"] = values.group(1)
        employee["Tenure"] = values.group(2)
        employee["Employee Class"] = values.group(3)
    except AttributeError:
        return AttributeError
    try:
        values = re.findall(r"(\d+\.\d+)\s+(\d+\.\d+)\s+\$(\d{1,3}(?:,\d{3})*\.\d{2})\s+\$(\d{1,3}(?:,\d{3})*\.\d{2})", line)
        employee["Present FTE"] = float(values[0][0])
        employee["Proposed FTE"] = float(values[0][1])
        employee["Present Salary"] = float(values[0][2].replace(",", ""))
        employee["Proposed Salary"] = float(values[0][3].replace(",", ""))
    except IndexError:
        return IndexError

