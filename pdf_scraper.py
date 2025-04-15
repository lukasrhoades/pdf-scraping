def graybook_scraper_2007(pdf, year):
    """Scrapes graybook pdf and returns csv and xlsx file"""
    from PyPDF2 import PdfReader
    import re
    import pandas as pd

    # Read in the pdf file
    reader = PdfReader(pdf)

    # List to store dictionaries of values for each employee
    employees = []

    # List to store missed lines
    missed = []

    broken = False

    # Iterate through each page
    for page in reader.pages:
        text = page.extract_text()

        # Skip irrelevant pages
        if "Job Title" not in text:
            continue

        # Split into lines
        lines = text.split("\n")

        # Dictionary for employee data
        employee = {}

        # Go through each line
        for line in lines:
            # Check if line starts with name
            name_match = re.match(r"([A-Z][a-z-]+),\s([A-Z][a-z-]+)\s(?:[A-Z][a-z]*\s)*", line)

            if name_match:
                # New employee record
                employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                broken = False

                # Get remainder of line
                remainder = line[name_match.end():].strip()

                try:
                    value_finder(employee, remainder)
                except (AttributeError, IndexError):
                    missed.append(line)
                    continue
                if employee and "Job Title" in employee:
                    employees.append(employee)
                else:
                    missed.append(line)
                    continue
            else:
                # Either department, 2nd job, total, broken name, broken name 2nd job, broken total
                if ", " in line and "$" in line:  # A broken name
                    missed.append(line)
                    broken = True
                    continue
                elif broken == True and "$" in line:  # Only valid 2nd job/total if name not broken
                    missed.append(line)
                    continue
                elif "Employee Total" not in line and "$" in line:
                    # Then 2nd job, need to add new row
                    try:  # Only catches if previous row is NOT a named row
                        employee = {"Name": employee["Name"]}
                    except KeyError:
                        missed.append(line)
                        continue
                    try:
                        value_finder(employee, line)  # Add 2nd job values
                    except (AttributeError, IndexError):
                        missed.append(line)
                        continue
                    if employee and "Job Title" in employee:
                        employees.append(employee)
                    else:
                        missed.append(line)
                        continue
                elif "Employee Total" in line:  # Total
                    try:
                        employee = {"Name": employee["Name"]}  # Only keep their name
                    except KeyError:
                        missed.append(line)
                        continue
                    employee["Job Title"] = "Total for All Jobs"
                    total_values = re.findall(r"(\d+\.\d+)\s+(\d+\.\d+)\s+\$(\d{1,3}(?:,\d{3})*\.\d{2})\s+\$(\d{1,3}(?:,\d{3})*\.\d{2})", line)
                    try:
                        employee["Present FTE"] = float(total_values[0][0])
                        employee["Proposed FTE"] = float(total_values[0][1])
                        employee["Present Salary"] = float(total_values[0][2].replace(",", ""))
                        employee["Proposed Salary"] = float(total_values[0][3].replace(",", ""))
                    except IndexError:
                        missed.append(line)
                        continue
                    if employee and "Job Title" in employee:
                        employees.append(employee)
    
    # Create excel file
    df = pd.DataFrame(employees)
    df.to_excel(f"converted/illinois/{year}.xlsx")

    return missed, len(df)


def value_finder(employee, line):
    """Fetches values for an employee"""
    import re
    try:
        values = re.match(r"([A-Z0-9\(\)',/&\s-]+?)\s+(?:([A-W])\s)?([A-P]{2})\s+\d+\.\d+", line)
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

