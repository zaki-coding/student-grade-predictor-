# Importing and exporting a semester

Open **Semester Planner** or **Grade Calculator**, then expand **Manage courses & local files**.

- **Workspace JSON** saves the full workspace, including marks, deadlines, credit hours, grade thresholds and GPA settings. Versions 1 and 2 can still be opened. A JSON import replaces the entire workspace.
- **Courses CSV** adds new courses. A course name must be unique within the file and the current workspace. Leave credits or target blank for 3 credit hours and 70%.
- **Assessments CSV** replaces the assessment list for each course in the file. Add the courses first. Leave marks blank for unfinished assessments and use ISO dates such as `2026-11-15`. Each course may have up to 100 assessments. Weights are percentages and may add up to 100%.

The CSV templates are available next to each uploader. Save CSV as UTF-8 with the headers shown below. The app checks the whole file before applying it.

```csv
course,credits,target
Statistics,3,80
```

```csv
course,name,kind,due,weight,mark
Statistics,Midterm,Exam,,40,80
Statistics,Final exam,Exam,2026-11-15,60,
```

Use **Download semester summary (CSV)** for progress, credits and upcoming or overdue deadlines, **Download grade summary (CSV)** for target calculations, and **Download GPA report (CSV)** for credit-weighted GPA and the hypothetical marks currently entered. The reports are for review or sharing. To reopen your editable workspace, save the JSON file.

The app compares deadlines to the date on the computer running Streamlit. Uploads and downloads are limited to 1 MB for workspace JSON, and CSV uploads share that limit. A legacy file close to the limit may open successfully but need fewer rows before it can be saved in the current format. On a hosted instance, use synthetic records for public demos.

