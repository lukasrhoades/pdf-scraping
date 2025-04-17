def graybook_scraper(pdf, year):
    """Scrapes graybook pdf and returns xlsx file"""
    from PyPDF2 import PdfReader
    import pdfplumber
    import re
    import pandas as pd

    # List to store dictionaries of values for each employee
    employees = []

    # List to store missed lines
    missed = []

    if year == 1990:
        # Read in the pdf file
        with pdfplumber.open(pdf) as pdf:
            # Iterate through each page
            for page in pdf.pages:  
                # Find columns based on words in header
                words = page.extract_words()
                for word in words[:50]:
                    if "SEPTEMBER" in word["text"]:
                        col_1 = word["x0"] - 10
                    elif "1990" in word["text"]:
                        col_2 = word["x1"] + 20
                    elif "ILLINOIS" in word["text"]:
                        col_3 = word["x0"] + 10
                        col_4 = word["x1"]
                    elif "PRESENT" in word["text"]:
                        col_5 = word["x0"] - 5
                    elif "PROPOSED" in word["text"]:
                        col_6 = word["x0"] - 1
                        col_7 = word["x1"] + 1
                
                try:
                    # Set column settings
                    table_settings = {
                        "explicit_vertical_lines": [col_1, col_2, col_3, col_4, col_5, col_6, col_7],
                        "horizontal_strategy": "text"
                        }
                except UnboundLocalError:
                    print(page)
                    continue

                table = page.extract_table(table_settings=table_settings)

                try:
                    for row in table:
                        # Skip title/empty rows
                        if "SEPTEMBER" in row[0]:
                            continue
                        if "PRESENT" in row[4]:
                            continue
                        if row[:] == ["", "", "", "", "", ""]:
                            continue

                        elif row[0] != "":  # First job
                            name = row[0]
                            employee = {"Name": name}
                            employee["Job Title"] = row[1]
                            if len(row[2]) != 2:
                                missed.append(row)
                                continue
                            try:
                                employee["Tenure"] = row[2][0]
                                employee["Services"] = row[2][1]
                            except IndexError:
                                missed.append(row)
                                continue
                            employee["Proposed FTE"] = row[3]
                            try:
                                employee["Present Salary"] = float(row[4])
                                employee["Proposed Salary"] = float(row[5])
                            except IndexError:
                                missed.append(row)
                                continue
                            except ValueError:
                                employee["Present Salary"] = row[4]
                                employee["Proposed Salary"] = row[5]
                            employees.append(employee)
                        elif "*" in row[3] or "•" in row[3]:  # Total
                            try:
                                employee = {"Name": name}
                                employee["Job Title"] = "Total for All Jobs"
                                employee["Proposed FTE"] = row[3].rstrip("*").rstrip("•").rstrip("'")
                                employee["Present Salary"] = float(row[4].rstrip("*").rstrip("•").rstrip("'"))
                                employee["Proposed Salary"] = float(row[5].rstrip("*").rstrip("•").rstrip("'"))
                            except IndexError:
                                missed.append(row)
                                continue
                            except ValueError:
                                employee = {"Name": name}
                                employee["Job Title"] = "Total for All Jobs"
                                employee["Proposed FTE"] = row[3].rstrip("*").rstrip("•").rstrip("'")
                                employee["Present Salary"] = row[4].rstrip("*").rstrip("•").rstrip("'")
                                employee["Proposed Salary"] = row[5].rstrip("*").rstrip("•").rstrip("'")
                            employees.append(employee)
                        elif row[1] == "" and row[-1] != "":  # 2nd payment?
                            try:
                                employee = {"Name": name}
                                employee["Job Title"] = "Second Payment"
                                employee["Proposed FTE"] = row[3]
                                employee["Present Salary"] = float(row[4])
                                employee["Proposed Salary"] = float(row[5])
                            except (UnboundLocalError, IndexError):
                                missed.append(row)
                                continue
                            except ValueError:
                                employee = {"Name": name}
                                employee["Job Title"] = "Second Payment"
                                employee["Proposed FTE"] = row[3]
                                employee["Present Salary"] = row[4]
                                employee["Proposed Salary"] = row[5]
                            employees.append(employee)
                        elif row[1] != "":  # Spillover of job title
                            try:
                                employee = employees[-1].pop()
                                employee["Job Title"] += " " + row[1]
                                employees.append(employee)
                            except (IndexError, ValueError, TypeError):
                                missed.append(row)
                                continue
                except IndexError:
                    missed.append(row)
                    continue
                except TypeError:
                    print(page)
                    continue
    elif 2003 < year < 2007:
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
    df.to_csv(f"converted/illinois/{year}.csv", index=False)

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


def graybook_scraper_v3(xlsx):
    """Scrapes graybook pdf and returns xlsx file"""
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
    """Scrapes Mich pdf and returns xlsx file"""
    import pdfplumber
    import re
    import pandas as pd

    # Read in the pdf file
    with pdfplumber.open(pdf) as pdf:

        # List to store dictionaries of values for each employee
        employees = []

        # List to store missed rows
        missed = []

        if 2016 < year < 2019:
            # Find page with the header data
            page = pdf.page[1]

            # Fetch all vertical edges and sort by x-coordinates
            edges = page.edges
            vertical_edges = [e for e in edges if e["orientation"] == "v"]
            x_coords = sorted(set([e["x0"] for e in vertical_edges]))

            # Find columns based on words in header
            words = page.extract_words()
            for word in words[:50]:
                if "NAME" in word["text"]:
                    col_2 = word["x0"] - 1
                elif "APPOINTMENT" in word["text"]:
                    col_3 = word["x0"] - 1
                elif "APPOINTING" in word["text"]:
                    col_4 = word["x0"] - 1
                elif "FTR" in word["text"]:
                    col_5 = word["x0"] - 1
                elif "BASIS" in word["text"]:
                    col_6 = word["x0"] - 12
                elif "FRACTION" in word["text"]:
                    col_7 = word["x0"] + 5
                elif "FUND" in word["text"]:
                    col_8 = word["x0"]

            # Set column settings
            table_settings = {
                "explicit_vertical_lines": [x_coords[0], col_2, col_3, col_4, col_5, col_6, col_7, col_8, x_coords[1]],
                "horizontal_strategy": "text"
            }

        # Iterate through each page
        for page in pdf.pages:
            if year > 2018:
                # Fetch all vertical edges and sort by x-coordinates
                edges = page.edges
                vertical_edges = [e for e in edges if e["orientation"] == "v"]
                x_coords = sorted(set([e["x0"] for e in vertical_edges]))

                # Find columns based on words in header
                words = page.extract_words()
                for word in words[:50]:
                    if "NAME" in word["text"]:
                        col_2 = word["x0"] - 1
                    elif "APPOINTMENT" in word["text"]:
                        col_3 = word["x0"] - 1
                    elif "APPOINTING" in word["text"]:
                        col_4 = word["x0"] - 1
                    elif "FTR" in word["text"]:
                        col_5 = word["x0"] - 1
                    elif "BASIS" in word["text"]:
                        if year > 2019:
                            col_6 = word["x0"] - 1
                        else:
                            col_6 = word["x0"] - 12
                    elif "FRACTION" in word["text"]:
                        col_7 = word["x0"] + 5
                    elif "FUND" in word["text"]:
                        col_8 = word["x0"]

                try:
                    # Set column settings
                    table_settings = {
                        "explicit_vertical_lines": [x_coords[0], col_2, col_3, col_4, col_5, col_6, col_7, col_8, x_coords[1]],
                        "horizontal_strategy": "text"
                    }
                except UnboundLocalError:
                    print(page)
                    continue

            table = page.extract_table(table_settings=table_settings)

            for row in table:
                if row[0] != "UM_ANN-ARBOR" and row[0] != "UM_DEARBORN":
                    continue
                try:
                    name_match = re.match(r"(.*),(.*)", row[1])
                    employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                except AttributeError:
                    print(row)
                    missed.append(row)
                    continue
                employee["Campus"] = row[0].lstrip("UM_")
                employee["Appointment Title"] = row[2]
                employee["Appointing Department"] = row[3]
                employee["Annnual FTR"] = float(row[4].replace(",", ""))
                employee["FTR Basis"] = row[5]
                employee["Fraction"] = float(row[6])
                employee["General Fund Amount"] = float(row[7].replace(",", ""))
                
                # Add employee
                employees.append(employee)
       
    # Create excel file
    df = pd.DataFrame(employees)
    df.to_excel(f"converted/umich/{year}.xlsx")

    return missed, len(df)

