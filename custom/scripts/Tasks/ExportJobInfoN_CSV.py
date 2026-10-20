from Deadline.Scripting import *
from System.IO import *
import os
import csv

def __main__(*args):
    # Get selected tasks
    selectedTasks = MonitorUtils.GetSelectedTasks()
    
    if not selectedTasks:
        print("No tasks selected!")
        return
    
    # Get user's desktop path
    desktop = Environment.GetFolderPath(Environment.SpecialFolder.Desktop)
    csvPath = os.path.join(desktop, "DeadlineTaskInfo.csv")
    
    # Field names to extract
    fields = [
        "TaskId", "Name", "Status", "RenderTime", "FrameTime", 
        "AverageFrameTime", "TaskTime", "TaskReportedTime",
        "TaskStartTime", "TaskEndTime", "TaskMachineName", 
        "TaskProgress", "Frames", "TaskOutputDirectory"
    ]
    
    # Write to CSV
    with open(csvPath, 'wb') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(fields)
        
        # Write each task's data
        for task in selectedTasks:
            row = []
            for field in fields:
                try:
                    value = str(getattr(task, field, ""))
                except:
                    value = ""
                row.append(value)
            writer.writerow(row)
    
    print("Saved task information to: " + csvPath)