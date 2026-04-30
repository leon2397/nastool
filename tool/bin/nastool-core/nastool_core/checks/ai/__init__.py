# AI checks module - lazy loading to avoid circular imports

_loaded = {}


def __getattr__(name: str):
    if name in _loaded:
        return _loaded[name]

    # GPU Detection
    if name == "GPUDetectedCheck":
        from .gpu_detected import GPUDetectedCheck

        _loaded[name] = GPUDetectedCheck
        return GPUDetectedCheck

    # Version checkers
    _version_map = {
        "NvidiaDriverVersionCheck": "NvidiaDriverVersionCheck",
        "CudaVersionCheck": "CudaVersionCheck",
        "TensorRTVersionCheck": "TensorRTVersionCheck",
        "JetPackVersionCheck": "JetPackVersionCheck",
        "RKNNVersionCheck": "RKNNVersionCheck",
        "PyTorchVersionCheck": "PyTorchVersionCheck",
        "ONNXRuntimeVersionCheck": "ONNXRuntimeVersionCheck",
        "VersionCheckerCheck": "AIVersionCheck",  # backward compat alias
    }

    if name in _version_map:
        from . import version_checker as vr

        _loaded[name] = getattr(vr, _version_map[name])
        return _loaded[name]

    # New AI Framework Checkers (direct import)
    _direct_imports = {
        "TensorFlowVersionCheck": "tensorflow_checker",
        "KerasVersionCheck": "keras_checker",
        "CUDNNVersionCheck": "cudnn_checker",
        "OpenVINOVersionCheck": "openvino_checker",
        "PaddlePaddleCheck": "paddlepaddle_checker",
        "TritonServerCheck": "triton_checker",
        "MLflowCheck": "mlflow_checker",
        "GPUMemoryCheck": "gpu_memory_checker",
        "GPUUtilizationCheck": "gpu_utilization_checker",
        "NVIDIAContainerToolkitCheck": "nvidia_container_checker",
        "ONNXModelCheck": "onnx_model_checker",
        "OneDNNVersionCheck": "onednn_checker",
        "TorchServeCheck": "torchserve_checker",
        "TensorFlowServingCheck": "tensorflow_serving_checker",
        "KubeflowCheck": "kubeflow_checker",
        "ModelFormatCheck": "model_format_checker",
    }

    if name in _direct_imports:
        module_name = _direct_imports[name]
        module = __import__(f"checks.ai.{module_name}", fromlist=[name])
        _loaded[name] = getattr(module, name)
        return _loaded[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return list(_loaded.keys()) + [
        # GPU Detection
        "GPUDetectedCheck",
        # Version Checkers
        "NvidiaDriverVersionCheck",
        "CudaVersionCheck",
        "TensorRTVersionCheck",
        "JetPackVersionCheck",
        "RKNNVersionCheck",
        "PyTorchVersionCheck",
        "ONNXRuntimeVersionCheck",
        "VersionCheckerCheck",
        # New Framework Checkers
        "TensorFlowVersionCheck",
        "KerasVersionCheck",
        "CUDNNVersionCheck",
        "OpenVINOVersionCheck",
        "PaddlePaddleCheck",
        "TritonServerCheck",
        "MLflowCheck",
        "GPUMemoryCheck",
        "GPUUtilizationCheck",
        "NVIDIAContainerToolkitCheck",
        "ONNXModelCheck",
        "OneDNNVersionCheck",
        "TorchServeCheck",
        "TensorFlowServingCheck",
        "KubeflowCheck",
        "ModelFormatCheck",
    ]
