import bpy

def set_cuda_as_compute_device():
    prefs = bpy.context.preferences
    cprefs = prefs.addons['cycles'].preferences

    # get available devices
    cprefs.get_devices()

    cuda_devices = [d for d in cprefs.devices if d.type == 'CUDA']

    if not cuda_devices:
        print("No CUDA devices found.")
        return

    cprefs.compute_device_type = 'CUDA'

    # enable CUDA 
    for device in cprefs.devices:
        device.use = (device.type == 'CUDA')

    print("CUDA compute device enabled.")

def set_cycles_to_gpu_compute():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'

    # Use GPU 
    scene.cycles.device = 'GPU'

    print("Cycles set to GPU compute.")


set_cuda_as_compute_device()
set_cycles_to_gpu_compute()
