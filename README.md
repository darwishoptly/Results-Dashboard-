Creates a Summarized Results Export

exporter.py is the main file to run (it determines which account to run the program for, and create the actual excel workbook)

OptlyData.py handles most results API calls, and calculates improvement / CTB numbers. One OptlyData object corresponds to all results for a given segment id value pair 
