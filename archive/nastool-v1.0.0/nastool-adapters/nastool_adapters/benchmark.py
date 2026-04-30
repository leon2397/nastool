# -*- coding: utf-8 -*-
"""
nastool adapters.benchmark - 推理基准测试

支持多框架推理基准：
- ONNX Runtime（通用）
- TensorRT（Jetson）
- ACL（昇腾）
- MindSpore（昇腾）
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("nastool.benchmark")

# 模型配置
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
    ONNX Runtime 推理基准测试。

    Args:
        model_name: 模型名称
        warmup: 预热次数
        iterations: 测试次数
        provider: 执行提供器 (CPUExecutionProvider / CUDAExecutionProvider / DnnlExecutionProvider)

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

        # 检查提供器可用性
        available_providers = ort.get_available_providers()
        if provider not in available_providers:
            result["error"] = f"Provider {provider} not available. Available: {available_providers}"
            result["available_providers"] = available_providers
            return result

        # 加载模型
        model_config = MODEL_CONFIG.get(model_name, MODEL_CONFIG["mobilenetv2"])
        input_shape = model_config["input_shape"]
        input_name = model_config["input_name"]

        # 尝试从缓存加载或下载
        import os

        cache_dir = os.environ.get("NASTOOL_MODEL_CACHE", "/tmp/nastool_models")
        model_path = os.path.join(cache_dir, f"{model_name}.onnx")

        if not os.path.isfile(model_path):
            # 尝试下载
            try:
                import urllib.request

                os.makedirs(cache_dir, exist_ok=True)
                logger.info(f"[Benchmark] Downloading {model_name}...")
                urllib.request.urlretrieve(model_config["model_url"], model_path)
                logger.info(f"[Benchmark] Downloaded to {model_path}")
            except Exception as e:
                result["error"] = f"Failed to download model: {e}"
                return result

        # 创建推理会话
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        session = ort.InferenceSession(model_path, sess_options, providers=[provider])

        # 生成随机输入
        input_data = np.random.randn(*input_shape).astype(np.float32)

        # 预热
        for _ in range(warmup):
            session.run([model_config["output_name"]], {input_name: input_data})

        # 正式测试
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            session.run([model_config["output_name"]], {input_name: input_data})
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # ms

        # 统计
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
    TensorRT 推理基准测试。

    Args:
        model_name: 模型名称
        warmup: 预热次数
        iterations: 测试次数
        engine_path: 预编译的 TensorRT engine 文件路径（可选）

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

        # 查找或创建 engine
        if engine_path is None:
            import os
            cache_dir = os.environ.get("NASTOOL_MODEL_CACHE", "/tmp/nastool_models")
            engine_path = os.path.join(cache_dir, f"{model_name}.trt")

        if not os.path.isfile(engine_path):
            # 需要先从 ONNX 转换
            onnx_path = os.path.join(cache_dir, f"{model_name}.onnx")
            if not os.path.isfile(onnx_path):
                result["error"] = f"ONNX model not found at {onnx_path}, need to download first"
                result["status"] = "todo"
                return result

            # ONNX -> TensorRT 转换
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

        # 加载 engine
        trt_logger = trt.Logger(trt.Logger.WARNING)
        with open(engine_path, "rb") as f:
            runtime = trt.Runtime(trt_logger)
            engine = runtime.deserialize_cuda_engine(f.read())

        context = engine.create_execution_context()

        # 分配显存
        input_name = model_config["input_name"]
        output_name = model_config["output_name"]
        
        input_size = trt.volume(input_shape) * np.dtype(np.float32).itemsize
        d_input = cuda.mem_alloc(input_size)
        
        output_shape = (1, 1000)  # ImageNet 1000 classes
        output_size = trt.volume(output_shape) * np.dtype(np.float32).itemsize
        d_output = cuda.mem_alloc(output_size)

        bindings = [int(d_input), int(d_output)]

        # 准备输入数据
        input_data = np.random.randn(*input_shape).astype(np.float32)
        output_data = np.empty(output_shape, dtype=np.float32)

        # 预热
        for _ in range(warmup):
            cuda.memcpy_htod(d_input, input_data)
            context.execute_v2(bindings)
            cuda.memcpy_dtoh(output_data, d_output)

        # 正式测试
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
    ACL (Ascend Computing Language) 推理基准测试。

    使用 PyACL 接口在昇腾 NPU 上运行推理。

    Args:
        model_name: 模型名称
        warmup: 预热次数
        iterations: 测试次数
        om_path: 预编译的 .om 模型文件路径（可选）

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

        # 查找 .om 模型
        if om_path is None:
            import os
            cache_dir = os.environ.get("NASTOOL_MODEL_CACHE", "/tmp/nastool_models")
            om_path = os.path.join(cache_dir, f"{model_name}.om")

        if not os.path.isfile(om_path):
            result["error"] = f".om model not found at {om_path}. Use ATC to convert ONNX to .om first"
            result["status"] = "todo"
            result["atc_command"] = f"atc --model={model_name}.onnx --framework=5 --output={model_name} --soc_version=Ascend310"
            return result

        # 初始化 ACL
        ret = acl.init()
        if ret != 0:
            result["error"] = f"acl.init() failed: {ret}"
            return result

        try:
            # 加载模型
            model_id, ret = acl.mdl.load_from_file(om_path)
            if ret != 0:
                result["error"] = f"Failed to load model: {ret}"
                return result

            # 获取模型描述
            model_desc = acl.mdl.create_desc()
            ret = acl.mdl.get_desc(model_desc, model_id)
            if ret != 0:
                result["error"] = f"Failed to get model desc: {ret}"
                return result

            # 获取输入输出大小
            input_size = acl.mdl.get_input_size_by_index(model_desc, 0)
            output_size = acl.mdl.get_output_size_by_index(model_desc, 0)

            # 创建输入输出 dataset
            input_dataset = acl.mdl.create_dataset()
            output_dataset = acl.mdl.create_dataset()

            input_data = np.random.randn(*input_shape).astype(np.float32)
            input_buffer, ret = acl.util.ptr_to_bytes(input_data, input_size)
            input_data_buffer = acl.create_data_buffer(input_buffer, input_size)
            acl.mdl.add_dataset_buffer(input_dataset, input_data_buffer)

            output_buffer, ret = acl.util.ptr_to_bytes(np.zeros(output_size, dtype=np.float32), output_size)
            output_data_buffer = acl.create_data_buffer(output_buffer, output_size)
            acl.mdl.add_dataset_buffer(output_dataset, output_data_buffer)

            # 预热
            for _ in range(warmup):
                ret, _ = acl.mdl.execute(model_id, input_dataset, output_dataset)
                if ret != 0:
                    result["error"] = f"Model execute failed: {ret}"
                    return result

            # 正式测试
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

            # 卸载模型
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
    启发式基准测试（无需模型文件）。

    根据 CPU/GPU 型号估算推理性能。
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

        # 启发式估算：MobileNetV2 在不同硬件上的典型性能
        # 基准：Intel i7 @ 3GHz ≈ 50ms, Jetson Nano ≈ 100ms, Orin AGX ≈ 5ms
        if cpu_freq:
            freq_ghz = cpu_freq.current / 1000
            # 简单线性估算
            base_latency = 50.0  # ms @ 3GHz
            estimated_latency = base_latency * (3.0 / freq_ghz) * (8 / cpu_count)
        else:
            # 无法获取频率时，使用核心数估算
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
    MindSpore 推理基准测试。

    Args:
        model_name: 模型名称
        warmup: 预热次数
        iterations: 测试次数
        device_target: 设备目标 (Ascend / GPU / CPU)

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

        # 设置设备
        context.set_context(mode=context.GRAPH_MODE, device_target=device_target)

        model_config = MODEL_CONFIG.get(model_name, MODEL_CONFIG["mobilenetv2"])
        input_shape = model_config["input_shape"]

        # 查找模型文件
        import os
        cache_dir = os.environ.get("NASTOOL_MODEL_CACHE", "/tmp/nastool_models")
        mindir_path = os.path.join(cache_dir, f"{model_name}.mindir")

        if not os.path.isfile(mindir_path):
            # 尝试使用 MindSpore Hub 或内置模型
            result["error"] = f".mindir model not found at {mindir_path}"
            result["status"] = "todo"
            result["hint"] = "Use MindSpore Hub to download pretrained model"
            return result

        # 加载模型
        graph = ms.load(mindir_path)
        model = nn.GraphCell(graph)

        # 准备输入
        input_data = Tensor(np.random.randn(*input_shape).astype(np.float32))

        # 预热
        for _ in range(warmup):
            _ = model(input_data)

        # 正式测试
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
