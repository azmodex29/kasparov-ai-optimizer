from datetime import datetime

def months_difference(date1_str, date2_str):
    # Convert string to date object
    date1 = datetime.strptime(date1_str, "%d/%m/%Y")
    date2 = datetime.strptime(date2_str, "%d/%m/%Y")

    # Ensure date1 is earlier
    if date1 > date2:
        date1, date2 = date2, date1

    # Calculate month difference
    months = (date2.year - date1.year) * 12 + (date2.month - date1.month)

    # Adjust if end day is smaller than start day
    if date2.day < date1.day:
        months -= 1

    return months


# Input
d1 = input("Enter first date (dd/mm/yyyy): ")
d2 = input("Enter second date (dd/mm/yyyy): ")

# Output
print("Months difference:", months_difference(d1, d2))