def graybook_scraper(pdf, year):
    """Scrapes graybook pdf and returns csv and xlsx file"""
    from PyPDF2 import PdfReader
    import pdfplumber
    import re
    import pandas as pd

    # List to store dictionaries of values for each employee
    employees = []

    # List to store missed lines
    missed = []

    if 2003 < year < 2007:
        # Read in the pdf file
        with pdfplumber.open(pdf) as pdf:
            # Iterate through each page
            for page in pdf.pages:
                table = page.extract_table(table_settings={
                    "vertical_strategy": "lines", 
                    "horizontal_strategy": "lines"}
                    )
                
                try:
                    for row in table:
                        if "$" not in row[-1]:  # Not an observation
                            continue
                        if row[0] != "":  # 1st job
                            try:
                                name_match = re.match(r"(.*),(.*)", row[0])
                                employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                                employee["Job Title"] = row[1]
                                employee["Tenure"] = row[2]
                                employee["Employee Class"] = row[3]
                                employee["Present FTE"] = float(row[4].lstrip("$"))
                                employee["Proposed FTE"] = float(row[5].lstrip("$"))
                                employee["Present Salary"] = float(row[6].replace(",", "").lstrip("$"))
                                employee["Proposed Salary"] = float(row[7].replace(",", "").lstrip("$"))
                            except IndexError:
                                missed.append(row)
                                continue
                            employees.append(employee)
                        elif row[1] != "":  # 2nd job
                            try:
                                employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                                employee["Job Title"] = row[1]
                                employee["Tenure"] = row[2]
                                employee["Employee Class"] = row[3]
                                employee["Present FTE"] = float(row[4].lstrip("$"))
                                employee["Proposed FTE"] = float(row[5].lstrip("$"))
                                employee["Present Salary"] = float(row[6].replace(",", "").lstrip("$"))
                                employee["Proposed Salary"] = float(row[7].replace(",", "").lstrip("$"))
                            except IndexError:
                                missed.append(row)
                                continue
                            employees.append(employee)
                        elif "*" in row[4]:  # Total
                            try:
                                employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                                employee["Job Title"] = "Total for All Jobs"
                                employee["Present FTE"] = float(row[4].lstrip("$").rstrip("*"))
                                employee["Proposed FTE"] = float(row[5].lstrip("$").rstrip("*"))
                                employee["Present Salary"] = float(row[6].replace(",", "").lstrip("$").rstrip("*"))
                                employee["Proposed Salary"] = float(row[7].replace(",", "").lstrip("$").rstrip("*"))
                            except IndexError:
                                missed.append(row)
                                continue
                            employees.append(employee)
                except TypeError:
                    print(year, page)

    else:
        # Read in the pdf file
        reader = PdfReader(pdf)

        broken = False

        # Iterate through each page
        for page in reader.pages:
            text = page.extract_text()

            # Split into lines
            lines = text.split("\n")

            # Dictionary for employee data
            employee = {}

            """
            if year < 2004:
                # Skip irrelevant pages
                if "PRESENT" and "PROPOSED" not in page:
                    continue
                # Count number of employee entries
                for line in lines:
                    if "-APPROPRIATED FUNDS" in line:  # 1st part of new section
            """
            if year < 2020:
                # Skip irrelevant pages
                if "Job Title" not in text:
                    continue
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
            else:
                # Skip irrelevant pages
                if "Job Title" not in text:
                    continue
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
                        # Either department, total, broken name, broken total
                        if ", " in line and "$" in line:  # A broken name
                            missed.append(line)
                            broken = True
                            continue
                        elif broken == True and "$" in line:  # Only valid total if name not broken
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


def graybook_scraper_v2(pdf, year):
    """Scrapes graybook pdf and returns csv and xlsx file"""
    import pdfplumber
    import re
    import pandas as pd

    # Read in the pdf file
    with pdfplumber.open(pdf) as pdf:

        # List to store dictionaries of values for each employee
        employees = []

        # Iterate through each page
        for page in pdf.pages:
            table = page.extract_table(table_settings={
                "vertical_strategy": "text", 
                "horizontal_strategy": "text"}
                )

            for row in table:
                print(len(row), row)
                """
                if "$" not in row[-1] + row[-2]:
                    continue
                if len(row) == 8:
                    if "," in row[0]:
                        name_match = re.match(r"(.*),(.*)", row[0])
                        employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                        employee["Job Title"] = row[1] + row[2]
                        employee["Tenure"] = None
                        employee["Employee Class"] = row[3]
                        employee["Present FTE"] = float(row[4])
                        employee["Proposed FTE"] = float(row[5])
                        employee["Present Salary"] = float(row[6].replace(",", ""))
                        employee["Proposed Salary"] = float(row[7].replace(",", ""))
                if len(row) == 9:
                    name_full = row[0] + row[1]
                    if "," in name_full:
                        name_match = re.match(r"(.*),(.*)", row[0])
                        employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                        employee["Job Title"] = row[2] + row[3]
                        employee["Tenure"] = None
                        employee["Employee Class"] = row[4]
                        employee["Present FTE"] = float(row[5])
                        employee["Proposed FTE"] = float(row[6])
                        employee["Present Salary"] = float(row[7].replace(",", ""))
                        employee["Proposed Salary"] = float(row[8].replace(",", ""))
                    elif "Total" not in row[3]:  # 2nd job
                        employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                        employee["Job Title"] = row[2] + row[3]
                        employee["Tenure"] = None
                        employee["Employee Class"] = row[4]
                        employee["Present FTE"] = float(row[5])
                        employee["Proposed FTE"] = float(row[6])
                        employee["Present Salary"] = float(row[7].replace(",", ""))
                        employee["Proposed Salary"] = float(row[8].replace(",", ""))
                    elif "Total" in row[3]:  # Total
                        employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                        employee["Job Title"] = "Total for All Jobs"
                        employee["Tenure"] = None
                        FTE = row[4] + row[5] + row[6]
                        values = re.findall(r"(\d+\.\d+)\s+(\d+\.\d+)\s", FTE)
                        employee["Present FTE"] = float(values[0][0])
                        employee["Proposed FTE"] = float(values[0][1])
                        employee["Present Salary"] = float(row[7].replace(",", ""))
                        employee["Proposed Salary"] = float(row[8].replace(",", ""))
                elif len(row) == 11 and row[1].isupper() and len(row[1]) > 1: 
                    name_full = row[0] + row[1]
                    if "," in name_full:
                        name_match = re.match(r"(.*),(.*)", name_full)
                        employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                        employee["Job Title"] = row[2] + row[3] + row[4]
                        employee["Tenure"] = row[5]
                        employee["Employee Class"] = row[6]
                        employee["Present FTE"] = float(row[7])
                        employee["Proposed FTE"] = float(row[8])
                        employee["Present Salary"] = float(row[9].replace(",", ""))
                        employee["Proposed Salary"] = float(row[10].replace(",", ""))
                elif len(row) == 11 and row[2] == "":
                    if "," in name_full:
                        name_match = re.match(r"(.*),(.*)", name_full)
                        employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                        employee["Job Title"] = row[3] + row[4]
                        employee["Tenure"] = row[5]
                        employee["Employee Class"] = row[6]
                        employee["Present FTE"] = float(row[7])
                        employee["Proposed FTE"] = float(row[8])
                        employee["Present Salary"] = float(row[9].replace(",", ""))
                        employee["Proposed Salary"] = float(row[10].replace(",", ""))
                    if "Total" in row[4]:  # Total
                        employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                        employee["Job Title"] = "Total for All Jobs"
                        employee["Tenure"] = None
                        FTE = row[6] + row[7] + row[8]
                        values = re.findall(r"(\d+\.\d+)\s+(\d+\.\d+)\s", FTE)
                        employee["Present FTE"] = float(values[0][0])
                        employee["Proposed FTE"] = float(values[0][1])
                        employee["Present Salary"] = float(row[9].replace(",", ""))
                        employee["Proposed Salary"] = float(row[10].replace(",", ""))
                elif len(row) == 11:

                elif len(row) == 12:
                    if "," in row[0]:
                        name_match = re.match(r"(.*),(.*)", row[0])
                        employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                        employee["Job Title"] = row[1] + row[2] + row[3]
                        employee["Tenure"] = row[4]
                        employee["Employee Class"] = row[7]
                        employee["Present FTE"] = float(row[8])
                        employee["Proposed FTE"] = float(row[9])
                        employee["Present Salary"] = float(row[10].replace(",", ""))
                        employee["Proposed Salary"] = float(row[11].replace(",", ""))
                elif len(row) == 13:
                    if "," in row[0]:
                        name_match = re.match(r"(.*),(.*)", row[0])
                        employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                        employee["Job Title"] = row[1] + row[2] + row[3] + row[4]
                        employee["Tenure"] = row[5]
                        employee["Employee Class"] = row[8]
                        employee["Present FTE"] = float(row[8])
                        employee["Proposed FTE"] = float(row[9])
                        employee["Present Salary"] = float(row[10].replace(",", ""))
                        employee["Proposed Salary"] = float(row[11].replace(",", ""))
                elif len(row) == 14:
                    if "," in row[0]:
                        name_match = re.match(r"(.*),(.*)", row[0])
                        employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                        employee["Job Title"] = row[1] + row[2] + row[3] + row[4] + row[5]
                        employee["Tenure"] = row[6]
                        employee["Employee Class"] = row[9]
                        employee["Present FTE"] = float(row[10])
                        employee["Proposed FTE"] = float(row[11])
                        employee["Present Salary"] = float(row[12].replace(",", ""))
                        employee["Proposed Salary"] = float(row[13].replace(",", ""))
                elif len(row) == 15:
                    name_full = row[0] + row[1]
                    if "," in name_full:
                        name_match = re.match(r"(.*),(.*)", name_full)
                        employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                        employee["Job Title"] = row[2] + row[3] + row[4] + row[5]
                        employee["Tenure"] = row[7]
                        employee["Employee Class"] = row[10]
                        employee["Present FTE"] = float(row[11])
                        employee["Proposed FTE"] = float(row[12])
                        employee["Present Salary"] = float(row[13].replace(",", ""))
                        employee["Proposed Salary"] = float(row[14].replace(",", ""))
                else:
                    print(len(row), row)
                """


def graybook_scraper_v3(xlsx):
    """Scrapes graybook pdf and returns csv and xlsx file"""
    import pdfplumber
    import re
    import pandas as pd

    temp = pd.read_excel(xlsx)
    df = pd.DataFrame(temp.loc[:,["Year", "Data"]])
    df["Name"] = None
    df["Job Title"] = None
    df["Tenure"] = None
    df["Employee Class"] = None
    df["Present FTE"] = None
    df["Proposed FTE"] = None
    df["Present Salary"] = None
    df["Proposed Salary"] = None

    for idx, row in df.iterrows():
        if ", " in row["Data"]:  # Name
            try:
                name_match = re.match(r"([^,]*),\s(.*?)(?=\s[A-Z]{2,})", row["Data"])
                df.loc[idx, "Name"] = name_match.group(2) + " " + name_match.group(1)
                remainder = row["Data"][name_match.end():].strip()
            except AttributeError:
                continue
            try:
                values = re.match(r"([A-Z0-9\(\)',/&\s-]+?)\s+(?:([A-W])\s)?([A-P]{2})\s+\d+\.\d+", remainder)
                df.loc[idx, "Job Title"] = values.group(1)
                df.loc[idx, "Tenure"] = values.group(2)
                df.loc[idx, "Employee Class"] = values.group(3)
            except AttributeError:
                continue
            try:
                values = re.findall(r"(\d+\.\d+)\s+(\d+\.\d+)\s+\$(\d{1,3}(?:,\d{3})*\.\d{2})\s+\$(\d{1,3}(?:,\d{3})*\.\d{2})", df.loc[idx, "Data"])
                df.loc[idx, "Present FTE"] = float(values[0][0])
                df.loc[idx, "Proposed FTE"] = float(values[0][1])
                df.loc[idx, "Present Salary"] = float(values[0][2].replace(",", ""))
                df.loc[idx, "Proposed Salary"] = float(values[0][3].replace(",", ""))
            except IndexError:
                continue
        elif "Total" not in df.loc[idx, "Data"]:  # Second job
            try:
                df.loc[idx, "Name"] = name_match.group(2) + " " + name_match.group(1)
                values = re.match(r"([A-Z0-9\(\)',/&\s-]+?)\s+(?:([A-W])\s)?([A-P]{2})\s+\d+\.\d+", remainder)
                df.loc[idx, "Job Title"] = values.group(1)
                df.loc[idx, "Tenure"] = values.group(2)
                df.loc[idx, "Employee Class"] = values.group(3)
            except AttributeError:
                continue
            try:
                values = re.findall(r"(\d+\.\d+)\s+(\d+\.\d+)\s+\$(\d{1,3}(?:,\d{3})*\.\d{2})\s+\$(\d{1,3}(?:,\d{3})*\.\d{2})", df.loc[idx, "Data"])
                df.loc[idx, "Present FTE"] = float(values[0][0])
                df.loc[idx, "Proposed FTE"] = float(values[0][1])
                df.loc[idx, "Present Salary"] = float(values[0][2].replace(",", ""))
                df.loc[idx, "Proposed Salary"] = float(values[0][3].replace(",", ""))
            except IndexError:
                continue
        elif "Total" in df.loc[idx, "Data"]:  # Total
            df.loc[idx, "Job Title"] = "Total for All Jobs"
            try:
                values = re.findall(r"(\d+\.\d+)\s+(\d+\.\d+)\s+\$(\d{1,3}(?:,\d{3})*\.\d{2})\s+\$(\d{1,3}(?:,\d{3})*\.\d{2})", df.loc[idx, "Data"])
                df.loc[idx, "Present FTE"] = float(values[0][0])
                df.loc[idx, "Proposed FTE"] = float(values[0][1])
                df.loc[idx, "Present Salary"] = float(values[0][2].replace(",", ""))
                df.loc[idx, "Proposed Salary"] = float(values[0][3].replace(",", ""))
            except IndexError:
                continue

    # Create excel file
    df.to_excel(f"converted/illinois/converted.xlsx")

    return df


def mich_scraper(pdf, year):
    """Scrapes Mich pdf and returns csv and xlsx file"""
    import pdfplumber
    import re
    import pandas as pd

    # Read in the pdf file
    with pdfplumber.open(pdf) as pdf:

        # List to store dictionaries of values for each employee
        employees = []

        # Iterate through each page
        for page in pdf.pages:
            table = page.extract_table(table_settings={
                "vertical_strategy": "text", 
                "horizontal_strategy": "text"}
                )

            for row in table:
                if row[0] != "UM_ANN-ARBOR" and row[0] != "UM_DEARBORN":
                    continue
                if len(row) == 9:
                    name_match = re.match(r"(.*),(.*)", row[1])
                    employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                    employee["Campus"] = row[0].lstrip("UM_")
                    employee["Appointment Title"] = row[2] + row[3]
                    employee["Appointing Department"] = row[4]
                    employee["Annnual FTR"] = row[5]
                    employee["FTR Basis"] = row[6]
                    employee["Fraction"] = row[7]
                    employee["General Fund Amount"] = row[8]
                elif len(row) == 10:
                    name_match = re.match(r"(.*),(.*)", row[1])
                    employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                    employee["Campus"] = row[0].lstrip("UM_")
                    employee["Appointment Title"] = row[2] + row[3]
                    employee["Appointing Department"] = row[4] + row[5]
                    employee["Annnual FTR"] = row[6]
                    employee["FTR Basis"] = row[7]
                    employee["Fraction"] = row[8]
                    employee["General Fund Amount"] = row[9]
                elif len(row) == 11:
                    name_match = re.match(r"(.*),(.*)", row[1])
                    employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                    employee["Campus"] = row[0].lstrip("UM_")
                    employee["Appointment Title"] = row[2] + row[3] + row[4]
                    employee["Appointing Department"] = row[5] + row[6]
                    employee["Annnual FTR"] = row[7]
                    employee["FTR Basis"] = row[8]
                    employee["Fraction"] = row[9]
                    employee["General Fund Amount"] = row[10]
                elif len(row) == 12:
                    name_match = re.match(r"(.*),(.*)", row[1])
                    employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                    employee["Campus"] = row[0].lstrip("UM_")
                    employee["Appointment Title"] = row[2] + row[3] + row[4] + row[5]
                    employee["Appointing Department"] = row[6] + row[7]
                    employee["Annnual FTR"] = row[8]
                    employee["FTR Basis"] = row[9]
                    employee["Fraction"] = row[10]
                    employee["General Fund Amount"] = row[11]
                elif len(row) == 13:
                    name_match = re.match(r"(.*),(.*)", row[1])
                    employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                    employee["Campus"] = row[0].lstrip("UM_")
                    employee["Appointment Title"] = row[2] + row[3] + row[4] + row[5] + row[6]
                    employee["Appointing Department"] = row[7] + row[8]
                    employee["Annnual FTR"] = row[9]
                    employee["FTR Basis"] = row[10]
                    employee["Fraction"] = row[11]
                    employee["General Fund Amount"] = row[12]
                elif len(row) == 14:
                    name_match = re.match(r"(.*),(.*)", row[1])
                    employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                    employee["Campus"] = row[0].lstrip("UM_")
                    employee["Appointment Title"] = row[2] + row[3] + row[4] + row[5] + row[6]
                    employee["Appointing Department"] = row[6] + row[7] + row[8] + row[9]
                    employee["Annnual FTR"] = row[10]
                    employee["FTR Basis"] = row[11]
                    employee["Fraction"] = row[12]
                    employee["General Fund Amount"] = row[13]
                else:
                    print(len(row), row)
                employees.append(employee)
       
    # Create excel file
    df = pd.DataFrame(employees)
    df.to_excel(f"converted/umich/{year}.xlsx")

    return len(df)

