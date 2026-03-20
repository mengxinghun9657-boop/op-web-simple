import csv

count = 0
with open('bcc_csv/bcc_instances_1765760420.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        count += 1
        if count <= 2:
            print("Row", count, "BCC_ID:", row['BCC_ID'])
print("Total rows parsed:", count)
