"""
内存清理工具模块

提供统一的内存清理功能，用于翻译完成后释放模型占用的内存。
特别针对CPU模式进行优化，因为CPU模式下模型权重直接占用RAM。
"""
import gc
import logging

logger = logging.getLogger(__name__)


def cleanup_all_model_caches(unload_models: bool = False) -> int:
    """
    清理所有模块的模型缓存，并可选择显式卸载模型实例
    
    Args:
        unload_models: 是否显式卸载模型实例（默认False）
                      - True: 卸载模型并清理缓存（释放内存更彻底，但下次使用需要重新加载）
                      - False: 只清理缓存字典（保留模型实例，下次使用更快）
    
    Returns:
        清理的缓存数量
    """
    cleanup_count = 0
    
    # 清理翻译器缓存
    try:
        from manga_translator.translators import translator_cache
        if translator_cache:
            if unload_models:
                # 先卸载所有模型实例
                for model_instance in list(translator_cache.values()):
                    try:
                        if hasattr(model_instance, '_unload'):
                            model_instance._unload()
                        elif hasattr(model_instance, 'unload'):
                            model_instance.unload()
                        # 删除模型引用
                        del model_instance
                    except Exception as e:
                        logger.debug(f"卸载翻译器模型时出错: {e}")
            
            cleanup_count += len(translator_cache)
            translator_cache.clear()
    except Exception as e:
        logger.debug(f"清理翻译器缓存时出错: {e}")
    
    # 清理OCR缓存
    try:
        from manga_translator.ocr import ocr_cache
        if ocr_cache:
            if unload_models:
                # 先卸载所有模型实例
                for model_instance in list(ocr_cache.values()):
                    try:
                        if hasattr(model_instance, '_unload'):
                            model_instance._unload()
                        elif hasattr(model_instance, 'unload'):
                            model_instance.unload()
                        del model_instance
                    except Exception as e:
                        logger.debug(f"卸载OCR模型时出错: {e}")
            
            cleanup_count += len(ocr_cache)
            ocr_cache.clear()
    except Exception as e:
        logger.debug(f"清理OCR缓存时出错: {e}")
    
    # 清理检测器缓存
    try:
        from manga_translator.detection import detector_cache
        if detector_cache:
            if unload_models:
                # 先卸载所有模型实例
                for model_instance in list(detector_cache.values()):
                    try:
                        if hasattr(model_instance, '_unload'):
                            model_instance._unload()
                        elif hasattr(model_instance, 'unload'):
                            model_instance.unload()
                        del model_instance
                    except Exception as e:
                        logger.debug(f"卸载检测器模型时出错: {e}")
            
            cleanup_count += len(detector_cache)
            detector_cache.clear()
    except Exception as e:
        logger.debug(f"清理检测器缓存时出错: {e}")
    
    # 清理修复器缓存
    try:
        from manga_translator.inpainting import inpainter_cache
        if inpainter_cache:
            if unload_models:
                # 先卸载所有模型实例
                for model_instance in list(inpainter_cache.values()):
                    try:
                        if hasattr(model_instance, '_unload'):
                            model_instance._unload()
                        elif hasattr(model_instance, 'unload'):
                            model_instance.unload()
                        del model_instance
                    except Exception as e:
                        logger.debug(f"卸载修复器模型时出错: {e}")
            
            cleanup_count += len(inpainter_cache)
            inpainter_cache.clear()
    except Exception as e:
        logger.debug(f"清理修复器缓存时出错: {e}")
    
    # 清理超分缓存
    try:
        from manga_translator.upscaling import upscaler_cache
        if upscaler_cache:
            if unload_models:
                # 先卸载所有模型实例
                for model_instance in list(upscaler_cache.values()):
                    try:
                        if hasattr(model_instance, '_unload'):
                            model_instance._unload()
                        elif hasattr(model_instance, 'unload'):
                            model_instance.unload()
                        del model_instance
                    except Exception as e:
                        logger.debug(f"卸载超分模型时出错: {e}")
            
            cleanup_count += len(upscaler_cache)
            upscaler_cache.clear()
    except Exception as e:
        logger.debug(f"清理超分缓存时出错: {e}")
    
    # 清理着色器缓存
    try:
        from manga_translator.colorization import colorizer_cache
        if colorizer_cache:
            if unload_models:
                # 先卸载所有模型实例
                for model_instance in list(colorizer_cache.values()):
                    try:
                        if hasattr(model_instance, '_unload'):
                            model_instance._unload()
                        elif hasattr(model_instance, 'unload'):
                            model_instance.unload()
                        del model_instance
                    except Exception as e:
                        logger.debug(f"卸载着色器模型时出错: {e}")
            
            cleanup_count += len(colorizer_cache)
            colorizer_cache.clear()
    except Exception as e:
        logger.debug(f"清理着色器缓存时出错: {e}")
    
    return cleanup_count


def cleanup_gpu_memory():
    """
    清理GPU显存和PyTorch内部缓存
    """
    try:
        import torch
        if torch.cuda.is_available():
            # 清空CUDA缓存
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            
            # 清理CUDA内存池
            try:
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.reset_accumulated_memory_stats()
            except Exception:
                pass
            
            # 清理cuDNN缓存
            try:
                torch.backends.cudnn.benchmark = False
                torch.backends.cudnn.deterministic = False
            except Exception:
                pass
            
            return True
    except Exception:
        pass
    return False


def cleanup_physical_memory():
    """
    释放物理内存（Windows特定）
    
    在Windows上调用SetProcessWorkingSetSize强制释放物理内存。
    对CPU模式特别重要。
    """
    try:
        import ctypes
        ctypes.windll.kernel32.SetProcessWorkingSetSize(-1, -1, -1)
        return True
    except Exception:
        pass  # 非Windows系统忽略
    return False


def full_memory_cleanup(log_callback=None, unload_models: bool = False):
    """
    执行完整的内存清理
    
    Args:
        log_callback: 日志回调函数，接收字符串消息（已弃用，保留参数兼容性）
        unload_models: 是否显式卸载模型实例（默认False）
                      - True: 卸载模型并清理缓存（释放内存更彻底，但下次使用需要重新加载）
                      - False: 只清理缓存字典（保留模型实例，下次使用更快）
    
    Returns:
        dict: 包含清理结果的字典
    """
    result = {
        'caches_cleared': 0,
        'gpu_cleared': False,
        'physical_memory_released': False,
        'models_unloaded': unload_models
    }
    
    # 1. 清理模型缓存
    result['caches_cleared'] = cleanup_all_model_caches(unload_models=unload_models)
    
    # 2. 强制垃圾回收（多次执行确保彻底清理）
    gc.collect()
    gc.collect()
    gc.collect()
    
    # 3. 清理GPU显存
    result['gpu_cleared'] = cleanup_gpu_memory()
    
    # 4. 释放物理内存
    result['physical_memory_released'] = cleanup_physical_memory()
    
    return result
