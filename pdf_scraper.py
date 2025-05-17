"""Functions to scrape PDFs for tabular salary data"""

def graybook_scraper(file, year):
    """Scrapes graybook pdf and returns csv file"""
    from PyPDF2 import PdfReader, PdfWriter
    import pdfplumber
    import re
    import pandas as pd

    # List to store dictionaries of values for each employee
    employees = []

    # List to store missed lines
    missed = []

    if year < 2004:

        broken = False

        # Read in the pdf file
        with pdfplumber.open(file) as pdf:
            # Iterate through each page
            for i, page in enumerate(pdf.pages): 
                # Find columns based on words in header
                words = page.extract_words()
                if year == 1990:
                    try:
                        if "=<C=" in words[1]["text"]:
                            break  # Reached end of salary data
                    except IndexError:
                        print(page)  # Not a page with employee data
                        continue
                if len(words) == 0:
                    continue  # Not a page with employee data
                col_1, col_3, col_6 = [None] * 3
                for word in words[:50]:
                    if "SEPT" in word["text"]:
                        if col_1 is None:
                            col_1 = word["x0"] - 10
                    elif f"{year}" in word["text"]:
                        col_2 = word["x1"] + 25
                    elif any(substring in word["text"] for substring in ["ILLINOIS", "ILLI", "NOIS", "NOJS"]):
                        if col_3 is None:
                            col_3 = word["x0"] + 10
                            col_4 = word["x1"] - 3
                    elif "PRESENT" in word["text"]:
                        col_5 = word["x0"] - 10
                    elif any(substring in word["text"] for substring in ["PROPOSED", "ROPOSE"]):
                        if col_6 is None:
                            col_6 = word["x0"] - 13
                            col_7 = word["x1"] + 1
                
                try:
                    # Set column settings
                    table_settings = {
                        "explicit_vertical_lines": [col_1, col_2, col_3, col_4, col_5, col_6, col_7],
                        "horizontal_strategy": "text"
                        }
                except UnboundLocalError:  # Not a page with employee data
                    print(page)
                    continue
                
                try:
                    table = page.extract_table(table_settings=table_settings)
                    if year == 1990 and i == 141:  # Buggy page, need to use Azure
                        raise TypeError
                except TypeError:
                    if year == 1990:
                        if len(words) < 25:  # Not a page with employee data
                            continue
                        else:  # Use Azure
                            # Save page
                            reader = PdfReader(file)
                            page_saver = PdfWriter()
                            page_saver.add_page(reader.pages[i])
                            page_saver.write("temp.pdf")

                            # Make API call
                            try:
                                table = get_azure_data("temp.pdf", "Illinois")
                            except IndexError:  # No tables detected
                                print(page)
                                continue
                    else:
                        continue
                
                for row in table:
                    # Skip title/empty/irrelevant rows
                    if row[0] is None:
                        continue
                    if "SEPTEMBER" in row[0]:
                        continue
                    if "PRESENT" in row[4]:
                        continue
                    if row[:] == ["", "", "", "", "", ""]:
                        continue
                    if re.match(r".-..-..\s", row[0]):
                        continue  # Department heading
                    if row[-1] == "":
                        continue  # No salary data
                    
                    if row[0] != "":  # First job
                        name = row[0]
                        employee = {"Name": name}
                        employee["Job Title"] = row[1]
                        employee["Tenure/Services"] = row[2]
                        try:
                            employee["Proposed FTE"] = float(fte_to_numer(row[3]))
                            if row[4] == "":  # Handle no present salary
                                employee["Present Salary"] = 0
                            else:
                                employee["Present Salary"] = float(sal_to_numer(row[4]))
                            employee["Proposed Salary"] = float(sal_to_numer(row[5]))
                        except (IndexError, ValueError):
                            broken = True
                            row.append("first job fail")
                            missed.append(row)
                            continue
                        broken = False
                        employees.append(employee)
                    elif broken == True:  # First job wasn't captured
                        row.append("continuation row")
                        missed.append(row)
                        continue
                    elif "*" in row[3] or "•" in row[3] or "'" in row[3]:  # Total
                        continue
                    elif row[-1] != "":  # 2nd payment
                        employee = employees.pop(-1)
                        employee["Job Title"] += " " + row[1]  # Sometimes has continuation of title
                        try:
                            employee["Proposed FTE"] += float(fte_to_numer(row[3]))
                            employee["Present Salary"] += float(sal_to_numer(row[4]))
                            employee["Proposed Salary"] += float(sal_to_numer(row[5]))
                            employees.append(employee)
                        except ValueError:
                            missed.append(employee.values())
                            row.append("2nd payment fail")
                            missed.append(row)
                    elif row[1] != "" and row[0] == "" and row[2:6] == [""] * 4:
                        # Second part of job title
                        employee = employees.pop(-1)
                        employee["Job Title"] += " " + row[1]
                        employees.append(employee)
    elif 2003 < year < 2007:
        # Read in the pdf file
        with pdfplumber.open(file) as pdf:
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
                        if "*" in row[-1]:
                            continue  # Total

                        if row[0] != "":  # 1st job
                            try:
                                name_match = re.match(r"(.*),(.*)", row[0])
                                employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                            except AttributeError:
                                employee = {"Name": row[1]}
                                name = row[1]  # Save for second job
                                missed.append(row)
                            employee["Job Title"] = row[1]
                            employee["Tenure"] = row[2]
                            employee["Employee Class"] = row[3]
                            try:
                                employee["Present FTE"] = float(row[4].lstrip("$"))
                            except ValueError:
                                employee["Present FTE"] = row[4]
                                missed.append(row)
                            try:
                                employee["Proposed FTE"] = float(row[5].lstrip("$"))
                            except ValueError:
                                employee["Proposed FTE"] = row[5]
                                missed.append(row)
                            try:
                                employee["Present Salary"] = float(row[6].replace(",", "").lstrip("$"))
                            except ValueError:
                                employee["Present Salary"] = row[6]
                                missed.append(row)
                            try:
                                employee["Proposed Salary"] = float(row[7].replace(",", "").lstrip("$"))
                            except ValueError:
                                employee["Proposed Salary"] = row[7]
                                missed.append(row)
                        elif row[1] != "":  # 2nd job
                            try:
                                employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                            except ValueError:
                                employee = {"Name": name}
                                missed.append(row)
                            employee["Job Title"] = row[1]
                            employee["Tenure"] = row[2]
                            employee["Employee Class"] = row[3]
                            try:
                                employee["Present FTE"] = float(row[4].lstrip("$"))
                            except ValueError:
                                employee["Present FTE"] = row[4]
                                missed.append(row)
                            try:
                                employee["Proposed FTE"] = float(row[5].lstrip("$"))
                            except ValueError:
                                employee["Proposed FTE"] = row[5]
                                missed.append(row)
                            try:
                                employee["Present Salary"] = float(row[6].replace(",", "").lstrip("$"))
                            except ValueError:
                                employee["Present Salary"] = row[6]
                                missed.append(row)
                            try:
                                employee["Proposed Salary"] = float(row[7].replace(",", "").lstrip("$"))
                            except ValueError:
                                employee["Proposed Salary"] = row[7]
                                missed.append(row)
                        employees.append(employee)
                except TypeError:
                    print(year, page)

    elif year < 2024:
        # Read in the pdf file
        with pdfplumber.open(file) as pdf:
            
            grab_name = False  # This is used for getting second part of name

            # Iterate through each page
            for page in pdf.pages:
                # Initialize columns
                col_1, col_2, col_3, col_4, col_5, col_6, col_7, col_8, col_9 = [None] * 9

                # Find columns based on words in header
                words = page.extract_words()
                for word in words[:50]:
                    if "Employee" in word["text"]:
                        if col_1 is None:
                            col_1 = word["x0"] - 1
                    elif "Job" in word["text"]:
                        if col_2 is None:
                            col_2 = word["x0"] - 1
                    elif "Tenure" in word["text"]:
                        if col_3 is None:
                            col_3 = word["x0"] + 10
                            col_4 = word["x1"] + 15
                    elif "Present" in word["text"]:
                        if col_5 is None:  # Only use first occurance
                            col_5 = word["x0"] - 5
                    elif "Proposed" in word["text"]:
                        if col_6 is None:
                            col_6 = word["x0"] - 3
                    elif "Salary" in word["text"]:
                        if col_7 is None:
                            col_7 = word["x0"] - 17
                            col_8 = word["x1"] + 17
                            col_9 = word["x1"] + 70
                    
                # Set column settings
                table_settings = {
                    "explicit_vertical_lines": [col_1, col_2, col_3, col_4, col_5, col_6, col_7, col_8, col_9],
                    "horizontal_strategy": "text"
                }

                try:
                    table = page.extract_table(table_settings=table_settings)
                except TypeError:
                    print(year, page)
                    continue  # Not a page with employee data

                for row in table:
                    if grab_name is True:  # Second part of name
                        employees.pop(-1)
                        employee["Name"] += row[0]
                        name_match = re.match(r"(.*),(.*)", employee["Name"])
                        employee["Name"] = name_match.group(2).strip() + " " + name_match.group(1).strip()
                        employees.append(employee)
                        grab_name = False
                        continue
                    if "August" and f"{year}" in row[0]:
                        continue  # Header
                    if "Employee Name" in row[0]:
                        continue  # Header
                    if row[0] == "" and row[1] == "":
                        continue  # Not a row with employee data
                    if "$" not in row[-1]:
                        continue  # Not a row with salary data
                    
                    if year < 2020:
                        if row[1] != "Employee":  # Not total
                            if row[0] != "" and row[0].strip()[-1] == ",":  # Need second part of name
                                employee = {"Name": row[0]}
                                grab_name = True
                            else:
                                try:
                                    if row[0] != "":  # First job
                                        name_match = re.match(r"(.*),(.*)", row[0])
                                    # Otherwise, second job
                                    employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                                except AttributeError:
                                    if row[0] == "":  # Second job
                                        employee = {"Name": name}
                                    employee = {"Name": row[0]}
                                    name = row[0]  # If match fails first time, will probably fail again so save it
                                    missed.append(row)
                            employee["Job Title"] = row[1]
                            employee["Tenure"] = row[2]
                            employee["Employee Class"] = row[3]
                            try:
                                employee["Present FTE"] = float(row[4])
                            except ValueError:
                                employee["Present FTE"] = row[4]
                                missed.append(row)
                            try:
                                employee["Proposed FTE"] = float(row[5])
                            except ValueError:
                                employee["Proposed FTE"] = row[5]
                                missed.append(row)
                            try:
                                employee["Present Salary"] = float(row[6].lstrip("$").replace(",", ""))
                            except ValueError:
                                employee["Present Salary"] = row[6]
                                missed.append(row)
                            if year == 2013 and row[0] == "Becker, Bryan":
                                employee["Proposed Salary"] = float(row[7].lstrip("0 $").replace(",", ""))
                            else:
                                try:
                                    employee["Proposed Salary"] = float(row[7].lstrip("(").lstrip("$").rstrip(")").replace(",", ""))
                                except ValueError:
                                    employee["Proposed Salary"] = row[7]
                                    missed.append(row)
                        elif row[1] == "Employee":  # Employee total
                            continue  # Will calculate later
                    else:
                        if row[1] != "Employee":  # Not total
                            if year == 2023 and row[0].strip() == "White, Judith Bess White,":
                                employee = {"Name": "Judith Bess White"}
                            elif row[0].strip()[-1] == ",":  # Need second part of name
                                employee = {"Name": row[0]}
                                grab_name = True
                            elif year == 2023 and row[0] == "Tiffany Barnett":
                                employee = {"Name": "Tiffany Barnett White"}
                            else:
                                try:
                                    name_match = re.match(r"(.*),(.*)", row[0])
                                    employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                                except AttributeError:
                                    employee = {"Name": row[0]}
                                    missed.append(row)
                            employee["Job Title"] = row[1]
                            employee["Tenure"] = row[2]
                            employee["Employee Class"] = row[3]
                            try:
                                employee["Present FTE"] = float(row[4])
                            except ValueError:
                                employee["Present FTE"] = row[4]
                                missed.append(row)
                            try:
                                employee["Proposed FTE"] = float(row[5])
                            except ValueError:
                                employee["Proposed FTE"] = row[5]
                                missed.append(row)
                            try:
                                employee["Present Salary"] = float(row[6].lstrip("$").replace(",", ""))
                            except ValueError:
                                employee["Present Salary"] = row[6]
                                missed.append(row)
                            try:
                                employee["Proposed Salary"] = float(row[7].lstrip("$").replace(",", ""))
                            except ValueError:
                                employee["Proposed Salary"] = row[7]
                                missed.append(row)
                        elif row[1] == "Employee":  # Employee total
                            continue  # Will calculate later
                    
                    employees.append(employee)  # Add row of employee data
    else:
        # Read in the pdf file
        reader = PdfReader(file)

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

    # Handle fractional appointments
    # Create dataframe with all employee data
    df = pd.DataFrame(employees)

    # Groupby name and then filter out groupings of different people
    salaries = df.groupby("Name", sort=False)
    if year < 2004:
        salaries = salaries.filter(lambda x: x["Proposed FTE"].sum() <= 100)
    else:
        salaries = salaries.filter(lambda x: x["Present FTE"].sum() <= 1.00)

    # Grab the index of those who were grouped after filtering
    filter = salaries.index

    # Then set index to be the name
    salaries.set_index("Name", inplace=True)

    # Collect all the employee information across appointments and merge them together 
    jobs = df.loc[filter,:].groupby("Name", sort=False)["Job Title"].apply(lambda x: " and ".join(x))
    if year < 2004:
        tenure_services = df.loc[filter,:].groupby("Name", sort=False)["Tenure/Services"].apply(lambda x: " and ".join(x))
        merge2 = pd.merge(jobs, tenure_services, on="Name")
    else:
        tenure = df.loc[filter,:].groupby("Name", sort=False)["Tenure"].apply(lambda x: " and ".join(x))
        employee_class = df.loc[filter,:].groupby("Name", sort=False)["Employee Class"].apply(lambda x: " and ".join(x))
        merge1 = pd.merge(jobs, tenure, on="Name")
        merge2 = pd.merge(merge1, employee_class, on="Name")

    # Now sum the FTE's and salaries and merge again
    if year < 2004:
        salaries = salaries.iloc[:,2:].groupby("Name", sort=False).sum()
    else:
        salaries = salaries.iloc[:,3:].groupby("Name", sort=False).sum()
    merge3 = pd.merge(merge2, salaries, on="Name")
    
    # Grab the names of those whose salaries have been summed
    names = salaries.index

    # Now grab the complete data for everyone else
    mask = df["Name"].isin(names)
    others = df.loc[~mask,:].set_index("Name")

    # Final merge for all the data and sort the data
    merge4 = pd.concat([merge3, others])
    merge4.sort_index(inplace=True)

    # Write csv file
    merge4.to_csv(f"converted/illinois/{year}.csv")

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


def fte_to_numer(value):
    return value.replace("so", "50").replace("TOO", "100").replace("D", "0").replace("O", "0").replace("S", "5")

def sal_to_numer(value):
    return value.replace("so", "50").replace("O", "0").replace("B", "8").replace("D", "0").replace("S", "5").replace("C", "0")


def graybook_missed_scraper(data):
    """Scrapes csv of missed observations"""
    import re
    import pandas as pd

    temp = pd.read_csv(data)
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

    # Create csv file
    df.to_csv(f"converted/illinois/converted.csv")

    return df


def mich_scraper(file, year):
    """Scrapes Mich pdf and returns csv file"""
    import pdfplumber
    from PyPDF2 import PdfReader, PdfWriter
    import re
    import pandas as pd

    # Read in the pdf file
    with pdfplumber.open(file) as pdf:

        # List to store dictionaries of values for each employee
        employees = []

        # List to store missed rows
        missed = []

        if year < 2002:
            # 2001 is a work in progress, requires Azure due to page warping
            reader = PdfReader(file)

            if year < 2001:
                table_settings = {
                    "explicit_vertical_lines": [73, 195, 320, 425, 480, 525, 565, 660],
                    "horizontal_strategy": "text",
                }

            for idx, page in enumerate(pdf.pages):
                # Rotate page
                rotated_page = reader.pages[idx]
                rotated_page.rotate(90)
                writer = PdfWriter()
                writer.add_page(rotated_page)
                with open("rotated_temp.pdf", "wb") as temp:
                    writer.write(temp)
                pdf = pdfplumber.open("rotated_temp.pdf")
                page = pdf.pages[0]  # Only one page

                # Check if has actual data
                words = page.extract_words()
                if len(words) < 50:
                    continue  # Blank page
                if year == "2001" and idx == 0:
                    continue  # CCA page
                
                if year == 2001:
                    # Extract from Azure
                    try:  # Make API call
                        table = get_azure_data("rotated_temp.pdf", "UMich")
                    except IndexError:  # No tables detected
                        print(page)
                        continue
                else:
                    table = page.extract_table(table_settings=table_settings)
                
                if len(table[0]) != 7:
                    print(idx)  # Page without employee data
                    continue
                
                for row in table:
                    if "NAME" in row[0]:
                        continue  # Header
                    if row[0] == "":
                        continue

                    try:
                        name_match = re.match(r"(.*),(.*)", row[0])
                        employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                    except AttributeError:
                        employee = {"Name": row[0]}
                    employee["Appointment Title"] = row[1]
                    employee["Appointing Department"] = row[2]
                    try:
                        employee["Annnual FTR"] = float(row[3].replace(",", ""))
                    except ValueError:
                        employee["Annnual FTR"] = row[3]
                        missed.append(row)
                    employee["FTR Basis"] = row[4]
                    try:
                        employee["Fraction"] = float(row[5])
                    except ValueError:
                        employee["Fraction"] = row[5]
                        missed.append(row)
                    try:
                        employee["General Fund Amount"] = float(row[6].replace(",", ""))
                    except ValueError:
                        employee["General Fund Amount"] = row[6]
                        missed.append(row)

                    # Add employee
                    employees.append(employee)

        elif year < 2008:  # Header data only on first page
            # Find page with the header data
            page = pdf.pages[0]

            # Fetch all vertical edges and sort by x-coordinates
            edges = page.edges
            vertical_edges = [e for e in edges if e["orientation"] == "v"]
            x_coords = sorted(set([e["x0"] for e in vertical_edges]))

            # Find columns based on words in header
            words = page.extract_words()
        
            if year == 2003:
                for word in words[:15]:
                    if "Campus" in word["text"]:
                        col_1 = word["x0"] - 1
                    elif "Employee" in word["text"]:
                        col_2 = word["x0"] - 1
                    elif "Jobcode" in word["text"]:
                        col_3 = word["x0"] - 1
                    elif "Dept" in word["text"]:
                        col_4 = word["x0"] - 1
                    elif "AnlFTR" in word["text"]:
                        col_5 = word["x0"] - 1
                    elif "Period" in word["text"]:
                        col_6 = word["x0"] - 1
                    elif "FTE" in word["text"]:
                        col_7 = word["x0"] - 1
                    elif "General" in word["text"]:
                        col_8 = word["x0"] - 1
                    elif "Fund" in word["text"]:
                        col_9 = word["x1"] - 5
            elif year == 2004:
                for word in words[:15]:
                    if "UM_" in word["text"]:
                        col_1 = word["x0"] - 1
                    elif "Brown,Karen" in word["text"]:
                        col_2 = word["x0"] - 1
                    elif "ADMINISTRATIVE" in word["text"]:
                        col_3 = word["x0"] - 1
                    elif "Continuing" in word["text"]:
                        col_4 = word["x0"] - 1
                    elif "92,983.27" in word["text"]:
                        col_5 = word["x0"] - 20
                    elif "12-Month" in word["text"]:
                        col_6 = word["x0"] - 1
                    elif "1" in word["text"]:
                        col_7 = word["x0"] - 20
                    elif "0.00" in word["text"]:
                        col_8 = word["x0"] - 1
                        col_9 = word["x1"] + 26
            else:
                for word in words[:25]:
                    if "CAMPUS" in word["text"]:
                        col_1 = word["x0"] - 1
                    elif "NAME" in word["text"]:
                        col_2 = word["x0"] - 1
                    elif "TITLE" in word["text"]:
                        if year != 2002 and year != 2006:
                            col_3 = word["x0"] - 60
                        else:
                            col_3 = word["x0"] - 1
                    elif "DEPT" in word["text"]:
                        if year == 2002 or year == 2006:
                            col_4 = word["x0"] - 1
                    elif "APPOINTING" in word["text"]:
                        if year != 2002 and year != 2006:
                            col_4 = word["x0"] - 1
                    elif "ANNUAL" in word["text"]:
                        if year == 2005:
                            col_5 = word["x0"] + 10
                        elif year == 2007:
                            col_5 = word["x0"] - 10
                    elif "FTR" in word["text"]:
                        if year == 2002:
                            col_5 = word["x0"] - 3
                        elif year == 2006:
                            col_5 = word["x0"] + 8
                        else:
                            col_6 = word["x0"] - 27 
                    elif "BASIS" in word["text"]:
                        if year == 2002:
                            col_6 = word["x0"] - 1
                        elif year == 2005:
                            col_7 = word["x0"] + 5
                    elif "RPT" in word["text"]:
                        if year == 2006:
                            col_6 = word["x0"] - 1
                    elif "FTE" in word["text"]:
                        if year == 2002 or year == 2006:
                            col_7 = word["x0"]
                    elif "FRAC" in word["text"]:
                        if year > 2006:
                            col_7 = word["x0"] - 5
                    elif "GF" in word["text"]:
                        if year == 2006:
                            col_8 = word["x0"] + 1
                            col_9 = word["x1"] + 41
                    elif "GEN" in word["text"]:
                        if year == 2002:
                            col_8 = word["x0"]
                    elif "OF" in word["text"]:
                        if year != 2002 and year != 2006:
                            col_8 = word["x0"] - 15
                    elif "PAID" in word["text"]:
                        if year == 2007:
                            col_9 = word["x0"] + 10
                        elif year == 2005:
                            col_9 = word["x0"] + 14
                    elif "FUND" in word["text"]:
                        if year == 2002:
                            col_9 = word["x1"] + 3

            # Set column settings
            table_settings = {
                "explicit_vertical_lines": [col_1, col_2, col_3, col_4, col_5, col_6, col_7, col_8, col_9],
                "horizontal_strategy": "text"
            }

        if 2016 < year < 2019:  # Only have header data on second page
            # Find page with the header data
            page = pdf.pages[1]

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
                    if year == 2017:
                        col_5 = word["x0"] - 5
                    else:
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

        if year > 2001:
            # Iterate through each page
            for page in pdf.pages:
                if year < 2008 or 2016 < year < 2019:
                    pass  # Already set master settings for whole document above

                # Determine the column settings for optimal scraping
                else:
                    # Fetch all vertical edges and sort by x-coordinates
                    edges = page.edges
                    vertical_edges = [e for e in edges if e["orientation"] == "v"]
                    x_coords = sorted(set([e["x0"] for e in vertical_edges]))

                    # Find columns based on words in header
                    words = page.extract_words()
                    for word in words[:55]:
                        if "NAME" in word["text"]:
                            if year > 2008:
                                col_2 = word["x0"] - 1
                            else:
                                col_2 = word["x0"] - 57
                        elif "APPOINTMENT" in word["text"]:
                            if year > 2008:
                                col_3 = word["x0"] - 1
                            else:
                                col_3 = word["x0"] - 35
                        elif "APPOINTING" in word["text"]:
                            if year > 2008:
                                col_4 = word["x0"] - 1
                            else:
                                col_4 = word["x0"] - 37
                        elif "FTR" in word["text"]:
                            if 2009 < year < 2012:
                                col_5 = word["x0"] - 27
                            elif year == 2012 or year == 2015:
                                col_5 = word["x0"] - 35
                            elif 2012 < year < 2015 or year == 2016:
                                col_5 = word["x0"] - 15
                            elif 2019 < year < 2022:
                                col_5 = word["x0"] - 1
                            else:
                                col_5 = word["x0"] - 6
                        elif "BASIS" in word["text"]:
                            if year == 2009:
                                col_6 = word["x0"] - 8
                            elif year == 2010:
                                col_6 = word["x0"] - 10
                            elif 2010 < year < 2015:
                                col_6 = word["x0"] - 5
                            elif year == 2008 or year == 2019:
                                col_6 = word["x0"] - 12
                            else:
                                col_6 = word["x0"] - 1
                        elif "FRACTION" in word["text"]:
                            col_7 = word["x0"] + 5
                        elif "FUND" in word["text"]:
                            if year < 2013:
                                col_8 = word["x0"] - 15
                            elif year < 2017:
                                col_8 = word["x0"] - 10
                            else:
                                col_8 = word["x0"]

                    try:
                        # Set column settings
                        table_settings = {
                            "explicit_vertical_lines": [x_coords[0], col_2, col_3, col_4, col_5, col_6, col_7, col_8, x_coords[-1]],
                            "horizontal_strategy": "text"
                        }
                    except UnboundLocalError:
                        print(year, page)
                        continue

                table = page.extract_table(table_settings=table_settings)

                re_match = False  # In case first name is on a second row

                for row in table:
                    if "UM_" not in row[0]:
                        if 2007 < year < 2012 and row[0] == "":
                            if row[1] != "Name" and row[1] != "":  # Second part of name
                                employee = employees.pop(-1)
                                if employee["Name"][-1] == "-":
                                    employee["Name"] += row[1]
                                else:
                                    employee["Name"] += " " + row[1]
                                
                                if re_match:
                                    name_match = re.match(r"(.*),(.*)", employee["Name"])
                                    employee["Name"] = name_match.group(2).strip() + " " + name_match.group(1).strip()
                                employees.append(employee)
                                re_match = False
                        continue  # Not a row with employee data
                    try:
                        name_match = re.match(r"(.*),(.*)", row[1])
                        employee = {"Name": name_match.group(2).strip() + " " + name_match.group(1).strip()}
                    except AttributeError:
                        if year < 2012:
                            employee = {"Name": row[1]}
                            re_match = True
                        else:
                            print(row)
                            missed.append(row)
                            continue
                    if year == 2004:
                        employee["Campus"] = row[0].lstrip('"UM_')
                    else:
                        employee["Campus"] = row[0].lstrip("UM_")
                    employee["Appointment Title"] = row[2]
                    employee["Appointing Department"] = row[3]
                    try:
                        employee["Annual FTR"] = float(row[4].replace(",", ""))
                    except ValueError:
                        if "###" in row[4]:
                            employee["Annual FTR"] = 0
                        else:
                            employee["Annual FTR"] = row[4]
                            missed.append(row)
                    employee["FTR Basis"] = row[5]
                    try:
                        employee["Fraction"] = float(row[6])
                    except ValueError:
                        employee["Fraction"] = row[6]
                        missed.append(row)
                    if year == 2004:
                        try:
                            employee["General Fund Amount"] = float(row[7].rstrip('"').replace(",", ""))
                        except ValueError:
                            employee["General Fund Amount"] = row[7].rstrip('"')
                            missed.append(row)
                    else:
                        try:
                            employee["General Fund Amount"] = float(row[7].replace(",", ""))
                        except ValueError:
                            employee["General Fund Amount"] = row[7]
                            missed.append(row)
                    
                    # Add employee
                    employees.append(employee)

    # Handle fractional appointments
    # Create dataframe with all employee data
    df = pd.DataFrame(employees)

    # Groupby name and then filter out groupings of different people
    salaries = df.groupby("Name", sort=False)
    salaries = salaries.filter(lambda x: x["Fraction"].sum() <= 1.00)

    # Grab the index of those who were grouped after filtering
    filter = salaries.index

    # Then set index to be the name
    salaries.set_index("Name", inplace=True)

    # Collect all the employee information across appointments 
    campus = df.loc[filter,:].groupby("Name", sort=False)["Campus"].first()
    jobs = df.loc[filter,:].groupby("Name", sort=False)["Appointment Title"].apply(lambda x: " and ".join(x))
    dpt = df.loc[filter,:].groupby("Name", sort=False)["Appointing Department"].apply(lambda x: " and ".join(x))
    ftr = df.loc[filter,:].groupby("Name", sort=False)["FTR Basis"].apply(lambda x: " and ".join(x))
    merge1 = pd.merge(campus, jobs, on="Name")
    merge2 = pd.merge(dpt, ftr, on="Name")
    merge2 = pd.merge(merge1, merge2, on="Name")

    # Now sum the fraction's and salaries and merge again
    salaries = salaries.iloc[:,[3,5,6]].groupby("Name", sort=False).sum()
    merge3 = pd.merge(merge2, salaries, on="Name")
    
    # Grab the names of those whose salaries have been summed
    names = salaries.index

    # Now grab the complete data for everyone else
    mask = df["Name"].isin(names)
    others = df.loc[~mask,:].set_index("Name")

    # Final merge for all the data and sort the data
    merge4 = pd.concat([merge3, others])
    merge4.sort_index(inplace=True)

    # Write csv file
    merge4.to_csv(f"converted/umich/umich-{year}.csv")

    return missed, len(df)


def uf_scraper(file, year):
    """Scrapes UF salary data pdf and returns csv"""
    import pdfplumber
    import re
    import pandas as pd

    # Read in the pdf file
    with pdfplumber.open(file) as pdf:

        # List to store dictionaries of values for each employee
        employees = []

        # List to store missed rows
        missed = []

        # Iterate through each page
        for page in pdf.pages:

            if year < 2018:
                # Find columns based on words in header
                words = page.extract_words()
                col_1, col_2, col_3, col_4, col_5, col_6, col_7, col_8 = [None] * 8  # Initialize columns
                for word in words[:70]:
                    if "NAME" in word["text"]:
                        if col_1 is None:  # Only use first occurance
                            if year < 2008:
                                col_1 = word["x0"] - 50
                            else:
                                col_1 = word["x0"] - 60
                    elif "JOB" in word["text"]:
                        if col_2 is None:
                            col_2 = word["x0"] + 25
                    elif "TENURE" in word["text"]:
                        if year < 2008 and col_3 is None:
                            col_3 = word["x0"] - 67
                            col_4 = word["x1"] + 73
                    elif "PAY" in word["text"]:
                        if year < 2004 and col_3 is None:
                            col_3 = word["x0"] - 23
                    elif "FTE" in word["text"]:
                        if year < 2004 and col_4 is None:
                            col_4 = word["x0"] - 15
                            col_5 = word["x1"] + 12
                        elif year < 2008 and col_5 is None:
                            col_5 = word["x0"] - 15
                            col_6 = word["x1"] + 12
                        elif year > 2007 and col_3 is None:
                            col_3 = word["x0"] - 17
                    elif "CURRENT" in word["text"]:
                        if year < 2004 and col_6 is None:
                            col_6 = word["x0"] - 23
                            col_7 = word["x1"] + 23
                        elif year < 2008 and col_7 is None:
                            col_7 = word["x0"] - 23
                            col_8 = word["x1"] + 23
                        elif year > 2007 and col_4 is None:
                            col_4 = word["x0"] - 20
                            col_5 = word["x1"] + 25

                # Set column settings
                if year < 2004:
                    table_settings = {
                        "explicit_vertical_lines": [col_1, col_2, col_3, col_4, col_5, col_6, col_7], 
                        "horizontal_strategy": "text"
                    }
                elif year < 2008:
                    table_settings = {
                        "explicit_vertical_lines": [col_1, col_2, col_3, col_4, col_5, col_6, col_7, col_8], 
                        "horizontal_strategy": "text"
                    }
                else:
                    table_settings = {
                        "explicit_vertical_lines": [col_1, col_2, col_3, col_4, col_5], 
                        "horizontal_strategy": "text"
                    }
                
                table = page.extract_table(table_settings=table_settings)

                college = None
                for row in table[:10]:  # Only check header rows
                    if row[0] != "" and row[1:4] == [""] * 3:
                        if college is None:  # First row is college
                            college = row[0]
                        else:
                            dpt = row[0]
                
                # Adjust for employee data extraction
                col_2 -= 90

                # Set new column settings
                if year < 2004:
                    table_settings = {
                        "explicit_vertical_lines": [col_1, col_2, col_3, col_4, col_5, col_6, col_7], 
                        "horizontal_strategy": "text"
                    }
                elif year < 2008:
                    table_settings = {
                        "explicit_vertical_lines": [col_1, col_2, col_3, col_4, col_5, col_6, col_7, col_8], 
                        "horizontal_strategy": "text"
                    }
                else:
                    table_settings = {
                        "explicit_vertical_lines": [col_1, col_2, col_3, col_4, col_5], 
                        "horizontal_strategy": "text"
                    }
            else:
                # Set column settings
                table_settings = {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines"
                }

            table = page.extract_table(table_settings=table_settings)

            if 2007 < year < 2018:
                if len(table[0]) != 4:  # Fix columns if not producing 4 rows
                    col_1 += 60
                    table_settings = {
                        "explicit_vertical_lines": [col_1, col_2, col_3, col_4, col_5], 
                        "horizontal_strategy": "text"
                        }
                    table = page.extract_table(table_settings=table_settings)

            for row in table:
                if year == 2003:
                    if row[0] == "" or row[0] == "NAME":
                        continue  # Header, empty, or non-salary
                    if row[0] != "" and row[1:6] == [""] * 5:
                        continue  # Faculty or staff
                    if row[:1] != "" and row[2:6] == [""] * 4:
                        continue  # College/department 
                    if "-----" in row[0]:
                        continue  # Separator
                    if row[2] != "SALARY":
                        continue  # Non-salary
                    
                    employee = {"Name": row[0].title()}
                    employee["College"] = college
                    employee["Department"] = dpt
                    employee["Job Title"] = row[1]
                    employee["Pay Source"] = row[2]
                    try:
                        employee["Budget FTE"] = float(row[3].replace(",", ""))
                    except AttributeError:
                        employee["Budget FTE"] = row[3]
                        missed.append(row)
                    try:
                        employee["Person Years"] = float(row[4].replace(",", ""))
                    except AttributeError:
                        employee["Person Years"] = row[4]
                        missed.append(row)
                    try:
                        employee["Current Rate"] = float(row[5].replace(",", ""))
                    except AttributeError:
                        employee["Current Rate"] = row[5]
                        missed.append(row)

                elif year < 2008:
                    if row[0] == "" or row[0] == "NAME":
                        continue  # Header, empty, or nonstaff
                    if row[0] != "" and row[1:7] == [""] * 6:
                        continue  # Faculty or staff
                    if row[:1] != "" and row[2:7] == [""] * 5:
                        continue  # College/department 
                    if "-----" in row[0]:
                        continue  # Separator
                    if row[3] != "SALARY":
                        continue  # Non-salary
                    
                    employee = {"Name": row[0].title()}
                    employee["College"] = college
                    employee["Department"] = dpt
                    employee["Job Title"] = row[1]
                    employee["Tenure Department"] = row[2]
                    employee["Pay Source"] = row[3]
                    try:
                        employee["Budget FTE"] = float(row[4].replace(",", ""))
                    except AttributeError:
                        employee["Budget FTE"] = row[4]
                        missed.append(row)
                    except ValueError:
                        if "+" in row[4]:
                            grand_total = row[4].lstrip("+") + row[6]
                            try:
                                employee["Current Rate"] = float(grand_total.replace(",", ""))
                            except AttributeError:
                                employee["Current Rate"] = grand_total
                                missed.append(row)
                            employees.append(employee)
                            continue
                        else:
                            missed.append(row)
                    try:
                        employee["Person Years"] = float(row[5].replace(",", ""))
                    except AttributeError:
                        employee["Person Years"] = row[5]
                        missed.append(row)
                    try:
                        employee["Current Rate"] = float(row[6].replace(",", ""))
                    except AttributeError:
                        employee["Current Rate"] = row[6]
                        missed.append(row)

                elif 2007 < year < 2018:
                    if row[0] == "" or row[0] == "NAME":
                        continue  # Header or empty
                    if row[2] == "" and row[3] == "":
                        continue  # College/department
                    if "-----" in row[0]:
                        continue  # Separator
                    if row[1] == "":
                        continue  # Total
                    
                    employee = {"Name": row[0].title()}
                    employee["College"] = college
                    employee["Department"] = dpt
                    employee["Job Title"] = row[1]
                    try:
                        employee["Budget FTE"] = float(row[2].replace(",", ""))
                    except AttributeError:
                        employee["Budget FTE"] = row[2]
                        missed.append(row)
                    except ValueError:
                        if "+" in row[2]:
                            grand_total = row[2].lstrip("+") + row[3]
                            try:
                                employee["Current Rate"] = float(grand_total.replace(",", ""))
                            except AttributeError:
                                employee["Current Rate"] = grand_total
                                missed.append(row)
                            employees.append(employee)
                            continue
                        else:
                            missed.append(row)
                    try:
                        employee["Current Rate"] = float(row[3].replace(",", ""))
                    except AttributeError:
                        employee["Current Rate"] = row[3]
                        missed.append(row)

                else:
                    if "College or Area" in row[0]:
                        continue  # Header row
                    elif row[0] != "":
                        college_area = row[0].replace("\n", " ")
                        department = row[1].replace("\n", " ")

                    employee = {"Name": row[2].replace(",", "").replace("\n", " ").title()}
                    if employee["Name"] == "":  # Total
                        continue
                    employee["College"] = college_area
                    employee["Department"] = department
                    employee["Job Title"] = row[3].replace("\n", " ")
                    try:
                        employee["Budget FTE"] = float(row[4].replace(",", ""))
                    except ValueError:
                        employee["Budget FTE"] = row[4]
                        missed.append(row)
                    try:
                        employee["Current Rate"] = float(row[5].lstrip("$").replace(",", ""))
                    except ValueError:
                        employee["Current Rate"] = row[5]
                        missed.append(row)
                
                # Add observation
                employees.append(employee)

    # Create dataframe with all employee data
    df = pd.DataFrame(employees)

    # Handle fractional appointments
    if 2002 < year < 2008:
        # First collect all employees who have fractional appointments
        fractional = df[df["Budget FTE"] != 1].copy()
        to_merge = fractional[["Name", "College", "Department", "Job Title", "Pay Source", "Budget FTE"]]
        to_merge.set_index("Name", inplace=True)

        # Then determine their primary job based on highest fraction
        primary = fractional.groupby("Name", sort=False)["Budget FTE"].max()

        # Merge the two to get their primary job
        merge_1 = pd.merge(to_merge, primary, how="right", on=["Name", "Budget FTE"])

        # Remove the partial fraction since we will want the final data to display the fractional sum
        merge_1.drop(columns="Budget FTE", inplace=True)

        # Now compute their total salary and add it back in
        total_salary = fractional.groupby("Name", sort=False)[["Budget FTE", "Current Rate"]].sum()
        merge_2 = pd.merge(merge_1, total_salary, how="left", on=["Name"])

        # Now collect all other employees
        other_employees = df[df["Budget FTE"] == 1].copy()
        other_employees.drop(columns="Person Years", inplace=True)
        if year != 2003:
            other_employees.drop(columns="Tenure Department", inplace=True)
        other_employees.set_index("Name", inplace=True)

        # Combine the two dataframes to get all employees
        df = pd.concat([merge_2, other_employees])
        df.sort_index(inplace=True)
    else:
        # First collect all employees who have fractional appointments
        fractional = df[df["Budget FTE"] != 1].copy()
        to_merge = fractional[["Name", "College", "Department", "Job Title", "Budget FTE"]]
        to_merge.set_index("Name", inplace=True)

        # Then determine their primary job based on highest fraction
        primary = fractional.groupby("Name", sort=False)["Budget FTE"].max()

        # Merge the two to get their primary job
        merge_1 = pd.merge(to_merge, primary, how="right", on=["Name", "Budget FTE"])

        # Remove the partial fraction since we will want the final data to display the fractional sum
        merge_1.drop(columns="Budget FTE", inplace=True)

        # Now compute their total salary and add it back in
        total_salary = fractional.groupby("Name", sort=False)[["Budget FTE", "Current Rate"]].sum()
        merge_2 = pd.merge(merge_1, total_salary, how="left", on=["Name"])

        # Now collect all other employees
        other_employees = df[df["Budget FTE"] == 1].copy()
        other_employees.set_index("Name", inplace=True)

        # Combine the two dataframes to get all employees
        df = pd.concat([merge_2, other_employees])
        df.sort_index(inplace=True)

    # Write csv
    df.to_csv(f"converted/uf/uf-{year}.csv")

    return missed, len(df)


def get_azure_data(file, school):
    """Uses Azure Document Intelligence to retrieve data when column identifiers fail"""
    import codes
    import base64
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
    import pandas as pd

    endpoint = codes.endpoint
    key = codes.api_key

    with open(file, "rb") as f:
        base64_encoded_pdf = base64.b64encode(f.read()).decode()

    document_intelligence_client  = DocumentIntelligenceClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    poller = document_intelligence_client.begin_analyze_document(
        "prebuilt-layout", AnalyzeDocumentRequest(bytes_source=base64_encoded_pdf)
    )
    result = poller.result()

    table = result.tables[-1]

    # Convert to pandas dataframe
    matrix = [["" for _ in range(table.column_count)] for _ in range(table.row_count)]
    for cell in table.cells:
        row_index = cell.row_index
        column_index = cell.column_index

        if row_index < table.row_count and column_index < table.column_count:
            matrix[row_index][column_index] = cell.content
    df = pd.DataFrame(matrix)

    # Get rid of extra rows if there are any
    if school == "Illinois":
        if len(df.columns) > 6:
            if len(df.columns) == 8:
                df = pd.DataFrame({
                    "0": df[0] + df[1], "1": df[2] + df[3], "2": df[4], "3": df[5], "4": df[6], "5": df[7]
                })
            else:
                print(len(df.columns))
                raise ValueError

    # Then convert to table to use in scraper
    table = []
    for idx, row in df.iterrows():
        table.append(list(row))

    return table


