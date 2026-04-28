# document/odt_watermark.py
"""
OpenDocument格式水印处理器 - 元数据嵌入

支持: ODT(文本文档), ODS(电子表格), ODP(演示文稿)

技术方案:
1. ODF文件本质是ZIP+XML
2. 在meta.xml中添加自定义元数据 <meta:user-defined>
3. Base64编码存储，不影响文档内容

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

META_NS = "urn:oasis:names:tc:opendocument:xmlns:meta:1.0"
OFFICE_NS = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"


class ODHandler(BaseHandler):
    """
    OpenDocument格式水印处理器基类
    
    在meta.xml中嵌入水印，适用于ODT/ODS/ODP。
    """
    
    HANDLER_NAME = "od"
    WATERMARK_META_NAME = "SMMark"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
    
    def _embed_odf(self, file_path: str, watermark: WatermarkData,
                   output_path: str) -> EmbedResult:
        logger.info(f"ODF embed: {file_path} -> {output_path}")
        
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
                
                # Update meta.xml
                meta_path = os.path.join(tmp_dir, 'meta.xml')
                if os.path.exists(meta_path):
                    tree = ET.parse(meta_path)
                    root = tree.getroot()
                else:
                    root = ET.Element(f'{{{OFFICE_NS}}}document-meta')
                    ET.register_namespace('office', OFFICE_NS)
                    ET.register_namespace('meta', META_NS)
                    meta_elem = ET.SubElement(root, f'{{{OFFICE_NS}}}meta')
                
                # Find or create office:meta
                meta_elem = root.find(f'{{{OFFICE_NS}}}meta')
                if meta_elem is None:
                    # Try with different namespace layout
                    for elem in root.iter():
                        if elem.tag.endswith('}meta') or elem.tag == 'meta':
                            meta_elem = elem
                            break
                    if meta_elem is None:
                        meta_elem = ET.SubElement(root, f'{{{OFFICE_NS}}}meta')
                
                # Remove existing SMMark
                to_remove = []
                for child in meta_elem:
                    if child.tag.endswith('}user-defined'):
                        name_attr = child.get(f'{{{META_NS}}}name', child.get('name', ''))
                        if name_attr == self.WATERMARK_META_NAME:
                            to_remove.append(child)
                for child in to_remove:
                    meta_elem.remove(child)
                
                # Add SMMark as user-defined metadata
                user_meta = ET.SubElement(meta_elem, f'{{{META_NS}}}user-defined')
                user_meta.set(f'{{{META_NS}}}name', self.WATERMARK_META_NAME)
                user_meta.set(f'{{{META_NS}}}value-type', 'string')
                user_meta.text = encoded_b64
                
                # Write back meta.xml
                ET.register_namespace('', OFFICE_NS)
                ET.register_namespace('meta', META_NS)
                tree = ET.ElementTree(root) if os.path.exists(meta_path) else ET.ElementTree(root)
                ET.indent(tree, space='  ')
                tree.write(meta_path, xml_declaration=True, encoding='UTF-8')
                
                # Repack ZIP
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for root_dir, dirs, files in os.walk(tmp_dir):
                        for file in files:
                            file_full = os.path.join(root_dir, file)
                            arcname = os.path.relpath(file_full, tmp_dir)
                            zf.write(file_full, arcname)
                
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            
            return self._create_success_result(output_path)
            
        except Exception as e:
            logger.error(f"ODF embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
                file_path=file_path
            )
    
    def _extract_odf(self, file_path: str) -> ExtractResult:
        logger.info(f"ODF extract: {file_path}")
        
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(status=error_result.status, message=error_result.message, file_path=file_path)
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                if 'meta.xml' not in zf.namelist():
                    return ExtractResult(
                        status=WatermarkStatus.EXTRACTION_FAILED,
                        message="未找到meta.xml",
                        file_path=file_path
                    )
                
                with zf.open('meta.xml') as f:
                    content = f.read().decode('utf-8')
                
                root = ET.fromstring(content)
                
                # Search for SMMark in user-defined metadata
                for elem in root.iter():
                    if elem.tag.endswith('}user-defined'):
                        name_attr = elem.get(f'{{{META_NS}}}name', elem.get('name', ''))
                        if name_attr == self.WATERMARK_META_NAME and elem.text:
                            encoded_data = self.codec.from_base64(elem.text)
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
            logger.error(f"ODF extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )
    
    def embed(self, file_path, watermark, output_path, **kwargs):
        return self._embed_odf(file_path, watermark, output_path)
    
    def extract(self, file_path, **kwargs):
        return self._extract_odf(file_path)
    
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


class ODTHandler(ODHandler):
    """OpenDocument文本文档水印处理器"""
    SUPPORTED_EXTENSIONS = ('.odt',)
    HANDLER_NAME = "odt"


class ODSHandler(ODHandler):
    """OpenDocument电子表格水印处理器"""
    SUPPORTED_EXTENSIONS = ('.ods',)
    HANDLER_NAME = "ods"


class ODPHandler(ODHandler):
    """OpenDocument演示文稿水印处理器"""
    SUPPORTED_EXTENSIONS = ('.odp',)
    HANDLER_NAME = "odp"


logger.info(f"{__name__} module loaded - ODF handlers ready")
