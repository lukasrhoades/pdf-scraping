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
            name_match = re.match(r"([A-Z][a-z]+),\s([A-Z][a-z]+)(\s[A-Z])?", line)

            if name_match:
                # Save previous employee's data
                if employee and "Name" in employee:
                    employees.append(employee)

                # New employee record
                employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}

                try:
                    values = re.findall(r"([A-W]\s)?([A-P]{2})\s+(\d+\.\d+)\s+(\d+\.\d+)\s+\$(\d+,\d+\.\d+)\s+\$(\d+,\d+\.\d+)", line)
                    employee["Tenure"] = values[0][0]
                    employee["Employee Class"] = values[0][1]
                    employee["Present FTE"] = float(values[0][2])
                    employee["Proposed FTE"] = float(values[0][3])
                    employee["Present Salary"] = float(values[0][4].replace(",", ""))
                    employee["Proposed Salary"] = float(values[0][5].replace(",", ""))
                except IndexError:
                    continue
            #else:
                #if "Employee Total" not in line and "$" in line:
                    # Then 2nd job
                #elif "Employee Total" in line:
                    # Total for that employee
            
        # If final employee of page, add
        if employee and "Name" in employee:
            employees.append(employee)

    return pd.DataFrame(employees)



