"""
This file is used to submit Deadline Jobs from houdini using the Deadline rop (Render OPerators).

Overview:
It does this by performing a post order traversal of the Houdini Node Graph starting from the Selected Deadline Node in order to determine which nodes need to be submitted and what they have for dependencies.
This information is stored in a list of DeadlineJob Objects.  After this we are then submitting the nodes in a linear order to ensure that all dependecies are submitted before the dependent nodes.


Additional Information
Nodes will be submitted using the last encountered Deadline node in the path to that node.
If a node is encountered in multiple paths in the graph it will only be submitted a single time.
We are doing a post order traversal, so we are able to collect all dependent nodes before operating on the current node.
If a node is Locked, then it will be ignore for rendering and all of it's dependencies will also be ignored ( unless they are also dependencies of other nodes)
If a node is Bypassed, then it will be ignored for rendering, however it's dependencies will still be rendered.
Fetch Nodes are Pointers to other sections of a graph and are used to insert sub graph into a dependency chain ( can bring in nodes from other Networks)

"""
from collections import defaultdict

import hou

import SubmitHoudiniToDeadlineFunctions as SHTDFunctions

class DeadlineRopSubmitter( object ):
    NON_RENDERABLE_ROPS = ( "batch","deadline", "fetch", "framedep", "merge", "null", "switch", )

    def __init__( self, dlNode ):
        self.dlNode = dlNode
        # This list will contain the DeadlineJob objects that this submission will be submitting
        self.jobsToSubmit = []
        # This dictionary will contain a mapping of the path to a node (eg. /out/mantra1 ) to a list of Deadline jobs
        # It is used so any future node that is dependent on a node we have already walked can easily set up it's dependncies
        # This dictionary is also used for helping us determine if any circular dependencies are present by initializing value to None.
        self.nodeDependencies = {}

        self.requiredFrames = defaultdict( list )
    
    def submitJobs( self ):
        """
        The main submission function which builds up a list of jobs and then submits each individual job.
        :return: None
        """
        self.setupRequiredFrames()
        self.prepareNodesForSubmission()

        #Any adittional process can be handled here in the future, such as sorting the jobs, or splitting jobs into smaller components.

        for job in self.jobsToSubmit:
            job.submitJob()
    
    def setupRequiredFrames( self ):
        """
        Get all input dependencies from the submitted deadline node and store the necessary frames in a dictionary
        :return: The dictionary that contains the nodes and their required frames.
        """
        self.requiredFrames = defaultdict( list )
        inputDeps = self.dlNode.inputDependencies()
        
        for node, framelist in inputDeps:
            #The same node can appear in input dependencies multiple times so we want to combine all of the lists.
            self.requiredFrames[ node.path() ].extend( [ int( frame ) for frame in framelist ] )

    def prepareNodesForSubmission( self ):
        """
        Entry point to the recursive function which walks the node graph and generates job objects for each submittable node and stores them in this objects jobsToSubmitProperty.
        """
        self.jobsToSubmit = []
        self.nodeDependencies = {}
        self._recursive_PrepareNodesForSubmission( self.dlNode, self.dlNode, None )
    
    def _recursive_PrepareNodesForSubmission( self, dlNode, curNode, fetchDependencies=None ):
        """
        Internal recursive function which generates Job objects for each node that we want to submit
        :param dlNode: The most recent Deadline Node we have come across.  Deadline Job settings are pulled from this node.
        :param curNode: The node that is currently being worked on.
        :param fetchDependencies: The dependencies from the last fetch node that we have come across.  Required to set dependencies across multiple chunks of graphs.
        :return:
        """

        #nodes can point to None sometimes so we want to ignore those cases
        if not curNode:
            return []

        #Get the path for the node to use the path instead of object. eg. /out/mantra1
        curPath = curNode.path()

        #If we have already seen a node there are 2 cases.  Either we have already submitted the node and we can just pull the dependencies from it or we are in a circular dependency.
        if curPath in self.nodeDependencies:
            #if we have seen this node before but we have not processed it then we have encountered a circular dependency.
            if self.nodeDependencies[ curPath ] is None:
                raise Exception( "Circular Dependency Detected - %s is dependent on itself" % curPath )
            #We have already seen this node before so we can just grab it's known dependencies.
            return self.nodeDependencies[ curPath ]

        try:
            # Locked nodes are ignored for the purposes of rendering and their dependencies are also ignored..
            if curNode.isLocked():
                self.nodeDependencies[ curPath ] = [ ]
                return [ ]
        except AttributeError:
            # If a node does not have the isLocked Property then it can never be locked and we can continue walking.
            pass

        # Add a Blank entry to the node So we can break out if we ever run into a circular dependency
        self.nodeDependencies[ curPath ] = None


        # Pull the flags and node type information we care about
        try:
            bypassed = curNode.isBypassed()
        except AttributeError:
            # Some types of nodes (Objects, SHOPs) do not have a bypassed flag.  In these cases we want to continue walking
            bypassed = False


        #Check if this is a Rop by determining if it has a render function and that it is callable
        try:
            isRop = callable(curNode.render)
        except AttributeError:
            #no Render function defined
            isRop = False

        isFetch = ( curNode.type().name() == "fetch" )
        isDeadline = ( curNode.type().name() == "deadline" )
        submitted = False

        #if the current node is being pointed to through a fetch node then we are dependent on anything the fetch node is dependent on
        if fetchDependencies:
            curDeps = fetchDependencies
        else:
            curDeps = []

        #get a list of all input nodes so we can process them
        inputNodes = self._getInputNodes(curNode)

        #if this is a deadline node then we need to update the Deadline Settings that upstream node will pull from.
        futureDlNode = dlNode
        if isDeadline:
            futureDlNode = curNode

        #Recurse into each input node.
        for inputNode in inputNodes:
            curDeps.extend( self._recursive_PrepareNodesForSubmission( futureDlNode, inputNode ) )

        if not bypassed:
            #if this is not a rop or fetch we cannot render anything so do not submit a job to deadline
            if isFetch:
                #if thie node is a fetch and the node it points to exists then we want to prepare the node it points to for submission and have it's chain be dependent on everything the fetch node is dependent on.

                fetchRop = self._getFetchedNode( curNode )
                if fetchRop:

                    # If this node has direct dependencies then we want the nodes this points to too also be dependent on those nodes
                    # If this node does not have direct dependencies then we want the nodes this points to be dependent on any fetch nodes that point to the current node.

                    fetchChainDependencies = self._recursive_PrepareNodesForSubmission( futureDlNode, fetchRop, curDeps  )
                    # If any jobs were created through the fetched node then any downstream nodes will be dependent on those.
                    if fetchChainDependencies:
                        curDeps = fetchChainDependencies
            elif isRop:
                #if this node is bypassed we don't want to submit a job but we still need to grab it's dependencies
                if curNode.type().name() not in DeadlineRopSubmitter.NON_RENDERABLE_ROPS:
                    #If this node is not directly dependent on any nodes, then we must add any fetched dependencies.
                    #We could do this to all nodes however it would add redundant dependencies.

                    frameRange = self._getFrameRangeForNode( curNode )
                    curJob = DeadlineJob( dlNode, curNode, curDeps, frameRange )
                    self.jobsToSubmit.append( curJob )
                    self.nodeDependencies[curPath] = [curJob]
                    #All future jobs that run into this node are dependent on this node
                    curDeps = [ curJob ]
                    submitted = True

        #If we have already submitted this job then we have already set the dependencies for future nodes.
        #Otherwise we want the future nodes to be dependent on all of the current nodes inputs.
        if not submitted:
            self.nodeDependencies[curPath] = curDeps
            
        return curDeps
    
    def _getFrameRangeForNode( self, renderNode ):
        """
        Internal function to get the required frames for a specific render Node.
        :param renderNode: The render node which you want to get the render frame range for.
        :return: An int array of the frames that are to be rendered.
        """
        frameRange = self.requiredFrames[ renderNode.path() ]
        
        return frameRange

    @staticmethod
    def _get_switch_node_selected_index( switch_node ):
        """
        Internal function to get the single specific input index from a
        switch node since switch nodes only respect one input and ignore
        the rest.

        Switch nodes come in a few flavours with slightly different APIs,
        so we perform an existence check to determine which parm to use.

        :param switch_node: The switch node we want to retrieve the input index from
        :return: An int indicating which input to active
        """
        # ie. Driver/switch nodes
        switch_parm = switch_node.parm('index')
        if switch_parm is None:
            # ie. SOP/switch nodes
            switch_parm = switch_node.parm('input')

        return switch_parm.eval()

    @staticmethod
    def _getInputNodes( curNode ):
        """
        Function to get a list of all input nodes for a specified node.
        Respects known flow control nodes in the form of switch and fetch nodes.
        :param curNode: The render node which you want to get the inputs for.
        :return: the list of input nodes.
        """
        isSwitch = ( curNode.type().name() == "switch" )
        
        #inputs returns a tuple we want this to be a list so we can modify it.
        inputNodes = list( curNode.inputs() )
        
        if isSwitch:
            selectedInput = DeadlineRopSubmitter._get_switch_node_selected_index(curNode)
            if 0 <= selectedInput < len( inputNodes ):
                inputNodes = [inputNodes[selectedInput]]
            else:
                inputNodes = []
        
        #remove all instances of None from inputNodes
        return filter( None, inputNodes )

    @staticmethod
    def _getFetchedNode( curNode ):

        # In addition to the normal inputs fetch nodes point to an additional node which we can treat like other input nodes
        fetchedPath = curNode.parm( "source" ).eval()
        fetchedRop = curNode.node( fetchedPath )
        return fetchedRop
    
class DeadlineJob( object ):

    # Property Tuples in the form of Submission property name, DL node Property name, Optional should we convert " " to "" ( see addPropertyToJobProperties )
    generalJobProps = [
        ("jobname", "dl_job_name"),
        ("comment", "dl_comment"),
        ("department", "dl_department"),

        ("pool", "dl_pool"),
        ("secondarypool", "dl_secondary_pool", True), #Combo box that can have an empty string value
        ("group", "dl_group"),
        ("priority", "dl_priority"),
        ("tasktimeout", "dl_task_timeout"),
        ("autotimeout", "dl_auto_task_timeout"),
        ("concurrent", "dl_concurrent_tasks"),
        ("machinelimit", "dl_machine_limit"),
        ("slavelimit", "dl_slave_task_limit"),
        ("limits", "dl_limits"),
        ("onjobcomplete", "dl_on_complete"),
        ("jobsuspended", "dl_submit_suspended"),
        ("shouldprecache", "dl_should_precache"),
        ("isblacklist", "dl_blacklist"),
        ("machinelist", "dl_machine_list"),
        ("isframedependent", "dl_frame_dependent"),

        ("submitscene", "dl_submit_scene"),

        ("gpuopenclenable", "dl_gpu_opencl_enable"),
        ("gpuspertask", "dl_gpus_per_task"),
        ("gpudevices", "dl_gpu_devices"),
    ]

    tileProperties = [
        ("tilesenabled", "dl_tiles_enabled"),
        ("tilesinx", "dl_tiles_in_x"),
        ("tilesiny", "dl_tiles_in_y"),
        ("tilessingleframeenabled", "dl_tiles_single_frame_enabled"),
        ("tilessingleframe", "dl_tiles_single_frame"),
        ("submitdependentassembly", "dl_submit_dependent_assembly"),
        ("backgroundoption", "dl_background_option"),
        ("backgroundimage", "dl_background_image"),
        ("erroronmissingtiles", "dl_error_on_missing_tiles"),
        ("erroronmissingbackground", "dl_error_on_missing_background"),
        ("cleanuptiles", "dl_cleanup_tiles"),
    ]

    jigsawProperties = [
        ("jigsawenabled", False),
        ("jigsawregioncount", 1),
        ("jigsawregions", [ ]),
    ]

    exportProperties = {
        "mantra": [
            ("mantrajob", "dl_mantra_job"),
            ("mantrapool", "dl_mantra_pool"),
            ("mantrasecondarypool", "dl_mantra_secondary_pool", True),#Combo box that can have an empty string value
            ("mantragroup", "dl_mantra_group"),
            ("mantrapriority", "dl_mantra_priority"),
            ("mantratasktimeout", "dl_mantra_task_timeout"),
            ("mantraautotimeout", "dl_mantra_auto_timeout"),
            ("mantraconcurrent", "dl_mantra_concurrent"),
            ("mantramachinelimit", "dl_mantra_machine_limit"),
            ("mantraslavelimit", "dl_mantra_slave_limit"),
            ("mantralimits", "dl_mantra_limits"),
            ("mantraonjobcomplete", "dl_mantra_on_complete"),
            ("mantraisblacklist", "dl_mantra_is_blacklist"),
            ("mantramachinelist", "dl_mantra_machine_list"),
            ("mantrathreads", "dl_mantra_threads"),
            ("mantralocalexport", "dl_mantra_local_export"),
        ],
        "arnold": [
            ("arnoldjob", "dl_arnold_job"),
            ("arnoldpool", "dl_arnold_pool"),
            ("arnoldsecondarypool", "dl_arnold_secondary_pool", True),#Combo box that can have an empty string value
            ("arnoldgroup", "dl_arnold_group"),
            ("arnoldpriority", "dl_arnold_priority"),
            ("arnoldtasktimeout", "dl_arnold_task_timeout"),
            ("arnoldautotimeout", "dl_arnold_auto_timeout"),
            ("arnoldconcurrent", "dl_arnold_concurrent"),
            ("arnoldmachinelimit", "dl_arnold_machine_limit"),
            ("arnoldslavelimit", "dl_arnold_slave_limit"),
            ("arnoldlimits", "dl_arnold_limits"),
            ("arnoldonjobcomplete", "dl_arnold_on_complete"),
            ("arnoldisblacklist", "dl_arnold_is_blacklist"),
            ("arnoldmachinelist", "dl_arnold_machine_list"),
            ("arnoldthreads", "dl_arnold_threads"),
            ("arnoldlocalexport", "dl_arnold_local_export"),
        ],
        "redshift": [
            ("redshiftjob", "dl_redshift_job"),
            ("redshiftpool", "dl_redshift_pool"),
            ("redshiftsecondarypool", "dl_redshift_secondary_pool", True),#Combo box that can have an empty string value
            ("redshiftgroup", "dl_redshift_group"),
            ("redshiftpriority", "dl_redshift_priority"),
            ("redshifttasktimeout", "dl_redshift_task_timeout"),
            ("redshiftautotimeout", "dl_redshift_auto_timeout"),
            ("redshiftconcurrent", "dl_redshift_concurrent"),
            ("redshiftmachinelimit", "dl_redshift_machine_limit"),
            ("redshiftslavelimit", "dl_redshift_slave_limit"),
            ("redshiftlimits", "dl_redshift_limits"),
            ("redshiftonjobcomplete", "dl_redshift_on_complete"),
            ("redshiftisblacklist", "dl_redshift_is_blacklist"),
            ("redshiftmachinelist", "dl_redshift_machine_list"),
            ("redshiftarguments", "dl_redshift_arguments"),
            ("redshiftlocalexport", "dl_redshift_local_export"),
        ],
        "renderman": [
            ("rendermanjob", "dl_renderman_job"),
            ("rendermanpool", "dl_renderman_pool"),
            ("rendermansecondarypool", "dl_renderman_secondary_pool", True),#Combo box that can have an empty string value
            ("rendermangroup", "dl_renderman_group"),
            ("rendermanpriority", "dl_renderman_priority"),
            ("rendermantasktimeout", "dl_renderman_task_timeout"),
            ("rendermanconcurrent", "dl_renderman_concurrent"),
            ("rendermanmachinelimit", "dl_renderman_machine_limit"),
            ("rendermanlimits", "dl_renderman_limits"),
            ("rendermanonjobcomplete", "dl_renderman_on_complete"),
            ("rendermanisblacklist", "dl_renderman_is_blacklist"),
            ("rendermanmachinelist", "dl_renderman_machine_list"),
            ("rendermanthreads", "dl_renderman_threads"),
            ("rendermanarguments", "dl_renderman_arguments"),
            ("rendermanlocalexport", "dl_renderman_local_export"),
        ],
        "vray": [
            ("vrayjob", "dl_vray_job"),
            ("vraypool", "dl_vray_pool"),
            ("vraysecondarypool", "dl_vray_secondary_pool", True),#Combo box that can have an empty string value
            ("vraygroup", "dl_vray_group"),
            ("vraypriority", "dl_vray_priority"),
            ("vraytasktimeout", "dl_vray_task_timeout"),
            ("vrayautotimeout", "dl_vray_auto_timeout"),
            ("vrayconcurrent", "dl_vray_concurrent"),
            ("vraymachinelimit", "dl_vray_machine_limit"),
            ("vrayslavelimit", "dl_vray_slave_limit"),
            ("vraylimits", "dl_vray_limits"),
            ("vrayonjobcomplete", "dl_vray_on_complete"),
            ("vrayisblacklist", "dl_vray_is_blacklist"),
            ("vraymachinelist", "dl_vray_machine_list"),
            ("vrayarguments", "dl_vray_arguments"),
            ("vraythreads", "dl_vray_threads"),
            ("vraylocalexport", "dl_vray_local_export"),
        ]
    }

    def __init__( self, dlNode, rop, dependencies, frameRange=None ):
        self.dlNode = dlNode
        self.rop = rop
        self.dependencies = dependencies
        self.submittedIDs = None
        self.frameRange = frameRange
    
    def getDLProperty( self, propertyName ):
        """
        Returns a Property from the Deadline Node associated with this job.
        :param propertyName: The name of the property to retrieve
        :return: the value of the property that was pulled from the Deadline Node
        """

        val = self.dlNode.parm( propertyName ).eval()

        return val    
    
    def submitJob( self ):
        """
        Submits the Deadline job(s) associated with the current object.
        :return: None
        """

        jobProperties = self.createJobProperties()
        
        # For every job, we need to add the UI dependencies in case they're using multiple deadline nodes in their graph
        # Get the submitted job ID's for all of our dependent jobs
        renderDependencies = [ dep.submittedIDs for dep in self.dependencies if dep.submittedIDs ]
        renderDependencies.extend( self.getDLProperty( "dl_dependencies" ).split(',') )

        jobDeps = SHTDFunctions.SubmitRenderJob( self.rop, jobProperties, ",".join( renderDependencies ) )
        
        #For now SHTDFunctions.SubmitRenderJob can submit multiple jobs at once (Region Rendering/export jobs) which  can cause there to be multiple job IDS.
        #This is used by subsequent job submissions to get dependent ID's
        self.submittedIDs = ",".join( jobDeps )
    
    def createJobProperties( self ):
        """
        Sets up the Job properties for this render job submission
        :return: the job property dictionary
        """
        # Get the General Job Properties that are always used
        jobProperties = {
            "integrationKVPs" : {},#The Deadline rop currently does not support Pipeline Tools.
            "batch" : True,#the jobs will be added to a batch based off the job name
            "ignoreinputs" : True,#each Job in deadline will render only a single job
            "separateWedgeJobs" : True,#If you submit a wedge node each variation will be submitted as a separate job
            "bits" : "None",#Bitness of the executable
        }

        self.addPropertyGroupToJobProperties( jobProperties, self.generalJobProps )

        # We are pulling the Frames separately since we have the option to limit frames based on the Deadline nodes frame range.
        self.addFramePropertiesToJob( jobProperties )

        if SHTDFunctions.NodeSupportsTiles( self.rop ):
            self.addPropertyGroupToJobProperties( jobProperties, self.tileProperties )

        self.addExportPropertiesToJob( jobProperties )
        
        return jobProperties

    def addPropertyGroupToJobProperties( self, jobProperties, propertyGroup ):
        """
        Helper function to walk over a list of property parameters and add the properties to the job properties.
        :param jobProperties: The dictionary that we are adding the parameter to
        :param propertyGroup: The list of Job Properties
        :return: None
        """

        for propertyTuple in propertyGroup:
            # Property is of the form ( Job Property, Node Property, [Optional]ReplaceSingleSpace )
            self.addPropertyToJobProperties( jobProperties, *propertyTuple )

    def addPropertyToJobProperties( self, jobProperties, propertyName, nodeProp, replaceSingleSpace=False ):
        """
        Helper function to add a property to the jobProperties dictionary if the value is valid
        :param jobProperties: The dictionary that we are adding the parameter to
        :param propertyName: The name of the property in the job Properties dictionary
        :param nodeProp: The name of the property within the node.
        :param replaceSingleSpace: Whether or not we should replace " " for "".  Required for Combo box properties that have an empty string as a valid option. eg SecondaryPool
        :param val: The value of the property
        :return: None
        """
        try:
            propertyVal = self.getDLProperty( nodeProp )
        except AttributeError:
            print( "Failed to pull %s from %s. Please consider reinstalling the Deadline Houdini integrated submitter." % (nodeProp, self.dlNode.path() ) )
            return

        if replaceSingleSpace and propertyVal == " ":
            propertyVal = ""

        jobProperties[propertyName] = propertyVal
    
    def addFramePropertiesToJob( self, jobProperties ):
        """
        Updates the jobProperties dictionary with the Frame Properties
        This is special cased because of our Limit Frames to DL node option requiring us to handle it separately.
        :param jobProperties: the job property dictionary that will have properties added to it
        """
        jobProperties["overrideframes"] = False
        self.addPropertyToJobProperties( jobProperties, "framespertask", "dl_chunk_size" )

        try:
            limitFrames = self.getDLProperty("dl_limit_frames_to_node")
        except AttributeError:
            print("Failed to pull dl_limit_frames_to_node from %s. Please consider reinstalling the Deadline Houdini integrated submitter." % (self.dlNode.path()))
        else:
            if limitFrames and self.frameRange:
                jobProperties[ "overrideframes"] =  True
                jobProperties[ "framelist"] = ",".join( str(frame) for frame in self.frameRange )

    def addExportPropertiesToJob( self, jobProperties ):
        """
        Updates the jobProperties dictionary with the appropriate export properties
        :param jobProperties: the job property dictionary that will have properties added to it
        :return: None
        """

        ropType = self.rop.type().name()

        if ropType == "ifd":
            renderer = "mantra"
        elif ropType == "arnold":
            renderer = "arnold"
        elif ropType == "Redshift_ROP":
            renderer = "redshift"
        elif ropType in ( "ris", "rib" ):
            renderer = "renderman"
        elif SHTDFunctions.is_vray_renderer_node( self.rop ):
            renderer = "vray"
        else:
            return

        self.addPropertyGroupToJobProperties( jobProperties, self.exportProperties[ renderer ] )

def SubmitToDeadline(): 
    """
    Entry Point for the main rop to submit using.
    """
    dlNode = hou.pwd()

    if not SHTDFunctions.SaveScene():
        return

    if not dlNode.isLocked():
        dlSubmitter = DeadlineRopSubmitter( dlNode )
        dlSubmitter.submitJobs()