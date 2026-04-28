# document/xlsx_watermark.py
"""
Excel表格水印处理器 - 自定义文档属性嵌入

技术方案:
1. XLSX本质是ZIP+XML
2. 在docProps/custom.xml中添加自定义属性 /SMMark
3. Base64编码存储，不影响表格内容

依赖: openpyxl (可选，仅用于验证文件)
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

# Namespaces
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
CUSTOM_NS = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
VT_NS = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"


class XLSXHandler(BaseHandler):
    """
    Excel表格水印处理器
    
    在docProps/custom.xml中嵌入Base64编码水印。
    不修改任何单元格内容。
    """
    
    SUPPORTED_EXTENSIONS = ('.xlsx',)
    HANDLER_NAME = "xlsx"
    WATERMARK_PROP_NAME = "SMMark"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.codec = WatermarkCodec(password=self.config.get('password'))
    
    def embed(self, file_path: str, watermark: WatermarkData,
              output_path: str, **kwargs) -> EmbedResult:
        logger.info(f"XLSX embed: {file_path} -> {output_path}")
        
        error_result = self._validate_file(file_path)
        if error_result:
            return error_result
        
        try:
            encoded_data = self.codec.encode(watermark.content)
            encoded_b64 = self.codec.to_base64(encoded_data)
            
            tmp_dir = tempfile.mkdtemp(prefix='stealthmark_')
            try:
                # Extract ZIP
                with zipfile.ZipFile(file_path, 'r') as zf:
                    zf.extractall(tmp_dir)
                
                # Build/update custom.xml
                custom_xml_path = os.path.join(tmp_dir, 'docProps', 'custom.xml')
                custom_dir = os.path.join(tmp_dir, 'docProps')
                os.makedirs(custom_dir, exist_ok=True)
                
                if os.path.exists(custom_xml_path):
                    tree = ET.parse(custom_xml_path)
                    root = tree.getroot()
                else:
                    root = ET.Element(f'{{{CUSTOM_NS}}}Properties')
                    ET.register_namespace('', CUSTOM_NS)
                    ET.register_namespace('vt', VT_NS)
                
                # Remove existing SMMark property
                to_remove = []
                pid = 1
                for prop in root:
                    name_elem = prop.find(f'{{{CUSTOM_NS}}}name')
                    if name_elem is not None and name_elem.text == self.WATERMARK_PROP_NAME:
                        to_remove.append(prop)
                    else:
                        pid += 1
                for prop in to_remove:
                    root.remove(prop)
                
                # Add SMMark property
                prop_elem = ET.SubElement(root, f'{{{CUSTOM_NS}}}property')
                prop_elem.set('fmtid', '{D5CDD505-2E9C-101B-9397-08002B2CF9AE}')
                prop_elem.set('pid', str(pid))
                prop_elem.set('name', self.WATERMARK_PROP_NAME)
                lpwstr_elem = ET.SubElement(prop_elem, f'{{{VT_NS}}}lpwstr')
                lpwstr_elem.text = encoded_b64
                
                # Write custom.xml
                ET.register_namespace('', CUSTOM_NS)
                ET.register_namespace('vt', VT_NS)
                tree = ET.ElementTree(root)
                ET.indent(tree, space='  ')
                tree.write(custom_xml_path, xml_declaration=True, encoding='UTF-8')
                
                # Update [Content_Types].xml to include custom.xml
                ct_path = os.path.join(tmp_dir, '[Content_Types].xml')
                if os.path.exists(ct_path):
                    ct_tree = ET.parse(ct_path)
                    ct_root = ct_tree.getroot()
                    CT_NS = 'http://schemas.openxmlformats.org/package/2006/content-types'
                    # Check if Override for custom.xml exists
                    has_custom = False
                    for elem in ct_root:
                        if elem.get('PartName') == '/docProps/custom.xml':
                            has_custom = True
                            break
                    if not has_custom:
                        override = ET.SubElement(ct_root, f'{{{CT_NS}}}Override')
                        override.set('PartName', '/docProps/custom.xml')
                        override.set('ContentType', 'application/vnd.openxmlformats-officedocument.spreadsheetml.custom-properties+xml')
                    ct_tree.write(ct_path, xml_declaration=True, encoding='UTF-8')
                
                # Update rels
                rels_path = os.path.join(tmp_dir, 'xl', '_rels', 'workbook.xml.rels')
                if os.path.exists(rels_path):
                    rels_tree = ET.parse(rels_path)
                    rels_root = rels_tree.getroot()
                    RELS_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
                    has_custom_rel = False
                    for elem in rels_root:
                        if elem.get('Target') == '../docProps/custom.xml':
                            has_custom_rel = True
                            break
                    if not has_custom_rel:
                        max_rid = 0
                        for elem in rels_root:
                            rid = elem.get('Id', '')
                            if rid.startswith('rId'):
                                try:
                                    max_rid = max(max_rid, int(rid[3:]))
                                except ValueError:
                                    pass
                        rel = ET.SubElement(rels_root, f'{{{RELS_NS}}}Relationship')
                        rel.set('Id', f'rId{max_rid + 1}')
                        rel.set('Type', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties')
                        rel.set('Target', '../docProps/custom.xml')
                    rels_tree.write(rels_path, xml_declaration=True, encoding='UTF-8')
                
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
            logger.error(f"XLSX embed failed: {e}")
            return EmbedResult(
                status=WatermarkStatus.FAILED,
                message=f"嵌入失败: {str(e)}",
                file_path=file_path
            )
    
    def extract(self, file_path: str, **kwargs) -> ExtractResult:
        logger.info(f"XLSX extract: {file_path}")
        
        error_result = self._validate_file(file_path)
        if error_result:
            return ExtractResult(status=error_result.status, message=error_result.message, file_path=file_path)
        
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                names = zf.namelist()
                
                # Try custom.xml first
                if 'docProps/custom.xml' in names:
                    with zf.open('docProps/custom.xml') as f:
                        content = f.read().decode('utf-8')
                    
                    root = ET.fromstring(content)
                    for prop in root:
                        if prop.get('name', '') == self.WATERMARK_PROP_NAME:
                            lpwstr_elem = prop.find(f'{{{VT_NS}}}lpwstr')
                            if lpwstr_elem is not None and lpwstr_elem.text:
                                encoded_data = self.codec.from_base64(lpwstr_elem.text)
                                success, content, details = self.codec.decode(encoded_data)
                                if success:
                                    return ExtractResult(
                                        status=WatermarkStatus.SUCCESS,
                                        message="水印提取成功",
                                        file_path=file_path,
                                        watermark=WatermarkData(content=content)
                                    )
                
                # Fallback: check core.xml
                if 'docProps/core.xml' in names:
                    with zf.open('docProps/core.xml') as f:
                        content = f.read().decode('utf-8')
                    if 'SMMark' in content:
                        root = ET.fromstring(content)
                        for elem in root:
                            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                            if tag == 'SMMark' and elem.text:
                                encoded_data = self.codec.from_base64(elem.text)
                                success, content, details = self.codec.decode(encoded_data)
                                if success:
                                    return ExtractResult(
                                        status=WatermarkStatus.SUCCESS,
                                        message="水印提取成功",
                                        file_path=file_path,
                                        watermark=WatermarkData(content=content)
                                    )
                
                return ExtractResult(
                    status=WatermarkStatus.EXTRACTION_FAILED,
                    message="未找到水印",
                    file_path=file_path
                )
                
        except Exception as e:
            logger.error(f"XLSX extract failed: {e}")
            return ExtractResult(
                status=WatermarkStatus.EXTRACTION_FAILED,
                message=f"提取失败: {str(e)}",
                file_path=file_path
            )
    
    def verify(self, file_path: str, original_watermark: WatermarkData,
               **kwargs) -> VerifyResult:
        extract_result = self.extract(file_path)
        if not extract_result.is_success or not extract_result.watermark:
            return VerifyResult(
                status=extract_result.status,
                is_valid=False, is_integrity_ok=False, match_score=0.0,
                message=f"提取失败: {extract_result.message}"
            )
        is_match = extract_result.watermark.content == original_watermark.content
        return VerifyResult(
            status=WatermarkStatus.SUCCESS if is_match else WatermarkStatus.VERIFICATION_FAILED,
            is_valid=is_match, is_integrity_ok=True,
            match_score=1.0 if is_match else 0.0
        )


logger.info(f"{__name__} module loaded - XLSX handler ready")
