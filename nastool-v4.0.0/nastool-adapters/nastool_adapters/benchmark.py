"""
nastool adapters.benchmark - æ¨çåºåæµè¯

æ¯æå¤æ¡æ¶æ¨çåºåï¼
- ONNX Runtimeï¼éç¨ï¼
- TensorRTï¼Jetsonï¼
- ACLï¼æè¾ï¼
- MindSporeï¼æè¾ï¼
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("nastool.benchmark")

# æ¨¡åéç½®
MODEL_CONFIG = {
    "mobilenetv2": {
        "input_shape": (1, 3, 224, 224),
        "input_name": "input",
        "output_name": "output",
        "model_url": "https://github.com/onnx/models/raw/main/validated/vision/classification/mobilenet/model/mobilenetv2-12.onnx",
    },
    "resnet50": {
        "input_shape": (1, 3, 224, 224),
        "input_name": "input",
        "output_name": "output",
        "model_url": "https://github.com/onnx/models/raw/main/validated/vision/classification/resnet/model/resnet50-v2-7.onnx",
    },
}


def run_onnx_benchmark(
    model_name: str = "mobilenetv2",
    warmup: int = 3,
    iterations: int = 10,
    provider: str = "CPUExecutionProvider",
) -> Dict[str, Any]:
    """
    ONNX Runtime æ¨çåºåæµè¯ã

    Args:
        model_name: æ¨¡ååç§°
        warmup: é¢ç­æ¬¡æ°
        iterations: æµè¯æ¬¡æ°
        provider: æ§è¡æä¾å¨ (CPUExecutionProvider / CUDAExecutionProvider / DnnlExecutionProvider)

    Returns:
        {latency_ms, throughput_fps, status, error}
    """
    import numpy as np

    result: Dict[str, Any] = {
        "model": model_name,
        "framework": "ONNX Runtime",
        "provider": provider,
        "warmup": warmup,
        "iterations": iterations,
        "latency_ms": None,
        "throughput_fps": None,
        "status": "error",
        "error": None,
    }

    try:
        import onnxruntime as ort

        # æ£æ¥æä¾å¨å¯ç¨æ§
        available_providers = ort.get_available_providers()
        if provider not in available_providers:
            result["error"] = f"Provider {provider} not available. Available: {available_providers}"
            result["available_providers"] = available_providers
            return result

        # å è½½æ¨¡å
        model_config = MODEL_CONFIG.get(model_name, MODEL_CONFIG["mobilenetv2"])
        input_shape = model_config["input_shape"]
        input_name = model_config["input_name"]

        # å°è¯ä»ç¼å­å è½½æä¸è½½
        import os

        cache_dir = os.environ.get("NASTOOL_MODEL_CACHE", "/tmp/nastool_models")
        model_path = os.path.join(cache_dir, f"{model_name}.onnx")

        if not os.path.isfile(model_path):
            # å°è¯ä¸è½½
            try:
                import urllib.request

                os.makedirs(cache_dir, exist_ok=True)
                logger.info(f"[Benchmark] Downloading {model_name}...")
                urllib.request.urlretrieve(model_config["model_url"], model_path)
                logger.info(f"[Benchmark] Downloaded to {model_path}")
            except Exception as e:
                result["error"] = f"Failed to download model: {e}"
                return result

        # åå»ºæ¨çä¼è¯
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        session = ort.InferenceSession(model_path, sess_options, providers=[provider])

        # çæéæºè¾å¥
        input_data = np.random.randn(*input_shape).astype(np.float32)

        # é¢ç­
        for _ in range(warmup):
            session.run([model_config["output_name"]], {input_name: input_data})

        # æ­£å¼æµè¯
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            session.run([model_config["output_name"]], {input_name: input_data})
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # ms

        # ç»è®¡
        avg_latency = sum(latencies) / len(latencies)
        throughput = 1000 / avg_latency  # FPS

        result["latency_ms"] = round(avg_latency, 2)
        result["throughput_fps"] = round(throughput, 1)
        result["latencies_ms"] = [round(l, 2) for l in latencies]
        result["status"] = "success"

        logger.info(f"[Benchmark] ONNX {model_name}: {result['latency_ms']}ms, {result['throughput_fps']} FPS")

    except ImportError:
        result["error"] = "onnxruntime not installed"
    except Exception as e:
        result["error"] = str(e)

    return result


def run_tensorrt_benchmark(
    model_name: str = "mobilenetv2",
    warmup: int = 3,
    iterations: int = 10,
    engine_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    TensorRT æ¨çåºåæµè¯ã

    Args:
        model_name: æ¨¡ååç§°
        warmup: é¢ç­æ¬¡æ°
        iterations: æµè¯æ¬¡æ°
        engine_path: é¢ç¼è¯ç TensorRT engine æä»¶è·¯å¾ï¼å¯éï¼

    Returns:
        {latency_ms, throughput_fps, status, error}
    """
    import numpy as np

    result: Dict[str, Any] = {
        "model": model_name,
        "framework": "TensorRT",
        "warmup": warmup,
        "iterations": iterations,
        "latency_ms": None,
        "throughput_fps": None,
        "status": "error",
        "error": None,
    }

    try:
        import tensorrt as trt
        import pycuda.driver as cuda
        import pycuda.autoinit

        model_config = MODEL_CONFIG.get(model_name, MODEL_CONFIG["mobilenetv2"])
        input_shape = model_config["input_shape"]

        # æ¥æ¾æåå»º engine
        if engine_path is None:
            import os
            cache_dir = os.environ.get("NASTOOL_MODEL_CACHE", "/tmp/nastool_models")
            engine_path = os.path.join(cache_dir, f"{model_name}.trt")

        if not os.path.isfile(engine_path):
            # éè¦åä» ONNX è½¬æ¢
            onnx_path = os.path.join(cache_dir, f"{model_name}.onnx")
            if not os.path.isfile(onnx_path):
                result["error"] = f"ONNX model not found at {onnx_path}, need to download first"
                result["status"] = "todo"
                return result

            # ONNX -> TensorRT è½¬æ¢
            logger.info(f"[Benchmark] Converting {model_name}.onnx to TensorRT...")
            trt_logger = trt.Logger(trt.Logger.WARNING)
            builder = trt.Builder(trt_logger)
            network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
            parser = trt.OnnxParser(network, trt_logger)

            with open(onnx_path, "rb") as f:
                if not parser.parse(f.read()):
                    result["error"] = "Failed to parse ONNX model"
                    return result

            config = builder.create_builder_config()
            config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 1 << 30)  # 1GB
            serialized_engine = builder.build_serialized_network(network, config)
            
            with open(engine_path, "wb") as f:
                f.write(serialized_engine)
            logger.info(f"[Benchmark] Saved TensorRT engine to {engine_path}")

        # å è½½ engine
        trt_logger = trt.Logger(trt.Logger.WARNING)
        with open(engine_path, "rb") as f:
            runtime = trt.Runtime(trt_logger)
            engine = runtime.deserialize_cuda_engine(f.read())

        context = engine.create_execution_context()

        # åéæ¾å­
        input_name = model_config["input_name"]
        output_name = model_config["output_name"]
        
        input_size = trt.volume(input_shape) * np.dtype(np.float32).itemsize
        d_input = cuda.mem_alloc(input_size)
        
        output_shape = (1, 1000)  # ImageNet 1000 classes
        output_size = trt.volume(output_shape) * np.dtype(np.float32).itemsize
        d_output = cuda.mem_alloc(output_size)

        bindings = [int(d_input), int(d_output)]

        # åå¤è¾å¥æ°æ®
        input_data = np.random.randn(*input_shape).astype(np.float32)
        output_data = np.empty(output_shape, dtype=np.float32)

        # é¢ç­
        for _ in range(warmup):
            cuda.memcpy_htod(d_input, input_data)
            context.execute_v2(bindings)
            cuda.memcpy_dtoh(output_data, d_output)

        # æ­£å¼æµè¯
        latencies = []
        for _ in range(iterations):
            cuda.memcpy_htod(d_input, input_data)
            start = time.perf_counter()
            context.execute_v2(bindings)
            cuda.memcpy_dtoh(output_data, d_output)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = sum(latencies) / len(latencies)
        throughput = 1000 / avg_latency

        result["latency_ms"] = round(avg_latency, 2)
        result["throughput_fps"] = round(throughput, 1)
        result["latencies_ms"] = [round(l, 2) for l in latencies]
        result["status"] = "success"
        result["engine_path"] = engine_path

        logger.info(f"[Benchmark] TensorRT {model_name}: {result['latency_ms']}ms, {result['throughput_fps']} FPS")

    except ImportError as e:
        result["error"] = f"TensorRT or PyCUDA not installed: {e}"
    except Exception as e:
        result["error"] = str(e)
        logger.exception(f"[Benchmark] TensorRT error: {e}")

    return result


def run_acl_benchmark(
    model_name: str = "mobilenetv2",
    warmup: int = 3,
    iterations: int = 10,
    om_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    ACL (Ascend Computing Language) æ¨çåºåæµè¯ã

    ä½¿ç¨ PyACL æ¥å£å¨æè¾ NPU ä¸è¿è¡æ¨çã

    Args:
        model_name: æ¨¡ååç§°
        warmup: é¢ç­æ¬¡æ°
        iterations: æµè¯æ¬¡æ°
        om_path: é¢ç¼è¯ç .om æ¨¡åæä»¶è·¯å¾ï¼å¯éï¼

    Returns:
        {latency_ms, throughput_fps, status, error}
    """
    import numpy as np

    result: Dict[str, Any] = {
        "model": model_name,
        "framework": "ACL",
        "warmup": warmup,
        "iterations": iterations,
        "latency_ms": None,
        "throughput_fps": None,
        "status": "error",
        "error": None,
    }

    try:
        import acl

        model_config = MODEL_CONFIG.get(model_name, MODEL_CONFIG["mobilenetv2"])
        input_shape = model_config["input_shape"]

        # æ¥æ¾ .om æ¨¡å
        if om_path is None:
            import os
            cache_dir = os.environ.get("NASTOOL_MODEL_CACHE", "/tmp/nastool_models")
            om_path = os.path.join(cache_dir, f"{model_name}.om")

        if not os.path.isfile(om_path):
            result["error"] = f".om model not found at {om_path}. Use ATC to convert ONNX to .om first"
            result["status"] = "todo"
            result["atc_command"] = f"atc --model={model_name}.onnx --framework=5 --output={model_name} --soc_version=Ascend310"
            return result

        # åå§å ACL
        ret = acl.init()
        if ret != 0:
            result["error"] = f"acl.init() failed: {ret}"
            return result

        try:
            # å è½½æ¨¡å
            model_id, ret = acl.mdl.load_from_file(om_path)
            if ret != 0:
                result["error"] = f"Failed to load model: {ret}"
                return result

            # è·åæ¨¡åæè¿°
            model_desc = acl.mdl.create_desc()
            ret = acl.mdl.get_desc(model_desc, model_id)
            if ret != 0:
                result["error"] = f"Failed to get model desc: {ret}"
                return result

            # è·åè¾å¥è¾åºå¤§å°
            input_size = acl.mdl.get_input_size_by_index(model_desc, 0)
            output_size = acl.mdl.get_output_size_by_index(model_desc, 0)

            # åå»ºè¾å¥è¾åº dataset
            input_dataset = acl.mdl.create_dataset()
            output_dataset = acl.mdl.create_dataset()

            input_data = np.random.randn(*input_shape).astype(np.float32)
            input_buffer, ret = acl.util.ptr_to_bytes(input_data, input_size)
            input_data_buffer = acl.create_data_buffer(input_buffer, input_size)
            acl.mdl.add_dataset_buffer(input_dataset, input_data_buffer)

            output_buffer, ret = acl.util.ptr_to_bytes(np.zeros(output_size, dtype=np.float32), output_size)
            output_data_buffer = acl.create_data_buffer(output_buffer, output_size)
            acl.mdl.add_dataset_buffer(output_dataset, output_data_buffer)

            # é¢ç­
            for _ in range(warmup):
                ret, _ = acl.mdl.execute(model_id, input_dataset, output_dataset)
                if ret != 0:
                    result["error"] = f"Model execute failed: {ret}"
                    return result

            # æ­£å¼æµè¯
            latencies = []
            for _ in range(iterations):
                start = time.perf_counter()
                ret, _ = acl.mdl.execute(model_id, input_dataset, output_dataset)
                end = time.perf_counter()
                if ret != 0:
                    result["error"] = f"Model execute failed: {ret}"
                    return result
                latencies.append((end - start) * 1000)

            avg_latency = sum(latencies) / len(latencies)
            throughput = 1000 / avg_latency

            result["latency_ms"] = round(avg_latency, 2)
            result["throughput_fps"] = round(throughput, 1)
            result["latencies_ms"] = [round(l, 2) for l in latencies]
            result["status"] = "success"
            result["model_id"] = model_id

            logger.info(f"[Benchmark] ACL {model_name}: {result['latency_ms']}ms, {result['throughput_fps']} FPS")

            # å¸è½½æ¨¡å
            acl.mdl.unload(model_id)

        finally:
            acl.finalize()

    except ImportError:
        result["error"] = "acl (PyACL) not installed. Install from Ascend SDK"
    except Exception as e:
        result["error"] = str(e)
        logger.exception(f"[Benchmark] ACL error: {e}")

    return result


def run_heuristic_benchmark() -> Dict[str, Any]:
    """
    å¯åå¼åºåæµè¯ï¼æ éæ¨¡åæä»¶ï¼ã

    æ ¹æ® CPU/GPU åå·ä¼°ç®æ¨çæ§è½ã
    """
    result: Dict[str, Any] = {
        "model": "heuristic",
        "framework": "heuristic",
        "latency_ms": None,
        "throughput_fps": None,
        "status": "success",
        "error": None,
    }

    try:
        import multiprocessing
        import platform

        cpu_count = multiprocessing.cpu_count()
        cpu_freq = None

        try:
            import psutil

            cpu_freq = psutil.cpu_freq()
        except Exception:
            pass

        # å¯åå¼ä¼°ç®ï¼MobileNetV2 å¨ä¸åç¡¬ä»¶ä¸çå¸åæ§è½
        # åºåï¼Intel i7 @ 3GHz â 50ms, Jetson Nano â 100ms, Orin AGX â 5ms
        if cpu_freq:
            freq_ghz = cpu_freq.current / 1000
            # ç®åçº¿æ§ä¼°ç®
            base_latency = 50.0  # ms @ 3GHz
            estimated_latency = base_latency * (3.0 / freq_ghz) * (8 / cpu_count)
        else:
            # æ æ³è·åé¢çæ¶ï¼ä½¿ç¨æ ¸å¿æ°ä¼°ç®
            estimated_latency = 100.0 * (8 / cpu_count)

        result["latency_ms"] = round(estimated_latency, 1)
        result["throughput_fps"] = round(1000 / estimated_latency, 1)
        result["cpu_count"] = cpu_count
        result["cpu_freq_mhz"] = cpu_freq.current if cpu_freq else None

    except Exception as e:
        result["error"] = str(e)
        result["status"] = "error"

    return result


def run_mindspore_benchmark(
    model_name: str = "mobilenetv2",
    warmup: int = 3,
    iterations: int = 10,
    device_target: str = "Ascend",
) -> Dict[str, Any]:
    """
    MindSpore æ¨çåºåæµè¯ã

    Args:
        model_name: æ¨¡ååç§°
        warmup: é¢ç­æ¬¡æ°
        iterations: æµè¯æ¬¡æ°
        device_target: è®¾å¤ç®æ  (Ascend / GPU / CPU)

    Returns:
        {latency_ms, throughput_fps, status, error}
    """
    import numpy as np

    result: Dict[str, Any] = {
        "model": model_name,
        "framework": "MindSpore",
        "device_target": device_target,
        "warmup": warmup,
        "iterations": iterations,
        "latency_ms": None,
        "throughput_fps": None,
        "status": "error",
        "error": None,
    }

    try:
        import mindspore as ms
        import mindspore.nn as nn
        import mindspore.ops as ops
        from mindspore import Tensor, context

        # è®¾ç½®è®¾å¤
        context.set_context(mode=context.GRAPH_MODE, device_target=device_target)

        model_config = MODEL_CONFIG.get(model_name, MODEL_CONFIG["mobilenetv2"])
        input_shape = model_config["input_shape"]

        # æ¥æ¾æ¨¡åæä»¶
        import os
        cache_dir = os.environ.get("NASTOOL_MODEL_CACHE", "/tmp/nastool_models")
        mindir_path = os.path.join(cache_dir, f"{model_name}.mindir")

        if not os.path.isfile(mindir_path):
            # å°è¯ä½¿ç¨ MindSpore Hub æåç½®æ¨¡å
            result["error"] = f".mindir model not found at {mindir_path}"
            result["status"] = "todo"
            result["hint"] = "Use MindSpore Hub to download pretrained model"
            return result

        # å è½½æ¨¡å
        graph = ms.load(mindir_path)
        model = nn.GraphCell(graph)

        # åå¤è¾å¥
        input_data = Tensor(np.random.randn(*input_shape).astype(np.float32))

        # é¢ç­
        for _ in range(warmup):
            _ = model(input_data)

        # æ­£å¼æµè¯
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            _ = model(input_data)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        avg_latency = sum(latencies) / len(latencies)
        throughput = 1000 / avg_latency

        result["latency_ms"] = round(avg_latency, 2)
        result["throughput_fps"] = round(throughput, 1)
        result["latencies_ms"] = [round(l, 2) for l in latencies]
        result["status"] = "success"

        logger.info(f"[Benchmark] MindSpore {model_name}: {result['latency_ms']}ms, {result['throughput_fps']} FPS")

    except ImportError:
        result["error"] = "mindspore not installed. Install from https://www.mindspore.cn/"
    except Exception as e:
        result["error"] = str(e)
        logger.exception(f"[Benchmark] MindSpore error: {e}")

    return result



def run_rknn_benchmark(
    model_name: str = "mobilenetv2",
    warmup: int = 3,
    iterations: int = 10,
    device_id: str = "0",
) -> Dict[str, Any]:
    """
    Rockchip RKNN 推理基准测试�?
    
    支持 RK3588 / RK356x 系列 NPU�?

    Args:
        model_name: 模型名称 (mobilenetv2 / resnet50)
        warmup: 预热次数
        iterations: 测试次数
        device_id: 设备 ID (默认 "0")

    Returns:
        {latency_ms, throughput_fps, status, error, npu_info}
    """
    import numpy as np

    result: Dict[str, Any] = {
        "model": model_name,
        "framework": "RKNN",
        "device_id": device_id,
        "warmup": warmup,
        "iterations": iterations,
        "latency_ms": None,
        "throughput_fps": None,
        "status": "error",
        "error": None,
        "npu_info": {},
    }

    try:
        from rknn.api import RKNN
        
        # 检�?NPU 设备
        import os
        if not os.path.exists("/dev/rknpu"):
            result["error"] = "/dev/rknpu not found. Is NPU driver loaded?"
            return result

        # 获取 RKNN 版本
        try:
            rknn_version = RKNN().get_version()
            result["npu_info"]["rknn_version"] = rknn_version
        except Exception:
            result["npu_info"]["rknn_version"] = "unknown"

        # 模型路径
        cache_dir = os.environ.get("NASTOOL_MODEL_CACHE", "/tmp/nastool_models")
        os.makedirs(cache_dir, exist_ok=True)
        
        # 支持的模型格�?
        onnx_path = os.path.join(cache_dir, f"{model_name}.onnx")
        rknn_path = os.path.join(cache_dir, f"{model_name}.rknn")
        
        # 检查是否有已转换的 RKNN 模型
        if not os.path.exists(rknn_path):
            # 需要先转换 ONNX -> RKNN
            if os.path.exists(onnx_path):
                # 进行一次转换（首次较慢�?
                logger.info("[Benchmark] Converting ONNX to RKNN format (first time only)...")
                rknn_obj = RKNN()
                
                # 转换模型
                ret = rknn_obj.load_onnx(onnx_path)
                if ret != 0:
                    result["error"] = f"Failed to load ONNX model: {ret}"
                    return result
                
                ret = rknn_obj.build(do_quantization=True, dataset=None)
                if ret != 0:
                    result["error"] = f"Failed to build RKNN model: {ret}"
                    return result
                
                ret = rknn_obj.export_rknn(rknn_path)
                if ret != 0:
                    result["error"] = f"Failed to export RKNN model: {ret}"
                    return result
                
                logger.info(f"[Benchmark] RKNN model saved to {rknn_path}")
            else:
                result["error"] = f"Model not found. Download {onnx_path} first."
                return result

        # 加载 RKNN 模型
        rknn_obj = RKNN()
        ret = rknn_obj.load_rknn(rknn_path)
        if ret != 0:
            result["error"] = f"Failed to load RKNN model: {ret}"
            return result

        # 初始化运行时
        ret = rknn_obj.init_runtime()
        if ret != 0:
            result["error"] = f"Failed to init runtime: {ret}"
            return result

        # 获取模型输入信息
        model_config = MODEL_CONFIG.get(model_name, MODEL_CONFIG["mobilenetv2"])
        input_shape = model_config["input_shape"]
        input_data = np.random.randn(*input_shape).astype(np.float32)

        # 预热
        for _ in range(warmup):
            rknn_obj.inference([input_data])

        # 正式测试
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            outputs = rknn_obj.inference([input_data])
            end = time.perf_counter()
            latencies.append((end - start) * 1000)

        # 统计
        avg_latency = sum(latencies) / len(latencies)
        throughput = 1000 / avg_latency

        result["latency_ms"] = round(avg_latency, 2)
        result["throughput_fps"] = round(throughput, 1)
        result["latencies_ms"] = [round(l, 2) for l in latencies]
        result["status"] = "success"
        
        # 获取 NPU 信息
        try:
            npu_freq_path = "/sys/class/npu/npu/clk_base_freq"
            if os.path.exists(npu_freq_path):
                with open(npu_freq_path, 'r') as f:
                    freq = int(f.read().strip())
                    result["npu_info"]["freq_mhz"] = round(freq / 1e6, 1)
        except Exception:
            pass

        logger.info(f"[Benchmark] RKNN {model_name}: {result['latency_ms']}ms, {result['throughput_fps']} FPS")

        # 清理
        rknn_obj.release()

    except ImportError:
        result["error"] = "rknn.api not installed. Install rknn-toolkit2 from Rockchip"
    except Exception as e:
        result["error"] = str(e)
        logger.exception(f"[Benchmark] RKNN error: {e}")

    return result


def run_rockchip_benchmark(
    model_name: str = "mobilenetv2",
    warmup: int = 3,
    iterations: int = 10,
) -> Dict[str, Any]:
    """
    Rockchip 设备通用基准测试�?
    
    自动检测可用的推理后端（RKNN / ONNX CPU / ONNX DNNL）�?
    
    Args:
        model_name: 模型名称
        warmup: 预热次数
        iterations: 测试次数
        
    Returns:
        {inference_backend, latency_ms, throughput_fps, status, error}
    """
    result: Dict[str, Any] = {
        "model": model_name,
        "framework": "Rockchip",
        "inference_backend": None,
        "warmup": warmup,
        "iterations": iterations,
        "latency_ms": None,
        "throughput_fps": None,
        "status": "error",
        "error": None,
    }
    
    # 尝试 RKNN (NPU)
    try:
        rknn_result = run_rknn_benchmark(model_name, warmup, iterations)
        if rknn_result["status"] == "success":
            result["inference_backend"] = "RKNN (NPU)"
            result["latency_ms"] = rknn_result["latency_ms"]
            result["throughput_fps"] = rknn_result["throughput_fps"]
            result["status"] = "success"
            result["npu_info"] = rknn_result.get("npu_info", {})
            return result
    except Exception as e:
        logger.info(f"[Benchmark] RKNN not available: {e}")
    
    # 回退�?ONNX CPU
    logger.info("[Benchmark] Falling back to ONNX CPU...")
    onnx_result = run_onnx_benchmark(model_name, warmup, iterations, "CPUExecutionProvider")
    if onnx_result["status"] == "success":
        result["inference_backend"] = "ONNX (CPU)"
        result["latency_ms"] = onnx_result["latency_ms"]
        result["throughput_fps"] = onnx_result["throughput_fps"]
        result["status"] = "success"
        return result
    
    # 回退�?CPU 基准
    logger.info("[Benchmark] Falling back to CPU benchmark...")
    cpu_result = run_heuristic_benchmark()
    if cpu_result["status"] == "success":
        result["inference_backend"] = "CPU"
        result["latency_ms"] = cpu_result["latency_ms"]
        result["throughput_fps"] = cpu_result["throughput_fps"]
        result["status"] = "success"
        return result
    
    result["error"] = "No available inference backend"
    return result
