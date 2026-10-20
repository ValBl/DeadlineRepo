from __future__ import absolute_import
import os
from typing import Any, Tuple

from System import *
from System.Collections.Specialized import StringCollection
from System.IO import Path, StreamWriter, File, Directory
from System.Text import Encoding

from Deadline.Scripting import RepositoryUtils, FrameUtils, ClientUtils, PathUtils
from DeadlineUI.Controls.Scripting.DeadlineScriptDialog import DeadlineScriptDialog

from ThinkboxUI.Controls.Scripting.CheckBoxControl import CheckBoxControl
from ThinkboxUI.Controls.Scripting.RangeControl import RangeControl
from ThinkboxUI.Controls.Scripting.TextControl import TextControl
from ThinkboxUI.Controls.Scripting.ButtonControl import ButtonControl

########################################################################
## Globals
########################################################################
scriptDialog = None  # type: DeadlineScriptDialog
settings = None

########################################################################
## Main Function Called By Deadline
########################################################################
def __main__( *args ):
    # type: (*Any) -> None
    global scriptDialog
    global settings
    
    scriptDialog = DeadlineScriptDialog()
    scriptDialog.SetTitle( "Submit Redshift USD Job To Deadline" )
    scriptDialog.SetIcon( scriptDialog.GetIcon( 'RedshiftUSD' ) )

    scriptDialog.AddTabControl( "Tabs", 0, 0 )
    
    scriptDialog.AddTabPage( "Job Options" )
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid( "Separator1", "SeparatorControl", "Job Description", 0, 0, colSpan=2 )

    scriptDialog.AddControlToGrid( "NameLabel", "LabelControl", "Job Name", 1, 0, "The name of your job. This is optional, and if left blank, it will default to 'Untitled'.", False )
    scriptDialog.AddControlToGrid( "NameBox", "TextControl", "Untitled", 1, 1 )

    scriptDialog.AddControlToGrid( "CommentLabel", "LabelControl", "Comment", 2, 0, "A simple description of your job. This is optional and can be left blank.", False )
    scriptDialog.AddControlToGrid( "CommentBox", "TextControl", "", 2, 1)

    scriptDialog.AddControlToGrid( "DepartmentLabel", "LabelControl", "Department", 3, 0, "The department you belong to. This is optional and can be left blank.", False )
    scriptDialog.AddControlToGrid( "DepartmentBox", "TextControl", "", 3, 1 )
    scriptDialog.EndGrid()

    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid( "Separator2", "SeparatorControl", "Job Options", 0, 0, colSpan=3 )
    
    scriptDialog.AddControlToGrid( "PoolLabel", "LabelControl", "Pool", 1, 0, "The pool that your job will be submitted to.", False )
    scriptDialog.AddControlToGrid( "PoolBox", "PoolComboControl", "none", 1, 1 )

    scriptDialog.AddControlToGrid( "SecondaryPoolLabel", "LabelControl", "Secondary Pool", 2, 0, "The secondary pool lets you specify a Pool to use if the primary Pool does not have any available Workers.", False )
    scriptDialog.AddControlToGrid( "SecondaryPoolBox", "SecondaryPoolComboControl", "", 2, 1 )

    scriptDialog.AddControlToGrid( "GroupLabel", "LabelControl", "Group", 3, 0, "The group that your job will be submitted to.", False )
    scriptDialog.AddControlToGrid( "GroupBox", "GroupComboControl", "none", 3, 1 )

    scriptDialog.AddControlToGrid( "PriorityLabel", "LabelControl", "Priority", 4, 0, "A job can have a numeric priority ranging from 0 to 100, where 0 is the lowest priority and 100 is the highest priority.", False )
    scriptDialog.AddRangeControlToGrid( "PriorityBox", "RangeControl", RepositoryUtils.GetMaximumPriority() // 2, 0, RepositoryUtils.GetMaximumPriority(), 0, 1, 4, 1 )

    scriptDialog.AddControlToGrid( "TaskTimeoutLabel", "LabelControl", "Task Timeout", 5, 0, "The number of minutes a Worker has to render a task for this job before it requeues it. Specify 0 for no limit.", False )
    scriptDialog.AddRangeControlToGrid( "TaskTimeoutBox", "RangeControl", 0, 0, 1000000, 0, 1, 5, 1 )
    scriptDialog.AddSelectionControlToGrid( "AutoTimeoutBox", "CheckBoxControl", False, "Enable Auto Task Timeout", 5, 2, "If the Auto Task Timeout is properly configured in the Repository Options, then enabling this will allow a task timeout to be automatically calculated based on the render times of previous frames for the job. " )

    scriptDialog.AddControlToGrid( "ConcurrentTasksLabel", "LabelControl", "Concurrent Tasks", 6, 0, "The number of tasks that can render concurrently on a single Worker. This is useful if the rendering application only uses one thread to render and your Workers have multiple CPUs.", False )
    scriptDialog.AddRangeControlToGrid( "ConcurrentTasksBox", "RangeControl", 1, 1, 16, 0, 1, 6, 1 )
    scriptDialog.AddSelectionControlToGrid( "LimitConcurrentTasksBox", "CheckBoxControl", True, "Limit Tasks To Worker's Task Limit", 6, 2, "If you limit the tasks to a Worker's task limit, then by default, the Worker won't dequeue more tasks then it has CPUs. This task limit can be overridden for individual Workers by an administrator." )

    scriptDialog.AddControlToGrid( "MachineLimitLabel", "LabelControl", "Machine Limit", 7, 0, "Use the Machine Limit to specify the maximum number of machines that can render your job at one time. Specify 0 for no limit.", False )
    scriptDialog.AddRangeControlToGrid( "MachineLimitBox", "RangeControl", 0, 0, 1000000, 0, 1, 7, 1 )
    scriptDialog.AddSelectionControlToGrid( "IsBlacklistBox", "CheckBoxControl", False, "Machine List Is A Deny List", 7, 2, "You can force the job to render on specific machines by using an allow list, or you can avoid specific machines by using a deny list." )

    scriptDialog.AddControlToGrid( "MachineListLabel", "LabelControl", "Machine List", 8, 0, "The list of machines on the deny list or allow list.", False )
    scriptDialog.AddControlToGrid( "MachineListBox", "MachineListControl", "", 8, 1, colSpan=2 )

    scriptDialog.AddControlToGrid( "LimitGroupLabel", "LabelControl", "Limits", 9, 0, "The Limits that your job requires.", False )
    scriptDialog.AddControlToGrid( "LimitGroupBox", "LimitGroupControl", "", 9, 1, colSpan=2 )

    scriptDialog.AddControlToGrid( "DependencyLabel", "LabelControl", "Dependencies", 10, 0, "Specify existing jobs that this job will be dependent on. This job will not start until the specified dependencies finish rendering.", False )
    scriptDialog.AddControlToGrid( "DependencyBox", "DependencyControl", "", 10, 1 )

    scriptDialog.AddControlToGrid( "OnJobCompleteLabel", "LabelControl", "On Job Complete", 11, 0, "If desired, you can automatically archive or delete the job when it completes.", False )
    scriptDialog.AddControlToGrid( "OnJobCompleteBox", "OnJobCompleteControl", "Nothing", 11, 1 )
    scriptDialog.AddSelectionControlToGrid( "SubmitSuspendedBox", "CheckBoxControl", False, "Submit Job As Suspended", 11, 2, "If enabled, the job will submit in the suspended state. This is useful if you don't want the job to start rendering right away. Just resume it from the Monitor when you want it to render.", False )
    scriptDialog.EndGrid()
    scriptDialog.EndTabPage()
    
    scriptDialog.AddTabPage( "Redshift Options" )
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid( "Separator3", "SeparatorControl", "Redshift Options", 0, 0, colSpan=4 )

    scriptDialog.AddControlToGrid( "SceneLabel", "LabelControl", "Redshift File", 1, 0, "The Redshift file(s) to be rendered. If you are submitting a sequence of .rs files, select one of the numbered frames in the sequence, and the frame range will automatically be detected.", False )
    sceneBox = scriptDialog.AddSelectionControlToGrid( "SceneBox", "FileBrowserControl", "", "USD Files (*.usd, *.usdc, *.usda);;All Files (*)", 1, 1, colSpan=3 )
    sceneBox.ValueModified.connect( UpdateFrames )

    scriptDialog.AddControlToGrid( "FramesLabel", "LabelControl", "Frame List", 2, 0, "The list of frames to render. If you are submitting a sequence of .rs files, the frames you choose to render should correspond to the numbers in the .rs files.", False )
    scriptDialog.AddControlToGrid( "FramesBox", "TextControl", "", 2, 1 )
    autoFramesBox = scriptDialog.AddSelectionControlToGrid( "AutoFramesBox", "CheckBoxControl", False, "Calculate Frames From Redshift File", 2, 2, "If enabled, the frame list will be calculated based on the selected input file.", colSpan=2 )
    autoFramesBox.ValueModified.connect( UpdateFrames )

    scriptDialog.AddControlToGrid( "RenderOptionsLabel", "LabelControl", "Render Options File", 3, 0, "Optional. Overrides render options using a text file. The text file should contain pairs of options on each line. ie.\nUnifiedMaxSamples 1500\nUnifiedFilterSize 3.4", False )
    sceneBox=scriptDialog.AddSelectionControlToGrid( "RenderOptionsBox", "FileBrowserControl", "", "Render Options (*.txt);;All Files (*)", 3, 1, colSpan=3 )

    scriptDialog.AddControlToGrid( "ImageOutputLabel", "LabelControl", "Image Output Directory", 4, 0, "Optional. Overrides the image output directory. If left blank, Redshift will save the image output to the folder defined in the .rs file.", False )
    scriptDialog.AddSelectionControlToGrid( "ImageOutputBox", "FolderBrowserControl", "", "", 4, 1, colSpan=3 )

    scriptDialog.AddControlToGrid( "PointBasedTechniqueOutputLabel", "LabelControl", "PBT Output Directory", 5, 0, "Optional. Overrides the point-based technique output directory. If left blank, Redshift will save the point-based technique output to the folder defined in the .rs file.", False )
    scriptDialog.AddSelectionControlToGrid( "PBTOutputBox", "FolderBrowserControl", "", "", 5, 1, colSpan=3 )

    scriptDialog.AddControlToGrid( "CacheDirectoryLabel", "LabelControl", "Cache Directory", 6, 0, "Optional. Overrides the cache path folder. If left blank, Redshift will output to the default cache path folder.", False )
    scriptDialog.AddSelectionControlToGrid( "CacheDirectoryBox", "FolderBrowserControl", "", "", 6, 1, colSpan=3 )

    scriptDialog.AddControlToGrid( "TextureCacheBudgetLabel", "LabelControl", "Texture Cache Budget (MB)", 7, 0, "Optional. Sets the texture cache size (in megabytes). If set to 0, will use the default texture cache budget.", False )
    scriptDialog.AddRangeControlToGrid( "TextureCacheBudgetBox", "RangeControl", 0, 0, 50000, 0, 1, 7, 1 )

    scriptDialog.AddControlToGrid( "GPUsPerTaskLabel", "LabelControl", "GPUs Per Task", 8, 0, "The number of GPUs to use per task. If set to 0, the default number of GPUs will be used.", False )
    gpusPerTaskBox = scriptDialog.AddRangeControlToGrid( "GPUsPerTaskBox", "RangeControl", 0, 0, 16, 0, 1, 8, 1 )
    gpusPerTaskBox.ValueModified.connect( GPUsPerTaskChanged )

    scriptDialog.AddControlToGrid( "SelectGPUDevicesLabel", "LabelControl", "Select GPU Devices", 9, 0, "A comma separated list of the GPUs to use specified by the device id. 'GPUs Per Task' will be ignored.\nie. '0' or '1' or '0,2' or '0,3,4' etc.", False )
    selectGPUDevicesBox = scriptDialog.AddControlToGrid( "SelectGPUDevicesBox", "TextControl", "", 9, 1, colSpan=3 )
    selectGPUDevicesBox.ValueModified.connect( SelectGPUDevicesChanged )

    scriptDialog.AddControlToGrid( "VersionLabel", "LabelControl", "Version", 10, 0, "The version of Redshift to render with.", False )
    scriptDialog.AddComboControlToGrid( "VersionBox", "ComboControl", "1", ( "1", ), 10, 1 )

    resOverrideBox = scriptDialog.AddSelectionControlToGrid( "ResOverrideBox", "CheckBoxControl", False, "Override Resolution", 11, 0, "If enabled, resolution will be overwritten with the values specified." )
    resOverrideBox.ValueModified.connect( enableResOverride )

    scriptDialog.AddControlToGrid( "WidthLabel", "LabelControl", "Width", 12, 0, "Width of the image." )
    scriptDialog.AddRangeControlToGrid( "WidthBox", "RangeControl", 800, 1, 50000, 0, 1, 12, 1, "Width" )
    scriptDialog.SetEnabled( "WidthLabel", False )
    scriptDialog.SetEnabled( "WidthBox", False )
    scriptDialog.AddControlToGrid( "HeightLabel", "LabelControl", "Height", 12, 2, "Height of the image." )
    scriptDialog.AddRangeControlToGrid( "HeightBox", "RangeControl", 600, 1, 50000, 0, 1, 12, 3, "Height" )
    scriptDialog.SetEnabled( "HeightLabel", False )
    scriptDialog.SetEnabled( "HeightBox", False )
    scriptDialog.EndGrid()

    scriptDialog.EndTabPage()
    
    scriptDialog.EndTabControl()
    
    scriptDialog.AddGrid()
    scriptDialog.AddHorizontalSpacerToGrid( "HSpacer1", 0, 0 )
    submitButton = scriptDialog.AddControlToGrid( "SubmitButton", "ButtonControl", "Submit", 0, 1, expand=False )
    submitButton.ValueModified.connect(SubmitButtonPressed)
    closeButton = scriptDialog.AddControlToGrid( "CloseButton", "ButtonControl", "Close", 0, 2, expand=False )
    closeButton.ValueModified.connect(scriptDialog.closeEvent)
    scriptDialog.EndGrid()
    
    #Application Box must be listed before version box or else the application changed event will change the version
    settings = ( "DepartmentBox", "CategoryBox", "PoolBox", "SecondaryPoolBox", "GroupBox", "PriorityBox", "MachineLimitBox", "IsBlacklistBox", "MachineListBox", "LimitGroupBox", "SceneBox", "FramesBox", "AutoFramesBox", "RenderOptionsBox", "ImageOutputBox", "PBTOutputBox", "CacheDirectoryBox", "TextureCacheBudgetBox", "GPUsPerTaskBox", "SelectGPUDevicesBox", "VersionBox" )
    scriptDialog.LoadSettings( GetSettingsFilename(), settings )
    scriptDialog.EnabledStickySaving( settings, GetSettingsFilename() )
    
    UpdateFrames()
    GPUsPerTaskChanged()
    SelectGPUDevicesChanged()
    scriptDialog.ShowDialog( False )

def enableResOverride( *args ):
    # type: (*CheckBoxControl) -> None
    global scriptDialog
    resOverride = scriptDialog.GetValue( "ResOverrideBox" )
    scriptDialog.SetEnabled( "WidthLabel", resOverride )
    scriptDialog.SetEnabled( "WidthBox", resOverride )
    scriptDialog.SetEnabled( "HeightLabel", resOverride )
    scriptDialog.SetEnabled( "HeightBox", resOverride )

def UpdateFrames( *args ):
    # type: (*Any) -> None
    global scriptDialog
    
    filename = scriptDialog.GetValue( "SceneBox" ).strip()
    if not scriptDialog.GetValue( "AutoFramesBox" ) or filename == "":
        return
    
    frameString = FrameUtils.GetFrameRangeFromFilename( filename )
    scriptDialog.SetValue( "FramesBox", frameString )

def GPUsPerTaskChanged( *args ):
    # type: (*RangeControl) -> None
    global scriptDialog

    perTaskEnabled = ( scriptDialog.GetValue( "GPUsPerTaskBox" ) == 0 )

    scriptDialog.SetEnabled( "SelectGPUDevicesLabel", perTaskEnabled )
    scriptDialog.SetEnabled( "SelectGPUDevicesBox", perTaskEnabled )

def SelectGPUDevicesChanged( *args ):
    # type: (*TextControl) -> None
    global scriptDialog

    selectDeviceEnabled = ( scriptDialog.GetValue( "SelectGPUDevicesBox" ) == "" )

    scriptDialog.SetEnabled( "GPUsPerTaskLabel", selectDeviceEnabled )
    scriptDialog.SetEnabled( "GPUsPerTaskBox", selectDeviceEnabled )
    
def GetSettingsFilename():
    # type: () -> str
    return os.path.join( ClientUtils.GetUsersSettingsDirectory(), "RedshiftSettings.ini" )
 
def SubmitButtonPressed( *args ):
    # type: (*ButtonControl) -> None
    global scriptDialog
    errors = ""
    warnings = ""
    
    # Check if Redshift files exist.
    sceneFile = scriptDialog.GetValue( "SceneBox" ).strip()
    tempErrors, tempWarnings = CheckFile( sceneFile, "USD", False )
    errors += tempErrors
    warnings += tempWarnings

    # Check if a valid frame range has been specified.
    frames = scriptDialog.GetValue( "FramesBox" ).strip()
    if not FrameUtils.FrameRangeValid( frames ):
        errors += 'The Frame Range "%s" is not valid.\n' % frames

    # Check the Render Options File
    renderOptionsFile = scriptDialog.GetValue( "RenderOptionsBox" ).strip()
    tempErrors, tempWarnings = CheckFile( sceneFile, "Render Options", True )
    errors += tempErrors
    warnings += tempWarnings

    # Check the image output folder
    imageOutputDirectory = scriptDialog.GetValue( "ImageOutputBox" ).strip()
    tempErrors, tempWarnings = CheckDirectory( imageOutputDirectory, "Image Output Directory", True )
    errors += tempErrors
    warnings += tempWarnings

    # Check the point-based technique output folder
    pbtOutputDirectory = scriptDialog.GetValue( "PBTOutputBox" ).strip()
    tempErrors, tempWarnings = CheckDirectory( pbtOutputDirectory, "PBT Output Directory", True )
    errors += tempErrors
    warnings += tempWarnings

    # Check the cache directory
    cacheDirectory = scriptDialog.GetValue( "CacheDirectoryBox" ).strip()
    tempErrors, tempWarnings = CheckDirectory( cacheDirectory, "Cache Directory", True )
    errors += tempErrors
    warnings += tempWarnings

    # Validate selected GPUs
    selectedGPUs = scriptDialog.GetValue( "SelectGPUDevicesBox" ).strip()
    if selectedGPUs != "":
        gpus = selectedGPUs.split(",")
        for gpu in gpus:
            gpu = gpu.strip()
            try:
                int( gpu )
            except ValueError:
                errors += '"%s" is an invalid gpu, please fix the error by using a comma-separated list of numbers such as "0,1,2"\n\n' % gpu
    
    concurrentTasks = scriptDialog.GetValue( "ConcurrentTasksBox" )
    gpusPerTask = scriptDialog.GetValue( "GPUsPerTaskBox" )
    if concurrentTasks > 1 and gpusPerTask == 0:
        warnings += "Redshift does not support running multiple processes on the same GPU.\nPlease ensure that GPUs Per Task is set to a non-0 value or concurrent tasks is set to 1, otherwise Workers may run into unexpected issues.\n\n"
    
    # output errors , warnings
    if errors:
        scriptDialog.ShowMessageBox( "The following errors must be fixed before submitting the Redshift job:\n\n%s" % errors, "Errors" )
        return
    elif warnings:
        result = scriptDialog.ShowMessageBox( "%sAre you sure you want to submit this job?" % warnings, "Warnings", ( "Yes", "No" ) )
        if result == "No":
            return
        
    jobName = scriptDialog.GetValue( "NameBox" )
    
    # Create job info file.
    jobInfoFilename = os.path.join( ClientUtils.GetDeadlineTempPath(), "redshift_job_info.job" )
    writer = StreamWriter( jobInfoFilename, False, Encoding.Unicode )
    writer.WriteLine( "Plugin=RedshiftUSD" )
    writer.WriteLine( "Name=%s" % jobName )
    writer.WriteLine( "Comment=%s" % scriptDialog.GetValue( "CommentBox" ) )
    writer.WriteLine( "Department=%s" % scriptDialog.GetValue( "DepartmentBox" ) )
    writer.WriteLine( "Pool=%s" % scriptDialog.GetValue( "PoolBox" ) )
    writer.WriteLine( "SecondaryPool=%s" % scriptDialog.GetValue( "SecondaryPoolBox" ) )
    writer.WriteLine( "Group=%s" % scriptDialog.GetValue( "GroupBox" ) )
    writer.WriteLine( "Priority=%s" % scriptDialog.GetValue( "PriorityBox" ) )
    writer.WriteLine( "TaskTimeoutMinutes=%s" % scriptDialog.GetValue( "TaskTimeoutBox" ) )
    writer.WriteLine( "EnableAutoTimeout=%s" % scriptDialog.GetValue( "AutoTimeoutBox" ) )
    writer.WriteLine( "ConcurrentTasks=%s" % concurrentTasks )
    writer.WriteLine( "LimitConcurrentTasksToNumberOfCpus=%s" % scriptDialog.GetValue( "LimitConcurrentTasksBox" ) )
    
    writer.WriteLine( "MachineLimit=%s" % scriptDialog.GetValue( "MachineLimitBox" ) )
    if bool( scriptDialog.GetValue( "IsBlacklistBox" ) ):
        writer.WriteLine( "Blacklist=%s" % scriptDialog.GetValue( "MachineListBox" ) )
    else:
        writer.WriteLine( "Whitelist=%s" % scriptDialog.GetValue( "MachineListBox" ) )
    
    writer.WriteLine( "LimitGroups=%s" % scriptDialog.GetValue( "LimitGroupBox" ) )
    writer.WriteLine( "JobDependencies=%s" % scriptDialog.GetValue( "DependencyBox" ) )
    writer.WriteLine( "OnJobComplete=%s" % scriptDialog.GetValue( "OnJobCompleteBox" ) )
    
    if bool( scriptDialog.GetValue( "SubmitSuspendedBox" ) ):
        writer.WriteLine( "InitialStatus=Suspended" )
    
    writer.WriteLine( "Frames=%s" % frames )
    writer.WriteLine( "ChunkSize=1" )

    outputDirectoryCount = 0
    if len( imageOutputDirectory ) > 0:
        writer.WriteLine( "OutputDirectory%s=%s" % ( outputDirectoryCount, imageOutputDirectory ) )
        outputDirectoryCount += 1

    if len( pbtOutputDirectory ) > 0:
        writer.WriteLine( "OutputDirectory%s=%s" % ( outputDirectoryCount, pbtOutputDirectory ) )
        outputDirectoryCount += 1

    if len( cacheDirectory ) > 0:
        writer.WriteLine( "OutputDirectory%s=%s" % ( outputDirectoryCount, cacheDirectory ) )
        outputDirectoryCount += 1

    writer.Close()
    
    # Create plugin info file.
    pluginInfoFilename = os.path.join( ClientUtils.GetDeadlineTempPath(), "redshift_plugin_info.job" )
    writer = StreamWriter( pluginInfoFilename, False, Encoding.Unicode )
    writer.WriteLine( "Version=%s" % scriptDialog.GetValue( "VersionBox" ) )
    writer.WriteLine( "SceneFile=%s" % sceneFile )
    writer.WriteLine( "RenderOptionsFile=%s" % renderOptionsFile )
    writer.WriteLine( "GPUsPerTask=%s" % gpusPerTask )
    writer.WriteLine( "SelectGPUDevices=%s" % selectedGPUs )
    writer.WriteLine( "TextureCacheBudget=%s" % scriptDialog.GetValue( "TextureCacheBudgetBox" ) )

    if len( imageOutputDirectory ) > 0:
        writer.WriteLine( "ImageOutputDirectory=%s" % imageOutputDirectory )
    
    if len( pbtOutputDirectory ) > 0:
        writer.WriteLine( "PBTOutputDirectory=%s" % pbtOutputDirectory )
    
    if len( cacheDirectory ) > 0:
        writer.WriteLine( "CacheDirectory=%s" % cacheDirectory )

    writer.WriteLine( "OverrideResolution=%s" % scriptDialog.GetValue( "ResOverrideBox" ) )
    writer.WriteLine( "Width=%d" % scriptDialog.GetValue( "WidthBox" ) )
    writer.WriteLine( "Height=%d" % scriptDialog.GetValue( "HeightBox" ) )

    writer.Close()
    
    # Setup the command line arguments.
    arguments = StringCollection()
    arguments.Add( jobInfoFilename )
    arguments.Add( pluginInfoFilename )
    
    # Now submit the job.
    results = ClientUtils.ExecuteCommandAndGetOutput( arguments )
    scriptDialog.ShowMessageBox( results, "Submission Results" )

def CheckFile( file, name, isOptional ):
    # type: (str, str, bool) -> Tuple[str, str]
    errors = ""
    warnings = ""

    if file:
        if not os.path.isfile( file ):
            if isOptional:
                warnings += 'The %s File "%s" does not exist.\n\n' % ( name, file )
            else:
                errors += 'The %s File "%s" does not exist.\n\n' % ( name, file )
        elif PathUtils.IsPathLocal( file ):
            warnings += 'The %s File "%s" is local.\n\n' % ( name, file )
    else:
        if not isOptional:
            errors += 'The %s File is not specified.\n\n' % name

    return errors, warnings

def CheckDirectory( folder, name, isOptional ):
    # type: (str, str, bool) -> Tuple[str, str]
    errors = ""
    warnings = ""

    if folder:
        if not os.path.isdir( folder ):
            if isOptional:
                warnings += 'The %s directory "%s" does not exist.\n\n' % ( name, folder )
            else:
                errors += 'The %s directory "%s" does not exist.\n\n' % ( name, folder )
        elif PathUtils.IsPathLocal( folder ):
            warnings += 'The %s directory "%s" is local.\n\n' % ( name, folder )
    else:
        if not isOptional:
            errors += 'The %s directory is not specified.\n\n' % name

    return errors, warnings