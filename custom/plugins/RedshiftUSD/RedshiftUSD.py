#!/usr/bin/env python3

from __future__ import absolute_import
from System import *
from System.Diagnostics import *
from System.IO import *

from Deadline.Plugins import DeadlinePlugin, PluginType
from Deadline.Scripting import FileUtils, SystemUtils, RepositoryUtils, FrameUtils, StringUtils

import io
import os
import re
from six.moves import range
######################################################################
## This is the function that Deadline calls to get an instance of the
## main DeadlinePlugin class.
######################################################################
def GetDeadlinePlugin():
    return RedshiftPlugin()

def CleanupDeadlinePlugin( deadlinePlugin ):
    deadlinePlugin.Cleanup()

class RedshiftPlugin( DeadlinePlugin ):

    def __init__( self ):
        import sys
        if sys.version_info.major == 3:
            super().__init__()
        self.InitializeProcessCallback += self.InitializeProcess
        self.RenderExecutableCallback += self.RenderExecutable
        self.RenderArgumentCallback += self.RenderArgument
    
    def Cleanup( self ):
        for stdoutHandler in self.StdoutHandlers:
            del stdoutHandler.HandleCallback
        
        del self.InitializeProcessCallback
        del self.RenderExecutableCallback
        del self.RenderArgumentCallback
    
    def InitializeProcess( self ):
        self.SingleFramesOnly = True
        self.StdoutHandling = True
        self.PopupHandling = True
        self.FinishedBlocks = 0
        
        self.AddStdoutHandlerCallback( ".*ERROR +\\|.*" ).HandleCallback += self.HandleStdoutError
        self.AddStdoutHandlerCallback( "Block (\\d+)/(\\d+) .+ rendered" ).HandleCallback += self.HandleProgress
        
        self.SetRedshiftPathmappingEnv()
        

    def RenderExecutable( self ):
        version = self.GetPluginInfoEntryWithDefault( "Version", "1" )
        return self.GetRenderExecutable("Redshift_Executable_" + version , "Redshift render (%s)" % version)

    def RenderArgument( self ):
        arguments = ''

        # Get the input .rs file and swap out the frame number.
        filename = self.GetPluginInfoEntry( "SceneFile" )
        filename = self.CheckPath( filename )
        
        substituteFrame = self.GetBooleanPluginInfoEntryWithDefault( "ReplaceFrameNumber", True )
        
        if substituteFrame:
            currPadding = FrameUtils.GetFrameStringFromFilename( filename )
            paddingSize = len( currPadding )
            if paddingSize > 0:
                newPadding = StringUtils.ToZeroPaddedString( self.GetStartFrame(), paddingSize, False )
                filename = FrameUtils.SubstituteFrameNumber( filename, newPadding )

        arguments += '"%s"' % filename

        outputImageDirectory = self.GetPluginInfoEntryWithDefault( "ImageOutputDirectory", "" )
        outputImageDirectory = self.CheckPath( outputImageDirectory )
        if outputImageDirectory != "":
            arguments += ' -oip "%s"' % outputImageDirectory

        pbtOutputDirectory = self.GetPluginInfoEntryWithDefault( "PBTOutputDirectory", "" )
        pbtOutputDirectory= self.CheckPath( pbtOutputDirectory )
        if pbtOutputDirectory != "":
            arguments += ' -opbp "%s"' % pbtOutputDirectory

        renderOptionsFile = self.GetPluginInfoEntryWithDefault( "RenderOptionsFile", "" )
        renderOptionsFile = self.CheckPath( renderOptionsFile )
        if renderOptionsFile != "":
            arguments += ' -oro "%s"' % renderOptionsFile

        if self.GetBooleanPluginInfoEntryWithDefault( "OverrideResolution", False ):
            width = self.GetIntegerPluginInfoEntryWithDefault( "Width", 800 )
            height = self.GetIntegerPluginInfoEntryWithDefault( "Height", 600 )
            arguments += ' -ores %sx%s' % ( width, height )

        gpus = self.getGPUList()
        if len(gpus) > 0:
            self.SetEnvironmentVariable('REDSHIFT_GPUDEVICES', ','.join(gpus))

        cacheDirectory = self.GetPluginInfoEntryWithDefault( "CacheDirectory", "" )
        cacheDirectory = self.CheckPath( cacheDirectory )
        if cacheDirectory != "":
            arguments += ' -cachepath "%s"' % cacheDirectory

        textureCacheBudget = self.GetIntegerPluginInfoEntryWithDefault( "TextureCacheBudget", 0 )
        if textureCacheBudget > 0:
            arguments += ' -texturecachebudget %s' % textureCacheBudget
        
        return arguments
    
    def CheckPath( self, path ):
        path = RepositoryUtils.CheckPathMapping( path )
        if SystemUtils.IsRunningOnWindows():
            path = path.replace( "/", "\\" )
            if path.startswith( "\\" ) and not path.startswith( "\\\\" ):
                path = "\\" + path
        else:
            path = path.replace( "\\", "/" )
        
        return path
    
    def HandleStdoutError( self ):
        self.FailRender( self.GetRegexMatch( 0 ) )

    def HandleProgress( self ):
        self.FinishedBlocks += 1
        totalBlockCount = float( self.GetRegexMatch( 2 ) )

        progress = 100 * self.FinishedBlocks / totalBlockCount
        self.SetProgress( progress )
        self.SetStatusMessage( "%s / %s Blocks Rendered" % ( self.FinishedBlocks, int( totalBlockCount ) ) )

    def getGPUList( self ):
        gpusPerTask = self.GetIntegerPluginInfoEntryWithDefault( "GPUsPerTask", 0 )
        selectGPUDevices = self.GetPluginInfoEntryWithDefault( "SelectGPUDevices", "" ).strip()
        resultGPUs = []

        if self.OverrideGpuAffinity():
            slaveGPUAffinity = list(self.GpuAffinity())
            if gpusPerTask == 0 and selectGPUDevices != "":
                tempGPUs = selectGPUDevices.split( "," )
                notFoundGPUs = []
                for gpu in tempGPUs:
                    gpu = gpu.strip()
                    if int( gpu ) in slaveGPUAffinity:
                        resultGPUs.append( gpu )
                    else:
                        notFoundGPUs.append( gpu )
                
                if len( notFoundGPUs ) > 0:
                    self.LogWarning( "The Worker is overriding its GPU affinity and the following GPUs do not match the Workers affinity so they will not be used: %s" % ",".join( notFoundGPUs ) )

                if len( resultGPUs ) == 0:
                    self.FailRender( "The Worker does not have affinity for any of the GPUs specified in the job." )

            elif gpusPerTask > 0:
                if gpusPerTask > len( slaveGPUAffinity ):
                    self.LogWarning( "The Worker is overriding its GPU affinity and the Worker only has affinity for %s Workers of the %s requested." % ( len( slaveGPUAffinity ), gpusPerTask ) )
                    resultGPUs = [ str( gpu ) for gpu in slaveGPUAffinity ]
                else:
                    startingGPU = self.GetThreadNumber() * gpusPerTask
                    numOverrideGPUs = len( slaveGPUAffinity )
                    startIndex = startingGPU % numOverrideGPUs
                    endIndex = ( startingGPU + gpusPerTask) % numOverrideGPUs
                    if startIndex < endIndex:
                        gpus = slaveGPUAffinity[startIndex:endIndex]
                    else:
                        #If there are multiple render threads going we could roll over the available GPUs in which case we need to grab from both ends of the available GPUs
                        gpus = slaveGPUAffinity[ :endIndex ] + slaveGPUAffinity[ startIndex: ]
                        
                    resultGPUs = [ str( gpu ) for gpu in gpus ]

            else:
                resultGPUs = [ str( gpu ) for gpu in slaveGPUAffinity ]
            
            self.LogInfo( "The Worker is overriding the GPUs to render, so the following GPUs will be used: %s" % ",".join( resultGPUs ) )

        elif gpusPerTask == 0 and selectGPUDevices != "":
            self.LogInfo( "Specific GPUs specified, so the following GPUs will be used: %s" % selectGPUDevices )
            resultGPUs = selectGPUDevices.split( "," )

        elif gpusPerTask > 0:
            # As of redshift 1.3 there is no command line option to specify multiple threads, but this code should still work
            startIndex = self.GetThreadNumber() * gpusPerTask
            
            for i in range( startIndex, startIndex + gpusPerTask ):
                resultGPUs.append( str( i ) )

            self.LogInfo( "GPUs per task is greater than 0, so the following GPUs will be used: " + ",".join( resultGPUs ) )

        return resultGPUs

    def SetRedshiftPathmappingEnv( self ):
        # "C:\MyTextures\" "\\MYSERVER01\Textures\" ...
        redshiftMappingRE = re.compile( r"\"([^\"]*)\"\s+\"([^\"]*)\"" )

        mappings = RepositoryUtils.GetPathMappings()
        #Remove Mappings with no to path.
        mappings = [ mappingPair for mappingPair in mappings if mappingPair[1] ]
        
        if len( mappings ) == 0:
            return

        self.LogInfo( "Redshift Path Mapping..." )

        oldRSMappingFileName = Environment.GetEnvironmentVariable( "REDSHIFT_PATHOVERRIDE_FILE" )
        if oldRSMappingFileName:
            self.LogInfo( '[REDSHIFT_PATHOVERRIDE_FILE]="%s"' % oldRSMappingFileName )
            with io.open( oldRSMappingFileName, mode="r", encoding="utf-8" ) as oldRSMappingFile:
                #lineFormat="from" "to"
                for line in oldRSMappingFile:
                    mappings.extend( redshiftMappingRE.findall( line ) )

        oldRSMappingString = Environment.GetEnvironmentVariable( "REDSHIFT_PATHOVERRIDE_STRING" )
        if oldRSMappingString:
            self.LogInfo( '[REDSHIFT_PATHOVERRIDE_STRING]="%s"' % oldRSMappingString )
            mappings.extend( redshiftMappingRE.findall( oldRSMappingString ) )
        
        newRSMappingFileName = os.path.join( self.CreateTempDirectory("RSMapping"), "RSMapping.txt" )
        with io.open( newRSMappingFileName, mode="w", encoding="utf-8" ) as newRSMappingFile:
            for mappingPair in mappings:
                self.LogInfo( u'source: "%s" dest: "%s"' % (mappingPair[0], mappingPair[1] ))
                newRSMappingFile.write( u'"%s" "%s"\n' % (mappingPair[0], mappingPair[1] ))
        
        self.LogInfo( '[REDSHIFT_PATHOVERRIDE_FILE] now set to: "%s"' % newRSMappingFileName )
        self.SetEnvironmentVariable( "REDSHIFT_PATHOVERRIDE_FILE", newRSMappingFileName )
