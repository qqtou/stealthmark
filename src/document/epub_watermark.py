# document/epub_watermark.py
"""
EPUB电子书水印处理器 - OPF元数据嵌入

技术方案:
1. EPUB本质是ZIP+HTML/XML
2. 在content.opf的<metadata>中添加<meta>元素
3. Base64编码存储，不影响阅读内容

依赖: 无特殊依赖 (仅使用标准库)
"""

import os
import zipfile
import shutil
import tempfile
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any
import logging

from ..core.base import (
    BaseHandler, WatermarkData, WatermarkStatus,
    EmbedResult, ExtractResult, VerifyResult
)
from ..core.codec import WatermarkCodec

logger = logging.getLogger(__name__)


class EPUBHandler(BaseHandler):
    """
    EPUB电子书水印处理器
    
    在OPF元数据中嵌入水印。不修改电子书文本内容。
    """
    
    SUPPORTED_EXTENSIONS = ('.epub',)
    HANDLER_NAME = "epub"
    WATERMARK_META_NAME = "SMMark"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
    
    def _find_opf_path(self, zf: zipfile.ZipFile) -> Optional[str]:
        """Find the OPF file path from container.xml"""
        if 'META-INF/container.xml' in zf.namelist():
            with zf.open('META-INF/container.xml') as f:
                container = ET.fromstring(f.read().decode('utf-8'))
            for rootfile in container.iter():
                if rootfile.tag.endswith('}rootfile') or rootfile.tag == 'rootfile':
                    path = rootfile.get('full-path', '')
                    if path:
                        return path
        # Fallback: search for .opf
        for name in zf.namelist():
            if name.endswith('.opf'):
                return name
        return None
    
    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        logger.info(f"EPUB embed: {file_path} -> {output_path}")
        
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result
        
        try:
            encoded_data = self.codec.encode(watermark.content)
            encoded_b64 = self.codec.to_base64(encoded_data)
            
            tmp_dir = tempfile.mkdtemp(prefix='stealthmark_')
            try:
                with zipfile.ZipFile(file_path, 'r') as zf:
                    zf.extractall(tmp_dir)
                
                # Find OPF
                with zipfile.ZipFile(file_path, 'r') as zf:
                    opf_path = self._find_opf_path(zf)
                
                if not opf_path:
                    return EmbedResult(
                        status=WatermarkStatus.FAILED,
                        message="无法找到OPF文件",
                        file_path=file_path
                    )
                
                opf_full = os.path.join(tmp_dir, opf_path)
                
                if not os.path.exists(opf_full):
                    return EmbedResult(
                        status=WatermarkStatus.FAILED,
                        message="OPF文件不存在",
                        file_path=file_path
                    )
                
                # Parse and update OPF
                tree = ET.parse(opf_full)
                root = tree.getroot()
                
                # Find metadata element
                metadata = None
                for elem in root:
                    if elem.tag.endswith('}metadata') or elem.tag == 'metadata':
                        metadata = elem
                        break
                
                if metadata is None:
                    return EmbedResult(
                        status=WatermarkStatus.FAILED,
                        message="OPF缺少metadata元素",
                        file_path=file_path
                    )
                
                # Remove existing SMMark
                to_remove = []
                for child in metadata:
                    if child.tag.endswith('}meta') or child.tag == 'meta':
                        if child.get('name', '') == self.WATERMARK_META_NAME:
                            to_remove.append(child)
                for child in to_remove:
                    metadata.remove(child)
                
                # Add watermark meta
                ns_map = {}
                for prefix, uri in ET.iterparse(opf_full, events=['start-ns']):
                    pass
                # Simple approach: just add meta element
                meta_elem = ET.SubElement(metadata, 'meta')
                meta_elem.set('name', self.WATERMARK_META_NAME)
                meta_elem.set('content', encoded_b64)
                
                tree.write(opf_full, xml_declaration=True, encoding='UTF-8')
                
                # Repack
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    # EPUB requires mimetype be first and uncompressed
                    mimetype_path = os.path.join(tmp_dir, 'mimetype')
                    if os.path.exists(mimetype_path):
                        zf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
                    
                    for root_dir, dirs, files in os.walk(tmp_dir):
                        for file in files:
                            file_full = os.path.join(root_dir, file)
                            arcname = os.path.relpath(file_full, tmp_dir).replace('\\', '/')
                            if arcname == 'mimetype':
                                continue  # Already added
                            zf.write(file_full, arcname)
                
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            
            return self._create_success_result(output_path)
            
        except Exception as e:
            logger.error(f"EPUB embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
                file_path=file_path
            )
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        logger.info(f"EPUB extract: {file_path}")
        
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(status=error_result.status, message=error_result.message, file_path=file_path)
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                opf_path = self._find_opf_path(zf)
                if not opf_path:
                    return ExtractResult(
                        status=WatermarkStatus.EXTRACTION_FAILED,
                        message="无法找到OPF文件",
                        file_path=file_path
                    )
                
                with zf.open(opf_path) as f:
                    content = f.read().decode('utf-8')
                
                root = ET.fromstring(content)
                
                for elem in root.iter():
                    if (elem.tag.endswith('}meta') or elem.tag == 'meta'):
                        if elem.get('name', '') == self.WATERMARK_META_NAME:
                            b64 = elem.get('content', '')
                            if b64:
                                encoded_data = self.codec.from_base64(b64)
                                success, text, details = self.codec.decode(encoded_data)
                                if success:
                                    return ExtractResult(
                                        status=WatermarkStatus.SUCCESS,
                                        message="水印提取成功",
                                        file_path=file_path,
                                        watermark=WatermarkData(content=text)
                                    )
                
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="未找到水印",
                    file_path=file_path
                )
                
        except Exception as e:
            logger.error(f"EPUB extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )
    
    def verify(self, file_path, original_watermark, **kwargs):
        extract_result = self.extract(file_path)
        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(
                status=extract_result.status,
                is_valid=False, is_integrity_ok=False, match_score=0.0
            )
        is_match = extract_result.watermark.content == original_watermark.content
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match, is_integrity_ok=True,
            match_score=1.0 if is_match else 0.0
        )


logger.info(f"{__name__} module loaded - EPUB handler ready")
